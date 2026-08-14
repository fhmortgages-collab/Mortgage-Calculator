import re
from datetime import datetime, timezone

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="OSFI Stress Test",
    page_icon="🏠",
    layout="wide",
)

OSFI_URL = (
    "https://www.osfi-bsif.gc.ca/en/supervision/financial-institutions/"
    "banks/minimum-qualifying-rate-uninsured-mortgages"
)

DEFAULT_BUFFER = 2.00
DEFAULT_FLOOR = 5.25


def get_osfi_rule():
    result = {
        "buffer": DEFAULT_BUFFER,
        "floor": DEFAULT_FLOOR,
        "status": "Using fallback values",
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "error": None,
    }

    try:
        response = requests.get(
            OSFI_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        response.raise_for_status()

        text = BeautifulSoup(
            response.text,
            "html.parser"
        ).get_text(" ", strip=True).lower()

        text = re.sub(r"\s+", " ", text)

        match = re.search(
            r"greater\s+of\s+the\s+mortgage\s+contract\s+rate\s+plus\s+"
            r"(\d+(?:\.\d+)?)\s*%\s+or\s+(\d+(?:\.\d+)?)\s*%",
            text,
        )

        if match:
            result["buffer"] = float(match.group(1))
            result["floor"] = float(match.group(2))
            result["status"] = "Live OSFI rule verified"
        else:
            result["status"] = "OSFI page reached; fallback values used"

    except requests.RequestException as error:
        result["error"] = str(error)

    return result


def monthly_payment(principal, annual_rate_pct, amortization_years):
    monthly_rate = annual_rate_pct / 100 / 12
    number_of_payments = amortization_years * 12

    if principal <= 0:
        return 0.0

    if monthly_rate == 0:
        return principal / number_of_payments

    return principal * (
        monthly_rate * (1 + monthly_rate) ** number_of_payments
    ) / ((1 + monthly_rate) ** number_of_payments - 1)


osfi = get_osfi_rule()

st.title("🏠 OSFI Uninsured Mortgage Stress Test")
st.caption(
    "This standalone calculator checks the OSFI guideline when the page runs."
)

if osfi["error"]:
    st.warning(
        f"Could not reach OSFI right now. Using fallback rule: "
        f"contract rate + {osfi['buffer']:.2f}% or {osfi['floor']:.2f}%, "
        f"whichever is greater."
    )
else:
    st.success(
        f"{osfi['status']} — checked {osfi['checked_at']}"
    )

st.markdown(
    f"OSFI source: [{OSFI_URL}]({OSFI_URL})"
)

left, right = st.columns(2)

with left:
    property_value = st.number_input(
        "Property value",
        min_value=0.0,
        value=1_000_000.0,
        step=10_000.0,
    )

    down_payment = st.number_input(
        "Down payment",
        min_value=0.0,
        value=250_000.0,
        step=5_000.0,
    )

    contract_rate = st.number_input(
        "Mortgage contract rate (%)",
        min_value=0.0,
        value=4.75,
        step=0.01,
        format="%.2f",
    )

with right:
    amortization_years = st.slider(
        "Amortization period (years)",
        min_value=5,
        max_value=30,
        value=25,
    )

    annual_income = st.number_input(
        "Annual gross household income",
        min_value=0.0,
        value=180_000.0,
        step=5_000.0,
    )

    monthly_debts = st.number_input(
        "Other monthly debt payments",
        min_value=0.0,
        value=0.0,
        step=50.0,
    )

mortgage_amount = max(property_value - down_payment, 0.0)
contract_plus_buffer = contract_rate + osfi["buffer"]
qualifying_rate = max(contract_plus_buffer, osfi["floor"])

contract_payment = monthly_payment(
    mortgage_amount,
    contract_rate,
    amortization_years,
)

qualifying_payment = monthly_payment(
    mortgage_amount,
    qualifying_rate,
    amortization_years,
)

monthly_income = annual_income / 12 if annual_income else 0.0
tds_ratio = (
    ((qualifying_payment + monthly_debts) / monthly_income) * 100
    if monthly_income else 0.0
)

st.divider()
st.subheader("Result")

a, b, c, d = st.columns(4)

a.metric("Mortgage amount", f"${mortgage_amount:,.0f}")
b.metric("Contract payment", f"${contract_payment:,.2f}/month")
c.metric("Qualifying rate", f"{qualifying_rate:.2f}%")
d.metric("Stress-test payment", f"${qualifying_payment:,.2f}/month")

st.metric("Indicative TDS ratio", f"{tds_ratio:.2f}%")

st.info(
    f"Rate applied: greater of {contract_rate:.2f}% + "
    f"{osfi['buffer']:.2f}% = {contract_plus_buffer:.2f}% "
    f"or the OSFI floor of {osfi['floor']:.2f}%."
)

st.caption(
    "Indicative tool only. It does not replace lender underwriting, "
    "income verification, credit review, or institution-specific policy."
)
