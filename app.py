import re
from datetime import date

import streamlit as st

from downpayment_sources import DOWN_PAYMENT_SOURCES

# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")

GENDER_OPTIONS = ["", "Male", "Female", "Other", "Prefer not to say"]
MARITAL_OPTIONS = ["", "Single", "Married", "Divorced", "Widowed", "Common-Law"]

STEPS = ["Client Details", "Down Payment", "Income", "Debts", "Analysis"]


def fmt_money(value):
    try:
        return "${:,.0f}".format(value)
    except (TypeError, ValueError):
        return "—"


def parse_money(raw):
    """Parses a user-entered numeric string (may contain $ and commas) into a float, or None."""
    if raw is None:
        return None
    cleaned = str(raw).replace("$", "").replace(",", "").strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Session state setup
# ---------------------------------------------------------------------------

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


def init_state():
    if "step" not in st.session_state:
        st.session_state.step = 0

    # Page 1 state
    if "borrower_count" not in st.session_state:
        st.session_state.borrower_count = 1
    if "borrowers" not in st.session_state:
        st.session_state.borrowers = [empty_borrower()]
    if "consent" not in st.session_state:
        st.session_state.consent = False
    if "borrower_errors" not in st.session_state:
        st.session_state.borrower_errors =
