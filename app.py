import re
import json
import ast
from datetime import date

import streamlit as st

from downpayment_sources import DOWN_PAYMENT_SOURCES
from income_sources import INCOME_SOURCES
from debt_types import DEBT_TYPES

# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")

GENDER_OPTIONS = ["", "Male", "Female", "Other", "Prefer not to say"]
MARITAL_OPTIONS = ["", "Single", "Married", "Divorced", "Widowed", "Common-Law"]
PROPERTY_TYPES = ["", "Primary Residence", "Secondary Home", "Investment Property", "Cottage / Vacation Home", "Other"]
PROPERTY_STYLE_TYPES = [
    "", "Detached", "Semi-Detached", "Townhouse / Row House", "Condo / Apartment",
    "Duplex", "Triplex / Fourplex", "Mobile / Manufactured Home", "Other",
]
PROPERTY_PURPOSE_OPTIONS = ["", "Owner-Occupied (Primary Residence)", "Second Home", "Investment / Rental Property"]
RURAL_URBAN_OPTIONS = ["", "Urban", "Suburban", "Rural", "Agricultural"]
HEATING_TYPE_OPTIONS = ["", "Forced Air (Natural Gas)", "Forced Air (Electric)", "Baseboard (Electric)", "Heat Pump", "Radiant", "Oil", "Propane", "Other"]
COOLING_OPTIONS = ["", "Central Air Conditioning", "Heat Pump", "Window/Wall Unit(s)", "None"]
SEWER_OPTIONS = ["", "Sanitary Sewer (Municipal)", "Septic System", "Other"]
WATER_OPTIONS = ["", "Municipal Water", "Well", "Other"]
TITLE_TYPE_OPTIONS = ["", "Freehold", "Condominium", "Leasehold", "Other"]

STEPS = ["Client Details", "Down Payment", "Property Details", "Income", "Debts", "Analysis", "Documents", "Notes"]

GDS_LIMIT = 32.0
TDS_LIMIT = 40.0

MORTGAGE_TERM_OPTIONS = ["1 Year", "2 Year", "3 Year", "4 Year", "5 Year"]
RATE_TYPE_OPTIONS = ["Fixed", "Variable"]


def help_contract_rate_text(rate):
    return (
        "This is the actual interest rate the lender charges on this mortgage — it's the number your real "
        "monthly payment is calculated from. It's set by the lender based on the borrower's credit profile, "
        "the product chosen, and current market conditions, and it stays fixed for the length of the term "
        "(unless it's a variable-rate product, in which case it can move with the lender's prime rate). "
        "This is different from the stress-test/benchmark rate elsewhere on this page — that rate is only "
        "used to check affordability on paper and never appears on the borrower's actual statement or "
        "changes what they're billed.\n\n"
        "**Example from this file:** the contract rate entered is **{:.2f}%**. That means this borrower's "
        "real monthly mortgage payment — the Principal + Interest figure shown further down this page — is "
        "calculated using {:.2f}% interest, not the higher stress-test rate the lender also has to check "
        "against.".format(rate, rate)
    )


def help_term_text(term):
    return (
        "The mortgage term is how long the borrower is locked into this specific rate and lender before "
        "having to renew — commonly 1 to 5 years in Canada, though some lenders offer up to 10. It's easy "
        "to confuse with amortization, but they're different things: amortization (usually 25–30 years) is "
        "the full timeline to pay the mortgage down to zero, while the term is just one chapter of that "
        "timeline. When the term ends, the borrower must renew — either with the same lender or by "
        "switching to a new one — and the rate they get at renewal depends on market conditions at that "
        "time, which may be higher or lower than what they have now.\n\n"
        "**Example from this file:** the term selected is **{}**, meaning this rate and lender commitment "
        "lasts {} before the borrower needs to renew — at which point the rate could change even though "
        "the mortgage balance still has years left on its amortization schedule.".format(term, term.lower())
    )


def help_amortization_text(years):
    return (
        "Amortization is the total number of years it will take to pay the mortgage off completely, "
        "assuming payments stay the same the whole time and nothing extra is paid down early. 25 years is "
        "the most common choice in Canada (up to 30 for some first-time buyers or new construction). The "
        "length chosen here directly trades off monthly affordability against total interest paid: a "
        "longer amortization spreads the same loan over more payments, so each one is smaller, but the "
        "lender collects interest for longer, so the total cost of borrowing goes up. A shorter "
        "amortization does the opposite — higher payments now, but the loan is paid off faster and costs "
        "less in interest overall.\n\n"
        "**Example from this file:** amortization is set to **{} years**, so at the current contract rate, "
        "this mortgage is scheduled to be fully paid off in {} years, assuming payments never change and "
        "no lump-sum prepayments are made along the way.".format(years, years)
    )


def help_rate_type_text(rate_type):
    if rate_type == "Fixed":
        detail = "the rate is locked for the whole term, so the payment amount won't change even if market rates move up or down."
    else:
        detail = "the rate moves with the lender's prime rate, so the interest portion of the payment can rise or fall during the term."
    return (
        "Fixed means the interest rate is locked in for the entire term, so the payment amount stays "
        "exactly the same every month, regardless of what happens to interest rates in the broader market. "
        "It offers certainty but usually starts slightly higher than a variable rate. Variable means the "
        "rate is tied to the lender's prime rate and moves when the Bank of Canada changes its policy rate "
        "— when prime goes up, more of the payment goes to interest (and less to principal); when it goes "
        "down, the opposite happens. Some variable products keep the payment amount fixed and just shift "
        "the principal/interest split, while others adjust the payment itself — it depends on the lender's "
        "specific product.\n\n"
        "**Example from this file:** the rate type selected is **" + rate_type + "**, so " + detail
    )


def help_benchmark_text(contract_rate, benchmark_rate, qualifying_rate):
    return (
        "Also called the mortgage 'stress test' rate. Since 2018, Canada's banking regulator (OSFI) has "
        "required federally regulated lenders to confirm a borrower could still afford their payments at a "
        "rate higher than what they're actually being offered — specifically, the greater of the contract "
        "rate plus 2%, or a fixed federal floor (5.25% as of 2026). This exists to build in a safety margin "
        "in case rates rise after closing, or the borrower's circumstances tighten. Critically, the "
        "qualifying rate never appears on the borrower's actual bill — it's purely a math exercise the "
        "lender runs behind the scenes to decide how much they're willing to lend.\n\n"
        "**Example from this file:** contract rate + 2% = **{:.2f}%**, and the benchmark floor entered here "
        "is **{:.2f}%** — since the lender must use whichever of those two numbers is higher, the qualifying "
        "rate actually used for this file's stress test is **{:.2f}%**.".format(
            contract_rate + 2.0, benchmark_rate, qualifying_rate
        )
    )


def help_gds_text(total_income_val, annual_housing_val, gds_val):
    if gds_val is not None:
        file_example = (
            "**Example from this file:** combined gross annual income across all borrowers is **"
            + fmt_money(total_income_val) + "**, and annual housing costs (mortgage principal + interest, "
            "property taxes, heat, and half of any condo fees) come to **" + fmt_money(annual_housing_val)
            + "**. Dividing one by the other: " + fmt_money(annual_housing_val) + " ÷ "
            + fmt_money(total_income_val) + " × 100 = **{:.2f}%**.".format(gds_val)
        )
    else:
        file_example = "**Example from this file:** income hasn't been entered yet, so GDS can't be calculated for this file."
    return (
        "Gross Debt Service ratio: the share of gross (pre-tax) household income that would go toward "
        "housing costs alone — the mortgage payment, property taxes, heating, and half of any condo fees "
        "(the other half is assumed to be a discretionary living cost, not a housing carrying cost). "
        "Lenders typically want this at or under roughly 32%, though insured mortgages can sometimes stretch "
        "to 39%. A lower GDS means more of the household's income is left over after housing is covered, "
        "which lenders read as lower risk.\n\n" + file_example
    )


def help_tds_text(total_income_val, annual_housing_val, annual_other_debt_val, tds_val):
    if tds_val is not None:
        total_debt = annual_housing_val + annual_other_debt_val
        file_example = (
            "**Example from this file:** annual housing costs are **" + fmt_money(annual_housing_val)
            + "**, plus other annual debt payments (car loans, credit cards, other properties, etc.) of **"
            + fmt_money(annual_other_debt_val) + "**, giving total annual debt obligations of **"
            + fmt_money(total_debt) + "**. Dividing by combined gross annual income: " + fmt_money(total_debt)
            + " ÷ " + fmt_money(total_income_val) + " × 100 = **{:.2f}%**.".format(tds_val)
        )
    else:
        file_example = "**Example from this file:** income hasn't been entered yet, so TDS can't be calculated for this file."
    return (
        "Total Debt Service ratio: builds on GDS by adding in every other debt obligation the borrower is "
        "carrying — car loans, credit cards, lines of credit, other properties, student loans, and so on — "
        "on top of the housing costs already counted in GDS. Lenders typically want this at or under "
        "roughly 40%, sometimes up to 44% for insured mortgages. It's possible for a borrower to have a "
        "perfectly healthy GDS but still fail TDS if they're carrying significant debt outside of housing, "
        "which is why lenders check both ratios rather than just one.\n\n" + file_example
    )



def fmt_money(value):
    try:
        return "${:,.0f}".format(value)
    except (TypeError, ValueError):
        return "—"


def parse_money(raw):
    if raw is None:
        return None
    cleaned = str(raw).replace("$", "").replace(",", "").strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_month_year(text):
    """Parses a 'MM/YYYY' string into a date (first of that month). Returns None if invalid/empty."""
    if not text:
        return None
    match = re.match(r"^\s*(\d{1,2})\s*/\s*(\d{4})\s*$", text)
    if not match:
        return None
    month, year = int(match.group(1)), int(match.group(2))
    if month < 1 or month > 12:
        return None
    try:
        return date(year, month, 1)
    except ValueError:
        return None


def months_elapsed_since(start):
    """Whole months between `start` (a date) and today."""
    today = date.today()
    return (today.year - start.year) * 12 + (today.month - start.month)


_CALC_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)
_CALC_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)


def safe_calculate(expression):
    """
    Safely evaluates a basic arithmetic expression (+ - * / ** % parentheses)
    without using eval(). Raises ValueError on anything unsupported.
    """
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BinOp) and isinstance(node.op, _CALC_ALLOWED_BINOPS):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left ** right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, _CALC_ALLOWED_UNARYOPS):
            value = _eval(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Unsupported expression")

    cleaned = expression.replace(",", "").replace("$", "").strip()
    if not cleaned:
        raise ValueError("Empty expression")
    parsed = ast.parse(cleaned, mode="eval")
    return _eval(parsed)


def render_calculator_popover(key_prefix):
    """
    A compact quick-calculator. Rendered in the sidebar rather than as a
    CSS-pinned floating button — Streamlit's internal DOM structure can
    silently break `position: fixed` (ancestor transforms change the
    containing block), so the sidebar is the reliable way to keep this
    visible on screen at all times regardless of scroll position.
    """
    with st.sidebar:
        st.caption("🧮 Calculator (+ − × ÷)")
        expr = st.text_input(
            "Expression", key=key_prefix + "_calc_expr", placeholder="1200 + 350*12",
            label_visibility="collapsed",
        )
        if expr.strip():
            try:
                result = safe_calculate(expr)
                st.markdown("**= " + "{:,.2f}".format(result) + "**")
            except (ValueError, ZeroDivisionError, SyntaxError, TypeError):
                st.caption(":red[Invalid expression]")


def empty_borrower():
    return {
        "full_name": "",
        "dob": None,
        "gender": "",
        "marital_status": "",
        "phone": "",
        "email": "",
        "address": "",
    }


def empty_property():
    return {
        "address": "",
        "prop_type": "",
        "other_type_desc": "",
        "mortgage_payment": "",
        "property_taxes": "",
        "condo_fees": "",
        "heating": "",
    }


def init_state():
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "doc_removed_items" not in st.session_state:
        st.session_state.doc_removed_items = []
    if "doc_edit_mode" not in st.session_state:
        st.session_state.doc_edit_mode = False
    if "broker_notes" not in st.session_state:
        st.session_state.broker_notes = ""
    if "combined_notes" not in st.session_state:
        st.session_state.combined_notes = ""
    if "mortgage_term" not in st.session_state:
        st.session_state.mortgage_term = "5 Year"
    if "rate_type" not in st.session_state:
        st.session_state.rate_type = "Fixed"
    if "borrower_count" not in st.session_state:
        st.session_state.borrower_count = 1
    if "borrowers" not in st.session_state:
        st.session_state.borrowers = [empty_borrower()]
    if "consent" not in st.session_state:
        st.session_state.consent = False
    if "borrower_errors" not in st.session_state:
        st.session_state.borrower_errors = [{}]
    if "purchase_price_raw" not in st.session_state:
        st.session_state.purchase_price_raw = ""
    if "down_payment_raw" not in st.session_state:
        st.session_state.down_payment_raw = ""
    if "selected_sources" not in st.session_state:
        st.session_state.selected_sources = []
    if "source_amounts" not in st.session_state:
        st.session_state.source_amounts = {}
    if "other_source_desc" not in st.session_state:
        st.session_state.other_source_desc = ""
    if "dp_errors" not in st.session_state:
        st.session_state.dp_errors = {}
    if "income_selected" not in st.session_state:
        st.session_state.income_selected = {}
    if "income_amounts" not in st.session_state:
        st.session_state.income_amounts = {}
    if "income_special" not in st.session_state:
        st.session_state.income_special = {}
    if "income_other_desc" not in st.session_state:
        st.session_state.income_other_desc = {}
    if "income_errors" not in st.session_state:
        st.session_state.income_errors = {}
    if "properties" not in st.session_state:
        st.session_state.properties = []
    if "debt_selected" not in st.session_state:
        st.session_state.debt_selected = []
    if "debt_amounts" not in st.session_state:
        st.session_state.debt_amounts = {}
    if "debt_other_desc" not in st.session_state:
        st.session_state.debt_other_desc = ""
    if "debt_errors" not in st.session_state:
        st.session_state.debt_errors = {}
    if "subject_address" not in st.session_state:
        st.session_state.subject_address = ""
    if "subject_taxes_raw" not in st.session_state:
        st.session_state.subject_taxes_raw = ""
    if "subject_condo_raw" not in st.session_state:
        st.session_state.subject_condo_raw = ""
    if "subject_heat_raw" not in st.session_state:
        st.session_state.subject_heat_raw = ""
    if "contract_rate" not in st.session_state:
        st.session_state.contract_rate = 5.0
    if "amortization_years" not in st.session_state:
        st.session_state.amortization_years = 25
    if "benchmark_rate" not in st.session_state:
        st.session_state.benchmark_rate = 5.25
    if "subject_prop_purpose" not in st.session_state:
        st.session_state.subject_prop_purpose = ""
    if "subject_prop_type" not in st.session_state:
        st.session_state.subject_prop_type = ""
    if "subject_prop_age" not in st.session_state:
        st.session_state.subject_prop_age = ""
    if "subject_garage" not in st.session_state:
        st.session_state.subject_garage = ""
    if "subject_rural_urban" not in st.session_state:
        st.session_state.subject_rural_urban = ""
    if "subject_sqft" not in st.session_state:
        st.session_state.subject_sqft = ""
    if "subject_storeys" not in st.session_state:
        st.session_state.subject_storeys = ""
    if "subject_heating_type" not in st.session_state:
        st.session_state.subject_heating_type = ""
    if "subject_cooling" not in st.session_state:
        st.session_state.subject_cooling = ""
    if "subject_foundation" not in st.session_state:
        st.session_state.subject_foundation = ""
    if "subject_exterior_finish" not in st.session_state:
        st.session_state.subject_exterior_finish = ""
    if "subject_sewer" not in st.session_state:
        st.session_state.subject_sewer = ""
    if "subject_water" not in st.session_state:
        st.session_state.subject_water = ""
    if "subject_parking_spaces" not in st.session_state:
        st.session_state.subject_parking_spaces = ""
    if "subject_land_size" not in st.session_state:
        st.session_state.subject_land_size = ""
    if "subject_title_type" not in st.session_state:
        st.session_state.subject_title_type = ""


SAVE_STATE_KEYS = [
    "step", "borrower_count", "borrowers", "consent", "borrower_errors",
    "purchase_price_raw", "down_payment_raw", "selected_sources", "source_amounts",
    "other_source_desc", "dp_errors",
    "income_selected", "income_amounts", "income_special", "income_other_desc", "income_errors",
    "properties", "debt_selected", "debt_amounts", "debt_other_desc", "debt_errors",
    "subject_address", "subject_taxes_raw", "subject_condo_raw", "subject_heat_raw",
    "subject_prop_type", "subject_prop_purpose", "subject_prop_age", "subject_garage",
    "subject_rural_urban", "subject_sqft", "subject_storeys", "subject_heating_type",
    "subject_cooling", "subject_foundation", "subject_exterior_finish", "subject_sewer",
    "subject_water", "subject_parking_spaces", "subject_land_size", "subject_title_type",
    "contract_rate", "amortization_years", "benchmark_rate", "doc_removed_items",
    "broker_notes", "combined_notes", "mortgage_term", "rate_type",
]


def serialize_application():
    """Builds a JSON-safe dict of the entire application for download."""
    data = {}
    for key in SAVE_STATE_KEYS:
        value = st.session_state.get(key)
        data[key] = value
    # borrowers contains date objects (dob) which aren't natively JSON-serializable
    borrowers_out = []
    for b in data.get("borrowers", []):
        b_copy = dict(b)
        if isinstance(b_copy.get("dob"), date):
            b_copy["dob"] = b_copy["dob"].isoformat()
        borrowers_out.append(b_copy)
    data["borrowers"] = borrowers_out
    return json.dumps(data, indent=2)


def load_application(json_text):
    """Restores session_state from a previously downloaded application JSON. Returns (success, message)."""
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return False, "That file doesn't look like a valid application JSON file."

    if not isinstance(data, dict) or "borrowers" not in data:
        return False, "That file doesn't look like a mortgage application save file."

    for key in SAVE_STATE_KEYS:
        if key not in data:
            continue
        value = data[key]
        if key == "borrowers":
            restored = []
            for b in value:
                b_copy = dict(b)
                dob_raw = b_copy.get("dob")
                if isinstance(dob_raw, str) and dob_raw:
                    try:
                        b_copy["dob"] = date.fromisoformat(dob_raw)
                    except ValueError:
                        b_copy["dob"] = None
                restored.append(b_copy)
            st.session_state[key] = restored
        else:
            st.session_state[key] = value
    return True, "Application loaded successfully."


def refresh_all():
    st.session_state.step = 0
    st.session_state.doc_removed_items = []
    st.session_state.doc_edit_mode = False
    st.session_state.broker_notes = ""
    st.session_state.combined_notes = ""
    st.session_state.mortgage_term = "5 Year"
    st.session_state.rate_type = "Fixed"
    st.session_state.borrower_count = 1
    st.session_state.borrowers = [empty_borrower()]
    st.session_state.borrower_errors = [{}]
    st.session_state.consent = False
    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.selected_sources = []
    st.session_state.source_amounts = {}
    st.session_state.other_source_desc = ""
    st.session_state.dp_errors = {}
    st.session_state.income_selected = {}
    st.session_state.income_amounts = {}
    st.session_state.income_special = {}
    st.session_state.income_other_desc = {}
    st.session_state.income_errors = {}
    st.session_state.properties = []
    st.session_state.debt_selected = []
    st.session_state.debt_amounts = {}
    st.session_state.debt_other_desc = ""
    st.session_state.debt_errors = {}
    st.session_state.subject_address = ""
    st.session_state.subject_taxes_raw = ""
    st.session_state.subject_condo_raw = ""
    st.session_state.subject_heat_raw = ""
    st.session_state.subject_prop_type = ""
    st.session_state.subject_prop_purpose = ""
    st.session_state.subject_prop_age = ""
    st.session_state.subject_garage = ""
    st.session_state.subject_rural_urban = ""
    st.session_state.subject_sqft = ""
    st.session_state.subject_storeys = ""
    st.session_state.subject_heating_type = ""
    st.session_state.subject_cooling = ""
    st.session_state.subject_foundation = ""
    st.session_state.subject_exterior_finish = ""
    st.session_state.subject_sewer = ""
    st.session_state.subject_water = ""
    st.session_state.subject_parking_spaces = ""
    st.session_state.subject_land_size = ""
    st.session_state.subject_title_type = ""
    st.session_state.contract_rate = 5.0
    st.session_state.amortization_years = 25
    st.session_state.benchmark_rate = 5.25


def render_stepper(active_index):
    with st.container(key="stepper_row"):
        cols = st.columns(len(STEPS), gap="small")
        for i, label in enumerate(STEPS):
            btn_type = "primary" if i == active_index else "secondary"
            with cols[i]:
                with st.container(key="stepbtn_" + str(i)):
                    if st.button(label, key="nav_step_" + str(i), type=btn_type, use_container_width=True):
                        st.session_state.step = i
                        st.rerun()




st.set_page_config(page_title="FH.Mortgage Calculator", page_icon="🏠", layout="centered")

st.markdown(
    """
    <style>
    div[class*="st-key-notes_font_scope"],
    div[class*="st-key-notes_font_scope"] p,
    div[class*="st-key-notes_font_scope"] span,
    div[class*="st-key-notes_font_scope"] li,
    div[class*="st-key-notes_font_scope"] textarea {
        font-family: "Times New Roman", Times, serif !important;
        font-size: 11pt !important;
        font-weight: 400 !important;
    }
    div[class*="st-key-notes_font_scope"] b,
    div[class*="st-key-notes_font_scope"] strong {
        font-weight: 400 !important;
    }
    div[class*="st-key-stepper_row"] div[data-testid="column"] {
        min-width: 0 !important;
        flex: 1 1 0 !important;
    }
    div[class*="st-key-stepper_row"] button {
        font-size: 12px !important;
        white-space: normal !important;
        word-break: keep-all !important;
        padding: 4px 2px !important;
        letter-spacing: -0.1px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    div[class*="st-key-stepbtn_3"] button,
    div[class*="st-key-stepbtn_4"] button,
    div[class*="st-key-stepbtn_5"] button,
    div[class*="st-key-stepbtn_6"] button,
    div[class*="st-key-stepbtn_7"] button {
        white-space: nowrap !important;
    }
    div[class*="st-key-fieldrow_"] div[data-testid="stHorizontalBlock"] {
        align-items: flex-end !important;
    }
    div[class*="st-key-helpbtn_"] {
        display: flex;
        justify-content: center;
        margin-bottom: 2px;
    }
    div[class*="st-key-helpbtn_"] button {
        min-height: 1.4em !important;
        height: 1.4em !important;
        width: 1.4em !important;
        min-width: 1.4em !important;
        padding: 0 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[class*="st-key-helpbtn_"] svg,
    div[class*="st-key-helpbtn_"] button svg,
    div[class*="st-key-helpbtn_"] [data-testid="stIconMaterial"],
    div[class*="st-key-helpbtn_"] [data-testid*="Icon"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzone"] small {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background-color: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0 !important;
        min-height: 0 !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        width: 100% !important;
        min-height: 3.4em !important;
        border-radius: 8px !important;
    }
    .stButton > button {
        min-height: 3.4em;
        white-space: normal;
        line-height: 1.2;
        font-size: 13px;
        padding: 4px 8px;
    }
    .stepper-wrap {display:flex; justify-content:space-between; margin-bottom: 1.5rem;}
    .step {text-align:center; flex:1; font-size:13px; color:#9ca3af;}
    .step-active {color:#111827; font-weight:600;}
    .step-circle {
        width:32px; height:32px; border-radius:50%; background:#e5e7eb; color:#6b7280;
        display:inline-flex; align-items:center; justify-content:center; font-weight:600; margin-bottom:4px;
    }
    .step-circle-active {background:#2563eb; color:#fff;}
    .consent-box, .calc-box {
        border-top: 1px solid #e5e7eb; padding-top: 1.2rem; margin-top: 0.5rem;
        font-size: 13px; color: #6b7280; line-height:1.6;
    }
    .doc-list {
        background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px;
        padding: 10px 14px; margin-top: 6px; font-size: 13px; color:#374151;
    }
    .metric-row {display:flex; gap: 16px; margin: 10px 0 4px; align-items: stretch;}
    .metric-card {
        flex:1; border:1px solid #e5e7eb; border-radius:10px; padding: 14px 16px; background:#f9fafb;
        min-height: 78px; box-sizing: border-box; display:flex; flex-direction:column; justify-content:center;
    }
    .metric-label {font-size:12px; color:#6b7280; margin-bottom:4px;}
    .metric-value {font-size:20px; font-weight:700; color:#111827; word-break:break-word;}
    .borrower-total {
        font-weight:600; font-size:15px; margin: 10px 0 4px; color:#111827;
    }
    .ratio-green {color:#16a34a; font-weight:700;}
    .ratio-yellow {color:#ca8a04; font-weight:700;}
    .ratio-red {color:#dc2626; font-weight:700;}
    .property-total {
        font-weight:600; font-size:14px; margin: 8px 0 4px; color:#111827;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_state()

st.markdown("## 🏠 FH.Mortgage Calculator")
st.caption("Residential Mortgage Application")

render_stepper(st.session_state.step)

with st.sidebar:
    st.download_button(
        "⬇️ Download", data=serialize_application(), file_name="mortgage_application.json",
        mime="application/json", use_container_width=True,
    )
    uploaded = st.file_uploader("Upload", type=["json"], key="load_app_uploader", label_visibility="collapsed")
    if uploaded is not None:
        if st.button("📂 Load this file", use_container_width=True, key="load_app_confirm"):
            success, message = load_application(uploaded.read().decode("utf-8"))
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    if st.button("🔄 Refresh", use_container_width=True, key="sidebar_refresh"):
        st.session_state["sidebar_show_refresh_confirm"] = True
    if st.session_state.get("sidebar_show_refresh_confirm"):
        st.warning("Clear all data? Cannot be undone.")
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("Confirm", type="primary", use_container_width=True, key="sidebar_confirm_refresh"):
                refresh_all()
                st.session_state["sidebar_show_refresh_confirm"] = False
                st.rerun()
        with rc2:
            if st.button("Cancel", use_container_width=True, key="sidebar_cancel_refresh"):
                st.session_state["sidebar_show_refresh_confirm"] = False
                st.rerun()


# ---------------------------------------------------------------------------
# STEP 0 — Client Details
# ---------------------------------------------------------------------------

def validate_borrower(b):
    errors = {}
    if not b["full_name"].strip():
        errors["full_name"] = "Full name is required."
    if not b["dob"]:
        errors["dob"] = "Date of birth is required."
    elif b["dob"] > date.today():
        errors["dob"] = "Date of birth cannot be in the future."
    if not b["gender"]:
        errors["gender"] = "Please select an option."
    if not b["marital_status"]:
        errors["marital_status"] = "Please select an option."
    if not b["phone"].strip():
        errors["phone"] = "Phone number is required."
    elif not PHONE_RE.match(b["phone"].strip()):
        errors["phone"] = "Enter a valid 10-digit phone number."
    if not b["email"].strip():
        errors["email"] = "Email is required."
    elif not EMAIL_RE.match(b["email"].strip()):
        errors["email"] = "Enter a valid email address."
    if not b["address"].strip():
        errors["address"] = "Current address is required."
    return errors


def sync_borrower_count(new_count):
    borrowers = st.session_state.borrowers
    if new_count > len(borrowers):
        borrowers.extend(empty_borrower() for _ in range(new_count - len(borrowers)))
    else:
        del borrowers[new_count:]
    st.session_state.borrowers = borrowers
    st.session_state.borrower_count = new_count

    errors = st.session_state.borrower_errors
    if new_count > len(errors):
        errors.extend({} for _ in range(new_count - len(errors)))
    else:
        del errors[new_count:]
    st.session_state.borrower_errors = errors


def refresh_page1():
    st.session_state.borrower_count = 1
    st.session_state.borrowers = [empty_borrower()]
    st.session_state.borrower_errors = [{}]
    st.session_state.consent = False


def render_client_details():
    spacer, back_col, continue_col = st.columns([3, 1, 1])

    with back_col:
        if st.button("← Back", use_container_width=True, key="p1_back_top"):
            st.info("This is the first screen.")
    with continue_col:
        continue_top = st.button("Continue →", type="primary", use_container_width=True, key="p1_continue_top")

    st.markdown("### Client Details")
    st.write("Enter information for each borrower on this application.")
    render_calculator_popover("client")

    st.write("**Number of Borrowers**")
    cols = st.columns(4)
    for i, n in enumerate([1, 2, 3, 4]):
        btn_type = "primary" if st.session_state.borrower_count == n else "secondary"
        if cols[i].button(str(n), key="count_" + str(n), type=btn_type, use_container_width=True):
            sync_borrower_count(n)
            st.rerun()

    st.divider()

    for idx in range(st.session_state.borrower_count):
        borrower = st.session_state.borrowers[idx]
        errors = st.session_state.borrower_errors[idx] if idx < len(st.session_state.borrower_errors) else {}

        with st.expander("Borrower " + str(idx + 1), expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                borrower["full_name"] = st.text_input(
                    "Full Name", value=borrower["full_name"], placeholder="Jane Smith", key="name_" + str(idx)
                )
                if errors.get("full_name"):
                    st.caption(":red[" + errors["full_name"] + "]")

                borrower["phone"] = st.text_input(
                    "Phone Number", value=borrower["phone"], placeholder="(416) 555-0100", key="phone_" + str(idx)
                )
                if errors.get("phone"):
                    st.caption(":red[" + errors["phone"] + "]")

                borrower["gender"] = st.selectbox(
                    "Gender", GENDER_OPTIONS,
                    index=GENDER_OPTIONS.index(borrower["gender"]) if borrower["gender"] in GENDER_OPTIONS else 0,
                    key="gender_" + str(idx),
                )
                if errors.get("gender"):
                    st.caption(":red[" + errors["gender"] + "]")

            with col2:
                borrower["email"] = st.text_input(
                    "Email Address", value=borrower["email"], placeholder="jane@example.com", key="email_" + str(idx)
                )
                if errors.get("email"):
                    st.caption(":red[" + errors["email"] + "]")

                borrower["dob"] = st.date_input(
                    "Date of Birth",
                    value=borrower["dob"] or date(1990, 1, 1),
                    min_value=date(1900, 1, 1),
                    max_value=date.today(),
                    key="dob_" + str(idx),
                )
                if errors.get("dob"):
                    st.caption(":red[" + errors["dob"] + "]")

                borrower["marital_status"] = st.selectbox(
                    "Marital Status", MARITAL_OPTIONS,
                    index=MARITAL_OPTIONS.index(borrower["marital_status"]) if borrower["marital_status"] in MARITAL_OPTIONS else 0,
                    key="marital_" + str(idx),
                )
                if errors.get("marital_status"):
                    st.caption(":red[" + errors["marital_status"] + "]")

            borrower["address"] = st.text_area(
                "Current Address", value=borrower["address"], placeholder="123 Main St, Toronto, ON M5V 1A1",
                key="address_" + str(idx), height=80,
            )
            if errors.get("address"):
                st.caption(":red[" + errors["address"] + "]")

        st.session_state.borrowers[idx] = borrower

    st.markdown(
        """
        <div class="consent-box">
        <b>Consent</b><br><br>
        By proceeding, you acknowledge and consent to the collection, use, and disclosure
        of your personal information for the purpose of processing this application.
        Your information will be kept confidential and used solely for this purpose.
        You have the right to access and correct your personal information at any time.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.consent = st.checkbox(
        "I acknowledge and consent to the above terms", value=st.session_state.consent
    )
    consent_error_slot = st.empty()

    st.divider()

    if st.button("🔄 Refresh Page", use_container_width=False, key="p1_refresh"):
        st.session_state["p1_show_refresh_confirm"] = True

    if st.session_state.get("p1_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p1_confirm_refresh"):
                refresh_page1()
                st.session_state["p1_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p1_cancel_refresh"):
                st.session_state["p1_show_refresh_confirm"] = False
                st.rerun()

    # Handle Continue button from top
    if continue_top:
        all_errors = [validate_borrower(b) for b in st.session_state.borrowers]
        st.session_state.borrower_errors = all_errors
        is_valid = all(len(e) == 0 for e in all_errors)

        if not st.session_state.consent:
            consent_error_slot.markdown(":red[You must acknowledge and consent before continuing.]")

        if is_valid and st.session_state.consent:
            st.session_state.step = 1
            st.rerun()
        else:
            st.rerun()


# ---------------------------------------------------------------------------
# STEP 1 — Down Payment
# ---------------------------------------------------------------------------

def refresh_page2():
    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.selected_sources = []
    st.session_state.source_amounts = {}
    st.session_state.other_source_desc = ""
    st.session_state.dp_errors = {}


def render_down_payment():
    spacer, back_col, continue_col = st.columns([3, 1, 1])

    with back_col:
        if st.button("← Back", use_container_width=True, key="p2_back_top"):
            st.session_state.step = 0
            st.rerun()
    with continue_col:
        continue_top = st.button("Continue →", type="primary", use_container_width=True, key="p2_continue_top")

    st.markdown("### Down Payment")
    st.write("Enter property price, down payment, and the sources funding it.")
    render_calculator_popover("downpayment")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.purchase_price_raw = st.text_input(
            "Purchase Price ($)", value=st.session_state.purchase_price_raw, placeholder="e.g., 500,000"
        )
    with col2:
        st.session_state.down_payment_raw = st.text_input(
            "Down Payment Amount ($)", value=st.session_state.down_payment_raw, placeholder="e.g., 100,000"
        )

    purchase_price = parse_money(st.session_state.purchase_price_raw)
    down_payment = parse_money(st.session_state.down_payment_raw)

    price_error = None
    dp_error = None
    if st.session_state.purchase_price_raw.strip() and purchase_price is None:
        price_error = "Enter a valid number."
    elif purchase_price is not None and purchase_price <= 0:
        price_error = "Purchase price must be greater than zero."

    if st.session_state.down_payment_raw.strip() and down_payment is None:
        dp_error = "Enter a valid number."
    elif down_payment is not None and down_payment < 0:
        dp_error = "Down payment cannot be negative."
    elif purchase_price is not None and down_payment is not None and down_payment > purchase_price:
        dp_error = "Down payment cannot exceed the purchase price."

    if price_error:
        st.caption(":red[" + price_error + "]")
    if dp_error:
        st.caption(":red[" + dp_error + "]")

    if purchase_price and down_payment is not None and not price_error and not dp_error:
        loan_amount = purchase_price - down_payment
        ltv = (loan_amount / purchase_price) * 100
        loan_display = fmt_money(loan_amount)
        ltv_display = "{:.2f}%".format(ltv)
    else:
        loan_display = "—"
        ltv_display = "—"

    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-card'><div class='metric-label'>Mortgage Loan Amount</div>"
        "<div class='metric-value'>" + loan_display + "</div></div>"
        "<div class='metric-card'><div class='metric-label'>LTV Ratio</div>"
        "<div class='metric-value'>" + ltv_display + "</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    st.write("**Select Down Payment Sources**")

    selected = st.session_state.selected_sources
    for source in DOWN_PAYMENT_SOURCES:
        checked = source["key"] in selected
        new_checked = st.checkbox(source["label"], value=checked, key="src_" + source["key"])

        if new_checked and source["key"] not in selected:
            selected.append(source["key"])
        elif not new_checked and source["key"] in selected:
            selected.remove(source["key"])
            st.session_state.source_amounts.pop(source["key"], None)

        if new_checked:
            if not source["eligible"]:
                st.markdown(
                    "<div class='doc-list'>⚠️ " + source["notes"] + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                amount_raw = st.text_input(
                    source["label"] + " Amount ($)",
                    value=st.session_state.source_amounts.get(source["key"], ""),
                    placeholder="Enter amount",
                    key="amt_" + source["key"],
                )
                st.session_state.source_amounts[source["key"]] = amount_raw

                if source["key"] == "other":
                    st.session_state.other_source_desc = st.text_input(
                        "Describe the other source",
                        value=st.session_state.other_source_desc,
                        key="other_source_desc_input",
                    )

                docs_html = ""
                for d in source["documents"]:
                    docs_html += "<li>" + d + "</li>"
                notes_html = "<div style='margin-top:6px;'>" + source["notes"] + "</div>" if source["notes"] else ""
                st.markdown(
                    "<div class='doc-list'><b>Required Documentation</b>"
                    "<ul style='margin:6px 0 0 18px;'>" + docs_html + "</ul>" + notes_html + "</div>",
                    unsafe_allow_html=True,
                )

    st.session_state.selected_sources = selected

    st.divider()

    eligible_selected = []
    for s in selected:
        for src in DOWN_PAYMENT_SOURCES:
            if src["key"] == s and src["eligible"]:
                eligible_selected.append(s)

    total_sources = 0.0
    for key in eligible_selected:
        amt = parse_money(st.session_state.source_amounts.get(key, ""))
        total_sources += amt or 0.0

    st.write("**Total from Sources: " + fmt_money(total_sources) + "**")

    totals_match = False
    if not selected:
        st.caption(":red[Please select at least one source.]")
    elif down_payment is None:
        st.caption(":gray[Enter a down payment amount above to check totals.]")
    else:
        if round(total_sources, 2) == round(down_payment, 2):
            st.success("✓ Source amounts match the down payment amount.")
            totals_match = True
        else:
            st.error(
                "✗ The total down payment amount (" + fmt_money(down_payment) + ") does not match "
                "the sum of the sources (" + fmt_money(total_sources) + "). Please adjust your entries."
            )

    st.divider()

    if st.button("🔄 Refresh Page", use_container_width=False, key="p2_refresh"):
        st.session_state["p2_show_refresh_confirm"] = True

    if st.session_state.get("p2_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p2_confirm_refresh"):
                refresh_page2()
                st.session_state["p2_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p2_cancel_refresh"):
                st.session_state["p2_show_refresh_confirm"] = False
                st.rerun()

    if continue_top:
        valid = (
            purchase_price is not None and purchase_price > 0 and not price_error
            and down_payment is not None and not dp_error
            and len(selected) > 0
            and totals_match
        )
        if valid:
            st.session_state.step = 2
            st.rerun()
        else:
            st.error("Please resolve the issues above before continuing.")


# ---------------------------------------------------------------------------
# STEP 2 — Property Details (subject property being purchased)
# ---------------------------------------------------------------------------

def monthly_mortgage_payment(principal, annual_rate_percent, amortization_years):
    """
    Canadian mortgages are compounded semi-annually by law (Interest Act),
    not monthly. This converts the nominal annual rate to an equivalent
    monthly rate before applying the standard annuity formula.
    """
    if principal <= 0 or amortization_years <= 0:
        return 0.0
    n = amortization_years * 12
    if annual_rate_percent == 0:
        return principal / n
    i_semi_annual = (annual_rate_percent / 100.0) / 2.0
    i_monthly = (1 + i_semi_annual) ** (2.0 / 12.0) - 1
    return principal * i_monthly / (1 - (1 + i_monthly) ** (-n))


def refresh_property_details():
    st.session_state.subject_address = ""
    st.session_state.subject_taxes_raw = ""
    st.session_state.subject_condo_raw = ""
    st.session_state.subject_heat_raw = ""
    st.session_state.subject_prop_type = ""
    st.session_state.subject_prop_purpose = ""
    st.session_state.subject_prop_age = ""
    st.session_state.subject_garage = ""
    st.session_state.subject_rural_urban = ""
    st.session_state.subject_sqft = ""
    st.session_state.subject_storeys = ""
    st.session_state.subject_heating_type = ""
    st.session_state.subject_cooling = ""
    st.session_state.subject_foundation = ""
    st.session_state.subject_exterior_finish = ""
    st.session_state.subject_sewer = ""
    st.session_state.subject_water = ""
    st.session_state.subject_parking_spaces = ""
    st.session_state.subject_land_size = ""
    st.session_state.subject_title_type = ""


def get_subject_property_costs():
    """Returns (pi_payment, taxes, condo, heat, monthly_housing_total) for the property being purchased."""
    purchase_price = parse_money(st.session_state.purchase_price_raw) or 0.0
    down_payment = parse_money(st.session_state.down_payment_raw) or 0.0
    loan_amount = max(purchase_price - down_payment, 0.0)
    pi = monthly_mortgage_payment(loan_amount, st.session_state.contract_rate, st.session_state.amortization_years)
    taxes = parse_money(st.session_state.subject_taxes_raw) or 0.0
    condo = parse_money(st.session_state.subject_condo_raw) or 0.0
    heat = parse_money(st.session_state.subject_heat_raw) or 0.0
    housing_total = pi + taxes + heat + condo
    return pi, taxes, condo, heat, housing_total


def render_property_details():
    spacer, back_col, continue_col = st.columns([3, 1, 1])

    with back_col:
        if st.button("← Back", use_container_width=True, key="p3_back_top"):
            st.session_state.step = 1
            st.rerun()
    with continue_col:
        continue_top = st.button("Continue →", type="primary", use_container_width=True, key="p3_continue_top")

    st.markdown("### Property Details")
    st.write("Tell us about the property you're purchasing — this feeds directly into your GDS/TDS calculation.")
    render_calculator_popover("property")

    purchase_price = parse_money(st.session_state.purchase_price_raw) or 0.0
    down_payment = parse_money(st.session_state.down_payment_raw) or 0.0
    loan_amount = max(purchase_price - down_payment, 0.0)

    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-card'><div class='metric-label'>Purchase Price (from Down Payment step)</div>"
        "<div class='metric-value'>" + fmt_money(purchase_price) + "</div></div>"
        "<div class='metric-card'><div class='metric-label'>Mortgage Loan Amount</div>"
        "<div class='metric-value'>" + fmt_money(loan_amount) + "</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("To change the purchase price or down payment, go back to the Down Payment step.")

    st.divider()

    st.session_state.subject_address = st.text_area(
        "Property Address", value=st.session_state.subject_address,
        placeholder="Enter the full address of the property you're purchasing", height=70,
    )
    if not st.session_state.subject_address.strip():
        st.caption(":red[Please enter the property address.]")

    st.caption(
        "Financing terms (contract rate, amortization) are now collected on the Analysis "
        "step, alongside the stress test."
    )

    st.write("**Property Characteristics**")
    st.caption(
        "Best-effort is fine here — the client may only have what's on the MLS listing "
        "or heard secondhand, not a formal appraisal. Leave anything unknown blank."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.subject_prop_purpose = st.selectbox(
            "Property Purpose", PROPERTY_PURPOSE_OPTIONS,
            index=PROPERTY_PURPOSE_OPTIONS.index(st.session_state.subject_prop_purpose)
            if st.session_state.subject_prop_purpose in PROPERTY_PURPOSE_OPTIONS else 0,
        )
        st.session_state.subject_title_type = st.selectbox(
            "Title", TITLE_TYPE_OPTIONS,
            index=TITLE_TYPE_OPTIONS.index(st.session_state.subject_title_type)
            if st.session_state.subject_title_type in TITLE_TYPE_OPTIONS else 0,
        )
        st.session_state.subject_sqft = st.text_input(
            "Square Footage", value=st.session_state.subject_sqft, placeholder="e.g. 1,850",
        )
        st.session_state.subject_storeys = st.text_input(
            "Number of Storeys", value=st.session_state.subject_storeys, placeholder="e.g. 2",
        )
        st.session_state.subject_parking_spaces = st.text_input(
            "Total Parking Spaces", value=st.session_state.subject_parking_spaces, placeholder="e.g. 4",
        )
        st.session_state.subject_cooling = st.selectbox(
            "Cooling", COOLING_OPTIONS,
            index=COOLING_OPTIONS.index(st.session_state.subject_cooling)
            if st.session_state.subject_cooling in COOLING_OPTIONS else 0,
        )
        st.session_state.subject_exterior_finish = st.text_input(
            "Exterior Finish", value=st.session_state.subject_exterior_finish,
            placeholder="e.g. Brick, Stone, Vinyl Siding",
        )
        st.session_state.subject_water = st.selectbox(
            "Water", WATER_OPTIONS,
            index=WATER_OPTIONS.index(st.session_state.subject_water)
            if st.session_state.subject_water in WATER_OPTIONS else 0,
        )
    with c2:
        st.session_state.subject_prop_type = st.selectbox(
            "Property Type", PROPERTY_STYLE_TYPES,
            index=PROPERTY_STYLE_TYPES.index(st.session_state.subject_prop_type)
            if st.session_state.subject_prop_type in PROPERTY_STYLE_TYPES else 0,
            key="subject_prop_type_select",
        )
        st.session_state.subject_prop_age = st.text_input(
            "Age of Property (years, or year built)", value=st.session_state.subject_prop_age,
            placeholder="e.g. 15 years or Built 2011",
        )
        st.session_state.subject_land_size = st.text_input(
            "Land Size", value=st.session_state.subject_land_size, placeholder="e.g. 50 x 120 FT",
        )
        st.session_state.subject_garage = st.selectbox(
            "Garage", ["", "None", "Attached", "Detached", "Carport"],
            index=["", "None", "Attached", "Detached", "Carport"].index(st.session_state.subject_garage)
            if st.session_state.subject_garage in ["", "None", "Attached", "Detached", "Carport"] else 0,
        )
        st.session_state.subject_heating_type = st.selectbox(
            "Heating Type", HEATING_TYPE_OPTIONS,
            index=HEATING_TYPE_OPTIONS.index(st.session_state.subject_heating_type)
            if st.session_state.subject_heating_type in HEATING_TYPE_OPTIONS else 0,
        )
        st.session_state.subject_foundation = st.text_input(
            "Foundation Type", value=st.session_state.subject_foundation,
            placeholder="e.g. Poured Concrete",
        )
        st.session_state.subject_sewer = st.selectbox(
            "Utility Sewer", SEWER_OPTIONS,
            index=SEWER_OPTIONS.index(st.session_state.subject_sewer)
            if st.session_state.subject_sewer in SEWER_OPTIONS else 0,
        )
        st.session_state.subject_rural_urban = st.selectbox(
            "Rural / Urban / Agricultural",
            RURAL_URBAN_OPTIONS,
            index=RURAL_URBAN_OPTIONS.index(st.session_state.subject_rural_urban)
            if st.session_state.subject_rural_urban in RURAL_URBAN_OPTIONS else 0,
        )

    st.write("**Monthly Carrying Costs**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state.subject_taxes_raw = st.text_input(
            "Monthly Property Taxes ($)", value=st.session_state.subject_taxes_raw,
            placeholder="Enter monthly tax amount",
        )
    with c2:
        st.session_state.subject_condo_raw = st.text_input(
            "Monthly Condo / Strata Fees ($)", value=st.session_state.subject_condo_raw,
            placeholder="Enter monthly fee amount (0 if none)",
        )
    with c3:
        st.session_state.subject_heat_raw = st.text_input(
            "Monthly Heating Costs ($)", value=st.session_state.subject_heat_raw,
            placeholder="Enter monthly heating amount",
        )

    st.caption(
        "Monthly P&I and total housing costs will be calculated once you set the "
        "contract rate and amortization on the Analysis step."
    )

    st.divider()

    if st.button("🔄 Refresh Page", use_container_width=False, key="p3_refresh"):
        st.session_state["p3_show_refresh_confirm"] = True

    if st.session_state.get("p3_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p3_confirm_refresh"):
                refresh_property_details()
                st.session_state["p3_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p3_cancel_refresh"):
                st.session_state["p3_show_refresh_confirm"] = False
                st.rerun()

    if continue_top:
        if st.session_state.subject_address.strip():
            st.session_state.step = 3
            st.rerun()
        else:
            st.error("Please enter the property address before continuing.")


# ---------------------------------------------------------------------------
# STEP 2 — Income
# ---------------------------------------------------------------------------

def refresh_page3():
    st.session_state.income_selected = {}
    st.session_state.income_amounts = {}
    st.session_state.income_special = {}
    st.session_state.income_other_desc = {}
    st.session_state.income_errors = {}


def get_income_source(key):
    for src in INCOME_SOURCES:
        if src["key"] == key:
            return src
    return None


VARIABLE_INCOME_KEYS = (
    "commission", "hourly", "bonus_overtime", "self_employed", "dividend",
    "self_employed_incorporated", "self_employed_professional",
)
EXCLUDED_INCOME_KEYS = ("capital_gains",)


def compute_qualifying_variable_income(amounts):
    """
    Applies the standard 2-year variable-income rule: if the most recent
    year is lower than the prior year, use the (lower) most recent year;
    otherwise use the 2-year average.
    """
    recent_v = parse_money(amounts.get("recent_year", ""))
    prior_v = parse_money(amounts.get("prior_year", ""))
    if recent_v is None and prior_v is None:
        return 0.0
    if recent_v is None:
        recent_v = 0.0
    if prior_v is None:
        prior_v = 0.0
    if recent_v < prior_v:
        return recent_v
    return (recent_v + prior_v) / 2.0


def compute_borrower_income(borrower_idx):
    bidx = str(borrower_idx)
    selected_keys = st.session_state.income_selected.get(bidx, [])
    total = 0.0
    breakdown = {}

    for key in selected_keys:
        amounts = st.session_state.income_amounts.get(bidx, {}).get(key, {})

        if key in EXCLUDED_INCOME_KEYS:
            value = 0.0
        elif key == "rental":
            gross_rental = parse_money(amounts.get("gross_rental", "")) or 0.0
            carrying_costs = parse_money(amounts.get("carrying_costs", "")) or 0.0
            value = max(gross_rental - carrying_costs, 0.0)
        elif key in VARIABLE_INCOME_KEYS:
            value = compute_qualifying_variable_income(amounts)
        else:
            value = parse_money(amounts.get("amount", "")) or 0.0

        breakdown[key] = value
        total += value

    return total, breakdown


def compute_total_income():
    grand_total = 0.0
    for idx in range(st.session_state.borrower_count):
        total, _ = compute_borrower_income(idx)
        grand_total += total
    return grand_total


def render_income_category_card(bidx, skey, source, amounts):
    """
    Renders the detailed input card for one selected income category, per the
    field mapping. Mutates `amounts` in place (caller persists it back to
    session_state). Also handles the 24-month previous-employer rule for
    salaried/commission/self-employed, and the alimony disclaimer.
    """
    st.markdown("**" + source["label"] + "**")
    prefix = "inc_" + bidx + "_" + skey + "_"

    needs_24mo_check = False

    def render_two_year_income_fields(amounts, field_prefix, label="Annual Income"):
        c1, c2 = st.columns(2)
        with c1:
            amounts["recent_year"] = st.text_input(
                "Most Recent Year — " + label + " ($)", value=amounts.get("recent_year", ""),
                placeholder="Enter amount", key=field_prefix + "recent_year",
            )
        with c2:
            amounts["prior_year"] = st.text_input(
                "Prior Year — " + label + " ($)", value=amounts.get("prior_year", ""),
                placeholder="Enter amount", key=field_prefix + "prior_year",
            )
        recent_v = parse_money(amounts.get("recent_year", ""))
        prior_v = parse_money(amounts.get("prior_year", ""))
        if recent_v is not None and prior_v is not None:
            if recent_v < prior_v:
                qualifying = recent_v
                rule_note = "most recent year is lower, so the most recent year's income is used."
            else:
                qualifying = (recent_v + prior_v) / 2.0
                rule_note = "most recent year is higher (or equal), so the 2-year average is used."
            st.caption("Qualifying Income (used for GDS/TDS): **" + fmt_money(qualifying) + "** — " + rule_note)
        elif recent_v is not None or prior_v is not None:
            st.caption("Enter both years to calculate qualifying income for GDS/TDS.")

    if skey == "salaried":
        needs_24mo_check = True
        c1, c2 = st.columns(2)
        with c1:
            amounts["employer_name"] = st.text_input("Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
            amounts["phone"] = st.text_input("Phone Number", value=amounts.get("phone", ""), key=prefix + "phone")
            amounts["start_date"] = st.text_input("Start Date (MM/YYYY)", value=amounts.get("start_date", ""), placeholder="e.g. 06/2022", key=prefix + "start_date")
        with c2:
            amounts["employer_address"] = st.text_input("Employer Address", value=amounts.get("employer_address", ""), key=prefix + "employer_address")
            amounts["title"] = st.text_input("Position / Title", value=amounts.get("title", ""), key=prefix + "title")
        amounts["amount"] = st.text_input("Gross Annual Base Income ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "commission":
        needs_24mo_check = True
        c1, c2 = st.columns(2)
        with c1:
            amounts["employer_name"] = st.text_input("Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
            amounts["phone"] = st.text_input("Phone Number", value=amounts.get("phone", ""), key=prefix + "phone")
            amounts["start_date"] = st.text_input("Start Date (MM/YYYY)", value=amounts.get("start_date", ""), placeholder="e.g. 06/2022", key=prefix + "start_date")
        with c2:
            amounts["employer_address"] = st.text_input("Employer Address", value=amounts.get("employer_address", ""), key=prefix + "employer_address")
            amounts["title"] = st.text_input("Position / Title", value=amounts.get("title", ""), key=prefix + "title")
        render_two_year_income_fields(amounts, prefix, "Commission Income")

    elif skey == "hourly":
        c1, c2 = st.columns(2)
        with c1:
            amounts["employer_name"] = st.text_input("Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            guaranteed_options = ["", "Guaranteed Hours", "Variable Hours"]
            cur_g = amounts.get("hours_type", "")
            amounts["hours_type"] = st.selectbox(
                "Hours Type", guaranteed_options,
                index=guaranteed_options.index(cur_g) if cur_g in guaranteed_options else 0,
                key=prefix + "hours_type",
            )
        render_two_year_income_fields(amounts, prefix, "Hourly Income")

    elif skey == "bonus_overtime":
        c1, c2 = st.columns(2)
        with c1:
            amounts["employer_name"] = st.text_input("Primary Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            st.write("")
        render_two_year_income_fields(amounts, prefix, "Bonus/Overtime Income")

    elif skey == "self_employed":
        needs_24mo_check = True
        c1, c2 = st.columns(2)
        with c1:
            amounts["business_name"] = st.text_input("Business Name", value=amounts.get("business_name", ""), key=prefix + "business_name")
            amounts["phone"] = st.text_input("Phone Number", value=amounts.get("phone", ""), key=prefix + "phone")
            amounts["start_date"] = st.text_input("Start Date (MM/YYYY)", value=amounts.get("start_date", ""), placeholder="e.g. 03/2019", key=prefix + "start_date")
        with c2:
            amounts["business_address"] = st.text_input("Business Address", value=amounts.get("business_address", ""), key=prefix + "business_address")
            amounts["title"] = st.text_input("Role / Title", value=amounts.get("title", ""), key=prefix + "title")
            amounts["ownership_pct"] = st.text_input("Ownership Percentage (%)", value=amounts.get("ownership_pct", ""), key=prefix + "ownership_pct")
        render_two_year_income_fields(amounts, prefix, "Net Business Income")

    elif skey == "dividend":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Financial Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
        with c2:
            amounts["account_number"] = st.text_input("Account Number", value=amounts.get("account_number", ""), key=prefix + "account_number")
        render_two_year_income_fields(amounts, prefix, "Dividend Income")

    elif skey == "parttime":
        c1, c2 = st.columns(2)
        with c1:
            amounts["employer_name"] = st.text_input("Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            amounts["amount"] = st.text_input("Gross Annual Income ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey in ("self_employed_incorporated", "self_employed_professional"):
        needs_24mo_check = True
        c1, c2 = st.columns(2)
        with c1:
            amounts["business_name"] = st.text_input("Business / Practice Name", value=amounts.get("business_name", ""), key=prefix + "business_name")
            amounts["phone"] = st.text_input("Phone Number", value=amounts.get("phone", ""), key=prefix + "phone")
            amounts["start_date"] = st.text_input("Start Date (MM/YYYY)", value=amounts.get("start_date", ""), placeholder="e.g. 03/2019", key=prefix + "start_date")
        with c2:
            amounts["business_address"] = st.text_input("Business Address", value=amounts.get("business_address", ""), key=prefix + "business_address")
            amounts["title"] = st.text_input("Role / Title", value=amounts.get("title", ""), key=prefix + "title")
            amounts["ownership_pct"] = st.text_input("Ownership Percentage (%)", value=amounts.get("ownership_pct", ""), key=prefix + "ownership_pct")
        render_two_year_income_fields(amounts, prefix, "Net Income")

    elif skey == "disability":
        c1, c2 = st.columns(2)
        with c1:
            amounts["benefit_type"] = st.text_input("Benefit Type / Provider", value=amounts.get("benefit_type", ""), key=prefix + "benefit_type")
            duration_options = ["", "Long-Term / Ongoing", "Temporary"]
            cur_d = amounts.get("duration_type", "")
            amounts["duration_type"] = st.selectbox(
                "Expected Duration", duration_options,
                index=duration_options.index(cur_d) if cur_d in duration_options else 0,
                key=prefix + "duration_type",
            )
        with c2:
            amounts["amount"] = st.text_input("Gross Annual Income ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "ei_parental_benefits":
        c1, c2 = st.columns(2)
        with c1:
            amounts["return_to_work_date"] = st.text_input("Expected Return-to-Work Date (MM/YYYY)", value=amounts.get("return_to_work_date", ""), key=prefix + "return_to_work_date")
        with c2:
            amounts["amount"] = st.text_input("Gross Annual Benefit Amount ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        st.caption("Note: EI/maternity/parental benefits are usually weaker for qualification since they're temporary.")

    elif skey == "foreign_income":
        c1, c2 = st.columns(2)
        with c1:
            amounts["country"] = st.text_input("Country of Income Source", value=amounts.get("country", ""), key=prefix + "country")
        with c2:
            amounts["amount"] = st.text_input("Gross Annual Income ($, CAD equivalent)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        st.caption("Note: lenders are usually conservative with foreign income due to currency and jurisdiction risk.")

    elif skey == "capital_gains":
        c1, c2 = st.columns(2)
        with c1:
            amounts["description"] = st.text_input("Source / Description", value=amounts.get("description", ""), key=prefix + "description")
        with c2:
            amounts["amount"] = st.text_input("Amount ($, for reference only)", value=amounts.get("amount", ""), placeholder="Enter amount", key=prefix + "amount")
        st.caption("⚠️ Capital gains are not recurring income — this amount is recorded for reference only and is excluded from GDS/TDS qualification.")

    elif skey == "board_director_fees":
        c1, c2 = st.columns(2)
        with c1:
            amounts["organization_name"] = st.text_input("Organization Name", value=amounts.get("organization_name", ""), key=prefix + "organization_name")
        with c2:
            amounts["amount"] = st.text_input("Gross Annual Amount ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "investment":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Financial Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
            amounts["account_number"] = st.text_input("Account Number", value=amounts.get("account_number", ""), key=prefix + "account_number")
        with c2:
            amounts["amount"] = st.text_input("Average Annual Income ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "rental":
        c1, c2 = st.columns(2)
        with c1:
            amounts["property_address"] = st.text_input("Property Address", value=amounts.get("property_address", ""), key=prefix + "property_address")
            amounts["property_value"] = st.text_input("Property Value ($)", value=amounts.get("property_value", ""), key=prefix + "property_value")
            occ_options = ["", "Primary", "Secondary", "Investment"]
            cur_occ = amounts.get("occupancy", "")
            amounts["occupancy"] = st.selectbox(
                "Intended Occupancy", occ_options,
                index=occ_options.index(cur_occ) if cur_occ in occ_options else 0,
                key=prefix + "occupancy",
            )
        with c2:
            amounts["gross_rental"] = st.text_input("Gross Annual Rental Income ($)", value=amounts.get("gross_rental", ""), placeholder="Enter annual amount", key=prefix + "gross_rental")
            amounts["carrying_costs"] = st.text_input("Annual Mortgage/Tax/HOA Dues ($)", value=amounts.get("carrying_costs", ""), key=prefix + "carrying_costs")
        gross_v = parse_money(amounts.get("gross_rental", "")) or 0.0
        carry_v = parse_money(amounts.get("carrying_costs", "")) or 0.0
        st.caption("Net Rental Income (used for qualification): " + fmt_money(max(gross_v - carry_v, 0.0)))

    elif skey == "pension":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Provider / Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
        with c2:
            amounts["amount"] = st.text_input("Gross Annual Income ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "government_benefits":
        c1, c2 = st.columns(2)
        with c1:
            amounts["benefit_type"] = st.text_input("Benefit Type", value=amounts.get("benefit_type", ""), key=prefix + "benefit_type")
        with c2:
            amounts["amount"] = st.text_input("Gross Annual Income ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "alimony":
        st.caption(
            "Notice: You do not have to disclose alimony, child support, or separate maintenance income if "
            "you do not wish to have it considered as a basis for repaying this obligation."
        )
        amounts["amount"] = st.text_input("Gross Annual Amount ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "trust_inheritance":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Trust / Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
            amounts["amount"] = st.text_input("Gross Annual Amount ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c2:
            amounts["duration"] = st.text_input("Expected Duration of Continued Payments (Months/Years)", value=amounts.get("duration", ""), key=prefix + "duration")

    else:  # "other"
        c1, c2 = st.columns(2)
        with c1:
            amounts["source_desc"] = st.text_input("Source Description", value=amounts.get("source_desc", ""), key=prefix + "source_desc")
        with c2:
            amounts["amount"] = st.text_input("Gross Annual Amount ($)", value=amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    # --- 24-month rule: salaried, commission, self-employed only ---
    if needs_24mo_check:
        parsed_start = parse_month_year(amounts.get("start_date", ""))
        if parsed_start is not None and months_elapsed_since(parsed_start) < 24:
            st.markdown(
                "<div style='margin-top:10px; font-weight:600;'>Previous Employer / Business Details "
                "(less than 24 months at current)</div>",
                unsafe_allow_html=True,
            )
            pc1, pc2 = st.columns(2)
            with pc1:
                amounts["prev_employer_name"] = st.text_input("Employer Name", value=amounts.get("prev_employer_name", ""), key=prefix + "prev_employer_name")
                amounts["prev_phone"] = st.text_input("Phone", value=amounts.get("prev_phone", ""), key=prefix + "prev_phone")
                amounts["prev_start_date"] = st.text_input("Start Date (MM/YYYY)", value=amounts.get("prev_start_date", ""), key=prefix + "prev_start_date")
            with pc2:
                amounts["prev_employer_address"] = st.text_input("Address", value=amounts.get("prev_employer_address", ""), key=prefix + "prev_employer_address")
                amounts["prev_title"] = st.text_input("Title", value=amounts.get("prev_title", ""), key=prefix + "prev_title")
                amounts["prev_end_date"] = st.text_input("End Date (MM/YYYY)", value=amounts.get("prev_end_date", ""), key=prefix + "prev_end_date")

    # --- Required documentation (unchanged from before) ---
    docs_html = "".join("<li>" + d + "</li>" for d in source["documents"])
    notes_html = "<div style='margin-top:6px;'>" + source["notes"] + "</div>" if source["notes"] else ""
    st.markdown(
        "<div class='doc-list'><b>Required Documentation</b>"
        "<ul style='margin:6px 0 0 18px;'>" + docs_html + "</ul>" + notes_html + "</div>",
        unsafe_allow_html=True,
    )


def render_income():
    spacer, back_col, continue_col = st.columns([3, 1, 1])

    with back_col:
        if st.button("← Back", use_container_width=True, key="p4_back_top"):
            st.session_state.step = 2
            st.rerun()
    with continue_col:
        continue_top = st.button("Continue →", type="primary", use_container_width=True, key="p4_continue_top")

    st.markdown("### Income Details")
    st.write("Enter income information for each borrower on this application.")
    st.info("💡 All income amounts below are **annual** figures, not monthly.")
    render_calculator_popover("income")

    borrower_count = st.session_state.borrower_count
    borrowers = st.session_state.borrowers
    all_valid = True
    grand_total = 0.0

    for idx in range(borrower_count):
        bidx = str(idx)
        borrower_name = borrowers[idx]["full_name"].strip() if idx < len(borrowers) else ""
        header = "Borrower " + str(idx + 1)
        if borrower_name:
            header += ": " + borrower_name
        header += " - Income Details"

        if bidx not in st.session_state.income_selected:
            st.session_state.income_selected[bidx] = []
        if bidx not in st.session_state.income_amounts:
            st.session_state.income_amounts[bidx] = {}
        if bidx not in st.session_state.income_errors:
            st.session_state.income_errors[bidx] = {}

        with st.expander(header, expanded=True):
            st.write("**Select Income Sources**")
            selected = st.session_state.income_selected[bidx]

            # --- Phase 1: plain checkbox list only (unchanged layout) ---
            for source in INCOME_SOURCES:
                skey = source["key"]
                checked = skey in selected
                new_checked = st.checkbox(
                    source["label"], value=checked, key="inc_src_" + bidx + "_" + skey
                )

                if new_checked and skey not in selected:
                    selected.append(skey)
                elif not new_checked and skey in selected:
                    selected.remove(skey)
                    st.session_state.income_amounts[bidx].pop(skey, None)

            st.session_state.income_selected[bidx] = selected

            # --- Phase 2: detail card for every selected source, injected here, sequentially ---
            for source in INCOME_SOURCES:
                skey = source["key"]
                if skey not in selected:
                    continue
                if skey not in st.session_state.income_amounts[bidx]:
                    st.session_state.income_amounts[bidx][skey] = {}
                amounts = st.session_state.income_amounts[bidx][skey]
                st.markdown("---")
                render_income_category_card(bidx, skey, source, amounts)
                st.session_state.income_amounts[bidx][skey] = amounts

            borrower_total, breakdown = compute_borrower_income(idx)
            grand_total += borrower_total

            label_name = borrower_name if borrower_name else ("Borrower " + str(idx + 1))
            st.markdown(
                "<div class='borrower-total'>" + label_name + " Total Income: " + fmt_money(borrower_total) + "</div>",
                unsafe_allow_html=True,
            )

            errors = {}
            if not selected:
                errors["no_sources"] = "Please select at least one income source for " + label_name + "."
            else:
                for skey in selected:
                    val = breakdown.get(skey, 0.0)
                    if val <= 0:
                        source = get_income_source(skey)
                        errors[skey] = "Please enter an amount for " + source["label"] + " for " + label_name + "."

            st.session_state.income_errors[bidx] = errors
            if errors:
                all_valid = False
                for msg in errors.values():
                    st.caption(":red[" + msg + "]")

    st.divider()
    st.markdown("#### Total Combined Income: " + fmt_money(grand_total))
    st.divider()

    if st.button("🔄 Refresh Page", use_container_width=False, key="p4_refresh"):
        st.session_state["p4_show_refresh_confirm"] = True

    if st.session_state.get("p4_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p4_confirm_refresh"):
                refresh_page3()
                st.session_state["p4_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p4_cancel_refresh"):
                st.session_state["p4_show_refresh_confirm"] = False
                st.rerun()

    if continue_top:
        if all_valid:
            st.session_state.step = 4
            st.rerun()
        else:
            st.error("Please resolve the issues above before continuing.")


# ---------------------------------------------------------------------------
# STEP 3 — Debts & Liabilities
# ---------------------------------------------------------------------------

def refresh_page4():
    st.session_state.properties = []
    st.session_state.debt_selected = []
    st.session_state.debt_amounts = {}
    st.session_state.debt_other_desc = ""
    st.session_state.debt_errors = {}


def get_debt_type(key):
    for dt in DEBT_TYPES:
        if dt["key"] == key:
            return dt
    return None


def compute_property_total(prop):
    m = parse_money(prop.get("mortgage_payment", "")) or 0.0
    t = parse_money(prop.get("property_taxes", "")) or 0.0
    c = parse_money(prop.get("condo_fees", "")) or 0.0
    h = parse_money(prop.get("heating", "")) or 0.0
    return m + t + c + h, m, t, c, h


def compute_debt_payment(debt_type, amounts):
    if debt_type["calc"] == "percent_of_balance":
        balance = parse_money(amounts.get("balance", "")) or 0.0
        return balance * debt_type["percent"]
    else:
        return parse_money(amounts.get("payment", "")) or 0.0


def explain_debt_payment(debt_type, amounts):
    """Returns (payment, explanation_string) showing the math behind a debt's monthly payment."""
    if debt_type["calc"] == "percent_of_balance":
        balance = parse_money(amounts.get("balance", "")) or 0.0
        pct = debt_type["percent"]
        payment = balance * pct
        explanation = (
            debt_type["label"] + ": " + "{:.0f}%".format(pct * 100) + " of "
            + fmt_money(balance) + " balance = " + fmt_money(payment) + "/month"
        )
        return payment, explanation
    else:
        payment = parse_money(amounts.get("payment", "")) or 0.0
        explanation = debt_type["label"] + ": stated monthly payment = " + fmt_money(payment) + "/month"
        return payment, explanation


def render_debts():
    spacer, back_col, continue_col = st.columns([3, 1, 1])

    with back_col:
        if st.button("← Back", use_container_width=True, key="p5_back_top"):
            st.session_state.step = 3
            st.rerun()
    with continue_col:
        continue_top = st.button("Continue →", type="primary", use_container_width=True, key="p5_continue_top")

    st.markdown("### Debts & Liabilities")
    st.write("Enter property debts and other liabilities for this application.")
    render_calculator_popover("debts")

    st.write("**Property Debts**")

    if st.button("+ Add Property", key="add_property"):
        st.session_state.properties.append(empty_property())
        st.rerun()

    total_property_debt = 0.0
    total_mortgage_pi_proxy = 0.0
    total_taxes = 0.0
    total_heat = 0.0
    total_condo = 0.0
    property_errors_any = False

    for pidx, prop in enumerate(st.session_state.properties):
        with st.expander("Property " + str(pidx + 1), expanded=True):
            prop["address"] = st.text_area(
                "Property Address", value=prop["address"], placeholder="Enter full property address",
                key="prop_addr_" + str(pidx), height=70,
            )
            prop["prop_type"] = st.selectbox(
                "Property Type", PROPERTY_TYPES,
                index=PROPERTY_TYPES.index(prop["prop_type"]) if prop["prop_type"] in PROPERTY_TYPES else 0,
                key="prop_type_" + str(pidx),
            )
            if prop["prop_type"] == "Other":
                prop["other_type_desc"] = st.text_input(
                    "Describe property type", value=prop.get("other_type_desc", ""), key="prop_other_" + str(pidx)
                )

            c1, c2 = st.columns(2)
            with c1:
                prop["mortgage_payment"] = st.text_input(
                    "Monthly Mortgage / Loan Payment ($)", value=prop["mortgage_payment"],
                    placeholder="Enter monthly payment amount", key="prop_mtg_" + str(pidx),
                )
                prop["condo_fees"] = st.text_input(
                    "Monthly Condo / Strata Fees ($)", value=prop["condo_fees"],
                    placeholder="Enter monthly fee amount (0 if none)", key="prop_condo_" + str(pidx),
                )
            with c2:
                prop["property_taxes"] = st.text_input(
                    "Monthly Property Taxes ($)", value=prop["property_taxes"],
                    placeholder="Enter monthly tax amount", key="prop_tax_" + str(pidx),
                )
                prop["heating"] = st.text_input(
                    "Monthly Heating Costs ($)", value=prop["heating"],
                    placeholder="Enter monthly heating amount", key="prop_heat_" + str(pidx),
                )

            prop_total, m, t, c, h = compute_property_total(prop)
            total_property_debt += prop_total
            total_mortgage_pi_proxy += m
            total_taxes += t
            total_condo += c
            total_heat += h

            st.caption(
                "Mortgage/Loan " + fmt_money(m) + " + Taxes " + fmt_money(t)
                + " + Condo " + fmt_money(c) + " + Heat " + fmt_money(h)
                + " = " + fmt_money(prop_total) + "/month"
            )
            st.markdown(
                "<div class='property-total'>Total Monthly Property Debt: " + fmt_money(prop_total) + "</div>",
                unsafe_allow_html=True,
            )

            if not prop["address"].strip():
                st.caption(":red[Please enter the property address.]")
                property_errors_any = True

            st.markdown(
                "<div class='doc-list'><b>Required Documentation</b><ul style='margin:6px 0 0 18px;'>"
                "<li>Mortgage statement or loan agreement</li>"
                "<li>Property tax assessment or bill</li>"
                "<li>Condo fee statement (if applicable)</li>"
                "<li>Heating bill or utility estimate</li>"
                "</ul></div>",
                unsafe_allow_html=True,
            )

            if st.button("Remove Property " + str(pidx + 1), key="remove_prop_" + str(pidx)):
                st.session_state["confirm_remove_prop"] = pidx
                st.rerun()

            if st.session_state.get("confirm_remove_prop") == pidx:
                st.warning("Remove this property? This cannot be undone.")
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("Yes, remove", key="confirm_remove_yes_" + str(pidx)):
                        st.session_state.properties.pop(pidx)
                        st.session_state["confirm_remove_prop"] = None
                        st.rerun()
                with rc2:
                    if st.button("Cancel", key="confirm_remove_no_" + str(pidx)):
                        st.session_state["confirm_remove_prop"] = None
                        st.rerun()

        st.session_state.properties[pidx] = prop

    st.divider()

    st.write("**Select Other Debt Types**")

    selected = st.session_state.debt_selected
    total_other_debt = 0.0
    other_debt_errors_any = False

    for debt_type in DEBT_TYPES:
        dkey = debt_type["key"]
        checked = dkey in selected
        new_checked = st.checkbox(debt_type["label"], value=checked, key="debt_" + dkey)

        if new_checked and dkey not in selected:
            selected.append(dkey)
        elif not new_checked and dkey in selected:
            selected.remove(dkey)
            st.session_state.debt_amounts.pop(dkey, None)

        if new_checked:
            if dkey not in st.session_state.debt_amounts:
                st.session_state.debt_amounts[dkey] = {}
            amounts = st.session_state.debt_amounts[dkey]

            if debt_type["calc"] == "percent_of_balance":
                amounts["balance"] = st.text_input(
                    "Total Outstanding Balance ($)", value=amounts.get("balance", ""),
                    placeholder="Enter total balance", key="debt_bal_" + dkey,
                )
                if amounts.get("balance", "").strip() == "":
                    other_debt_errors_any = True
            else:
                amounts["payment"] = st.text_input(
                    "Monthly Payment Amount ($)", value=amounts.get("payment", ""),
                    placeholder="Enter monthly payment amount", key="debt_pay_" + dkey,
                )
                if amounts.get("payment", "").strip() == "":
                    other_debt_errors_any = True

            _, debt_explanation = explain_debt_payment(debt_type, amounts)
            st.caption(debt_explanation)

            if dkey == "other":
                st.session_state.debt_other_desc = st.text_input(
                    "Describe the other obligation", value=st.session_state.debt_other_desc,
                    key="debt_other_desc_input",
                )

            payment_value = compute_debt_payment(debt_type, amounts)
            total_other_debt += payment_value

            docs_html = ""
            for d in debt_type["documents"]:
                docs_html += "<li>" + d + "</li>"
            notes_html = "<div style='margin-top:6px;'>" + debt_type["notes"] + "</div>" if debt_type["notes"] else ""
            st.markdown(
                "<div class='doc-list'><b>Required Documentation</b>"
                "<ul style='margin:6px 0 0 18px;'>" + docs_html + "</ul>" + notes_html + "</div>",
                unsafe_allow_html=True,
            )

            st.session_state.debt_amounts[dkey] = amounts

    st.session_state.debt_selected = selected

    st.divider()

    if selected:
        st.write("**Other Debt Breakdown**")
        for dkey in selected:
            dt = get_debt_type(dkey)
            amounts = st.session_state.debt_amounts.get(dkey, {})
            _, exp = explain_debt_payment(dt, amounts)
            st.caption(exp)

    total_monthly_debt = total_property_debt + total_other_debt
    st.markdown("#### Total Monthly Debt Obligations (Other Properties + Debts): " + fmt_money(total_monthly_debt))
    st.caption("Note: the property you're purchasing is entered in the Property Details step, not here — this page is for your other existing debts.")
    st.caption("Full GDS/TDS qualification is calculated on the Analysis step, after financing terms are set.")

    st.divider()

    has_any_debt = len(st.session_state.properties) > 0 or len(selected) > 0
    is_valid = has_any_debt and not property_errors_any and not other_debt_errors_any

    if not has_any_debt:
        st.caption(":red[Please add at least one property or select at least one debt type.]")

    st.divider()

    if st.button("🔄 Refresh Page", use_container_width=False, key="p5_refresh"):
        st.session_state["p5_show_refresh_confirm"] = True

    if st.session_state.get("p5_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p5_confirm_refresh"):
                refresh_page4()
                st.session_state["p5_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p5_cancel_refresh"):
                st.session_state["p5_show_refresh_confirm"] = False
                st.rerun()

    if continue_top:
        if is_valid:
            st.session_state.step = 5
            st.rerun()
        else:
            st.error("Please resolve the issues above before continuing.")


# ---------------------------------------------------------------------------
# STEP 4 — Analysis (GDS/TDS Qualification Summary)
# ---------------------------------------------------------------------------

STRESS_TEST_ADDON = 2.0  # commonly: contract rate + 2%, per public stress-test convention
DEFAULT_BENCHMARK_RATE = 5.25  # a commonly cited public benchmark qualifying rate; editable below


def compute_gds_tds(pi_payment, taxes, heat, condo, other_debt_monthly, annual_income):
    annual_housing = (pi_payment + taxes + heat + condo * 0.5) * 12
    annual_other_debt = other_debt_monthly * 12
    if annual_income <= 0:
        return None, None, annual_housing, annual_other_debt
    gds = annual_housing / annual_income * 100
    tds = (annual_housing + annual_other_debt) / annual_income * 100
    return gds, tds, annual_housing, annual_other_debt


def ratio_badge(value, limit):
    if value is None:
        return "—", ""
    display = "{:.2f}%".format(value)
    if value <= limit * 0.9:
        return display, "ratio-green"
    elif value <= limit:
        return display, "ratio-yellow"
    else:
        return display, "ratio-red"


def render_gauge(label, value, limit):
    if value is None:
        st.write("**" + label + ":** —")
        return
    pct_of_scale = min(value / 50.0, 1.0)
    filled = int(pct_of_scale * 28)
    bar = "█" * filled + "░" * (28 - filled)
    display, css_class = ratio_badge(value, limit)
    check = "✓" if value <= limit else "✗"
    st.markdown(
        "<div style='margin-bottom:10px;'>"
        "<b>" + label + ":</b> <span class='" + css_class + "'>" + display + "</span> " + check + "<br>"
        "<span style='font-family:monospace; letter-spacing:1px;'>[" + bar + "]</span><br>"
        "<span style='font-size:12px; color:#6b7280;'>Acceptable Range: ≤ " + str(int(limit)) + "%</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_analysis():
    spacer, back_col, continue_col = st.columns([3, 1, 1])

    with back_col:
        if st.button("← Back", use_container_width=True, key="p6_back_top"):
            st.session_state.step = 4
            st.rerun()
    with continue_col:
        continue_top = st.button("Continue →", type="primary", use_container_width=True, key="p6_continue_top")

    st.markdown("### Qualification Summary")
    st.write("This page aggregates data from all previous steps — nothing to re-enter here.")
    render_calculator_popover("analysis")

    # --- Financing Terms (moved here from Property Details) ---
    st.markdown("#### Financing Terms")

    def field_row(label_widget_fn, help_text_fn, help_key):
        with st.container(key="fieldrow_" + help_key):
            c1, c2 = st.columns([12, 1])
            with c1:
                label_widget_fn()
            with c2:
                with st.container(key="helpbtn_" + help_key):
                    with st.popover("?", key=help_key):
                        st.caption(help_text_fn())

    fc1, fc2 = st.columns(2)
    with fc1:
        field_row(
            lambda: st.session_state.__setitem__("contract_rate", st.number_input(
                "Contract Interest Rate (%)", min_value=0.0, max_value=25.0,
                value=st.session_state.contract_rate, step=0.05, key="analysis_contract_rate",
            )),
            lambda: help_contract_rate_text(st.session_state.contract_rate),
            "help_contract_rate",
        )
        field_row(
            lambda: st.session_state.__setitem__("mortgage_term", st.selectbox(
                "Mortgage Term", MORTGAGE_TERM_OPTIONS,
                index=MORTGAGE_TERM_OPTIONS.index(st.session_state.mortgage_term)
                if st.session_state.mortgage_term in MORTGAGE_TERM_OPTIONS else 4,
                key="mortgage_term_select",
            )),
            lambda: help_term_text(st.session_state.mortgage_term),
            "help_term",
        )
        field_row(
            lambda: st.session_state.__setitem__("benchmark_rate", st.number_input(
                "Benchmark Qualifying Rate (%)", min_value=0.0, max_value=25.0,
                value=st.session_state.benchmark_rate, step=0.05, key="benchmark_rate_input",
            )),
            lambda: help_benchmark_text(
                st.session_state.contract_rate, st.session_state.benchmark_rate,
                max(st.session_state.contract_rate + STRESS_TEST_ADDON, st.session_state.benchmark_rate),
            ),
            "help_benchmark",
        )
    with fc2:
        field_row(
            lambda: st.session_state.__setitem__("amortization_years", st.number_input(
                "Amortization (years)", min_value=1, max_value=35,
                value=st.session_state.amortization_years, step=1, key="analysis_amortization",
            )),
            lambda: help_amortization_text(st.session_state.amortization_years),
            "help_amortization",
        )
        field_row(
            lambda: st.session_state.__setitem__("rate_type", st.selectbox(
                "Rate Type", RATE_TYPE_OPTIONS,
                index=RATE_TYPE_OPTIONS.index(st.session_state.rate_type)
                if st.session_state.rate_type in RATE_TYPE_OPTIONS else 0,
                key="rate_type_select",
            )),
            lambda: help_rate_type_text(st.session_state.rate_type),
            "help_rate_type",
        )
    st.divider()

    # --- Aggregate data ---
    total_income = compute_total_income()
    purchase_price = parse_money(st.session_state.purchase_price_raw) or 0.0
    down_payment = parse_money(st.session_state.down_payment_raw) or 0.0
    loan_amount = max(purchase_price - down_payment, 0.0)
    ltv = (loan_amount / purchase_price * 100) if purchase_price else None

    pi_payment, taxes, condo, heat, _ = get_subject_property_costs()

    other_debt_monthly = 0.0
    for dkey in st.session_state.debt_selected:
        dt = get_debt_type(dkey)
        amounts = st.session_state.debt_amounts.get(dkey, {})
        other_debt_monthly += compute_debt_payment(dt, amounts)
    # All properties listed in the Debts step are treated as additional (non-subject) properties
    for prop in st.session_state.properties:
        p_total, _, _, _, _ = compute_property_total(prop)
        other_debt_monthly += p_total

    st.markdown("#### Combined Figures")
    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-card'><div class='metric-label'>Combined Gross Annual Income</div>"
        "<div class='metric-value'>" + fmt_money(total_income) + "</div></div>"
        "<div class='metric-card'><div class='metric-label'>Mortgage Loan Amount</div>"
        "<div class='metric-value'>" + fmt_money(loan_amount) + "</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    ltv_display = "{:.2f}%".format(ltv) if ltv is not None else "—"
    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-card'><div class='metric-label'>LTV Ratio</div>"
        "<div class='metric-value'>" + ltv_display + "</div></div>"
        "<div class='metric-card'><div class='metric-label'>Monthly Housing Costs (Primary Residence)</div>"
        "<div class='metric-value'>" + fmt_money(pi_payment + taxes + heat + condo) + "</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # --- Stress test numbers (computed early so they can sit next to contract GDS/TDS) ---
    qualifying_rate = max(st.session_state.contract_rate + STRESS_TEST_ADDON, st.session_state.benchmark_rate)
    st.caption(
        "Qualifying Rate Used for Stress Test: " + "{:.2f}%".format(qualifying_rate)
        + " (greater of contract + " + str(int(STRESS_TEST_ADDON)) + "%, or benchmark)"
    )
    stressed_pi = monthly_mortgage_payment(loan_amount, qualifying_rate, st.session_state.amortization_years)

    # --- GDS / TDS at contract terms AND stressed, side by side ---
    gds, tds, annual_housing, annual_other_debt = compute_gds_tds(
        pi_payment, taxes, heat, condo, other_debt_monthly, total_income
    )
    stressed_gds, stressed_tds, stressed_annual_housing, stressed_annual_other_debt = compute_gds_tds(
        stressed_pi, taxes, heat, condo, other_debt_monthly, total_income
    )

    gds_header_col, gds_help_col = st.columns([12, 1])
    with gds_header_col:
        st.markdown("#### GDS / TDS Calculation (Contract vs. Stressed)")
    with gds_help_col:
        with st.container(key="helpbtn_help_gds_tds"):
            with st.popover("?", key="help_gds_tds"):
                st.caption(help_gds_text(total_income, annual_housing, gds))
                st.divider()
                st.caption(help_tds_text(total_income, annual_housing, annual_other_debt, tds))

    gds_display = "{:.2f}%".format(gds) if gds is not None else "—"
    tds_display = "{:.2f}%".format(tds) if tds is not None else "—"
    stressed_gds_display = "{:.2f}%".format(stressed_gds) if stressed_gds is not None else "—"
    stressed_tds_display = "{:.2f}%".format(stressed_tds) if stressed_tds is not None else "—"

    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-card'><div class='metric-label'>GDS — Contract Rate</div>"
        "<div class='metric-value'>" + gds_display + "</div></div>"
        "<div class='metric-card'><div class='metric-label'>GDS — Stressed</div>"
        "<div class='metric-value'>" + stressed_gds_display + "</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-card'><div class='metric-label'>TDS — Contract Rate</div>"
        "<div class='metric-value'>" + tds_display + "</div></div>"
        "<div class='metric-card'><div class='metric-label'>TDS — Stressed</div>"
        "<div class='metric-value'>" + stressed_tds_display + "</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    def render_ratio_breakdown(pi_amount, annual_housing_amount, annual_other_debt_amount, gds_disp, tds_disp, is_stressed):
        rows = [
            ("Principal + Interest (P + I)", pi_amount, pi_amount * 12),
            ("Property Taxes (T)", taxes, taxes * 12),
            ("Heating (H)", heat, heat * 12),
            ("50% Condo Fees (0.5 × C)", condo * 0.5, condo * 0.5 * 12),
        ]
        cell = "padding:4px 8px; border-bottom:1px solid #94a3b8 !important; color:#0f172a !important; background:#f1f5f9 !important;"
        head = "padding:4px 8px; color:#0f172a !important; background:#cbd5e1 !important; font-weight:700 !important;"
        total_cell = "padding:4px 8px; color:#78350f !important; background:#fde047 !important; font-weight:700 !important;"

        # --- Row 1: both tables side by side ---
        gds_col, tds_col = st.columns(2)

        with gds_col:
            table_rows_html = "".join(
                "<tr><td style='" + cell + "'>" + name + "</td>"
                "<td style='" + cell + " text-align:right;'>" + fmt_money(monthly) + "</td>"
                "<td style='" + cell + " text-align:right;'>" + fmt_money(annual) + "</td></tr>"
                for name, monthly, annual in rows
            )
            st.markdown(
                "<table style='width:100%; border-collapse:collapse; font-size:13px; margin-bottom:6px;'>"
                "<tr>"
                "<th style='" + head + " text-align:left;'>Housing Cost Component</th>"
                "<th style='" + head + " text-align:right;'>Monthly</th>"
                "<th style='" + head + " text-align:right;'>Annual</th></tr>"
                + table_rows_html +
                "<tr>"
                "<td style='" + total_cell + "'>Total Annual Housing Costs (PITH)</td>"
                "<td style='" + total_cell + "'></td>"
                "<td style='" + total_cell + " text-align:right;'>" + fmt_money(annual_housing_amount) + "</td></tr>"
                "</table>",
                unsafe_allow_html=True,
            )

        with tds_col:
            tds_rows_html = (
                "<tr><td style='" + cell + "'>Annual Housing Costs (PITH, from left)</td>"
                "<td style='" + cell + " text-align:right;'>" + fmt_money(annual_housing_amount) + "</td></tr>"
                "<tr><td style='" + cell + "'>All Other Monthly Debt Payments × 12</td>"
                "<td style='" + cell + " text-align:right;'>" + fmt_money(annual_other_debt_amount) + "</td></tr>"
            )
            st.markdown(
                "<table style='width:100%; border-collapse:collapse; font-size:13px; margin-bottom:6px;'>"
                "<tr>"
                "<th style='" + head + " text-align:left;'>Debt Obligation Component</th>"
                "<th style='" + head + " text-align:right;'>Annual</th></tr>"
                + tds_rows_html +
                "<tr>"
                "<td style='" + total_cell + "'>Total Annual Debt Obligations</td>"
                "<td style='" + total_cell + " text-align:right;'>" + fmt_money(annual_housing_amount + annual_other_debt_amount) + "</td></tr>"
                "</table>",
                unsafe_allow_html=True,
            )

        # --- Row 2: both formula results side by side, aligned at the same height ---
        gds_formula_col, tds_formula_col = st.columns(2)
        with gds_formula_col:
            st.markdown(
                "<div style='background:#bfdbfe !important; border-radius:6px; padding:6px 10px; "
                "font-size:13px; color:#1e3a8a !important;'>"
                "<b>GDS</b> = " + fmt_money(annual_housing_amount) + " ÷ " + fmt_money(total_income)
                + " × 100 = <b>" + gds_disp + "</b></div>",
                unsafe_allow_html=True,
            )
        with tds_formula_col:
            st.markdown(
                "<div style='background:#bfdbfe !important; border-radius:6px; padding:6px 10px; "
                "font-size:13px; color:#1e3a8a !important;'>"
                "<b>TDS</b> = " + fmt_money(annual_housing_amount + annual_other_debt_amount) + " ÷ " + fmt_money(total_income)
                + " × 100 = <b>" + tds_disp + "</b></div>",
                unsafe_allow_html=True,
            )

    with st.expander("Show calculation details (Contract Rate)", expanded=False):
        st.caption("Formula: GDS = (P + I + T + H + 0.5C) ÷ Gross Annual Income × 100  |  TDS adds all other monthly debts.")
        render_ratio_breakdown(pi_payment, annual_housing, annual_other_debt, gds_display, tds_display, is_stressed=False)

    with st.expander("Show calculation details (Stressed, at " + "{:.2f}%".format(qualifying_rate) + ")", expanded=False):
        st.caption(
            "Stressed P&I substitutes the qualifying rate (" + "{:.2f}%".format(qualifying_rate)
            + ") in place of the contract rate (" + "{:.2f}%".format(st.session_state.contract_rate)
            + "); taxes, heat, and condo fees are unchanged."
        )
        render_ratio_breakdown(stressed_pi, stressed_annual_housing, stressed_annual_other_debt, stressed_gds_display, stressed_tds_display, is_stressed=True)

    st.divider()

    # --- Qualification status ---
    qualified = gds is not None and tds is not None and gds <= GDS_LIMIT and tds <= TDS_LIMIT

    if total_income <= 0:
        st.warning("Enter income details in the Income step to calculate qualification.")
    elif qualified:
        st.success("✅ QUALIFIED — Your GDS and TDS ratios are within acceptable limits.")
    else:
        st.error(
            "❌ NOT QUALIFIED — Your GDS/TDS ratios exceed acceptable limits.\n\n"
            "GDS: " + gds_display + " (Acceptable: ≤ " + str(int(GDS_LIMIT)) + "%)\n\n"
            "TDS: " + tds_display + " (Acceptable: ≤ " + str(int(TDS_LIMIT)) + "%)\n\n"
            "Please consider:\n"
            "- Increasing down payment to reduce mortgage amount\n"
            "- Reducing debt obligations\n"
            "- Increasing income\n"
            "- Adding a co-signer or guarantor"
        )

    st.divider()

    # --- Stress test qualification (detail already shown above) ---
    stressed_qualified = (
        stressed_gds is not None and stressed_tds is not None
        and stressed_gds <= GDS_LIMIT and stressed_tds <= TDS_LIMIT
    )
    stress_result = "PASS ✓" if stressed_qualified else "FAIL ✗"
    st.caption(
        "Stress Test Result (Qualifying Rate " + "{:.2f}%".format(qualifying_rate) + "): **" + stress_result + "**"
    )

    st.divider()

    # --- Navigation ---
    if st.button("🔄 Refresh Page", use_container_width=False, key="p6_refresh"):
        st.session_state["p6_show_refresh_confirm"] = True

    if st.session_state.get("p6_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data across all pages will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p6_confirm_refresh"):
                refresh_all()
                st.session_state["p6_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p6_cancel_refresh"):
                st.session_state["p6_show_refresh_confirm"] = False
                st.rerun()

    submit_col, docs_col = st.columns(2)
    with submit_col:
        submit_disabled = total_income <= 0
        if st.button("Submit Application", type="primary", use_container_width=True, key="p6_submit", disabled=submit_disabled):
            st.success("Application submitted. (Connect this button to your backend to persist the data.)")

    with docs_col:
        if st.button("Required Documents →", use_container_width=True, key="p6_to_docs"):
            st.session_state.step = 6
            st.rerun()

    if continue_top:
        st.session_state.step = 6
        st.rerun()


# ---------------------------------------------------------------------------
# STEP 5 — Documents Checklist
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# STEP 5 — Documents Checklist
# ---------------------------------------------------------------------------
#
# This step is a generic, data-driven checklist component. The renderer
# (render_document_checklist) only knows the schema below — it has no idea
# where the data came from. build_document_checklist_data() is the one
# function that maps THIS app's session_state into that schema; a different
# client/source could swap in a different builder (JSON file, API, DB) and
# the renderer would still work unchanged.
#
# Schema:
# {
#   "categories": [
#     {
#       "name": "<category name>",
#       "items": [
#         {"text": "<description only>"},
#         {"applicant": "<name>", "text": "<description>"},
#         {"applicant": "<name>", "subcategory": "<sub-label>", "text": "<description>"},
#         {"subcategory": "<sub-label>", "text": "<description>"},
#       ]
#     },
#     ...
#   ]
# }

GENERAL_APPLICATION_DOCS = [
    "Signed consent for collection, use, and disclosure of personal information",
    "Void cheque or pre-authorized debit form for the account to be used",
]

PER_BORROWER_ID_DOCS = [
    "Two pieces of government-issued photo ID (e.g. driver's licence, passport)",
    "Social Insurance Number (SIN)",
]

SUBJECT_PROPERTY_DOCS = [
    "Signed Agreement of Purchase and Sale, including all schedules and amendments",
    "MLS listing or property summary, if available",
    "Proof of property insurance (binder) naming the lender as loss payee, arranged prior to closing",
]

OTHER_PROPERTY_DOC_LABELS = [
    "Mortgage statement or loan agreement",
    "Property tax assessment or bill",
    "Condo fee statement (if applicable)",
    "Heating bill or utility estimate",
]


def borrower_display_name(idx):
    borrowers = st.session_state.borrowers
    if idx < len(borrowers) and borrowers[idx]["full_name"].strip():
        return borrowers[idx]["full_name"].strip()
    return "Borrower " + str(idx + 1)


def build_document_checklist_data():
    """
    Maps this application's session_state into the generic checklist schema.
    Swap this function out (JSON file, API call, DB query) to drive the same
    render_document_checklist() component from a different data source.
    """
    categories = []

    categories.append({
        "name": "Application & Consent",
        "items": [{"text": d} for d in GENERAL_APPLICATION_DOCS],
    })

    # Identification — one item per borrower per required ID document
    id_items = []
    for idx in range(st.session_state.borrower_count):
        name = borrower_display_name(idx)
        for doc in PER_BORROWER_ID_DOCS:
            id_items.append({"applicant": name, "text": doc})
    if id_items:
        categories.append({"name": "Identification", "items": id_items})

    # Down Payment — one item per selected source per its required document
    dp_items = []
    for key in st.session_state.selected_sources:
        src = next((s for s in DOWN_PAYMENT_SOURCES if s["key"] == key), None)
        if src:
            for doc in src["documents"]:
                dp_items.append({"subcategory": src["label"], "text": doc})
    if dp_items:
        categories.append({"name": "Down Payment", "items": dp_items})

    # Income — one item per borrower per selected income source per document
    income_items = []
    for idx in range(st.session_state.borrower_count):
        bidx = str(idx)
        name = borrower_display_name(idx)
        for key in st.session_state.income_selected.get(bidx, []):
            src = get_income_source(key)
            if src:
                for doc in src["documents"]:
                    income_items.append({"applicant": name, "subcategory": src["label"], "text": doc})
    if income_items:
        categories.append({"name": "Income", "items": income_items})

    categories.append({
        "name": "Property Being Purchased",
        "items": [{"text": d} for d in SUBJECT_PROPERTY_DOCS],
    })

    # Other Properties Owned — one item per property per standard doc label
    other_prop_items = []
    for pidx, prop in enumerate(st.session_state.properties):
        label = prop["address"].strip() if prop["address"].strip() else "Property " + str(pidx + 1)
        for doc in OTHER_PROPERTY_DOC_LABELS:
            other_prop_items.append({"subcategory": label, "text": doc})
    if other_prop_items:
        categories.append({"name": "Other Properties Owned", "items": other_prop_items})

    # Other Debts & Liabilities — one item per selected debt type per document
    debt_items = []
    for key in st.session_state.debt_selected:
        dt = get_debt_type(key)
        if dt:
            for doc in dt["documents"]:
                debt_items.append({"subcategory": dt["label"], "text": doc})
    if debt_items:
        categories.append({"name": "Other Debts & Liabilities", "items": debt_items})

    return {"categories": categories}


def group_checklist_items(items):
    """
    Groups a category's flat items by (applicant, subcategory), preserving
    first-seen order. Items with neither field form their own group with
    a None key, so they render directly under the category with no
    sub-heading (e.g. the plain "Application & Consent" docs).
    """
    order = []
    grouped = {}
    for item in items:
        key = (item.get("applicant"), item.get("subcategory"))
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(item)
    return [(key, grouped[key]) for key in order]


def render_document_checklist(data):
    """
    Generic renderer for the checklist schema described above. Doesn't know
    or care where `data` came from — any dict matching the schema renders
    the same way. Returns the total item count.

    Hierarchy: Category (bold heading) -> applicant/subcategory (indented
    sub-heading, when present) -> individual required documents (indented
    further beneath their sub-heading).
    """
    st.markdown("### Required Documentation")

    total_count = 0
    categories = data.get("categories", [])
    for category in categories:
        items = category.get("items", [])
        if not items:
            continue
        total_count += len(items)
        st.markdown(
            "<div style='font-size:18px; font-weight:700; margin-top:14px; margin-bottom:6px;'>"
            + category.get("name", "") + " (" + str(len(items)) + ")</div>",
            unsafe_allow_html=True,
        )

        for (applicant, subcategory), group_items in group_checklist_items(items):
            if applicant or subcategory:
                heading_parts = []
                if applicant:
                    heading_parts.append("<b>" + applicant + "</b>")
                if subcategory:
                    heading_parts.append(subcategory)
                st.markdown(
                    "<div style='margin-left:20px; font-weight:600; margin-top:8px; margin-bottom:2px;'>"
                    + " — ".join(heading_parts) + "</div>",
                    unsafe_allow_html=True,
                )
                item_indent = 40
            else:
                item_indent = 20

            for item in group_items:
                st.markdown(
                    "<div style='margin-left:" + str(item_indent) + "px; margin-bottom:2px;'>"
                    "☐ " + item["text"] + "</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")

    return total_count


def serialize_checklist_text(data):
    """Plain-text version of the same hierarchy, matching the on-screen format exactly."""
    lines = ["Required Documentation"]
    for category in data.get("categories", []):
        items = category.get("items", [])
        if not items:
            continue
        lines.append(category.get("name", "") + " (" + str(len(items)) + ")")

        for (applicant, subcategory), group_items in group_checklist_items(items):
            if applicant or subcategory:
                heading_parts = [p for p in [applicant, subcategory] if p]
                lines.append(" — ".join(heading_parts))
            for item in group_items:
                lines.append("☐ " + item["text"])

    return "\n".join(lines)


def checklist_item_key(category_name, item):
    """Stable identifier for one checklist item, used to track removals across reruns/saves."""
    return category_name + "||" + (item.get("applicant") or "") + "||" + (item.get("subcategory") or "") + "||" + item["text"]


def filter_checklist_data(data, removed_keys):
    """Returns a copy of the checklist data with any previously-removed items stripped out."""
    removed_set = set(removed_keys)
    filtered = []
    for category in data.get("categories", []):
        name = category.get("name", "")
        kept_items = [it for it in category.get("items", []) if checklist_item_key(name, it) not in removed_set]
        filtered.append({"name": name, "items": kept_items})
    return {"categories": filtered}


def render_document_checklist_editable(data):
    """
    Edit-mode view: every item gets a checkbox (checked = keep). Unchecking
    and saving permanently removes that item from the checklist. Returns
    the set of item-keys the user unchecked in this pass.
    """
    unchecked_keys = set()
    for category in data.get("categories", []):
        items = category.get("items", [])
        if not items:
            continue
        st.markdown(
            "<div style='font-size:18px; font-weight:700; margin-top:14px; margin-bottom:6px;'>"
            + category.get("name", "") + " (" + str(len(items)) + ")</div>",
            unsafe_allow_html=True,
        )
        for (applicant, subcategory), group_items in group_checklist_items(items):
            if applicant or subcategory:
                heading_parts = []
                if applicant:
                    heading_parts.append("<b>" + applicant + "</b>")
                if subcategory:
                    heading_parts.append(subcategory)
                st.markdown(
                    "<div style='margin-left:20px; font-weight:600; margin-top:8px; margin-bottom:2px;'>"
                    + " — ".join(heading_parts) + "</div>",
                    unsafe_allow_html=True,
                )
                indent_col = st.columns([1, 19])[1]
            else:
                indent_col = st.columns([1, 19])[1]

            for item in group_items:
                key = checklist_item_key(category.get("name", ""), item)
                with indent_col:
                    keep = st.checkbox(item["text"], value=True, key="doc_edit_" + key)
                if not keep:
                    unchecked_keys.add(key)
    return unchecked_keys


def render_documents():
    spacer, back_col, continue_col = st.columns([3, 1, 1])

    with back_col:
        if st.button("← Back", use_container_width=True, key="p7_back_top"):
            st.session_state.step = 5
            st.rerun()
    with continue_col:
        continue_top = st.button("Continue →", type="primary", use_container_width=True, key="p7_continue_top")

    render_calculator_popover("documents")
    raw_checklist_data = build_document_checklist_data()
    checklist_data = filter_checklist_data(raw_checklist_data, st.session_state.doc_removed_items)

    always_present = ("Application & Consent", "Property Being Purchased")
    has_client_specific_items = any(
        cat.get("items") for cat in checklist_data["categories"] if cat.get("name") not in always_present
    )
    if not has_client_specific_items:
        st.info(
            "This list will fill in as you complete the earlier steps — right now it only shows the "
            "documents that always apply (application/consent and the property being purchased)."
        )

    if st.session_state.doc_removed_items:
        st.caption(str(len(st.session_state.doc_removed_items)) + " item(s) manually removed from this checklist.")

    if not st.session_state.doc_edit_mode:
        edit_col, _ = st.columns([1, 3])
        with edit_col:
            if st.button("✏️ Edit List", use_container_width=True, key="doc_edit_toggle_on"):
                st.session_state.doc_edit_mode = True
                st.rerun()

        total_count = render_document_checklist(checklist_data)

        st.divider()
        st.markdown("#### Total Documents Required: " + str(total_count))

        st.download_button(
            "Download Checklist (.txt)",
            data=serialize_checklist_text(checklist_data),
            file_name="required_documents_checklist.txt",
            mime="text/plain",
        )
    else:
        st.warning("**Edit mode:** uncheck any item you want to permanently remove, then Save. This cannot be undone from within this page.")
        unchecked_keys = render_document_checklist_editable(checklist_data)

        st.divider()
        save_col, cancel_col = st.columns(2)
        with save_col:
            if st.button("💾 Save Changes", type="primary", use_container_width=True, key="doc_save_edits"):
                st.session_state["doc_pending_removal"] = list(unchecked_keys)
                st.session_state["doc_show_save_confirm"] = True
        with cancel_col:
            if st.button("Cancel", use_container_width=True, key="doc_cancel_edits"):
                st.session_state.doc_edit_mode = False
                st.rerun()

        if st.session_state.get("doc_show_save_confirm"):
            pending = st.session_state.get("doc_pending_removal", [])
            if pending:
                st.warning(
                    "Are you sure you want to permanently remove " + str(len(pending)) + " item(s) from this "
                    "checklist? This cannot be undone (unless you re-check the item's original selection, which "
                    "won't bring it back — you'd need to clear removals via a fresh Refresh)."
                )
            else:
                st.info("No items were unchecked — nothing will be removed.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm & Save", type="primary", use_container_width=True, key="doc_confirm_save"):
                    existing = set(st.session_state.doc_removed_items)
                    existing.update(pending)
                    st.session_state.doc_removed_items = list(existing)
                    st.session_state.doc_edit_mode = False
                    st.session_state["doc_show_save_confirm"] = False
                    st.rerun()
            with c2:
                if st.button("Cancel", use_container_width=True, key="doc_cancel_save"):
                    st.session_state["doc_show_save_confirm"] = False
                    st.rerun()

    st.divider()

    if st.button("🔄 Refresh Page", use_container_width=False, key="p7_refresh"):
        st.session_state["p7_show_refresh_confirm"] = True

    notes_col = st.columns([1])[0]
    with notes_col:
        if st.button("Notes →", use_container_width=True, key="p7_to_notes"):
            st.session_state.step = 7
            st.rerun()

    if st.session_state.get("p7_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data across all pages will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p7_confirm_refresh"):
                refresh_all()
                st.session_state["p7_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p7_cancel_refresh"):
                st.session_state["p7_show_refresh_confirm"] = False
                st.rerun()

    if continue_top:
        st.session_state.step = 7
        st.rerun()


def build_system_notes():
    """
    Compiles a structured, deterministic narrative summary from everything
    entered in the application — personal details, down payment source,
    income source, the property, and GDS/TDS — for the underwriter to read
    alongside the broker's own notes. This is a rules-based compilation of
    the application's own data, not a live AI model call (this app has no
    LLM API connected) — it's built to read like a summary a broker would
    write, sourced entirely from what's on file.
    """
    lines = []

    # --- Borrowers ---
    borrower_bits = []
    for idx in range(st.session_state.borrower_count):
        b = st.session_state.borrowers[idx]
        name = b["full_name"].strip() if b["full_name"].strip() else "Borrower " + str(idx + 1)
        details = []
        if b.get("marital_status"):
            details.append(b["marital_status"].lower())
        if b.get("dob"):
            age = (date.today() - b["dob"]).days // 365
            details.append(str(age) + " years old")
        detail_str = " (" + ", ".join(details) + ")" if details else ""
        borrower_bits.append(name + detail_str)
    if borrower_bits:
        lines.append(
            "APPLICANT(S): This application includes " + str(st.session_state.borrower_count)
            + " borrower(s): " + "; ".join(borrower_bits) + "."
        )

    # --- Down payment source ---
    dp_amount = parse_money(st.session_state.down_payment_raw) or 0.0
    purchase_price = parse_money(st.session_state.purchase_price_raw) or 0.0
    dp_sources = []
    for key in st.session_state.selected_sources:
        src = next((s for s in DOWN_PAYMENT_SOURCES if s["key"] == key), None)
        if src:
            amt = parse_money(st.session_state.source_amounts.get(key, "")) or 0.0
            dp_sources.append(src["label"] + " (" + fmt_money(amt) + ")")
    if purchase_price or dp_sources:
        dp_pct = (dp_amount / purchase_price * 100) if purchase_price else None
        pct_str = " ({:.1f}% of purchase price)".format(dp_pct) if dp_pct is not None else ""
        source_str = ", ".join(dp_sources) if dp_sources else "not yet specified"
        lines.append(
            "DOWN PAYMENT: " + fmt_money(dp_amount) + pct_str + " on a purchase price of " + fmt_money(purchase_price)
            + ". Source(s): " + source_str + "."
        )

    # --- Income ---
    income_bits = []
    for idx in range(st.session_state.borrower_count):
        name = borrower_display_name(idx)
        bidx = str(idx)
        sources_for_borrower = []
        for key in st.session_state.income_selected.get(bidx, []):
            src = get_income_source(key)
            if src:
                sources_for_borrower.append(src["label"])
        if sources_for_borrower:
            income_bits.append(name + ": " + ", ".join(sources_for_borrower))
    total_income = compute_total_income()
    if income_bits:
        lines.append(
            "INCOME: Combined gross annual income of " + fmt_money(total_income) + ". "
            + " | ".join(income_bits) + "."
        )

    # --- Property ---
    prop_bits = []
    if st.session_state.subject_address.strip():
        prop_bits.append(st.session_state.subject_address.strip())
    if st.session_state.subject_prop_type:
        prop_bits.append(st.session_state.subject_prop_type)
    if st.session_state.subject_prop_purpose:
        prop_bits.append(st.session_state.subject_prop_purpose)
    if st.session_state.subject_prop_age:
        prop_bits.append("age: " + st.session_state.subject_prop_age)
    if st.session_state.subject_sqft:
        prop_bits.append(st.session_state.subject_sqft + " sqft")
    if prop_bits:
        lines.append("SUBJECT PROPERTY: " + ", ".join(prop_bits) + ".")

    # --- GDS/TDS ---
    pi_payment, taxes, condo, heat, _ = get_subject_property_costs()
    other_debt_monthly = 0.0
    for dkey in st.session_state.debt_selected:
        dt = get_debt_type(dkey)
        amounts = st.session_state.debt_amounts.get(dkey, {})
        other_debt_monthly += compute_debt_payment(dt, amounts)
    for prop in st.session_state.properties:
        p_total, _, _, _, _ = compute_property_total(prop)
        other_debt_monthly += p_total

    gds, tds, _, _ = compute_gds_tds(pi_payment, taxes, heat, condo, other_debt_monthly, total_income)
    qualifying_rate = max(st.session_state.contract_rate + STRESS_TEST_ADDON, st.session_state.benchmark_rate)
    purchase_price_v = parse_money(st.session_state.purchase_price_raw) or 0.0
    down_payment_v = parse_money(st.session_state.down_payment_raw) or 0.0
    loan_amount = max(purchase_price_v - down_payment_v, 0.0)
    stressed_pi = monthly_mortgage_payment(loan_amount, qualifying_rate, st.session_state.amortization_years)
    stressed_gds, stressed_tds, _, _ = compute_gds_tds(stressed_pi, taxes, heat, condo, other_debt_monthly, total_income)

    if gds is not None and tds is not None:
        qualifies = gds <= GDS_LIMIT and tds <= TDS_LIMIT
        stress_qualifies = stressed_gds is not None and stressed_tds is not None and stressed_gds <= GDS_LIMIT and stressed_tds <= TDS_LIMIT
        lines.append(
            "GDS/TDS: At the contract rate of {:.2f}%, GDS is {:.2f}% and TDS is {:.2f}% (limits: {:.0f}%/{:.0f}%) — {}. "
            "Stressed at the qualifying rate of {:.2f}%, GDS is {} and TDS is {} — {}.".format(
                st.session_state.contract_rate, gds, tds, GDS_LIMIT, TDS_LIMIT,
                "within limits" if qualifies else "exceeds limits",
                qualifying_rate,
                "{:.2f}%".format(stressed_gds) if stressed_gds is not None else "—",
                "{:.2f}%".format(stressed_tds) if stressed_tds is not None else "—",
                "within limits" if stress_qualifies else "exceeds limits",
            )
        )

    if not lines:
        return "No application data entered yet — complete the earlier steps to generate a summary."
    return "\n\n".join(lines)


def render_notes():
    spacer, back_col, continue_col = st.columns([3, 1, 1])

    with back_col:
        if st.button("← Back", use_container_width=True, key="p8_back_top"):
            st.session_state.step = 6
            st.rerun()
    with continue_col:
        st.write("")  # No more pages, so no Continue button

    st.markdown("### Notes for Underwriter")
    render_calculator_popover("notes")
    st.write(
        "A system-compiled summary of the application below, plus space for the broker's own notes. "
        "Combine them into one final note for the file."
    )

    with st.container(key="notes_font_scope"):
        with st.expander("System-Generated Summary (from application data)", expanded=True):
            system_notes = build_system_notes()
            st.markdown(system_notes.replace("\n", "  \n"))

        st.divider()

        st.markdown("#### Broker's Notes")
        st.session_state.broker_notes = st.text_area(
            "Add any context the system can't infer — client's story, special circumstances, verbal explanations, etc.",
            value=st.session_state.broker_notes, height=150, key="broker_notes_input",
        )

        st.caption(
            "Note: this app isn't connected to a live AI model — \"Combine Notes\" below merges the system "
            "summary and your notes into one clean file note using a fixed format, not generative rewriting."
        )
        if st.button("🧩 Combine Notes", type="primary", use_container_width=True, key="combine_notes_btn"):
            combined = "UNDERWRITER FILE NOTE\n" + "=" * 40 + "\n\n"
            combined += "SYSTEM-GENERATED SUMMARY\n" + "-" * 40 + "\n" + system_notes + "\n\n"
            combined += "BROKER'S NOTES\n" + "-" * 40 + "\n"
            combined += st.session_state.broker_notes.strip() if st.session_state.broker_notes.strip() else "(none provided)"
            st.session_state.combined_notes = combined
            st.success("Notes combined below — feel free to edit before downloading.")

        if st.session_state.combined_notes:
            st.divider()
            st.markdown("#### Combined File Note")
            st.session_state.combined_notes = st.text_area(
                "Final note (editable)", value=st.session_state.combined_notes, height=300, key="combined_notes_editor",
                label_visibility="collapsed",
            )
            st.download_button(
                "Download File Note (.txt)",
                data=st.session_state.combined_notes,
                file_name="underwriter_file_note.txt",
                mime="text/plain",
            )

    st.divider()

    if st.button("🔄 Refresh Page", use_container_width=False, key="p8_refresh"):
        st.session_state["p8_show_refresh_confirm"] = True

    if st.session_state.get("p8_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data across all pages will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p8_confirm_refresh"):
                refresh_all()
                st.session_state["p8_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p8_cancel_refresh"):
                st.session_state["p8_show_refresh_confirm"] = False
                st.rerun()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

if st.session_state.step == 0:
    render_client_details()
elif st.session_state.step == 1:
    render_down_payment()
elif st.session_state.step == 2:
    render_property_details()
elif st.session_state.step == 3:
    render_income()
elif st.session_state.step == 4:
    render_debts()
elif st.session_state.step == 5:
    render_analysis()
elif st.session_state.step == 6:
    render_documents()
elif st.session_state.step == 7:
    render_notes()
