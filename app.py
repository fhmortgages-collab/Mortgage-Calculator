import re
import json
import ast
import time
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from downpayment_sources import DOWN_PAYMENT_SOURCES
DOWN_PAYMENT_SOURCES_BY_KEY = {s["key"]: s for s in DOWN_PAYMENT_SOURCES}
from income_sources import INCOME_SOURCES

INCOME_SOURCES_ALPHA = sorted(INCOME_SOURCES, key=lambda s: s["label"])
from debt_types import DEBT_TYPES
from switch_in_rules import (
    MORTGAGE_TYPES,
    SWITCH_TIMING_OPTIONS,
    CONVENTIONAL_MAX_LTV,
    is_straight_switch,
    requires_discharge_and_reregistration,
    determine_qualifying_path,
    switch_in_document_requirements,
)
from builder_rules import (
    MORTGAGE_PRODUCT_OPTIONS,
    BUILDER_TYPE_OPTIONS,
    INTEREST_RATE_TYPE_OPTIONS,
    CASHBACK_PROGRAM_OPTIONS,
    CASHBACK_ELIGIBLE_PROGRAMS,
    is_amortization_valid,
    calculate_gst_hst_adjusted_price,
    is_cashback_eligible,
    builder_document_requirements,
)
from refinance_rules import (
    equity_requirement_note,
    ltv_calculation_note,
    determine_amortization_increase,
    change_of_borrower_note,
    high_risk_review_note,
)

# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")

GENDER_OPTIONS = ["", "Male", "Female", "Other", "Prefer not to say"]
MARITAL_OPTIONS = ["", "Single", "Married", "Divorced", "Widowed", "Common-Law"]
RESIDENCE_STATUS_OPTIONS = ["", "Owned", "Rented", "Living with Parents/Family", "Other"]
RESIDENCE_DISPOSITION_OPTIONS = [
    "", "Sold — Firm Sale", "Sold — Conditional Sale", "Currently Listed for Sale", "To Be Listed / Sold",
    "Keeping as Primary Residence", "Keeping as Primary Residence (with Rental Unit/Suite)",
    "Converting to Rental Property", "Keeping as Secondary/Vacation Home",
    "Currently Rented — Lease Continuing", "Currently Rented — Lease Ending",
    "Rent-to-Own Arrangement", "Gifted / Transferred to Family",
    "Bridge Financing Required", "Still Deciding", "Not Applicable", "Other",
]
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
FOUNDATION_TYPE_OPTIONS = [
    "", "Poured Concrete", "Concrete Block", "Stone", "Preserved Wood (PWF)",
    "Slab-on-Grade", "Crawl Space", "Pier & Post", "Other",
]
EXTERIOR_FINISH_OPTIONS = [
    "", "Brick", "Brick Veneer", "Vinyl Siding", "Stucco", "Stone", "Stone Veneer",
    "Wood Siding", "Aluminum/Steel Siding", "Fiber Cement (Hardie Board)", "Other",
]
GARAGE_OPTIONS = ["", "None", "Attached", "Detached", "Carport", "Underground Parking", "Other"]
PROPERTY_STATUS_OPTIONS = [
    "", "Keeping — Primary Residence", "Keeping — Primary Residence with Rental Unit (Secondary Suite)",
    "Keeping — Second Home / Cottage", "Keeping — Investment Property",
    "Converting — Owner-Occupied (Primary) to Rental", "Converting — Second Home / Cottage to Rental",
    "Converting — Investment Property to Owner-Occupied", "Converting — Investment Property to Second Home / Cottage",
    "Being Sold — Firm (Unconditional) Sale Agreement", "Being Sold — Not Yet Firm / Listed Only",
]

STEPS = ["Deal", "Client", "Down Payment", "Property", "Income", "Debts", "Analysis", "Docs", "Notes"]

TRANSACTION_TYPE_OPTIONS = [
    {
        "key": "purchase",
        "label": "Purchase",
        "description": "Buying an existing resale property from a seller.",
    },
    {
        "key": "builder_purchase",
        "label": "Builder Purchase",
        "description": "Buying a newly built property directly from a builder or developer.",
    },
    {
        "key": "refinance_existing_lender",
        "label": "Refinance — Existing Lender",
        "description": "Refinancing the current mortgage with the same lender already on title.",
    },
    {
        "key": "refinance_new_lender",
        "label": "Switch",
        "description": "Refinancing (switching) the mortgage to a different lender than the one currently on title.",
    },
]

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
        return "${:,.2f}".format(value)
    except (TypeError, ValueError):
        return "—"


def fmt_money_md(value):
    """Same as fmt_money, but with the $ escaped for use inside st.markdown/st.caption/
    st.write text. Streamlit's markdown renderer treats a pair of literal $ characters
    in the same string as LaTeX math delimiters, which silently mangles the output
    whenever two or more dollar amounts land in the same line — use this any time
    more than one fmt_money() result is combined into one markdown string."""
    return fmt_money(value).replace("$", "\\$")


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


def money_text_input(label, value, key, placeholder=None):
    """
    A text_input for dollar amounts that displays the stored value reformatted
    as $X,XXX.XX (once it parses as a number) instead of a bare number string,
    so the field itself always reads like a dollar amount, not raw digits.
    Returns the new raw string — store it back into session_state as usual.
    """
    parsed = parse_money(value)
    display_value = fmt_money(parsed) if parsed is not None else value
    kwargs = {"key": key}
    if placeholder is not None:
        kwargs["placeholder"] = placeholder
    return st.text_input(label, value=display_value, **kwargs)


def render_missing_fields_warning(missing_items):
    """Shows a consolidated warning listing everything still needed before continuing, if anything is missing."""
    if missing_items:
        st.warning(
            "**Before continuing, please complete:**\n\n"
            + "\n".join("- " + item for item in missing_items)
        )


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
    A compact quick-calculator, rendered in the sidebar rather than as a
    CSS-pinned floating button — Streamlit's internal DOM structure can
    silently break `position: fixed` (ancestor transforms change the
    containing block), so the sidebar is the reliable way to keep this
    visible on screen at all times regardless of scroll position.
    """
    with st.sidebar:
        with st.expander("🧮 Calculator", expanded=False):
            expr = st.text_input(
                "Expression", key=key_prefix + "_calc_expr", placeholder="1200 + 350*12",
                label_visibility="collapsed",
            )
            if expr.strip():
                try:
                    result = safe_calculate(expr)
                    st.markdown(
                        "<div style='text-align:center; font-weight:700;'>= " + "{:,.2f}".format(result) + "</div>",
                        unsafe_allow_html=True,
                    )
                except (ValueError, ZeroDivisionError, SyntaxError, TypeError):
                    st.markdown(
                        "<div style='text-align:center; color:#ef4444;'>Invalid expression</div>",
                        unsafe_allow_html=True,
                    )


def empty_borrower():
    return {
        "full_name": "",
        "dob": None,
        "gender": "",
        "marital_status": "",
        "phone": "",
        "email": "",
        "address": "",
        "residence_status": "",
        "residence_status_other": "",
        "residence_disposition": "",
        "residence_disposition_other": "",
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
        "status": "",
        "property_value": "",
        "num_mortgages": "",
        "mortgages": [],
    }


def init_state():
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "visited_steps" not in st.session_state:
        st.session_state.visited_steps = set()
    if "app_start_time" not in st.session_state:
        st.session_state.app_start_time = time.time()
    if "app_completed_seconds" not in st.session_state:
        st.session_state.app_completed_seconds = None
    if "app_is_paused" not in st.session_state:
        st.session_state.app_is_paused = False
    if "app_paused_elapsed" not in st.session_state:
        st.session_state.app_paused_elapsed = 0.0
    if "transaction_type" not in st.session_state:
        st.session_state.transaction_type = ""
    if "transaction_type_error" not in st.session_state:
        st.session_state.transaction_type_error = ""
    if "client_intake_notes" not in st.session_state:
        st.session_state.client_intake_notes = ""
    if "discrepancies_notes" not in st.session_state:
        st.session_state.discrepancies_notes = ""
    if "discrepancy_entries" not in st.session_state:
        st.session_state.discrepancy_entries = []
    if "doc_removed_items" not in st.session_state:
        st.session_state.doc_removed_items = []
    if "doc_edit_mode" not in st.session_state:
        st.session_state.doc_edit_mode = False
    if "docs_reviewed" not in st.session_state:
        st.session_state.docs_reviewed = False
    if "doc_text_overrides" not in st.session_state:
        st.session_state.doc_text_overrides = {}
    if "doc_custom_items" not in st.session_state:
        st.session_state.doc_custom_items = {}
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
    if "refinance_balance_raw" not in st.session_state:
        st.session_state.refinance_balance_raw = ""
    if "refinance_remaining_amortization" not in st.session_state:
        st.session_state.refinance_remaining_amortization = ""
    if "subject_property_value_raw" not in st.session_state:
        st.session_state.subject_property_value_raw = ""
    if "selected_sources" not in st.session_state:
        st.session_state.selected_sources = []
    if "source_amounts" not in st.session_state:
        st.session_state.source_amounts = {}
    if "source_details" not in st.session_state:
        st.session_state.source_details = {}
    if "other_source_desc" not in st.session_state:
        st.session_state.other_source_desc = ""
    if "dp_errors" not in st.session_state:
        st.session_state.dp_errors = {}
    if "income_selected" not in st.session_state:
        st.session_state.income_selected = {}
    if "income_counts" not in st.session_state:
        st.session_state.income_counts = {}
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
    if "subject_has_rental_component" not in st.session_state:
        st.session_state.subject_has_rental_component = ""
    if "subject_num_units" not in st.session_state:
        st.session_state.subject_num_units = ""
    if "property_appraisal_type" not in st.session_state:
        st.session_state.property_appraisal_type = ""
    if "property_appraisal_ordered" not in st.session_state:
        st.session_state.property_appraisal_ordered = False
    if "property_appraisal_value_raw" not in st.session_state:
        st.session_state.property_appraisal_value_raw = ""
    if "property_purchase_channel" not in st.session_state:
        st.session_state.property_purchase_channel = ""
    if "property_mls_link" not in st.session_state:
        st.session_state.property_mls_link = ""
    if "property_details_method" not in st.session_state:
        st.session_state.property_details_method = ""
    if "mls_autofill_status" not in st.session_state:
        st.session_state.mls_autofill_status = ""
    if "mls_autofilled_fields" not in st.session_state:
        st.session_state.mls_autofilled_fields = []
    if "subject_rental_kitchen" not in st.session_state:
        st.session_state.subject_rental_kitchen = False
    if "subject_rental_bathroom" not in st.session_state:
        st.session_state.subject_rental_bathroom = False
    if "subject_rental_entrance" not in st.session_state:
        st.session_state.subject_rental_entrance = False
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
    if "subject_foundation_other" not in st.session_state:
        st.session_state.subject_foundation_other = ""
    if "subject_exterior_finish" not in st.session_state:
        st.session_state.subject_exterior_finish = ""
    if "subject_exterior_finish_other" not in st.session_state:
        st.session_state.subject_exterior_finish_other = ""
    if "subject_garage_other" not in st.session_state:
        st.session_state.subject_garage_other = ""
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
    if "subject_title_type_other" not in st.session_state:
        st.session_state.subject_title_type_other = ""
    if "subject_prop_type_other" not in st.session_state:
        st.session_state.subject_prop_type_other = ""
    if "subject_heating_type_other" not in st.session_state:
        st.session_state.subject_heating_type_other = ""
    if "subject_sewer_other" not in st.session_state:
        st.session_state.subject_sewer_other = ""
    if "subject_water_other" not in st.session_state:
        st.session_state.subject_water_other = ""
    # --- Switch-in (Refinance - New Lender) fields ---
    if "switch_ofi_name" not in st.session_state:
        st.session_state.switch_ofi_name = ""
    if "switch_ofi_is_frfi" not in st.session_state:
        st.session_state.switch_ofi_is_frfi = ""
    if "switch_reg_type" not in st.session_state:
        st.session_state.switch_reg_type = "Traditional Mortgage"
    if "switch_mortgage_type" not in st.session_state:
        st.session_state.switch_mortgage_type = ""
    if "switch_timing" not in st.session_state:
        st.session_state.switch_timing = ""
    if "switch_current_balance_raw" not in st.session_state:
        st.session_state.switch_current_balance_raw = ""
    if "switch_remaining_amortization" not in st.session_state:
        st.session_state.switch_remaining_amortization = ""
    if "switch_amortization_unchanged" not in st.session_state:
        st.session_state.switch_amortization_unchanged = ""
    if "switch_additional_funds" not in st.session_state:
        st.session_state.switch_additional_funds = ""
    if "switch_amortization_changed" not in st.session_state:
        st.session_state.switch_amortization_changed = ""
    if "switch_borrowers_changed" not in st.session_state:
        st.session_state.switch_borrowers_changed = ""
    if "switch_lender_count" not in st.session_state:
        st.session_state.switch_lender_count = "1"
    if "switch_lender2_name" not in st.session_state:
        st.session_state.switch_lender2_name = ""
    if "switch_lender2_is_frfi" not in st.session_state:
        st.session_state.switch_lender2_is_frfi = ""
    if "switch_lender2_reg_type" not in st.session_state:
        st.session_state.switch_lender2_reg_type = "Traditional Mortgage"
    if "switch_lender2_mortgage_type" not in st.session_state:
        st.session_state.switch_lender2_mortgage_type = ""
    if "switch_lender2_balance_raw" not in st.session_state:
        st.session_state.switch_lender2_balance_raw = ""
    if "switch_lender3_name" not in st.session_state:
        st.session_state.switch_lender3_name = ""
    if "switch_lender3_is_frfi" not in st.session_state:
        st.session_state.switch_lender3_is_frfi = ""
    if "switch_lender3_reg_type" not in st.session_state:
        st.session_state.switch_lender3_reg_type = "Traditional Mortgage"
    if "switch_lender3_mortgage_type" not in st.session_state:
        st.session_state.switch_lender3_mortgage_type = ""
    if "switch_lender3_balance_raw" not in st.session_state:
        st.session_state.switch_lender3_balance_raw = ""
    if "switch_lender4_name" not in st.session_state:
        st.session_state.switch_lender4_name = ""
    if "switch_lender4_is_frfi" not in st.session_state:
        st.session_state.switch_lender4_is_frfi = ""
    if "switch_lender4_reg_type" not in st.session_state:
        st.session_state.switch_lender4_reg_type = "Traditional Mortgage"
    if "switch_lender4_mortgage_type" not in st.session_state:
        st.session_state.switch_lender4_mortgage_type = ""
    if "switch_lender4_balance_raw" not in st.session_state:
        st.session_state.switch_lender4_balance_raw = ""
    if "switch_requested_loan_amount_raw" not in st.session_state:
        st.session_state.switch_requested_loan_amount_raw = ""
    if "switch_amortization_change_years_raw" not in st.session_state:
        st.session_state.switch_amortization_change_years_raw = ""
    if "switch_additional_funds_amount_raw" not in st.session_state:
        st.session_state.switch_additional_funds_amount_raw = ""
    if "switch_mortgages_good_standing" not in st.session_state:
        st.session_state.switch_mortgages_good_standing = ""
    if "switch_taxes_up_to_date" not in st.session_state:
        st.session_state.switch_taxes_up_to_date = ""
    if "switch_insurance_provider" not in st.session_state:
        st.session_state.switch_insurance_provider = ""
    if "switch_insurance_good_standing" not in st.session_state:
        st.session_state.switch_insurance_good_standing = ""
    # --- Debt payout tracking (Refinance - New Lender) ---
    if "debt_payout_selected" not in st.session_state:
        st.session_state.debt_payout_selected = {}
    if "debt_payout_balance" not in st.session_state:
        st.session_state.debt_payout_balance = {}
    if "debt_paid_from_own_funds" not in st.session_state:
        st.session_state.debt_paid_from_own_funds = {}
    if "debt_type_checked" not in st.session_state:
        st.session_state.debt_type_checked = {}
    if "debt_counts" not in st.session_state:
        st.session_state.debt_counts = {}
    # --- Builder Purchase Program ---
    if "builder_name" not in st.session_state:
        st.session_state.builder_name = ""
    if "builder_code" not in st.session_state:
        st.session_state.builder_code = ""
    if "builder_type" not in st.session_state:
        st.session_state.builder_type = ""
    if "builder_warranty_provider" not in st.session_state:
        st.session_state.builder_warranty_provider = ""
    if "builder_mortgage_product" not in st.session_state:
        st.session_state.builder_mortgage_product = ""
    if "builder_amortization_years" not in st.session_state:
        st.session_state.builder_amortization_years = ""
    if "builder_interest_rate_type" not in st.session_state:
        st.session_state.builder_interest_rate_type = ""
    if "builder_gst_hst_included" not in st.session_state:
        st.session_state.builder_gst_hst_included = ""
    if "builder_gst_hst_percent_raw" not in st.session_state:
        st.session_state.builder_gst_hst_percent_raw = ""
    if "builder_cashback_requested" not in st.session_state:
        st.session_state.builder_cashback_requested = ""
    if "builder_cashback_program" not in st.session_state:
        st.session_state.builder_cashback_program = ""
    if "builder_rate_buydown" not in st.session_state:
        st.session_state.builder_rate_buydown = ""


SAVE_STATE_KEYS = [
    "step", "transaction_type", "borrower_count", "borrowers", "consent", "borrower_errors",
    "purchase_price_raw", "down_payment_raw", "selected_sources", "source_amounts", "source_details",
    "other_source_desc", "dp_errors",
    "income_selected", "income_counts", "income_amounts", "income_special", "income_other_desc", "income_errors",
    "properties", "debt_selected", "debt_amounts", "debt_other_desc", "debt_errors",
    "subject_address", "subject_taxes_raw", "subject_condo_raw", "subject_heat_raw",
    "subject_has_rental_component", "subject_rental_kitchen", "subject_rental_bathroom", "subject_rental_entrance",
    "subject_num_units",
    "property_appraisal_type", "property_appraisal_ordered", "property_appraisal_value_raw",
    "property_purchase_channel", "property_mls_link",
    "property_details_method", "mls_autofill_status", "mls_autofilled_fields",
    "subject_prop_type", "subject_prop_purpose", "subject_prop_age", "subject_garage",
    "subject_rural_urban", "subject_sqft", "subject_storeys", "subject_heating_type",
    "subject_cooling", "subject_foundation", "subject_foundation_other",
    "subject_exterior_finish", "subject_exterior_finish_other", "subject_garage_other", "subject_sewer",
    "subject_water", "subject_parking_spaces", "subject_land_size", "subject_title_type",
    "subject_title_type_other", "subject_prop_type_other", "subject_heating_type_other",
    "subject_sewer_other", "subject_water_other",
    "contract_rate", "amortization_years", "benchmark_rate", "doc_removed_items",
    "doc_text_overrides", "doc_custom_items", "docs_reviewed",
    "broker_notes", "combined_notes", "mortgage_term", "rate_type",
    "client_intake_notes", "discrepancies_notes", "discrepancy_entries",
    "switch_ofi_name", "switch_ofi_is_frfi", "switch_reg_type", "switch_mortgage_type",
    "switch_timing", "switch_current_balance_raw", "switch_remaining_amortization",
    "switch_amortization_unchanged", "switch_additional_funds",
    "switch_amortization_changed", "switch_borrowers_changed",
    "switch_amortization_change_years_raw", "switch_additional_funds_amount_raw",
    "switch_lender_count",
    "switch_lender2_name", "switch_lender2_is_frfi", "switch_lender2_reg_type",
    "switch_lender2_mortgage_type", "switch_lender2_balance_raw",
    "switch_lender3_name", "switch_lender3_is_frfi", "switch_lender3_reg_type",
    "switch_lender3_mortgage_type", "switch_lender3_balance_raw",
    "switch_lender4_name", "switch_lender4_is_frfi", "switch_lender4_reg_type",
    "switch_lender4_mortgage_type", "switch_lender4_balance_raw",
    "switch_requested_loan_amount_raw",
    "switch_mortgages_good_standing", "switch_taxes_up_to_date",
    "switch_insurance_provider", "switch_insurance_good_standing",
    "refinance_balance_raw", "refinance_remaining_amortization", "subject_property_value_raw",
    "debt_payout_selected", "debt_payout_balance", "debt_paid_from_own_funds",
    "debt_type_checked", "debt_counts",
    "builder_name", "builder_code", "builder_type", "builder_warranty_provider",
    "builder_mortgage_product", "builder_amortization_years", "builder_interest_rate_type",
    "builder_gst_hst_included", "builder_gst_hst_percent_raw", "builder_cashback_requested",
    "builder_cashback_program", "builder_rate_buydown",
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
    st.session_state.visited_steps = set()
    st.session_state.app_start_time = time.time()
    st.session_state.app_completed_seconds = None
    st.session_state.app_is_paused = False
    st.session_state.app_paused_elapsed = 0.0
    st.session_state.transaction_type = ""
    st.session_state.transaction_type_error = ""
    st.session_state.doc_removed_items = []
    st.session_state.doc_edit_mode = False
    st.session_state.docs_reviewed = False
    st.session_state.doc_text_overrides = {}
    st.session_state.doc_custom_items = {}
    st.session_state.broker_notes = ""
    st.session_state.combined_notes = ""
    st.session_state.client_intake_notes = ""
    st.session_state.discrepancies_notes = ""
    st.session_state.discrepancy_entries = []
    st.session_state.mortgage_term = "5 Year"
    st.session_state.rate_type = "Fixed"
    st.session_state.borrower_count = 1
    st.session_state.borrowers = [empty_borrower()]
    st.session_state.borrower_errors = [{}]
    st.session_state.consent = False
    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.refinance_balance_raw = ""
    st.session_state.refinance_remaining_amortization = ""
    st.session_state.subject_property_value_raw = ""
    st.session_state["amortization_synced_from"] = None
    st.session_state.selected_sources = []
    st.session_state.source_amounts = {}
    st.session_state.other_source_desc = ""
    st.session_state.dp_errors = {}
    st.session_state.income_selected = {}
    st.session_state.income_counts = {}
    st.session_state.income_amounts = {}
    st.session_state.income_special = {}
    st.session_state.income_other_desc = {}
    st.session_state.income_errors = {}
    st.session_state.properties = []
    st.session_state.debt_selected = []
    st.session_state.debt_amounts = {}
    st.session_state.debt_payout_selected = {}
    st.session_state.debt_payout_balance = {}
    st.session_state.debt_paid_from_own_funds = {}
    st.session_state.debt_type_checked = {}
    st.session_state.debt_counts = {}
    st.session_state.debt_other_desc = ""
    st.session_state.debt_errors = {}
    st.session_state.builder_name = ""
    st.session_state.builder_code = ""
    st.session_state.builder_type = ""
    st.session_state.builder_warranty_provider = ""
    st.session_state.builder_mortgage_product = ""
    st.session_state.builder_amortization_years = ""
    st.session_state.builder_interest_rate_type = ""
    st.session_state.builder_gst_hst_included = ""
    st.session_state.builder_gst_hst_percent_raw = ""
    st.session_state.builder_cashback_requested = ""
    st.session_state.builder_cashback_program = ""
    st.session_state.builder_rate_buydown = ""
    st.session_state.subject_address = ""
    st.session_state.subject_has_rental_component = ""
    st.session_state.subject_rental_kitchen = False
    st.session_state.subject_rental_bathroom = False
    st.session_state.subject_rental_entrance = False
    st.session_state.subject_num_units = ""
    st.session_state.property_appraisal_type = ""
    st.session_state.property_appraisal_ordered = False
    st.session_state.property_appraisal_value_raw = ""
    st.session_state.property_purchase_channel = ""
    st.session_state.property_mls_link = ""
    st.session_state.property_details_method = ""
    st.session_state.mls_autofill_status = ""
    st.session_state.mls_autofilled_fields = []
    st.session_state.subject_taxes_raw = ""
    st.session_state.subject_condo_raw = ""
    st.session_state.subject_heat_raw = ""
    st.session_state.subject_prop_type = ""
    st.session_state.subject_prop_purpose = ""
    st.session_state.subject_prop_age = ""
    st.session_state.subject_garage = ""
    st.session_state.subject_garage_other = ""
    st.session_state.subject_rural_urban = ""
    st.session_state.subject_sqft = ""
    st.session_state.subject_storeys = ""
    st.session_state.subject_heating_type = ""
    st.session_state.subject_cooling = ""
    st.session_state.subject_foundation = ""
    st.session_state.subject_foundation_other = ""
    st.session_state.subject_exterior_finish = ""
    st.session_state.subject_exterior_finish_other = ""
    st.session_state.subject_sewer = ""
    st.session_state.subject_water = ""
    st.session_state.subject_parking_spaces = ""
    st.session_state.subject_land_size = ""
    st.session_state.subject_title_type = ""
    st.session_state.subject_title_type_other = ""
    st.session_state.subject_prop_type_other = ""
    st.session_state.subject_heating_type_other = ""
    st.session_state.subject_sewer_other = ""
    st.session_state.subject_water_other = ""
    st.session_state.contract_rate = 5.0
    st.session_state.amortization_years = 25
    st.session_state.benchmark_rate = 5.25
    st.session_state.switch_ofi_name = ""
    st.session_state.switch_ofi_is_frfi = ""
    st.session_state.switch_reg_type = "Traditional Mortgage"
    st.session_state.switch_mortgage_type = ""
    st.session_state.switch_timing = ""
    st.session_state.switch_current_balance_raw = ""
    st.session_state.switch_remaining_amortization = ""
    st.session_state.switch_amortization_unchanged = ""
    st.session_state.switch_additional_funds = ""
    st.session_state.switch_amortization_changed = ""
    st.session_state.switch_borrowers_changed = ""
    st.session_state.switch_amortization_change_years_raw = ""
    st.session_state.switch_additional_funds_amount_raw = ""
    st.session_state.switch_lender_count = "1"
    st.session_state.switch_lender2_name = ""
    st.session_state.switch_lender2_is_frfi = ""
    st.session_state.switch_lender2_reg_type = "Traditional Mortgage"
    st.session_state.switch_lender2_mortgage_type = ""
    st.session_state.switch_lender2_balance_raw = ""
    st.session_state.switch_lender3_name = ""
    st.session_state.switch_lender3_is_frfi = ""
    st.session_state.switch_lender3_reg_type = "Traditional Mortgage"
    st.session_state.switch_lender3_mortgage_type = ""
    st.session_state.switch_lender3_balance_raw = ""
    st.session_state.switch_lender4_name = ""
    st.session_state.switch_lender4_is_frfi = ""
    st.session_state.switch_lender4_reg_type = "Traditional Mortgage"
    st.session_state.switch_lender4_mortgage_type = ""
    st.session_state.switch_lender4_balance_raw = ""
    st.session_state.switch_requested_loan_amount_raw = ""
    st.session_state.switch_mortgages_good_standing = ""
    st.session_state.switch_taxes_up_to_date = ""
    st.session_state.switch_insurance_provider = ""
    st.session_state.switch_insurance_good_standing = ""


def is_refinance():
    return st.session_state.transaction_type in ("refinance_existing_lender", "refinance_new_lender")


def get_loan_amount():
    """
    Purchase/Builder Purchase: purchase price - down payment.
    Refinance (both Existing Lender and New Lender): the loan amount the client is requesting
    (from the Lender Details step), falling back to Lender 1's balance if not entered.
    """
    if is_refinance():
        requested = parse_money(st.session_state.switch_requested_loan_amount_raw)
        if requested is not None:
            return requested
        return parse_money(st.session_state.switch_current_balance_raw) or 0.0
    purchase_price = parse_money(st.session_state.purchase_price_raw) or 0.0
    down_payment = parse_money(st.session_state.down_payment_raw) or 0.0
    return max(purchase_price - down_payment, 0.0)


def get_reference_property_value():
    """
    The property value to carry into Property Details' appraisal section — whatever was
    already entered elsewhere: purchase price for purchase/builder purchase, or the
    property value entered on the Lender Details step for either refinance type.
    """
    if is_refinance():
        return parse_money(st.session_state.subject_property_value_raw)
    return parse_money(st.session_state.purchase_price_raw)


def get_ltv_denominator():
    """
    The value used as the LTV denominator, per policy:
    - Refinance: strictly the Appraised Value.
    - Purchase: the lower of Appraised Value or Purchase Price — but only when an
      appraisal has actually been entered and it comes in lower; otherwise Purchase Price.
    """
    appraised = parse_money(st.session_state.property_appraisal_value_raw)
    if is_refinance():
        return appraised
    purchase_price = parse_money(st.session_state.purchase_price_raw)
    if appraised is not None and purchase_price is not None and appraised < purchase_price:
        return appraised
    return purchase_price


# Maps the field this app can attempt to auto-fill to a friendly label, used for highlighting.
MLS_AUTOFILL_TARGET_FIELDS = {
    "subject_prop_type": "Property Type",
    "subject_sqft": "Square Footage",
    "subject_storeys": "Number of Storeys",
    "subject_parking_spaces": "Total Parking Spaces",
}

MLS_AUTOFILL_PROPERTY_TYPE_KEYWORDS = {
    "semi-detached": "Semi-Detached", "semi detached": "Semi-Detached",
    "townhouse": "Townhouse", "town house": "Townhouse",
    "condo": "Condo / Apartment", "apartment": "Condo / Apartment",
    "duplex": "Duplex", "triplex": "Triplex",
    "bungalow": "Detached", "detached": "Detached",
}


def attempt_mls_autofill(url):
    """
    Best-effort attempt to read a few basic property characteristics off an MLS listing
    page by fetching its raw HTML and keyword/regex-matching common phrasing (square
    footage, storeys, parking spaces, property type).

    This is NOT a real MLS data integration — there's no licensed MLS/board API connected.
    Most listing sites render their key details client-side via JavaScript or actively
    block automated requests, so this frequently finds nothing at all. When that happens,
    it fails cleanly and the broker enters everything manually — that's expected, not a bug.

    Returns (found_fields_dict, error_message) — exactly one is populated.
    found_fields_dict maps session_state keys (from MLS_AUTOFILL_TARGET_FIELDS) to values.
    """
    if not url or not url.strip():
        return {}, "No MLS link entered."

    try:
        import requests
    except ImportError:
        return {}, "The 'requests' package isn't installed on this deployment."

    try:
        resp = requests.get(
            url.strip(), timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MortgageAppBot/1.0)"},
        )
    except Exception:
        return {}, "Could not reach that link — check that it's a valid, complete URL."

    if resp.status_code == 403:
        return {}, (
            "That site (realtor.ca and most other MLS/board listing sites) actively blocks automated "
            "requests like this one — that's the site's own bot protection, not something this app can "
            "get around. This is expected for most listing sites."
        )
    if resp.status_code == 404:
        return {}, "That link returned a 404 (page not found) — double check the URL."
    if resp.status_code >= 400:
        return {}, "That link returned an error (status " + str(resp.status_code) + ") — the site may be unreachable or blocking automated access."

    text = resp.text
    found = {}

    sqft_match = re.search(r'([\d,]{3,6})\s*(?:sq\.?\s?ft\.?|square feet|sqft)', text, re.IGNORECASE)
    if sqft_match:
        found["subject_sqft"] = sqft_match.group(1).replace(",", "")

    storeys_match = re.search(r'(\d)\s*(?:storeys?|stor(?:y|ies))', text, re.IGNORECASE)
    if storeys_match:
        found["subject_storeys"] = storeys_match.group(1)

    parking_match = re.search(r'(\d)\s*(?:parking spaces?|car garage)', text, re.IGNORECASE)
    if parking_match:
        found["subject_parking_spaces"] = parking_match.group(1)

    for keyword, prop_type in MLS_AUTOFILL_PROPERTY_TYPE_KEYWORDS.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            found["subject_prop_type"] = prop_type
            break

    if not found:
        return {}, (
            "No recognizable property details found on that page. Most listing sites load their "
            "details via JavaScript or block automated requests, so this often won't work — that's "
            "a limitation of the source page, not this app."
        )
    return found, None


def get_switch_total_mortgage_balance():
    """Sum of all mortgages/LOCs being paid out on the switch-in, across as many lenders as selected (1-4)."""
    total = parse_money(st.session_state.switch_current_balance_raw) or 0.0
    count = int(st.session_state.switch_lender_count) if st.session_state.switch_lender_count else 1
    if count >= 2:
        total += parse_money(st.session_state.switch_lender2_balance_raw) or 0.0
    if count >= 3:
        total += parse_money(st.session_state.switch_lender3_balance_raw) or 0.0
    if count >= 4:
        total += parse_money(st.session_state.switch_lender4_balance_raw) or 0.0
    return total


def get_switch_additional_lenders():
    """Returns a list of dicts (name, is_frfi, reg_type, mortgage_type, balance) for lenders 2-4."""
    count = int(st.session_state.switch_lender_count) if st.session_state.switch_lender_count else 1
    lenders = []
    if count >= 2:
        lenders.append({
            "name": st.session_state.switch_lender2_name, "is_frfi": st.session_state.switch_lender2_is_frfi,
            "reg_type": st.session_state.switch_lender2_reg_type,
            "mortgage_type": st.session_state.switch_lender2_mortgage_type,
            "balance": parse_money(st.session_state.switch_lender2_balance_raw),
        })
    if count >= 3:
        lenders.append({
            "name": st.session_state.switch_lender3_name, "is_frfi": st.session_state.switch_lender3_is_frfi,
            "reg_type": st.session_state.switch_lender3_reg_type,
            "mortgage_type": st.session_state.switch_lender3_mortgage_type,
            "balance": parse_money(st.session_state.switch_lender3_balance_raw),
        })
    if count >= 4:
        lenders.append({
            "name": st.session_state.switch_lender4_name, "is_frfi": st.session_state.switch_lender4_is_frfi,
            "reg_type": st.session_state.switch_lender4_reg_type,
            "mortgage_type": st.session_state.switch_lender4_mortgage_type,
            "balance": parse_money(st.session_state.switch_lender4_balance_raw),
        })
    return lenders


def get_debts_payout_total():
    """Sum of balances for debts the broker has flagged to be paid out from the mortgage proceeds."""
    total = 0.0
    for dkey, included in st.session_state.debt_payout_selected.items():
        if included:
            dt = get_debt_type(dkey)
            amounts = st.session_state.debt_amounts.get(dkey, {})
            if dt:
                total += get_debt_balance(dt, amounts) or 0.0
    return total


def get_switch_net_proceeds():
    """What's left of the requested loan amount after all mortgages/LOCs and flagged debts are paid out."""
    return get_loan_amount() - get_switch_total_mortgage_balance() - get_debts_payout_total()


def get_switch_payout_breakdown():
    """
    Itemized list of {label, amount} for everything being paid out of the switch-in proceeds:
    Lender 1 + any additional lenders, then each debt flagged for payout.
    """
    items = []
    balance1 = parse_money(st.session_state.switch_current_balance_raw)
    if balance1 is not None:
        items.append({
            "label": "Lender 1 — " + (st.session_state.switch_ofi_name or "OFI") + " (first mortgage)",
            "amount": balance1,
        })
    for idx, lender in enumerate(get_switch_additional_lenders(), start=2):
        if lender["balance"] is not None:
            items.append({
                "label": "Lender " + str(idx) + " — " + (lender["name"] or "unspecified"),
                "amount": lender["balance"],
            })
    for dkey, included in st.session_state.debt_payout_selected.items():
        if included:
            dt = get_debt_type(dkey)
            amounts = st.session_state.debt_amounts.get(dkey, {})
            amt = get_debt_balance(dt, amounts) if dt else None
            if amt is not None:
                label = debt_instance_label(dt, dkey) if dt else dkey
                items.append({"label": label + " (payout)", "amount": amt})
    return items


def get_step_missing_fields(step_index):
    """
    Returns a list of short descriptions of what's still needed to consider
    this step complete. Empty list means the step is complete. Best-effort —
    covers the fields each step's own on-page validation already treats as
    required; Analysis has no hard requirements of its own (it's a computed
    summary) and always returns an empty list.
    """
    missing = []

    if step_index == 0:
        if not st.session_state.transaction_type:
            missing.append("Select a transaction type")
        if not st.session_state.client_intake_notes.strip():
            missing.append("Client Intake Notes must be filled in")

    elif step_index == 1:
        if not st.session_state.consent:
            missing.append("Consent must be acknowledged")
        for idx, b in enumerate(st.session_state.borrowers):
            errs = validate_borrower(b)
            name = b.get("full_name", "").strip() or ("Borrower " + str(idx + 1))
            for msg in errs.values():
                missing.append(name + ": " + msg)

    elif step_index == 2:
        if is_refinance():
            if st.session_state.transaction_type == "refinance_new_lender":
                if compute_switch_in_analysis() is None:
                    missing.append("Complete all Lender Details questions")
            else:
                required = [
                    st.session_state.switch_mortgage_type, st.session_state.switch_ofi_is_frfi,
                    st.session_state.switch_amortization_unchanged, st.session_state.switch_additional_funds,
                    st.session_state.switch_amortization_changed, st.session_state.switch_borrowers_changed,
                ]
                if any(v == "" for v in required):
                    missing.append("Complete all Lender Details questions")
        else:
            if not st.session_state.purchase_price_raw.strip():
                missing.append("Purchase price is required")
            if not st.session_state.down_payment_raw.strip():
                missing.append("Down payment amount is required")
            if not st.session_state.selected_sources:
                missing.append("Select at least one down payment source")
            else:
                total_sources = 0.0
                for key in st.session_state.selected_sources:
                    src = next((s for s in DOWN_PAYMENT_SOURCES if s["key"] == key), None)
                    if not src:
                        continue
                    amt_raw = st.session_state.source_amounts.get(key, "")
                    if src["eligible"] and not amt_raw.strip():
                        missing.append(src["label"] + ": amount is required")
                    total_sources += parse_money(amt_raw) or 0.0
                down_payment_val = parse_money(st.session_state.down_payment_raw)
                if down_payment_val is not None and round(total_sources, 2) != round(down_payment_val, 2):
                    missing.append("Down payment source amounts (" + fmt_money(total_sources) + ") must sum to the down payment total (" + fmt_money(down_payment_val) + ")")

    elif step_index == 3:
        if not st.session_state.subject_address.strip():
            missing.append("Property address is required")
        for label, raw in [
            ("Monthly property taxes", st.session_state.subject_taxes_raw),
            ("Monthly condo/strata fees", st.session_state.subject_condo_raw),
            ("Monthly heating costs", st.session_state.subject_heat_raw),
        ]:
            if raw.strip() == "":
                missing.append(label + " must be entered (0 if none)")

    elif step_index == 4:
        if compute_total_income() <= 0:
            missing.append("Enter at least one income source with an amount")
        for idx in range(st.session_state.borrower_count):
            bidx = str(idx)
            name = borrower_display_name(idx)
            for skey in st.session_state.income_selected.get(bidx, []):
                src = get_income_source(skey)
                amounts = st.session_state.income_amounts.get(bidx, {}).get(skey, {})
                has_value = any(str(v).strip() for v in amounts.values()) if amounts else False
                if src and not has_value:
                    missing.append(name + " — " + src["label"] + ": amount is required")

    elif step_index == 5:
        if len(st.session_state.properties) == 0 and len(st.session_state.debt_selected) == 0:
            missing.append("At least one property or debt type must be added")
        for pidx, prop in enumerate(st.session_state.properties):
            if not prop.get("address", "").strip():
                missing.append("Other Property #" + str(pidx + 1) + ": address is required")
        for dkey in st.session_state.debt_selected:
            dt = get_debt_type(dkey)
            amounts = st.session_state.debt_amounts.get(dkey, {})
            if dt:
                if base_debt_key(dkey) != "alimony" and not amounts.get("lender", "").strip():
                    missing.append(debt_instance_label(dt, dkey) + ": Creditor/Bank Name is required")
                if dt["calc"] == "percent_of_balance":
                    if not amounts.get("balance", "").strip():
                        missing.append(debt_instance_label(dt, dkey) + ": balance is required")
                else:
                    if not amounts.get("payment", "").strip():
                        missing.append(debt_instance_label(dt, dkey) + ": monthly payment is required")

    elif step_index == 7:
        if not st.session_state.docs_reviewed:
            missing.append("Check \"I've reviewed this checklist\" at the bottom of the Docs page")

    elif step_index == 8:
        if not st.session_state.broker_notes.strip():
            missing.append("Broker Notes to Underwriter must be filled in")
        if not st.session_state.combined_notes.strip():
            missing.append("Click \"Combine Notes\" to generate the final file note")

    return missing


def is_step_fully_complete(step_index):
    """
    A step is only shown as complete (green) if its own required fields are
    filled in AND every step before it is also complete — this stops
    downstream pages like Analysis/Docs/Notes (which have no fields of their
    own) from showing green on a blank application just because they
    individually have nothing to fill in.
    """
    for i in range(step_index + 1):
        if get_step_missing_fields(i):
            return False
    return True


def render_stepper(active_index):
    with st.container(key="stepper_row"):
        cols = st.columns(len(STEPS), gap="small")
        for i, label in enumerate(STEPS):
            btn_type = "primary" if i == active_index else "secondary"
            display_label = label
            if i == 2 and is_refinance():
                display_label = "Refinance"

            step_missing = get_step_missing_fields(i)
            is_step_complete = is_step_fully_complete(i)
            was_visited = i in st.session_state.visited_steps
            is_currently_active = i == active_index

            if is_step_complete:
                state_suffix = "_complete"
            elif was_visited and not is_currently_active and step_missing:
                state_suffix = "_flagged"
            else:
                state_suffix = ""

            container_key = "stepbtn_" + str(i) + state_suffix + ("_active" if is_currently_active else "")
            with cols[i]:
                with st.container(key=container_key):
                    if st.button(display_label, key="nav_step_" + str(i), type=btn_type, use_container_width=True):
                        st.session_state.step = i
                        st.rerun()

    st.markdown(
        "<div style='text-align:center; font-size:11px; color:#9ca3af; margin-bottom:4px;'>"
        "🟢 Complete &nbsp;•&nbsp; 🟡 Missing info (tap ⚠ for details) &nbsp;•&nbsp; ⚪ Not yet visited"
        "</div>",
        unsafe_allow_html=True,
    )
    with st.container(key="stepper_help_row"):
        help_cols = st.columns(len(STEPS), gap="small")
        for i, label in enumerate(STEPS):
            step_missing = get_step_missing_fields(i)
            was_visited = i in st.session_state.visited_steps
            is_currently_active = i == active_index
            show_help = was_visited and not is_currently_active and step_missing and not is_step_fully_complete(i)
            with help_cols[i]:
                if show_help:
                    with st.container(key="helpbtn_step_" + str(i)):
                        with st.popover("⚠", key="step_help_" + str(i)):
                            st.markdown("**Still needed on this page:**")
                            for m in step_missing:
                                st.markdown("- " + m)


st.set_page_config(page_title="FH.Mortgages Calculator", page_icon="🏠", layout="centered")

st.markdown(
    """
    <style>
    html, body, [class*="css"], .stApp,
    .stApp p, .stApp span:not([data-testid="stIconMaterial"]), .stApp li, .stApp label,
    .stApp textarea, .stApp input, .stApp div[data-baseweb="select"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        font-size: 14px !important;
    }
    .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {
        font-size: 13px !important;
    }
    /* Calculated values shown inline via markdown backticks (e.g. debt/income math
       explanations) render as <code> spans, which Streamlit sizes/fonts differently
       from surrounding text by default. Match the font-size to body text so the
       highlighted values read at the same size as the rest of the line — keep the
       theme's own color, just fix the size. */
    .stApp p code, .stApp [data-testid="stCaptionContainer"] code, .stApp li code {
        font-size: 1em !important;
        padding: 0.1em 0.3em !important;
    }
    /* App-wide fix: when two fields sit side by side in columns and one label wraps to
       2 lines while the other doesn't, the input boxes end up at different heights.
       Giving every label a fixed min-height (room for 2 lines) keeps every input box
       in a row starting at the same vertical position, regardless of label length. */
    [data-testid="stWidgetLabel"] {
        min-height: 2.4em !important;
        display: flex !important;
        align-items: flex-end !important;
    }
    /* Uniform height for every single-line text input, number input, and dropdown
       app-wide — so fields sitting side by side (like the Income section) always
       present the same box size regardless of field type. */
    .stTextInput input, .stNumberInput input,
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        min-height: 2.6em !important;
        box-sizing: border-box !important;
    }
    div[class*="st-key-notes_font_scope"],
    div[class*="st-key-notes_font_scope"] p,
    div[class*="st-key-notes_font_scope"] span:not([data-testid="stIconMaterial"]),
    div[class*="st-key-notes_font_scope"] li,
    div[class*="st-key-notes_font_scope"] textarea {
        font-size: 15px !important;
        font-weight: 400 !important;
    }
    div[class*="st-key-notes_font_scope"] [data-testid="stIconMaterial"] {
        font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons", sans-serif !important;
    }
    div[class*="st-key-sub_checkbox"] label p {
        font-size: 13px !important;
    }
    div[class*="st-key-sub_checkbox"] label p:not(:has(span)) {
        color: #b0b6c0 !important;
    }
    div[class*="st-key-stepper_row"] div[data-testid="column"] {
        min-width: 0 !important;
        flex: 1 1 0 !important;
    }
    div[class*="st-key-stepper_row"] button {
        font-size: 9.5px !important;
        white-space: normal !important;
        word-break: keep-all !important;
        overflow-wrap: normal !important;
        padding: 6px 1px !important;
        letter-spacing: -0.4px !important;
        width: 100% !important;
        box-sizing: border-box !important;
        min-height: 4.4em !important;
        height: 4.4em !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        line-height: 1.25 !important;
        overflow: hidden !important;
    }
    div[class*="st-key-stepbtn_"][class*="_complete"] button {
        background-color: #16a34a !important;
        border: 1px solid #16a34a !important;
        color: white !important;
        font-weight: 700 !important;
    }
    div[class*="st-key-stepbtn_"][class*="_flagged"] button {
        background-color: #eab308 !important;
        border: 1px solid #eab308 !important;
        color: #1a1a1a !important;
        font-weight: 700 !important;
    }
    @keyframes stepbtn-active-flash {
        0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.85); }
        50% { box-shadow: 0 0 0 4px rgba(239,68,68,0.85); }
    }
    div[class*="st-key-stepbtn_"][class*="_active"] button {
        outline: 2px solid #ef4444 !important;
        outline-offset: 1px !important;
        animation: stepbtn-active-flash 1.4s ease-in-out infinite !important;
    }
    div[class*="st-key-stepper_help_row"] div[data-testid="column"] {
        min-width: 0 !important;
        flex: 1 1 0 !important;
    }
    div[class*="st-key-stepper_help_row"] {
        margin-top: -4px;
        margin-bottom: 6px;
    }
    div[class*="st-key-helpbtn_step_"] {
        display: flex;
        justify-content: center;
    }
    div[class*="st-key-helpbtn_step_"] button {
        min-height: 1.2em !important;
        height: 1.2em !important;
        width: 1.2em !important;
        min-width: 1.2em !important;
        padding: 0 !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        color: #6b7280 !important;
    }
    div[class*="st-key-helpbtn_step_"] svg,
    div[class*="st-key-helpbtn_step_"] [data-testid="stIconMaterial"],
    div[class*="st-key-helpbtn_step_"] [data-testid*="Icon"] {
        display: none !important;
    }
    div[class*="st-key-fieldrow_"] div[data-testid="stHorizontalBlock"] {
        align-items: flex-end !important;
    }
    div[class*="st-key-order_appraisal_btn_wrap"],
    div[class*="st-key-mls_autofill_btn_wrap"] {
        margin-top: 2.1rem;
    }
    div[class*="st-key-helpbtn_"] {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 6px;
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
    /* File uploader: the widget's own outer label was leaking through as a
       separate floating "Upload" text above the box even with label_visibility
       collapsed — hide it outright, it's redundant with the box itself. */
    [data-testid="stFileUploader"] > label,
    [data-testid="stFileUploader"] [data-testid="stWidgetLabel"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzone"] small {
        display: none !important;
    }
    [data-testid="stFileUploader"] {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
    }
    [data-testid="stFileUploader"] svg,
    [data-testid="stFileUploader"] [data-testid="stIconMaterial"],
    [data-testid="stFileUploader"] [data-testid*="Icon"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background-color: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0 !important;
        margin: 0 !important;
        min-height: 3.4em !important;
        width: 100% !important;
        box-sizing: border-box !important;
        position: relative !important;
        color: transparent !important;
        font-size: 0 !important;
    }
    [data-testid="stFileUploaderDropzone"] * {
        color: transparent !important;
        font-size: 0 !important;
    }
    [data-testid="stFileUploaderDropzone"]::after {
        content: "Upload File";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fafafa;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        pointer-events: none;
        z-index: 1;
    }
    /* Make every native text node inside the dropzone invisible (but keep it
       clickable/functional) and overlay our own guaranteed-correct label via
       CSS content instead — this doesn't depend on knowing Streamlit's exact
       internal element names, which is what kept breaking here before. */
    [data-testid="stFileUploaderDropzone"] button {
        color: transparent !important;
        font-size: 0 !important;
        min-height: 3.4em !important;
        width: 100% !important;
        border-radius: 8px !important;
        position: relative !important;
    }
    section[data-testid="stSidebar"] input {
        text-align: center !important;
    }
    section[data-testid="stSidebar"] button {
        min-height: 3.4em !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        white-space: normal !important;
        line-height: 1.2 !important;
        font-size: 13px !important;
        padding: 4px 8px !important;
        box-sizing: border-box !important;
    }
    section[data-testid="stSidebar"] button p,
    section[data-testid="stSidebar"] button div,
    section[data-testid="stSidebar"] button span {
        text-align: center !important;
        width: 100% !important;
        margin: 0 !important;
    }
    .stButton > button, .stDownloadButton > button {
        min-height: 3.4em;
        white-space: normal;
        line-height: 1.2;
        font-size: 13px;
        padding: 4px 8px;
        box-sizing: border-box;
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
    .stApp hr {
        margin: 10px 0 !important;
    }
    .stApp div[data-testid="stMarkdownContainer"] p {
        margin-bottom: 0.35rem !important;
    }
    .doc-list {
        background: rgba(37,99,235,0.08); border:1px solid rgba(37,99,235,0.35); border-radius:8px;
        padding: 16px; margin-top: 8px; margin-bottom: 16px; font-size: 13px; color:#e5e7eb;
    }
    /* Checkbox lists (Down Payment Sources, Debt Types, Income Sources, etc.) —
       even, generous vertical spacing so they read as a clean scannable column
       instead of clustering unevenly. */
    .stApp input::placeholder, .stApp textarea::placeholder {
        font-size: 14px !important;
        color: #6b7280 !important;
        opacity: 1 !important;
    }
    [data-testid="stCheckbox"] {
        margin-bottom: 10px !important;
    }
    [data-testid="stCheckbox"] label {
        line-height: 2.0 !important;
        align-items: center !important;
    }
    /* Force the exact brand blue (#2563eb) for checked checkbox labels, rather
       than Streamlit's default built-in blue shade from :blue[] markdown. */
    [data-testid="stCheckbox"] label p [style*="color"],
    [data-testid="stCheckbox"] label [data-testid="stMarkdownContainer"] span[style*="color"] {
        color: #2563eb !important;
    }
    .doc-list-note {
        margin: 4px 0 14px 2px; font-size: 13px; color: #9ca3af;
    }
    div[class*="st-key-docs_reviewed_box_pending"] {
        background-color: rgba(239,68,68,0.12);
        border: 1px solid #ef4444;
        border-radius: 8px;
        padding: 10px 14px;
    }
    div[class*="st-key-docs_reviewed_box_done"] {
        background-color: rgba(34,197,94,0.12);
        border: 1px solid #16a34a;
        border-radius: 8px;
        padding: 10px 14px;
    }
    div[class*="st-key-card_"],
    div[class*="st-key-notes_font_scope_"] {
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 10px;
        padding: 16px !important;
        margin: 8px 0 20px !important;
    }
    div[class*="st-key-card_doc_cat_"],
    div[class*="st-key-card_doc_edit_"] {
        padding: 12px 16px !important;
        margin: 10px 0 !important;
    }
    div[class*="st-key-card_doc_cat_"] [data-testid="stCheckbox"],
    div[class*="st-key-card_doc_edit_"] [data-testid="stCheckbox"] {
        margin-bottom: 4px !important;
    }
    div[class*="st-key-card_doc_cat_"] [data-testid="stCheckbox"]:last-of-type,
    div[class*="st-key-card_doc_edit_"] [data-testid="stCheckbox"]:last-of-type {
        margin-bottom: 0 !important;
    }
    div[class*="st-key-card_doc_cat_"] [data-testid="stVerticalBlock"] > div:last-child,
    div[class*="st-key-card_doc_edit_"] [data-testid="stVerticalBlock"] > div:last-child {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    div[class*="st-key-card_doc_cat_"] [data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-card_doc_edit_"] [data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-card_doc_cat_"] [data-testid="stElementContainer"],
    div[class*="st-key-card_doc_edit_"] [data-testid="stElementContainer"] {
        margin-bottom: 0 !important;
        gap: 0 !important;
    }
    div[class*="st-key-card_doc_cat_"] [data-testid="stVerticalBlock"],
    div[class*="st-key-card_doc_edit_"] [data-testid="stVerticalBlock"] {
        gap: 0.15rem !important;
    }
    div[class*="st-key-card_doc_cat_"] [data-testid="stCheckbox"] label,
    div[class*="st-key-card_doc_edit_"] [data-testid="stCheckbox"] label {
        display: flex !important;
        align-items: center !important;
        min-height: 1.8em !important;
    }
    div[class*="st-key-card_doc_cat_"] [data-testid="stMarkdownContainer"] p,
    div[class*="st-key-card_doc_edit_"] [data-testid="stMarkdownContainer"] p {
        margin-bottom: 4px !important;
        white-space: normal !important;
        overflow-wrap: break-word !important;
    }
    div[class*="st-key-card_debt_totals"] {
        padding: 8px 12px !important;
    }
    div[class*="st-key-card_debt_totals"] [data-testid="stExpanderDetails"] {
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    div[class*="st-key-card_debt_totals"] [data-testid="stCaptionContainer"] {
        margin-bottom: 0px !important;
        line-height: 1.3 !important;
    }
    div[class*="st-key-card_debt_totals"] [data-testid="stMarkdownContainer"] p {
        margin-bottom: 2px !important;
    }
    div[class*="st-key-card_debt_totals"] hr {
        margin: 4px 0 !important;
    }
    div[class*="st-key-card_debt_totals"] [data-testid="stVerticalBlock"] {
        gap: 0.35rem !important;
    }
    div[class*="st-key-card_debt_totals"] [data-testid="stElementContainer"] {
        margin-bottom: 0 !important;
    }
    div[class*="st-key-card_"] hr,
    div[class*="st-key-notes_font_scope_"] hr {
        margin: 8px 0 !important;
    }
    .metric-row {display:flex; gap: 12px; margin: 6px 0 2px; align-items: stretch;}
    .metric-card {
        flex:1; border:1px solid rgba(37,99,235,0.35); border-radius:10px; padding: 10px 14px; background: rgba(37,99,235,0.08);
        min-height: 62px; box-sizing: border-box; display:flex; flex-direction:column; justify-content:center;
    }
    .metric-label {font-size:12px; color:#9ca3af; margin-bottom:4px;}
    .metric-value {font-size:20px; font-weight:700; color:#f3f4f6; word-break:break-word;}
    .borrower-total {
        font-weight:600; font-size:15px; margin: 10px 0 4px; color:#f3f4f6;
    }
    .ratio-green {color:#16a34a; font-weight:700;}
    .ratio-yellow {color:#ca8a04; font-weight:700;}
    .ratio-red {color:#dc2626; font-weight:700;}
    .property-total {
        font-weight:600; font-size:14px; margin: 8px 0 4px; color:#f3f4f6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_state()

_title_suffix = ""
for _opt in TRANSACTION_TYPE_OPTIONS:
    if _opt["key"] == st.session_state.transaction_type:
        _title_suffix = " - " + _opt["label"]
        break

st.markdown(
    "<div style='font-size:17.5px; font-weight:700; white-space:nowrap; overflow:hidden; "
    "text-overflow:ellipsis; line-height:1.3;'>🏠 FH.Mortgages Calculator" + _title_suffix + "</div>",
    unsafe_allow_html=True,
)
st.caption("Residential Mortgage Application")

stepper_placeholder = st.empty()

with st.sidebar:
    timer_placeholder = st.empty()
    st.download_button(
        "Download / Save File", data=serialize_application(), file_name="mortgage_application.json",
        mime="application/json", use_container_width=True,
    )
    uploaded = st.file_uploader("Upload", type=["json"], key="load_app_uploader", label_visibility="collapsed")
    if uploaded is not None:
        if st.button("Load this file", use_container_width=True, key="load_app_confirm"):
            success, message = load_application(uploaded.read().decode("utf-8"))
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    if st.button("Refresh", use_container_width=True, key="sidebar_refresh"):
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


# ---------------------------------------------------------------------------
# STEP 0 — Transaction Type
# ---------------------------------------------------------------------------

YES_NO_OPTIONS = ["", "Yes", "No"]


def yes_no_bool(value):
    return value == "Yes"


def compute_switch_in_analysis():
    """
    Runs the session_state switch-in fields through the rules module.
    Returns a dict with straight_switch, needs_discharge, qualifying_rate,
    requires_refinance_registration, explanation — or None if not enough
    fields are filled in yet to evaluate.
    """
    required = [
        st.session_state.switch_reg_type, st.session_state.switch_mortgage_type,
        st.session_state.switch_timing, st.session_state.switch_ofi_is_frfi,
        st.session_state.switch_amortization_unchanged,
        st.session_state.switch_additional_funds, st.session_state.switch_amortization_changed,
        st.session_state.switch_borrowers_changed,
    ]
    if any(v == "" for v in required):
        return None

    ofi_is_frfi = yes_no_bool(st.session_state.switch_ofi_is_frfi)
    additional_funds = yes_no_bool(st.session_state.switch_additional_funds)
    amortization_unchanged = yes_no_bool(st.session_state.switch_amortization_unchanged)
    # No additional funds requested means the new mortgage amount matches the OFI balance.
    amount_unchanged = not additional_funds

    straight_switch = is_straight_switch(
        st.session_state.switch_reg_type, st.session_state.switch_mortgage_type,
        st.session_state.switch_timing, ofi_is_frfi, amount_unchanged, amortization_unchanged,
    )
    needs_discharge = requires_discharge_and_reregistration(st.session_state.switch_reg_type, straight_switch)
    qualifying_rate, requires_refi_reg, explanation = determine_qualifying_path(
        st.session_state.switch_mortgage_type, st.session_state.switch_timing,
        additional_funds, yes_no_bool(st.session_state.switch_amortization_changed),
        amortization_unchanged, yes_no_bool(st.session_state.switch_borrowers_changed),
    )
    return {
        "straight_switch": straight_switch,
        "needs_discharge": needs_discharge or requires_refi_reg,
        "qualifying_rate": qualifying_rate,
        "requires_refinance_registration": requires_refi_reg,
        "explanation": explanation,
    }


def clear_transaction_type_specific_fields():
    """
    Called whenever the transaction type actually changes. Clears fields
    specific to OTHER transaction types (switch-in/lender details, builder
    program, purchase channel/MLS) so nothing from a previously-tested
    transaction type can leak into the document checklist or elsewhere.
    Does not touch borrowers, income, debts, or notes.
    """
    refresh_switch_in()
    st.session_state.builder_name = ""
    st.session_state.builder_code = ""
    st.session_state.builder_type = ""
    st.session_state.builder_warranty_provider = ""
    st.session_state.builder_mortgage_product = ""
    st.session_state.builder_amortization_years = ""
    st.session_state.builder_interest_rate_type = ""
    st.session_state.builder_gst_hst_included = ""
    st.session_state.builder_gst_hst_percent_raw = ""
    st.session_state.builder_cashback_requested = ""
    st.session_state.builder_cashback_program = ""
    st.session_state.builder_rate_buydown = ""
    st.session_state.property_purchase_channel = ""
    st.session_state.property_mls_link = ""
    st.session_state.property_details_method = ""
    st.session_state.mls_autofill_status = ""
    st.session_state.mls_autofilled_fields = []
    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.selected_sources = []
    st.session_state.source_amounts = {}
    st.session_state.source_details = {}
    st.session_state.subject_property_value_raw = ""


def refresh_switch_in():
    st.session_state.switch_ofi_name = ""
    st.session_state.switch_ofi_is_frfi = ""
    st.session_state.switch_reg_type = "Traditional Mortgage"
    st.session_state.switch_mortgage_type = ""
    st.session_state.switch_timing = ""
    st.session_state.switch_current_balance_raw = ""
    st.session_state.switch_remaining_amortization = ""
    st.session_state.switch_amortization_unchanged = ""
    st.session_state.switch_additional_funds = ""
    st.session_state.switch_amortization_changed = ""
    st.session_state.switch_borrowers_changed = ""
    st.session_state.switch_amortization_change_years_raw = ""
    st.session_state.switch_additional_funds_amount_raw = ""
    st.session_state.switch_lender_count = "1"
    st.session_state.switch_lender2_name = ""
    st.session_state.switch_lender2_is_frfi = ""
    st.session_state.switch_lender2_reg_type = "Traditional Mortgage"
    st.session_state.switch_lender2_mortgage_type = ""
    st.session_state.switch_lender2_balance_raw = ""
    st.session_state.switch_lender3_name = ""
    st.session_state.switch_lender3_is_frfi = ""
    st.session_state.switch_lender3_reg_type = "Traditional Mortgage"
    st.session_state.switch_lender3_mortgage_type = ""
    st.session_state.switch_lender3_balance_raw = ""
    st.session_state.switch_lender4_name = ""
    st.session_state.switch_lender4_is_frfi = ""
    st.session_state.switch_lender4_reg_type = "Traditional Mortgage"
    st.session_state.switch_lender4_mortgage_type = ""
    st.session_state.switch_lender4_balance_raw = ""
    st.session_state.switch_requested_loan_amount_raw = ""
    st.session_state.switch_mortgages_good_standing = ""
    st.session_state.switch_taxes_up_to_date = ""
    st.session_state.switch_insurance_provider = ""
    st.session_state.switch_insurance_good_standing = ""


def render_switch_in_step():
    """
    Shown in place of Down Payment for both refinance types. For 'Refinance -
    New Lender' this captures the OFI mortgage facts needed to determine (a)
    whether this is a straight switch or requires discharge/re-registration,
    and (b) which qualifying rate applies (Contract Rate / AMQR / MQR). For
    'Refinance - Existing Lender', Lender 1 is simply the lender staying on
    title, and the same lender/amortization/standing/insurance fields are
    captured, replacing the switch-specific determination with the internal-
    refinance amortization-increase rules.
    """
    is_new_lender = st.session_state.transaction_type == "refinance_new_lender"

    if is_new_lender:
        st.markdown("### Refinance Details (Switch-In — Existing Lender Being Replaced)")
        st.write(
            "This new lender is replacing the client's current lender. Answer the questions below to "
            "determine whether this qualifies as a straight switch and which qualifying rate applies."
        )
    else:
        st.markdown("### Refinance Details (Staying with the Existing Lender)")
        st.write(
            "This refinance stays with the client's current lender. Answer the questions below to capture "
            "the mortgage(s) on the property and the refinance requirements."
        )
    render_calculator_popover("switchin")

    # --- Amount Requested: first field in this section, per spec ---
    st.markdown("#### Loan Amount Requested")
    st.session_state.switch_requested_loan_amount_raw = money_text_input("Loan Amount Being Requested ($)", st.session_state.switch_requested_loan_amount_raw,
        placeholder="Defaults to Lender 1's balance above if left blank", key="switch_requested_loan_amount_input",
    )
    st.markdown(
        "<span style='color:#22c55e; font-weight:700;'>Existing Mortgages Total: "
        + fmt_money(get_switch_total_mortgage_balance()).replace("$", "\\$") + "</span><br>"
        "<span style='color:#22c55e; font-weight:700;'>New Amount Requested: "
        + fmt_money(get_loan_amount()).replace("$", "\\$") + "</span>",
        unsafe_allow_html=True,
    )

    st.divider()

    # --- Section 1: Current lenders & registration ---
    st.markdown("#### Current Lenders & Registration")
    st.session_state.switch_lender_count = st.selectbox(
        "How many current lenders (mortgages/LOCs) are on this property?", ["1", "2", "3", "4"],
        index=["1", "2", "3", "4"].index(st.session_state.switch_lender_count)
        if st.session_state.switch_lender_count in ["1", "2", "3", "4"] else 0,
        key="switch_lender_count_input",
    )
    lender_count = int(st.session_state.switch_lender_count)

    st.markdown("**Lender 1 (" + ("being switched in" if is_new_lender else "staying on this mortgage") + ")**")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.switch_ofi_name = st.text_input(
            "Current (Other) Financial Institution Name" if is_new_lender else "Current Financial Institution Name",
            value=st.session_state.switch_ofi_name,
            placeholder="e.g. Bank of Example", key="switch_ofi_name_input",
        )
        st.session_state.switch_ofi_is_frfi = st.selectbox(
            "Federally Regulated Institution (FRFI)?", YES_NO_OPTIONS,
            index=YES_NO_OPTIONS.index(st.session_state.switch_ofi_is_frfi), key="switch_ofi_is_frfi_input",
        )
    with c2:
        st.session_state.switch_mortgage_type = st.selectbox(
            "Mortgage Type", MORTGAGE_TYPES,
            index=MORTGAGE_TYPES.index(st.session_state.switch_mortgage_type), key="switch_mortgage_type_input",
        )
        st.session_state.switch_current_balance_raw = money_text_input(
            "Current Outstanding Balance ($)" if not is_new_lender else "Current Outstanding Balance at OFI ($)",
            st.session_state.switch_current_balance_raw,
            key="switch_current_balance_input", placeholder="e.g. 425,000",
        )

    def render_additional_lender(n):
        st.markdown("**Lender " + str(n) + "**")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state["switch_lender" + str(n) + "_name"] = st.text_input(
                "Financial Institution Name", value=st.session_state["switch_lender" + str(n) + "_name"],
                placeholder="e.g. Bank of Example", key="switch_lender" + str(n) + "_name_input",
            )
            st.session_state["switch_lender" + str(n) + "_is_frfi"] = st.selectbox(
                "Federally Regulated Institution (FRFI)?", YES_NO_OPTIONS,
                index=YES_NO_OPTIONS.index(st.session_state["switch_lender" + str(n) + "_is_frfi"]),
                key="switch_lender" + str(n) + "_is_frfi_input",
            )
        with c2:
            st.session_state["switch_lender" + str(n) + "_mortgage_type"] = st.selectbox(
                "Mortgage Type", MORTGAGE_TYPES,
                index=MORTGAGE_TYPES.index(st.session_state["switch_lender" + str(n) + "_mortgage_type"]),
                key="switch_lender" + str(n) + "_mortgage_type_input",
            )
            st.session_state["switch_lender" + str(n) + "_balance_raw"] = money_text_input("Balance ($)", st.session_state["switch_lender" + str(n) + "_balance_raw"],
                placeholder="e.g. 45,000", key="switch_lender" + str(n) + "_balance_input",
            )

    if lender_count >= 2:
        render_additional_lender(2)
    if lender_count >= 3:
        render_additional_lender(3)
    if lender_count >= 4:
        render_additional_lender(4)

    st.markdown(
        "<span style='color:#22c55e; font-weight:700;'>Running Combined Existing Mortgages so far: "
        + fmt_money(get_switch_total_mortgage_balance()).replace("$", "\\$") + "</span>",
        unsafe_allow_html=True,
    )

    st.divider()
    if is_new_lender:
        st.session_state.switch_timing = st.selectbox(
            "Switch Timing", SWITCH_TIMING_OPTIONS,
            index=SWITCH_TIMING_OPTIONS.index(st.session_state.switch_timing), key="switch_timing_input",
        )
        st.divider()

    # --- Section 2: Amortization & change requests ---
    st.markdown("#### Amortization & Change Requests")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.switch_remaining_amortization = st.text_input(
            "Remaining Amortization (years)" if not is_new_lender else "Remaining Amortization at OFI (years)",
            value=st.session_state.switch_remaining_amortization,
            placeholder="e.g. 22", key="switch_remaining_amortization_input",
        )
        st.session_state.switch_amortization_unchanged = st.selectbox(
            "Is amortization staying the same as the remaining amortization above?" if not is_new_lender
            else "Is amortization staying the same as the OFI's remaining amortization?", YES_NO_OPTIONS,
            index=YES_NO_OPTIONS.index(st.session_state.switch_amortization_unchanged),
            key="switch_amortization_unchanged_input",
        )
        st.session_state.switch_amortization_change_years_raw = st.text_input(
            "What amortization does the client require (years)? (leave blank if unchanged)",
            value=st.session_state.switch_amortization_change_years_raw,
            placeholder="e.g. 30", key="switch_amortization_change_years_input",
        )
        st.session_state.switch_amortization_changed = "Yes" if st.session_state.switch_amortization_change_years_raw.strip() else "No"
        if st.session_state.switch_amortization_changed == "Yes":
            if not is_new_lender:
                max_years, credit_app_required, amort_note = determine_amortization_increase(
                    st.session_state.switch_mortgage_type, None, True,
                )
                st.caption(amort_note)
    with c2:
        st.session_state.switch_additional_funds = st.selectbox(
            "Is the client requesting additional funds (cash out)?", YES_NO_OPTIONS,
            index=YES_NO_OPTIONS.index(st.session_state.switch_additional_funds), key="switch_additional_funds_input",
        )
        st.session_state.switch_borrowers_changed = st.selectbox(
            "Are the borrowers/guarantors on title changing?" if not is_new_lender
            else "Are the borrowers/guarantors on title changing from the OFI mortgage?", YES_NO_OPTIONS,
            index=YES_NO_OPTIONS.index(st.session_state.switch_borrowers_changed),
            key="switch_borrowers_changed_input",
        )
        if st.session_state.switch_borrowers_changed == "Yes" and not is_new_lender:
            st.caption(change_of_borrower_note())

    if not is_new_lender:
        st.caption(equity_requirement_note())

    st.divider()

    # --- Section 3: Standing ---
    st.markdown("#### Standing")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.switch_mortgages_good_standing = st.selectbox(
            "Mortgages/LOCs in good standing?", YES_NO_OPTIONS,
            index=YES_NO_OPTIONS.index(st.session_state.switch_mortgages_good_standing),
            key="switch_mortgages_good_standing_input",
        )
        if st.session_state.switch_mortgages_good_standing == "No":
            st.caption(":red[Flag for underwriting — a mortgage/LOC not in good standing needs review before proceeding.]")
    with c2:
        st.session_state.switch_taxes_up_to_date = st.selectbox(
            "Are property taxes up to date?", YES_NO_OPTIONS,
            index=YES_NO_OPTIONS.index(st.session_state.switch_taxes_up_to_date),
            key="switch_taxes_up_to_date_input",
        )
        if st.session_state.switch_taxes_up_to_date == "No":
            st.caption(":red[Outstanding property taxes may need to be paid out or added to the new mortgage balance.]")

    st.divider()

    # --- Section 4: Insurance ---
    st.markdown("#### Property Insurance")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.switch_insurance_provider = st.text_input(
            "Who is the property insurance with?", value=st.session_state.switch_insurance_provider,
            placeholder="e.g. Insurance Co.", key="switch_insurance_provider_input",
        )
    with c2:
        st.session_state.switch_insurance_good_standing = st.selectbox(
            "Is the property insurance policy in good standing?", YES_NO_OPTIONS,
            index=YES_NO_OPTIONS.index(st.session_state.switch_insurance_good_standing),
            key="switch_insurance_good_standing_input",
        )
        if st.session_state.switch_insurance_good_standing == "No":
            st.caption(":red[Updated proof of property insurance will be required before the mortgage documents can be signed.]")

    st.divider()

    # --- Deal at a Glance: moved to the bottom of the section, per spec ---
    st.markdown("#### Deal at a Glance")
    glance_cols = "<div class='metric-row'>"
    glance_cols += (
        "<div class='metric-card'><div class='metric-label'>Combined Existing Mortgages</div>"
        "<div class='metric-value'>" + fmt_money(get_switch_total_mortgage_balance()) + "</div></div>"
        "<div class='metric-card'><div class='metric-label'>Loan Amount Requested</div>"
        "<div class='metric-value'>" + fmt_money(get_loan_amount()) + "</div></div>"
    )
    if st.session_state.switch_amortization_changed == "Yes":
        years_amt = st.session_state.switch_amortization_change_years_raw or "—"
        glance_cols += (
            "<div class='metric-card'><div class='metric-label'>Amortization Requested</div>"
            "<div class='metric-value'>" + years_amt + " yrs</div></div>"
        )
    glance_cols += "</div>"
    st.markdown(glance_cols, unsafe_allow_html=True)

    st.divider()

    if is_new_lender:
        # --- Determined path (switch-specific) ---
        analysis = compute_switch_in_analysis()
        st.markdown("**Determined Path**")
        if analysis is None:
            st.info("Answer all questions above to determine the switch path and qualifying rate.")
        else:
            path_label = "Straight Switch (no discharge/re-registration)" if analysis["straight_switch"] else \
                "Discharge & Re-Registration Required"
            st.markdown(
                "<div class='metric-row'>"
                "<div class='metric-card'><div class='metric-label'>Transaction Path</div>"
                "<div class='metric-value' style='font-size:15px;'>" + path_label + "</div></div>"
                "<div class='metric-card'><div class='metric-label'>Qualifying Rate</div>"
                "<div class='metric-value' style='font-size:15px;'>" + analysis["qualifying_rate"] + "</div></div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.caption(analysis["explanation"])
            if st.session_state.switch_mortgage_type == "Conventional":
                st.caption(
                    "Conventional switch-in balances must not exceed {:.0f}% of the current appraised value "
                    "(clients may pay down the balance to reach this if it's pushed over).".format(CONVENTIONAL_MAX_LTV)
                )
            st.caption("Mandatory documents and business case notes for this switch-in are listed on the Documents step.")
        completion_ok = analysis is not None
        missing_message = "Complete all Switch-In Details questions"
    else:
        # --- Refinance Requirements (internal refinance, same lender) ---
        st.markdown("**Refinance Requirements**")
        if st.session_state.switch_mortgage_type:
            _, credit_app_required, amort_note = determine_amortization_increase(
                st.session_state.switch_mortgage_type, None,
                st.session_state.switch_additional_funds == "Yes",
            )
            st.markdown(
                "<div class='metric-row'>"
                "<div class='metric-card'><div class='metric-label'>Credit Application Required</div>"
                "<div class='metric-value' style='font-size:15px;'>" + ("Yes" if credit_app_required else "Not always") + "</div></div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.caption(amort_note)
        st.caption(ltv_calculation_note())
        st.caption("Mandatory documents for this refinance are listed on the Documents step.")
        completion_required = [
            st.session_state.switch_mortgage_type, st.session_state.switch_ofi_is_frfi,
            st.session_state.switch_amortization_unchanged, st.session_state.switch_additional_funds,
            st.session_state.switch_amortization_changed, st.session_state.switch_borrowers_changed,
        ]
        completion_ok = all(v != "" for v in completion_required)
        missing_message = "Complete all Lender Details questions"

    switch_missing = [] if completion_ok else [missing_message]
    if st.session_state.get("p2_show_warning"):
        render_missing_fields_warning(switch_missing)

    st.divider()

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p2switch_back"):
            st.session_state.step = 1
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p2switch_refresh"):
            st.session_state["p2switch_show_refresh_confirm"] = True

    if st.session_state.get("p2switch_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p2switch_confirm_refresh"):
                refresh_switch_in()
                st.session_state["p2switch_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p2switch_cancel_refresh"):
                st.session_state["p2switch_show_refresh_confirm"] = False
                st.rerun()

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p2switch_continue"):
            if not completion_ok:
                st.session_state["p2_show_warning"] = True
                st.error("Please complete the " + ("Switch-In" if is_new_lender else "Lender") + " Details questions before continuing.")
            else:
                st.session_state["p2_show_warning"] = False
                st.session_state.step = 3
                st.rerun()


def render_transaction_type():
    st.markdown("### Transaction Type")
    st.write("Select the type of transaction this application is for.")
    render_calculator_popover("txntype")

    for opt in TRANSACTION_TYPE_OPTIONS:
        selected = st.session_state.transaction_type == opt["key"]
        with st.container(key="txntype_card_" + opt["key"]):
            col_radio, col_text = st.columns([1, 6])
            with col_radio:
                if st.button(
                    "●" if selected else "○",
                    key="txntype_pick_" + opt["key"],
                    use_container_width=True,
                    type="primary" if selected else "secondary",
                ):
                    if st.session_state.transaction_type != opt["key"]:
                        clear_transaction_type_specific_fields()
                    st.session_state.transaction_type = opt["key"]
                    st.session_state.transaction_type_error = ""
                    st.rerun()
            with col_text:
                st.markdown("**" + opt["label"] + "**")
                st.caption(opt["description"])

    if st.session_state.transaction_type_error:
        st.markdown(":red[" + st.session_state.transaction_type_error + "]")

    if st.session_state.get("p0_show_warning"):
        render_missing_fields_warning(
            [] if st.session_state.transaction_type else ["Transaction type"]
        )

    st.divider()

    with st.container(key="card_intake_notes"):
        st.markdown("#### Client Intake Notes")
        st.caption("Capture the initial conversation with the client here — what they told you, in their own words, before the application was filled in. This is the reference point for spotting discrepancies later.")
        st.session_state.client_intake_notes = st.text_area(
            "Client Intake Notes / Initial Conversation", value=st.session_state.client_intake_notes,
            height=140, key="client_intake_notes_input",
        )

    st.divider()

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p0_back"):
            st.info("This is the first screen.")
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p0_refresh"):
            st.session_state["p0_show_refresh_confirm"] = True

    if st.session_state.get("p0_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p0_confirm_refresh"):
                refresh_all()
                st.session_state["p0_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p0_cancel_refresh"):
                st.session_state["p0_show_refresh_confirm"] = False
                st.rerun()

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p0_continue"):
            if not st.session_state.transaction_type:
                st.session_state.transaction_type_error = "Please select a transaction type before continuing."
                st.session_state["p0_show_warning"] = True
                st.rerun()
            else:
                st.session_state["p0_show_warning"] = False
                st.session_state.step = 1
                st.rerun()


# ---------------------------------------------------------------------------
# STEP 1 — Client Details
# ---------------------------------------------------------------------------

def render_client_details():
    st.markdown("### Client Details")
    st.write("Enter information for each borrower on this application.")
    render_calculator_popover("client")

    with st.container(key="card_borrower_count"):
        new_borrower_count = st.selectbox(
            "Number of Borrowers", [1, 2, 3, 4],
            index=[1, 2, 3, 4].index(st.session_state.borrower_count)
            if st.session_state.borrower_count in [1, 2, 3, 4] else 0,
            key="borrower_count_select",
        )
    if new_borrower_count != st.session_state.borrower_count:
        sync_borrower_count(new_borrower_count)
        st.rerun()

    st.divider()

    for idx in range(st.session_state.borrower_count):
        borrower = st.session_state.borrowers[idx]
        errors = st.session_state.borrower_errors[idx] if idx < len(st.session_state.borrower_errors) else {}

        with st.expander("Borrower " + str(idx + 1), expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                borrower["full_name"] = st.text_input(
                    "Full Name", value=borrower["full_name"], key="name_" + str(idx)
                )
                if errors.get("full_name"):
                    st.caption(":red[" + errors["full_name"] + "]")

                borrower["phone"] = st.text_input(
                    "Phone Number", value=borrower["phone"], key="phone_" + str(idx)
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
                    "Email Address", value=borrower["email"], key="email_" + str(idx)
                )
                if errors.get("email"):
                    st.caption(":red[" + errors["email"] + "]")

                borrower["dob"] = st.date_input(
                    "Date of Birth",
                    value=borrower["dob"],
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
                "Current Address", value=borrower["address"],
                key="address_" + str(idx), height=80,
            )
            if errors.get("address"):
                st.caption(":red[" + errors["address"] + "]")

            rc1, rc2 = st.columns(2)
            with rc1:
                borrower["residence_status"] = st.selectbox(
                    "What is this property?", RESIDENCE_STATUS_OPTIONS,
                    index=RESIDENCE_STATUS_OPTIONS.index(borrower.get("residence_status", ""))
                    if borrower.get("residence_status", "") in RESIDENCE_STATUS_OPTIONS else 0,
                    key="residence_status_" + str(idx),
                )
                if borrower["residence_status"] == "Other":
                    borrower["residence_status_other"] = st.text_input(
                        "Please describe", value=borrower.get("residence_status_other", ""),
                        key="residence_status_other_" + str(idx),
                    )
            with rc2:
                borrower["residence_disposition"] = st.selectbox(
                    "What's happening with it?", RESIDENCE_DISPOSITION_OPTIONS,
                    index=RESIDENCE_DISPOSITION_OPTIONS.index(borrower.get("residence_disposition", ""))
                    if borrower.get("residence_disposition", "") in RESIDENCE_DISPOSITION_OPTIONS else 0,
                    key="residence_disposition_" + str(idx),
                )
                if borrower["residence_disposition"] == "Other":
                    borrower["residence_disposition_other"] = st.text_input(
                        "Please describe", value=borrower.get("residence_disposition_other", ""),
                        key="residence_disposition_other_" + str(idx),
                    )

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
    consent_checked = st.session_state.get("consent_input", st.session_state.consent)
    st.session_state.consent = st.checkbox(
        ":blue[**I acknowledge and consent to the above terms**]" if consent_checked
        else "I acknowledge and consent to the above terms",
        value=consent_checked, key="consent_input",
    )
    consent_error_slot = st.empty()

    live_errors = [validate_borrower(b) for b in st.session_state.borrowers]
    missing_items = []
    field_labels = {
        "full_name": "Full Name", "dob": "Date of Birth", "gender": "Gender",
        "marital_status": "Marital Status", "phone": "Phone Number", "email": "Email Address",
        "address": "Current Address",
    }
    for idx, errs in enumerate(live_errors):
        for fkey in errs:
            missing_items.append("Borrower " + str(idx + 1) + " — " + field_labels.get(fkey, fkey))
    if not st.session_state.consent:
        missing_items.append("Consent checkbox")
    if st.session_state.get("p1_show_warning"):
        render_missing_fields_warning(missing_items)

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p1_back"):
            st.session_state.step = 0
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p1_refresh"):
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

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p1_continue"):
            all_errors = [validate_borrower(b) for b in st.session_state.borrowers]
            st.session_state.borrower_errors = all_errors
            is_valid = all(len(e) == 0 for e in all_errors)

            if not st.session_state.consent:
                consent_error_slot.markdown(":red[You must acknowledge and consent before continuing.]")

            if is_valid and st.session_state.consent:
                st.session_state["p1_show_warning"] = False
                st.session_state.step = 2
                st.rerun()
            else:
                st.session_state["p1_show_warning"] = True
                st.rerun()


# ---------------------------------------------------------------------------
# STEP 1 — Down Payment
# ---------------------------------------------------------------------------

def refresh_page2():
    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.refinance_balance_raw = ""
    st.session_state.selected_sources = []
    st.session_state.source_amounts = {}
    st.session_state.source_details = {}
    st.session_state.other_source_desc = ""
    st.session_state.dp_errors = {}


def render_down_payment():
    st.markdown("### Down Payment")
    st.write("Enter property price, down payment, and the sources funding it.")
    render_calculator_popover("downpayment")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.purchase_price_raw = money_text_input(
            "Purchase Price ($)", st.session_state.purchase_price_raw, key="purchase_price_input",
            placeholder="e.g., 500,000",
        )
    with col2:
        st.session_state.down_payment_raw = money_text_input(
            "Down Payment Amount ($)", st.session_state.down_payment_raw, key="down_payment_input",
            placeholder="e.g., 100,000",
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

    with st.container(key="card_dp_sources"):
        st.write("**Select Down Payment Sources**")

        selected = st.session_state.selected_sources
        sources_by_label = {s["label"]: s for s in DOWN_PAYMENT_SOURCES}
        sorted_labels = sorted(sources_by_label.keys())
        current_labels = [DOWN_PAYMENT_SOURCES_BY_KEY[k]["label"] for k in selected if k in DOWN_PAYMENT_SOURCES_BY_KEY]

        chosen_labels = st.multiselect(
            "Down Payment Sources", sorted_labels, default=current_labels, key="dp_sources_multiselect",
            label_visibility="collapsed",
        )
        new_selected_keys = [sources_by_label[lbl]["key"] for lbl in chosen_labels]

        for removed_key in set(selected) - set(new_selected_keys):
            st.session_state.source_amounts.pop(removed_key, None)
        selected = new_selected_keys

        for source_key in selected:
            source = DOWN_PAYMENT_SOURCES_BY_KEY[source_key]
            st.markdown(
                "<div style='color:#2563eb; font-weight:700; font-size:15px; margin-top:8px;'>"
                + source["label"] + "</div>",
                unsafe_allow_html=True,
            )
            if not source["eligible"]:
                st.markdown(
                    "<div class='doc-list'>⚠️ " + source["notes"] + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                amount_raw = money_text_input(
                    source["label"] + " Amount ($)",
                    st.session_state.source_amounts.get(source["key"], ""),
                    key="amt_" + source["key"],
                    placeholder="Enter amount",
                )
                st.session_state.source_amounts[source["key"]] = amount_raw

                st.session_state.source_details[source["key"]] = st.text_input(
                    "Detail (optional)",
                    value=st.session_state.source_details.get(source["key"], ""),
                    key="detail_" + source["key"],
                    placeholder="e.g. who, or which account/institution",
                )

                if source["key"] == "other":
                    st.session_state.other_source_desc = st.text_input(
                        "Describe the other source",
                        value=st.session_state.other_source_desc,
                        key="other_source_desc_input",
                    )

                docs_html = ""
                for d in source["documents"]:
                    docs_html += "<li>" + d + "</li>"
                st.markdown(
                    "<div class='doc-list'><b>Required Documentation</b>"
                    "<ul style='margin:6px 0 0 18px;'>" + docs_html + "</ul></div>",
                    unsafe_allow_html=True,
                )
                if source["notes"]:
                    st.markdown("<div class='doc-list-note'>" + source["notes"] + "</div>", unsafe_allow_html=True)

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

    missing_items = []
    if purchase_price is None or purchase_price <= 0:
        missing_items.append("Purchase Price")
    if down_payment is None:
        missing_items.append("Down Payment Amount")
    if not selected:
        missing_items.append("At least one Down Payment Source")
    if selected and down_payment is not None and not totals_match:
        missing_items.append("Source amounts must sum to the Down Payment Amount")
    if st.session_state.get("p2_show_warning"):
        render_missing_fields_warning(missing_items)

    back_col, refresh_col, continue_col = st.columns(3)
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p2_refresh"):
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

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p2_continue"):
            valid = (
                purchase_price is not None and purchase_price > 0 and not price_error
                and down_payment is not None and not dp_error
                and len(selected) > 0
                and totals_match
            )
            if valid:
                st.session_state["p2_show_warning"] = False
                st.session_state.step = 3
                st.rerun()
            else:
                st.session_state["p2_show_warning"] = True
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
    st.session_state.subject_has_rental_component = ""
    st.session_state.subject_rental_kitchen = False
    st.session_state.subject_rental_bathroom = False
    st.session_state.subject_rental_entrance = False
    st.session_state.subject_num_units = ""
    st.session_state.property_appraisal_type = ""
    st.session_state.property_appraisal_ordered = False
    st.session_state.property_appraisal_value_raw = ""
    st.session_state.property_purchase_channel = ""
    st.session_state.property_mls_link = ""
    st.session_state.property_details_method = ""
    st.session_state.mls_autofill_status = ""
    st.session_state.mls_autofilled_fields = []
    st.session_state.subject_taxes_raw = ""
    st.session_state.subject_condo_raw = ""
    st.session_state.subject_heat_raw = ""
    st.session_state.subject_prop_type = ""
    st.session_state.subject_prop_purpose = ""
    st.session_state.subject_prop_age = ""
    st.session_state.subject_garage = ""
    st.session_state.subject_garage_other = ""
    st.session_state.subject_rural_urban = ""
    st.session_state.subject_sqft = ""
    st.session_state.subject_storeys = ""
    st.session_state.subject_heating_type = ""
    st.session_state.subject_cooling = ""
    st.session_state.subject_foundation = ""
    st.session_state.subject_foundation_other = ""
    st.session_state.subject_exterior_finish = ""
    st.session_state.subject_exterior_finish_other = ""
    st.session_state.subject_sewer = ""
    st.session_state.subject_water = ""
    st.session_state.subject_parking_spaces = ""
    st.session_state.subject_land_size = ""
    st.session_state.subject_title_type = ""
    st.session_state.subject_title_type_other = ""
    st.session_state.subject_prop_type_other = ""
    st.session_state.subject_heating_type_other = ""
    st.session_state.subject_sewer_other = ""
    st.session_state.subject_water_other = ""


def get_subject_property_costs():
    """Returns (pi_payment, taxes, condo, heat, monthly_housing_total) for the subject property."""
    loan_amount = get_loan_amount()
    pi = monthly_mortgage_payment(loan_amount, st.session_state.contract_rate, st.session_state.amortization_years)
    taxes = parse_money(st.session_state.subject_taxes_raw) or 0.0
    condo = parse_money(st.session_state.subject_condo_raw) or 0.0
    heat = parse_money(st.session_state.subject_heat_raw) or 0.0
    housing_total = pi + taxes + heat + condo
    return pi, taxes, condo, heat, housing_total


def render_other_description_field(label, session_state_key, widget_key):
    """
    Renders a custom 'Other' description field inside a distinct, collapsible
    expander so it visually stands apart from the standard dropdown fields —
    clicking it opens up to show exactly what the client typed for that
    custom answer. Indented under the field it belongs to, so it reads as a
    sub-field rather than a new top-level question.
    """
    current_value = st.session_state.get(session_state_key, "")
    if current_value.strip():
        expander_label = "✏️ Client entered: \"" + current_value.strip() + "\"  (click to edit)"
    else:
        expander_label = "✏️ " + label + " — click to enter the client's own description"
    indent_spacer, indent_content = st.columns([0.4, 9.6])
    with indent_content:
        with st.expander(expander_label, expanded=not current_value.strip()):
            st.session_state[session_state_key] = st.text_input(
                label, value=current_value, key=widget_key,
                placeholder="Type the client's own description here",
            )


def render_property_details():
    st.markdown("### Property Details")
    if is_refinance():
        st.write("Tell us about the property being refinanced — this feeds directly into your GDS/TDS calculation.")
    else:
        st.write("Tell us about the property you're purchasing — this feeds directly into your GDS/TDS calculation.")
    render_calculator_popover("property")

    with st.container(key="card_property_address"):
        st.session_state.subject_address = st.text_area(
            "Property Address", value=st.session_state.subject_address,
            placeholder="Enter the full address of the property you're purchasing", height=70,
        )
        if not st.session_state.subject_address.strip():
            st.caption(":red[Please enter the property address.]")

    st.divider()

    if is_refinance():
        loan_amount = get_loan_amount()
        st.session_state.subject_property_value_raw = money_text_input(
            "Current Estimated Property Value ($)", st.session_state.subject_property_value_raw,
            key="subject_property_value_input", placeholder="e.g. 650,000",
        )
        st.caption(ltv_calculation_note())
        st.markdown(
            "<div class='metric-row'>"
            "<div class='metric-card'><div class='metric-label'>Mortgage Loan Amount (from Lender Details)</div>"
            "<div class='metric-value'>" + fmt_money(loan_amount) + "</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption("To change this amount, go back to the Deal step and update Lender Details.")
    else:
        purchase_price = parse_money(st.session_state.purchase_price_raw) or 0.0
        loan_amount = get_loan_amount()
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

    # --- Appraisal, Property Value & Purchase Channel (compacted into one section) ---
    with st.container(key="card_appraisal_channel"):
        st.markdown("#### Appraisal" + (" & Purchase Channel" if not is_refinance() else ""))
        oa_c1, oa_c2 = st.columns(2)
        with oa_c1:
            st.session_state.property_appraisal_type = st.selectbox(
                "Order Appraisal", ["", "Appraisal", "Appraisal with Market Rent"],
                index=["", "Appraisal", "Appraisal with Market Rent"].index(st.session_state.property_appraisal_type)
                if st.session_state.property_appraisal_type in ["", "Appraisal", "Appraisal with Market Rent"] else 0,
                key="property_appraisal_type_input",
            )
        with oa_c2:
            with st.container(key="order_appraisal_btn_wrap"):
                if st.button("📋 Order Appraisal", key="order_appraisal_btn", disabled=not st.session_state.property_appraisal_type, use_container_width=True):
                    st.session_state.property_appraisal_ordered = True
            if st.session_state.property_appraisal_ordered:
                st.caption(":green[✓ Ordered (to be set up later).]")

        ref_value = get_reference_property_value()
        pv_header_col, pv_help_col = st.columns([12, 1])
        with pv_header_col:
            st.write("**Property Value & Appraisal**")
        with pv_help_col:
            with st.container(key="helpbtn_help_ltv_calc"):
                with st.popover("?", key="help_ltv_calc"):
                    st.caption(
                        "For Refinance transactions, LTV is calculated using the Appraised Value. "
                        "For Purchase transactions, LTV is calculated using the lower of the Purchase "
                        "Price or Appraised Value."
                    )

        pv_c1, pv_c2 = st.columns(2)
        with pv_c1:
            st.markdown("<div style='min-height:2.4em;'></div>", unsafe_allow_html=True)
            st.markdown(
                "<span style='font-family: \"Source Code Pro\", monospace; font-size: 14px; color:#22c55e;'>"
                "Property Value: `" + fmt_money(ref_value) + "`</span>",
                unsafe_allow_html=True,
            )
            st.caption("Carried over from " + ("Lender Details" if is_refinance() else "Down Payment") + ".")
        with pv_c2:
            st.session_state.property_appraisal_value_raw = money_text_input(
                "Appraisal Value ($)", st.session_state.property_appraisal_value_raw,
                key="property_appraisal_value_input", placeholder="Enter once the appraisal comes back",
            )
            appraisal_val = parse_money(st.session_state.property_appraisal_value_raw)
            if appraisal_val is not None:
                diff_caption = ""
                if ref_value is not None and ref_value > 0:
                    diff_pct = (appraisal_val - ref_value) / ref_value * 100
                    if abs(diff_pct) >= 1:
                        diff_caption = " (" + ("{:.1f}% below" if diff_pct < 0 else "{:.1f}% above").format(abs(diff_pct)) + " property value)"
                st.markdown(
                    "<span style='font-family: \"Source Code Pro\", monospace; font-size: 14px; color:#22c55e;'>"
                    "Appraisal Value: `" + fmt_money(appraisal_val) + "`</span>" + diff_caption,
                    unsafe_allow_html=True,
                )

        if not is_refinance():
            pc_c1, pc_c2 = st.columns(2)
            with pc_c1:
                st.session_state.property_purchase_channel = st.selectbox(
                    "Purchase Channel", ["", "Private Sale - No MLS", "MLS Listed"],
                    index=["", "Private Sale - No MLS", "MLS Listed"].index(st.session_state.property_purchase_channel)
                    if st.session_state.property_purchase_channel in ["", "Private Sale - No MLS", "MLS Listed"] else 0,
                    key="property_purchase_channel_input",
                )
            with pc_c2:
                if st.session_state.property_purchase_channel == "MLS Listed":
                    st.session_state.property_details_method = st.selectbox(
                        "Property Characteristics", ["", "Auto-fill from MLS Link", "Enter Manually"],
                        index=["", "Auto-fill from MLS Link", "Enter Manually"].index(st.session_state.property_details_method)
                        if st.session_state.property_details_method in ["", "Auto-fill from MLS Link", "Enter Manually"] else 0,
                        key="property_details_method_input",
                    )

            if st.session_state.property_purchase_channel == "MLS Listed":
                if st.session_state.property_details_method == "Auto-fill from MLS Link":
                    mls_c1, mls_c2 = st.columns(2)
                    with mls_c1:
                        st.session_state.property_mls_link = st.text_input(
                            "MLS Listing Link", value=st.session_state.property_mls_link, placeholder="https://...",
                        )
                        st.caption("No MLS link? Enter N/A and continue.")
                    with mls_c2:
                        with st.container(key="mls_autofill_btn_wrap"):
                            autofill_clicked = st.button(
                                "🔎 Auto-Fill", key="mls_autofill_btn",
                                disabled=not st.session_state.property_mls_link.strip(), use_container_width=True,
                            )
                    if autofill_clicked:
                        with st.spinner("Attempting to read the MLS listing..."):
                            found, error = attempt_mls_autofill(st.session_state.property_mls_link)
                        if error:
                            st.session_state.mls_autofill_status = "failed"
                            st.session_state.mls_autofilled_fields = []
                            st.warning("⚠ " + error + " Please complete the highlighted fields below manually.")
                        else:
                            for k, v in found.items():
                                st.session_state[k] = v
                            st.session_state.mls_autofilled_fields = list(found.keys())
                            st.session_state.mls_autofill_status = "success"
                            st.success("✓ Auto-filled " + str(len(found)) + " field(s) — please verify below, and complete any highlighted fields manually.")
                            st.rerun()
                    if st.session_state.mls_autofill_status == "failed":
                        st.caption(":orange[Could not auto-fill from that link — the fields below need to be entered manually.]")
                elif st.session_state.property_details_method == "Enter Manually":
                    st.session_state.property_mls_link = st.text_input(
                        "MLS Listing Link (for reference)", value=st.session_state.property_mls_link, placeholder="https://...",
                    )
                    st.caption("No MLS link? Enter N/A and continue.")
                    st.caption("Property characteristics below will be entered manually.")

    if st.session_state.transaction_type == "builder_purchase":
        st.divider()
        with st.container(key="card_builder_program"):
            st.markdown("#### Builder Program Details")
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.builder_name = st.text_input(
                    "Builder Name", value=st.session_state.builder_name, placeholder="e.g. Example Homes Inc.",
                )
                st.session_state.builder_type = st.selectbox(
                    "Builder Type", BUILDER_TYPE_OPTIONS,
                    index=BUILDER_TYPE_OPTIONS.index(st.session_state.builder_type)
                    if st.session_state.builder_type in BUILDER_TYPE_OPTIONS else 0,
                )
                st.session_state.builder_code = st.text_input(
                    "Builder Code (if known)", value=st.session_state.builder_code, placeholder="e.g. B107A6",
                )
                st.session_state.builder_warranty_provider = st.text_input(
                    "New Home Warranty Provider", value=st.session_state.builder_warranty_provider,
                    placeholder="e.g. a provincial new home warranty program",
                )
            with c2:
                st.session_state.builder_mortgage_product = st.selectbox(
                    "Mortgage Product", MORTGAGE_PRODUCT_OPTIONS,
                    index=MORTGAGE_PRODUCT_OPTIONS.index(st.session_state.builder_mortgage_product)
                    if st.session_state.builder_mortgage_product in MORTGAGE_PRODUCT_OPTIONS else 0,
                )
                st.session_state.builder_amortization_years = st.text_input(
                    "Amortization Requested (years)", value=st.session_state.builder_amortization_years,
                    placeholder="e.g. 30",
                )
                amort_val = parse_money(st.session_state.builder_amortization_years)
                if amort_val is not None and st.session_state.builder_mortgage_product:
                    valid, needs_approval, msg = is_amortization_valid(int(amort_val), st.session_state.builder_mortgage_product)
                    if not valid:
                        st.caption(":red[" + msg + "]")
                    elif needs_approval:
                        st.caption(":orange[" + msg + "]")
                    else:
                        st.caption(msg)
                    if st.session_state.builder_mortgage_product == "Homeline Plan (Single Advance)":
                        st.caption("Note: the qualifying amortization for a Homeline Plan is standardized at 30 years, regardless of the amortization entered above.")
                st.session_state.builder_interest_rate_type = st.selectbox(
                    "Interest Rate Type", INTEREST_RATE_TYPE_OPTIONS,
                    index=INTEREST_RATE_TYPE_OPTIONS.index(st.session_state.builder_interest_rate_type)
                    if st.session_state.builder_interest_rate_type in INTEREST_RATE_TYPE_OPTIONS else 0,
                )
                st.session_state.builder_rate_buydown = st.selectbox(
                    "Is a Builder Interest Rate Buydown being offered?", YES_NO_OPTIONS,
                    index=YES_NO_OPTIONS.index(st.session_state.builder_rate_buydown)
                    if st.session_state.builder_rate_buydown in YES_NO_OPTIONS else 0,
                )

            st.markdown("**GST/HST**")
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.builder_gst_hst_included = st.selectbox(
                    "Does the purchase price already include GST/HST?", YES_NO_OPTIONS,
                    index=YES_NO_OPTIONS.index(st.session_state.builder_gst_hst_included)
                    if st.session_state.builder_gst_hst_included in YES_NO_OPTIONS else 0,
                )
            with c2:
                if st.session_state.builder_gst_hst_included == "No":
                    st.session_state.builder_gst_hst_percent_raw = st.text_input(
                        "Exact GST/HST % (if confirmed by builder/lawyer/notary)",
                        value=st.session_state.builder_gst_hst_percent_raw, placeholder="e.g. 5",
                    )
            if st.session_state.builder_gst_hst_included == "No":
                purchase_price_for_gst = parse_money(st.session_state.purchase_price_raw) or 0.0
                gst_pct = parse_money(st.session_state.builder_gst_hst_percent_raw)
                gst_pct_fraction = (gst_pct / 100.0) if gst_pct is not None else None
                adjusted_price, gst_note = calculate_gst_hst_adjusted_price(
                    purchase_price_for_gst, False, gst_pct_fraction,
                )
                st.caption(
                    "Adjusted purchase price: " + fmt_money(adjusted_price) + ". " + gst_note
                )

            st.markdown("**Cashback**")
            c1, c2 = st.columns(2)
            with c1:
                st.session_state.builder_cashback_requested = st.selectbox(
                    "Is the client requesting cashback?", YES_NO_OPTIONS,
                    index=YES_NO_OPTIONS.index(st.session_state.builder_cashback_requested)
                    if st.session_state.builder_cashback_requested in YES_NO_OPTIONS else 0,
                )
            with c2:
                if st.session_state.builder_cashback_requested == "Yes":
                    st.session_state.builder_cashback_program = st.selectbox(
                        "Program", CASHBACK_PROGRAM_OPTIONS,
                        index=CASHBACK_PROGRAM_OPTIONS.index(st.session_state.builder_cashback_program)
                        if st.session_state.builder_cashback_program in CASHBACK_PROGRAM_OPTIONS else 0,
                    )
                    if st.session_state.builder_cashback_program and st.session_state.builder_cashback_program != "Not Applicable / Standard":
                        if is_cashback_eligible(st.session_state.builder_cashback_program):
                            st.caption(":green[Eligible for cashback combined with this program.]")
                        else:
                            st.caption(":red[This program cannot be combined with cashback.]")

            with st.expander("Standard documents for this builder-purchase file"):
                reqs = builder_document_requirements()
                for d in reqs["documents"]:
                    st.markdown("- " + d)

    st.divider()

    with st.container(key="card_rental_component"):
        st.markdown("#### Rental Component")
        st.caption("Does this property have a secondary suite or unit being rented out (e.g. a basement apartment)?")
        rc_a, rc_b = st.columns(2)
        with rc_a:
            st.session_state.subject_has_rental_component = st.selectbox(
                "Does this property have a rental unit?", YES_NO_OPTIONS,
                index=YES_NO_OPTIONS.index(st.session_state.subject_has_rental_component)
                if st.session_state.subject_has_rental_component in YES_NO_OPTIONS else 0,
                key="subject_has_rental_component_input",
            )
        with rc_b:
            if st.session_state.subject_has_rental_component == "Yes":
                units_input_col, units_help_col = st.columns([5, 1])
                with units_input_col:
                    st.session_state.subject_num_units = st.text_input(
                        "How many units does the property have?", value=st.session_state.subject_num_units,
                        placeholder="e.g. 2", key="subject_num_units_input",
                    )
                with units_help_col:
                    with st.container(key="helpbtn_help_num_units"):
                        with st.popover("?", key="help_num_units"):
                            st.caption(
                                "Enter the number of rental units in addition to the primary residence "
                                "(e.g., if the property has 1 rental unit, enter 1; if it has 2 rental "
                                "units, enter 2)."
                            )
        if st.session_state.subject_has_rental_component == "Yes":
            st.caption("For the rental income to be usable for qualification, the unit must be self-contained:")
            with st.container(key="sub_checkbox_rental"):
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    kitchen_checked = st.session_state.get("subject_rental_kitchen_input", st.session_state.subject_rental_kitchen)
                    st.session_state.subject_rental_kitchen = st.checkbox(
                        ":blue[Has its own kitchen]" if kitchen_checked else "Has its own kitchen",
                        value=kitchen_checked, key="subject_rental_kitchen_input",
                    )
                with rc2:
                    bathroom_checked = st.session_state.get("subject_rental_bathroom_input", st.session_state.subject_rental_bathroom)
                    st.session_state.subject_rental_bathroom = st.checkbox(
                        ":blue[Has its own bathroom]" if bathroom_checked else "Has its own bathroom",
                        value=bathroom_checked, key="subject_rental_bathroom_input",
                    )
                with rc3:
                    entrance_checked = st.session_state.get("subject_rental_entrance_input", st.session_state.subject_rental_entrance)
                    st.session_state.subject_rental_entrance = st.checkbox(
                        ":blue[Has a separate entrance]" if entrance_checked else "Has a separate entrance",
                        value=entrance_checked, key="subject_rental_entrance_input",
                    )
            is_self_contained = (
                st.session_state.subject_rental_kitchen and st.session_state.subject_rental_bathroom
                and st.session_state.subject_rental_entrance
            )
            st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
            if is_self_contained:
                st.caption(":green[Self-contained unit confirmed — rental income can be used for qualification under Income → Rental Income (Component of Primary Residence).]")
            else:
                st.caption(":red[Not self-contained — a kitchen, bathroom, and separate entrance are all required. Rental income from this unit cannot be used for qualification until all three are confirmed.]")

        st.caption(
            "Financing terms (contract rate, amortization) are now collected on the Analysis "
            "step, alongside the stress test."
        )

    st.divider()

    with st.container(key="card_property_characteristics"):
        st.markdown("#### Property Characteristics")
        st.caption(
            "Best-effort is fine here — the client may only have what's on the MLS listing "
            "or heard secondhand, not a formal appraisal. Leave anything unknown blank."
        )
        if st.session_state.mls_autofill_status == "success":
            st.caption(":green[✓ green] = auto-filled from the MLS link, please verify · :orange[⚠ orange] = not found automatically, needs manual entry")

        def mls_field_note(field_key):
            if st.session_state.mls_autofill_status != "success":
                return
            if field_key in st.session_state.mls_autofilled_fields:
                st.caption(":green[✓ auto-filled from MLS — verify]")
            else:
                st.caption(":orange[⚠ not found — enter manually]")

        c1, c2, c3 = st.columns(3)
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
            if st.session_state.subject_title_type == "Other":
                render_other_description_field(
                    "Describe title type", "subject_title_type_other", "subject_title_type_other_input",
                )
            st.session_state.subject_prop_type = st.selectbox(
                "Property Type", PROPERTY_STYLE_TYPES,
                index=PROPERTY_STYLE_TYPES.index(st.session_state.subject_prop_type)
                if st.session_state.subject_prop_type in PROPERTY_STYLE_TYPES else 0,
                key="subject_prop_type_select",
            )
            if st.session_state.subject_prop_type == "Other":
                render_other_description_field(
                    "Describe property type", "subject_prop_type_other", "subject_prop_type_other_input",
                )
            else:
                mls_field_note("subject_prop_type")
            st.session_state.subject_prop_age = st.text_input(
                "Property Age (yrs or year built)", value=st.session_state.subject_prop_age,
                placeholder="e.g. 15 years or Built 2011",
            )
            st.session_state.subject_rural_urban = st.selectbox(
                "Rural / Urban / Ag.",
                RURAL_URBAN_OPTIONS,
                index=RURAL_URBAN_OPTIONS.index(st.session_state.subject_rural_urban)
                if st.session_state.subject_rural_urban in RURAL_URBAN_OPTIONS else 0,
            )
            st.session_state.subject_foundation = st.selectbox(
                "Foundation Type", FOUNDATION_TYPE_OPTIONS,
                index=FOUNDATION_TYPE_OPTIONS.index(st.session_state.subject_foundation)
                if st.session_state.subject_foundation in FOUNDATION_TYPE_OPTIONS else 0,
            )
            if st.session_state.subject_foundation == "Other":
                render_other_description_field(
                    "Describe foundation type", "subject_foundation_other", "subject_foundation_other_input",
                )

        with c2:
            st.session_state.subject_sqft = st.text_input(
                "Square Footage", value=st.session_state.subject_sqft, placeholder="e.g. 1,850",
            )
            mls_field_note("subject_sqft")
            st.session_state.subject_storeys = st.text_input(
                "Number of Storeys", value=st.session_state.subject_storeys, placeholder="e.g. 2",
            )
            mls_field_note("subject_storeys")
            st.session_state.subject_land_size = st.text_input(
                "Land Size", value=st.session_state.subject_land_size, placeholder="e.g. 50 x 120 FT",
            )
            st.session_state.subject_parking_spaces = st.text_input(
                "Total Parking Spaces", value=st.session_state.subject_parking_spaces, placeholder="e.g. 4",
            )
            mls_field_note("subject_parking_spaces")
            st.session_state.subject_garage = st.selectbox(
                "Garage", GARAGE_OPTIONS,
                index=GARAGE_OPTIONS.index(st.session_state.subject_garage)
                if st.session_state.subject_garage in GARAGE_OPTIONS else 0,
            )
            if st.session_state.subject_garage == "Other":
                render_other_description_field(
                    "Describe garage / parking", "subject_garage_other", "subject_garage_other_input",
                )

        with c3:
            st.session_state.subject_heating_type = st.selectbox(
                "Heating Type", HEATING_TYPE_OPTIONS,
                index=HEATING_TYPE_OPTIONS.index(st.session_state.subject_heating_type)
                if st.session_state.subject_heating_type in HEATING_TYPE_OPTIONS else 0,
            )
            if st.session_state.subject_heating_type == "Other":
                render_other_description_field(
                    "Describe heating type", "subject_heating_type_other", "subject_heating_type_other_input",
                )
            st.session_state.subject_exterior_finish = st.selectbox(
                "Exterior Finish", EXTERIOR_FINISH_OPTIONS,
                index=EXTERIOR_FINISH_OPTIONS.index(st.session_state.subject_exterior_finish)
                if st.session_state.subject_exterior_finish in EXTERIOR_FINISH_OPTIONS else 0,
            )
            if st.session_state.subject_exterior_finish == "Other":
                render_other_description_field(
                    "Describe exterior finish", "subject_exterior_finish_other", "subject_exterior_finish_other_input",
                )
            st.session_state.subject_water = st.selectbox(
                "Water", WATER_OPTIONS,
                index=WATER_OPTIONS.index(st.session_state.subject_water)
                if st.session_state.subject_water in WATER_OPTIONS else 0,
            )
            if st.session_state.subject_water == "Other":
                render_other_description_field(
                    "Describe water source", "subject_water_other", "subject_water_other_input",
                )
            st.session_state.subject_sewer = st.selectbox(
                "Utility Sewer", SEWER_OPTIONS,
                index=SEWER_OPTIONS.index(st.session_state.subject_sewer)
                if st.session_state.subject_sewer in SEWER_OPTIONS else 0,
            )
            if st.session_state.subject_sewer == "Other":
                render_other_description_field(
                    "Describe utility sewer", "subject_sewer_other", "subject_sewer_other_input",
                )

    st.divider()

    with st.container(key="card_carrying_costs"):
        st.markdown("#### Monthly Carrying Costs")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.session_state.subject_taxes_raw = money_text_input(
                "Monthly Property Taxes ($)", st.session_state.subject_taxes_raw,
                key="subject_taxes_input", placeholder="Enter monthly tax amount",
            )
        with c2:
            st.session_state.subject_condo_raw = money_text_input(
                "Monthly Condo / Strata Fees ($)", st.session_state.subject_condo_raw,
                key="subject_condo_input", placeholder="Enter monthly fee amount (0 if none)",
            )
        with c3:
            st.session_state.subject_heat_raw = money_text_input(
                "Monthly Heating Costs ($)", st.session_state.subject_heat_raw,
                key="subject_heat_input", placeholder="Enter monthly heating amount",
            )

        st.caption(
            "Monthly P&I and total housing costs will be calculated once you set the "
            "contract rate and amortization on the Analysis step."
        )

    st.divider()

    carrying_costs_missing = [
        label for label, raw in [
            ("Monthly Property Taxes", st.session_state.subject_taxes_raw),
            ("Monthly Condo / Strata Fees", st.session_state.subject_condo_raw),
            ("Monthly Heating Costs", st.session_state.subject_heat_raw),
        ] if raw.strip() == ""
    ]

    if st.session_state.get("p2b_show_warning"):
        missing = [] if st.session_state.subject_address.strip() else ["Property Address"]
        missing += carrying_costs_missing
        render_missing_fields_warning(missing)

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p2b_back"):
            st.session_state.step = 2
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p2b_refresh"):
            st.session_state["p2b_show_refresh_confirm"] = True

    if st.session_state.get("p2b_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p2b_confirm_refresh"):
                refresh_property_details()
                st.session_state["p2b_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p2b_cancel_refresh"):
                st.session_state["p2b_show_refresh_confirm"] = False
                st.rerun()

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p2b_continue"):
            if st.session_state.subject_address.strip() and not carrying_costs_missing:
                st.session_state["p2b_show_warning"] = False
                st.session_state.step = 4
                st.rerun()
            else:
                st.session_state["p2b_show_warning"] = True
                if not st.session_state.subject_address.strip():
                    st.error("Please enter the property address before continuing.")
                else:
                    st.error("Please enter 0 for any carrying cost the property doesn't have — these fields can't be left blank.")


# ---------------------------------------------------------------------------
# STEP 2 — Income
# ---------------------------------------------------------------------------

def refresh_page3():
    st.session_state.income_selected = {}
    st.session_state.income_counts = {}
    st.session_state.income_amounts = {}
    st.session_state.income_special = {}
    st.session_state.income_other_desc = {}
    st.session_state.income_errors = {}


def base_income_key(instance_key):
    """Strips a '#N' instance suffix (e.g. 'salaried#2' -> 'salaried'), mirroring base_debt_key."""
    return instance_key.split("#")[0]


def income_instance_label(source, instance_key, total_instances=1):
    """'Employed (Salaried)' when there's only one; 'Employed (Salaried) #1', '#2', etc. when there's more than one."""
    if total_instances <= 1:
        return source["label"]
    if "#" in instance_key:
        return source["label"] + " #" + instance_key.split("#")[1]
    return source["label"] + " #1"


def get_income_source(key):
    base = base_income_key(key)
    for src in INCOME_SOURCES:
        if src["key"] == base:
            return src
    return None


VARIABLE_INCOME_KEYS = (
    "commission", "hourly", "bonus_overtime", "self_employed", "dividend",
    "self_employed_incorporated", "self_employed_professional",
)
EXCLUDED_INCOME_KEYS = ("capital_gains",)
RENTAL_INCLUSION_RATE_OPTIONS = ["50%", "80%", "100%"]


def rental_inclusion_rate_value(rate_label):
    """Converts a rental inclusion rate label ('50%'/'80%'/'100%') into its decimal fraction."""
    try:
        return float(str(rate_label).replace("%", "").strip()) / 100.0
    except (ValueError, TypeError):
        return 0.50


def compute_qualifying_variable_income(amounts):
    """
    Applies the standard 2-year variable-income rule: if the most recent
    year is lower than the prior year, use the (lower) most recent year;
    otherwise use the 2-year average. For self-employed income sources that
    carry an Ownership Percentage, that percentage is applied to each year's
    declared figure first (e.g. 50% ownership on $100,000 declared income
    means $50,000 is used), before the 2-year rule is applied.
    """
    recent_v = parse_money(amounts.get("recent_year", ""))
    prior_v = parse_money(amounts.get("prior_year", ""))
    if recent_v is None and prior_v is None:
        return 0.0
    if recent_v is None:
        recent_v = 0.0
    if prior_v is None:
        prior_v = 0.0
    if "ownership_pct" in amounts:
        ownership_v = parse_money(amounts.get("ownership_pct", ""))
        ownership_fraction = (ownership_v / 100.0) if ownership_v is not None else 1.0
        recent_v *= ownership_fraction
        prior_v *= ownership_fraction
    if recent_v < prior_v:
        return recent_v
    return (recent_v + prior_v) / 2.0


def compute_income_source_value(key, amounts):
    """Qualifying value for one income source's amounts dict, per its calc rule."""
    base_key = base_income_key(key)
    if base_key in EXCLUDED_INCOME_KEYS:
        return 0.0
    elif base_key == "rental":
        if amounts.get("status", "").startswith("Being Sold"):
            return 0.0
        gross_rental = parse_money(amounts.get("gross_rental", "")) or 0.0
        rate_label = amounts.get("inclusion_rate", "50%")
        rate = rental_inclusion_rate_value(rate_label)
        return gross_rental * rate
    elif base_key == "rental_component_primary":
        gross_amount = parse_money(amounts.get("amount", "")) or 0.0
        rate_label = amounts.get("inclusion_rate", "100%")
        rate = rental_inclusion_rate_value(rate_label)
        return gross_amount * rate
    elif base_key in VARIABLE_INCOME_KEYS:
        return compute_qualifying_variable_income(amounts)
    else:
        return parse_money(amounts.get("amount", "")) or 0.0


def explain_income_source(key, source, amounts):
    """Returns a human-readable string showing the full math behind one income source's qualifying value."""
    base_key = base_income_key(key)
    if base_key in EXCLUDED_INCOME_KEYS:
        return source["label"] + ": excluded from qualifying income (not treated as stable, recurring income)."

    if base_key == "rental":
        if amounts.get("status", "").startswith("Being Sold"):
            return source["label"] + ": $0 — property is marked \"" + amounts.get("status", "") + "\", so this income is not used."
        gross_rental = parse_money(amounts.get("gross_rental", "")) or 0.0
        rate_label = amounts.get("inclusion_rate", "50%")
        rate = rental_inclusion_rate_value(rate_label)
        qualifying = gross_rental * rate
        return (
            source["label"] + ": :green[" + fmt_money(gross_rental) + "] gross annual rental × :green[" + rate_label + "]"
            + " inclusion rate = :green[" + fmt_money(qualifying) + "]"
        )

    if base_key == "rental_component_primary":
        gross_amount = parse_money(amounts.get("amount", "")) or 0.0
        rate_label = amounts.get("inclusion_rate", "100%")
        rate = rental_inclusion_rate_value(rate_label)
        qualifying = gross_amount * rate
        return (
            source["label"] + ": :green[" + fmt_money(gross_amount) + "] gross annual rental × :green[" + rate_label + "]"
            + " inclusion rate = :green[" + fmt_money(qualifying) + "]"
        )

    if base_key in VARIABLE_INCOME_KEYS:
        recent_v = parse_money(amounts.get("recent_year", "")) or 0.0
        prior_v = parse_money(amounts.get("prior_year", "")) or 0.0
        ownership_note = ""
        if "ownership_pct" in amounts:
            ownership_v = parse_money(amounts.get("ownership_pct", ""))
            ownership_fraction = (ownership_v / 100.0) if ownership_v is not None else 1.0
            if ownership_v is not None and ownership_v != 100:
                ownership_note = " (at :green[" + "{:.0f}%".format(ownership_v) + "] ownership)"
            recent_v *= ownership_fraction
            prior_v *= ownership_fraction
        qualifying = compute_qualifying_variable_income(amounts)
        if recent_v < prior_v:
            return (
                source["label"] + ownership_note + ": most recent year (:green[" + fmt_money(recent_v) + "]) is lower than the "
                "prior year (:green[" + fmt_money(prior_v) + "]), so the lower, most recent year is used = "
                + ":green[" + fmt_money(qualifying) + "]"
            )
        else:
            return (
                source["label"] + ownership_note + ": :green[" + fmt_money(recent_v) + "] (recent year) + :green[" + fmt_money(prior_v)
                + "] (prior year), 2-year average = (:green[" + fmt_money(recent_v) + "] + :green[" + fmt_money(prior_v)
                + "]) ÷ 2 = :green[" + fmt_money(qualifying) + "]"
            )

    amount = parse_money(amounts.get("amount", "")) or 0.0
    return source["label"] + ": stated annual amount = :green[" + fmt_money(amount) + "]"


def compute_borrower_income(borrower_idx):
    bidx = str(borrower_idx)
    selected_keys = st.session_state.income_selected.get(bidx, [])
    total = 0.0
    breakdown = {}

    for key in selected_keys:
        amounts = st.session_state.income_amounts.get(bidx, {}).get(key, {})
        value = compute_income_source_value(key, amounts)
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
    st.markdown(
        "<div style='color:#2563eb; font-weight:700; font-size:15px; margin-top:8px;'>"
        + source["label"] + "</div>",
        unsafe_allow_html=True,
    )
    prefix = "inc_" + bidx + "_" + skey + "_"
    skey = base_income_key(skey)

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
                rule_note = (
                    "most recent year (" + fmt_money(recent_v) + ") is lower than the prior year ("
                    + fmt_money(prior_v) + "), so the lower, most recent year is used"
                )
            else:
                qualifying = (recent_v + prior_v) / 2.0
                rule_note = (
                    "(" + fmt_money(recent_v) + " + " + fmt_money(prior_v) + ") ÷ 2 = "
                    + fmt_money(qualifying) + " (2-year average, since the most recent year is higher or equal)"
                )
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
        amounts["amount"] = money_text_input("Gross Annual Base Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

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
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

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
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "ei_parental_benefits":
        c1, c2 = st.columns(2)
        with c1:
            amounts["return_to_work_date"] = st.text_input("Expected Return-to-Work Date (MM/YYYY)", value=amounts.get("return_to_work_date", ""), key=prefix + "return_to_work_date")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Benefit Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        st.caption("Note: EI/maternity/parental benefits are usually weaker for qualification since they're temporary.")

    elif skey == "foreign_income":
        c1, c2 = st.columns(2)
        with c1:
            amounts["country"] = st.text_input("Country of Income Source", value=amounts.get("country", ""), key=prefix + "country")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($, CAD equivalent)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        st.caption("Note: lenders are usually conservative with foreign income due to currency and jurisdiction risk.")

    elif skey == "capital_gains":
        c1, c2 = st.columns(2)
        with c1:
            amounts["description"] = st.text_input("Source / Description", value=amounts.get("description", ""), key=prefix + "description")
        with c2:
            amounts["amount"] = money_text_input("Amount ($, for reference only)", amounts.get("amount", ""), placeholder="Enter amount", key=prefix + "amount")
        st.caption("⚠️ Capital gains are not recurring income — this amount is recorded for reference only and is excluded from GDS/TDS qualification.")

    elif skey == "board_director_fees":
        c1, c2 = st.columns(2)
        with c1:
            amounts["organization_name"] = st.text_input("Organization Name", value=amounts.get("organization_name", ""), key=prefix + "organization_name")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "investment":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Financial Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
            amounts["account_number"] = st.text_input("Account Number", value=amounts.get("account_number", ""), key=prefix + "account_number")
        with c2:
            amounts["amount"] = money_text_input("Average Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "rental_component_primary":
        c1, c2 = st.columns(2)
        with c1:
            default_address = st.session_state.subject_address.strip()
            amounts["property_address"] = st.text_input(
                "Property Address", value=amounts.get("property_address", default_address),
                placeholder="Defaults to the subject property address", key=prefix + "property_address",
            )
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""),
                placeholder="Enter annual amount", key=prefix + "amount",
            )
            cur_rate = amounts.get("inclusion_rate", "100%")
            amounts["inclusion_rate"] = st.selectbox(
                "Rental Income Inclusion Rate",
                RENTAL_INCLUSION_RATE_OPTIONS,
                index=RENTAL_INCLUSION_RATE_OPTIONS.index(cur_rate) if cur_rate in RENTAL_INCLUSION_RATE_OPTIONS else 2,
                key=prefix + "inclusion_rate",
            )
        is_self_contained = (
            st.session_state.subject_has_rental_component == "Yes"
            and st.session_state.subject_rental_kitchen and st.session_state.subject_rental_bathroom
            and st.session_state.subject_rental_entrance
        )
        if not is_self_contained:
            st.caption(
                ":red[This income cannot be used for qualification until the Rental Component question on "
                "Property Details confirms a self-contained unit (kitchen, bathroom, separate entrance).]"
            )

    elif skey == "rental":
        rental_disposition_hints = (
            "Converting to Rental Property", "Currently Rented — Lease Continuing",
            "Currently Rented — Lease Ending", "Keeping as Secondary/Vacation Home",
        )
        borrower_idx_int = int(bidx) if bidx.isdigit() else -1
        suggested_address = ""
        if 0 <= borrower_idx_int < len(st.session_state.borrowers):
            b = st.session_state.borrowers[borrower_idx_int]
            if b.get("residence_disposition") in rental_disposition_hints:
                suggested_address = b.get("address", "").strip()
        c1, c2 = st.columns(2)
        with c1:
            amounts["property_address"] = st.text_input(
                "Property Address", value=amounts.get("property_address", "") or suggested_address,
                key=prefix + "property_address",
            )
            if suggested_address and not amounts.get("property_address", "").strip():
                st.caption("Suggested from this borrower's current address on Client Details, based on their stated disposition — edit if this is a different property.")
            cur_prop_type = amounts.get("prop_type", "")
            amounts["prop_type"] = st.selectbox(
                "Property Type", PROPERTY_TYPES,
                index=PROPERTY_TYPES.index(cur_prop_type) if cur_prop_type in PROPERTY_TYPES else 0,
                key=prefix + "prop_type",
            )
            cur_status = amounts.get("status", "")
            amounts["status"] = st.selectbox(
                "What's happening with this property?", PROPERTY_STATUS_OPTIONS,
                index=PROPERTY_STATUS_OPTIONS.index(cur_status) if cur_status in PROPERTY_STATUS_OPTIONS else 0,
                key=prefix + "status",
            )
        with c2:
            amounts["gross_rental"] = money_text_input("Gross Annual Rental Income ($)", amounts.get("gross_rental", ""), placeholder="Enter annual amount", key=prefix + "gross_rental")
            cur_rate = amounts.get("inclusion_rate", "50%")
            amounts["inclusion_rate"] = st.selectbox(
                "Rental Income Inclusion Rate",
                RENTAL_INCLUSION_RATE_OPTIONS,
                index=RENTAL_INCLUSION_RATE_OPTIONS.index(cur_rate) if cur_rate in RENTAL_INCLUSION_RATE_OPTIONS else 0,
                key=prefix + "inclusion_rate",
            )
        if amounts["status"].startswith("Being Sold"):
            st.caption(
                "⚠️ This property is marked **" + amounts["status"] + "** — its rental income is excluded "
                "from GDS/TDS qualification (it won't be an ongoing source of income once sold)."
            )
        else:
            gross_v = parse_money(amounts.get("gross_rental", "")) or 0.0
            rate_v = rental_inclusion_rate_value(amounts["inclusion_rate"])
            st.caption(
                "Qualifying Rental Income (:green[" + amounts["inclusion_rate"] + "] of gross rent): "
                + ":green[" + fmt_money(gross_v * rate_v) + "]"
            )
        st.caption(
            "This property's mortgage payment, taxes, condo fees, and heating should be entered "
            "under Debts & Liabilities → Property Debts so they're included in the debt service calculation."
        )

    elif skey == "pension":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Provider / Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "government_benefits":
        c1, c2 = st.columns(2)
        with c1:
            amounts["benefit_type"] = st.text_input("Benefit Type", value=amounts.get("benefit_type", ""), key=prefix + "benefit_type")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "alimony":
        st.caption(
            "Notice: You do not have to disclose alimony, child support, or separate maintenance income if "
            "you do not wish to have it considered as a basis for repaying this obligation."
        )
        amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

    elif skey == "trust_inheritance":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Trust / Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
            amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c2:
            amounts["duration"] = st.text_input("Expected Duration of Continued Payments (Months/Years)", value=amounts.get("duration", ""), key=prefix + "duration")

    else:  # "other"
        c1, c2 = st.columns(2)
        with c1:
            amounts["source_desc"] = st.text_input("Source Description", value=amounts.get("source_desc", ""), key=prefix + "source_desc")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")

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
    st.markdown(
        "<div class='doc-list'><b>Required Documentation</b>"
        "<ul style='margin:6px 0 0 18px;'>" + docs_html + "</ul></div>",
        unsafe_allow_html=True,
    )
    if source["notes"]:
        st.markdown("<div class='doc-list-note'>" + source["notes"] + "</div>", unsafe_allow_html=True)


def render_income():
    st.markdown("### Income Details")
    st.write("Enter income information for each borrower on this application.")
    st.info("💡 All income amounts below are **annual** figures, not monthly.")
    render_calculator_popover("income")

    borrower_count = st.session_state.borrower_count
    borrowers = st.session_state.borrowers
    all_valid = True
    grand_total = 0.0
    borrower_totals_for_display = []

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
            selected_types = sorted({base_income_key(k) for k in st.session_state.income_selected[bidx]})

            income_sources_by_label = {s["label"]: s for s in INCOME_SOURCES_ALPHA}
            income_sorted_labels = [s["label"] for s in INCOME_SOURCES_ALPHA]
            current_income_labels = [
                get_income_source(k)["label"] for k in selected_types if get_income_source(k)
            ]
            chosen_income_labels = st.multiselect(
                "Income Sources", income_sorted_labels, default=current_income_labels,
                key="inc_src_multiselect_" + bidx, label_visibility="collapsed",
            )
            chosen_type_keys = [income_sources_by_label[lbl]["key"] for lbl in chosen_income_labels]

            selected = []
            for type_key in chosen_type_keys:
                source = get_income_source(type_key)
                count_key = "inc_count_" + bidx + "_" + type_key
                count = st.session_state.income_counts.get(bidx, {}).get(type_key, 1)
                if len(chosen_type_keys) >= 1:
                    count = st.selectbox(
                        "How many " + source["label"] + " income sources does this borrower have?",
                        [1, 2, 3, 4, 5],
                        index=min(count, 5) - 1,
                        key=count_key,
                    )
                if bidx not in st.session_state.income_counts:
                    st.session_state.income_counts[bidx] = {}
                st.session_state.income_counts[bidx][type_key] = count
                for i in range(1, count + 1):
                    instance_key = type_key if i == 1 else type_key + "#" + str(i)
                    selected.append(instance_key)

            # Drop amounts for any instance that's no longer selected (type removed or count reduced).
            for stale_key in list(st.session_state.income_amounts[bidx].keys()):
                if stale_key not in selected:
                    st.session_state.income_amounts[bidx].pop(stale_key, None)
            for stale_type in list(st.session_state.income_counts.get(bidx, {}).keys()):
                if stale_type not in chosen_type_keys:
                    st.session_state.income_counts[bidx].pop(stale_type, None)

            st.session_state.income_selected[bidx] = selected

            # --- Phase 2: detail card for every selected instance, injected here, sequentially ---
            for instance_key in selected:
                type_key = base_income_key(instance_key)
                source = get_income_source(type_key)
                if instance_key not in st.session_state.income_amounts[bidx]:
                    st.session_state.income_amounts[bidx][instance_key] = {}
                amounts = st.session_state.income_amounts[bidx][instance_key]
                st.markdown("---")
                total_instances_for_type = st.session_state.income_counts.get(bidx, {}).get(type_key, 1)
                if total_instances_for_type > 1:
                    st.markdown(
                        "<div style='color:#2563eb; font-weight:400;'>"
                        + income_instance_label(source, instance_key, total_instances_for_type) + "</div>",
                        unsafe_allow_html=True,
                    )
                render_income_category_card(bidx, instance_key, source, amounts)
                if type_key not in VARIABLE_INCOME_KEYS:
                    # Variable-income sources already show their own full-calculation
                    # caption inline within the card (2-year rule breakdown).
                    st.caption(explain_income_source(instance_key, source, amounts))
                st.session_state.income_amounts[bidx][instance_key] = amounts

            borrower_total, breakdown = compute_borrower_income(idx)
            grand_total += borrower_total
            label_name = borrower_name if borrower_name else ("Borrower " + str(idx + 1))
            borrower_totals_for_display.append((label_name, borrower_total))

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
    income_header_col, income_help_col = st.columns([12, 1])
    with income_header_col:
        st.markdown("#### Total Combined Income: " + fmt_money(grand_total))

    calc_terms = []
    for idx in range(borrower_count):
        bidx = str(idx)
        name = borrower_display_name(idx)
        _, breakdown = compute_borrower_income(idx)
        for skey in st.session_state.income_selected.get(bidx, []):
            src = get_income_source(skey)
            val = breakdown.get(skey, 0.0)
            if src:
                calc_terms.append((name + " — " + src["label"], val))
    if calc_terms:
        with income_help_col:
            with st.container(key="helpbtn_help_income_calc"):
                with st.popover("?", key="help_income_calc"):
                    st.caption(
                        "Calculation: " + " + ".join(fmt_money(v) for _, v in calc_terms) + " = " + fmt_money(grand_total)
                    )
                    st.divider()
                    for label, v in calc_terms:
                        st.markdown("- " + label + ": **" + fmt_money(v) + "**")
    st.divider()

    income_missing_items = []
    for bidx_key, errs in st.session_state.income_errors.items():
        for msg in errs.values():
            income_missing_items.append(msg)
    if st.session_state.get("p3_show_warning"):
        render_missing_fields_warning(income_missing_items)

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p3_back"):
            st.session_state.step = 3
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p3_refresh"):
            st.session_state["p3_show_refresh_confirm"] = True

    if st.session_state.get("p3_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p3_confirm_refresh"):
                refresh_page3()
                st.session_state["p3_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p3_cancel_refresh"):
                st.session_state["p3_show_refresh_confirm"] = False
                st.rerun()

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p3_continue"):
            if all_valid:
                st.session_state["p3_show_warning"] = False
                st.session_state.step = 5
                st.rerun()
            else:
                st.session_state["p3_show_warning"] = True
                st.error("Please resolve the issues above before continuing.")


# ---------------------------------------------------------------------------
# STEP 3 — Debts & Liabilities
# ---------------------------------------------------------------------------

def refresh_page4():
    st.session_state.properties = []
    st.session_state.debt_selected = []
    st.session_state.debt_amounts = {}
    st.session_state.debt_payout_selected = {}
    st.session_state.debt_payout_balance = {}
    st.session_state.debt_paid_from_own_funds = {}
    st.session_state.debt_type_checked = {}
    st.session_state.debt_counts = {}
    st.session_state.debt_other_desc = ""
    st.session_state.debt_errors = {}


def base_debt_key(instance_key):
    """Strips a '#N' instance suffix (e.g. 'credit_card#2' -> 'credit_card')."""
    return instance_key.split("#")[0]


def debt_instance_label(debt_type, instance_key, total_instances=1):
    """'Credit Cards' when there's only one; 'Credit Cards #1', 'Credit Cards #2', etc.
    when there's more than one — so every instance is labeled consistently, including the first."""
    if total_instances <= 1:
        return debt_type["label"]
    if "#" in instance_key:
        return debt_type["label"] + " #" + instance_key.split("#")[1]
    return debt_type["label"] + " #1"


def get_debt_type(key):
    base = base_debt_key(key)
    for dt in DEBT_TYPES:
        if dt["key"] == base:
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


def get_debt_balance(debt_type, amounts):
    """The outstanding balance for a debt, regardless of which field type it's stored under."""
    if debt_type["calc"] == "percent_of_balance":
        return parse_money(amounts.get("balance", ""))
    return parse_money(amounts.get("total_balance", ""))


def explain_debt_payment(debt_type, amounts):
    """Returns (payment, explanation_string) showing the math behind a debt's monthly payment."""
    if debt_type["calc"] == "percent_of_balance":
        balance = parse_money(amounts.get("balance", "")) or 0.0
        pct = debt_type["percent"]
        payment = balance * pct
        explanation = (
            debt_type["label"] + ": " + "{:.0f}%".format(pct * 100) + " of "
            + ":green[" + fmt_money(balance) + "]" + " balance = " + ":green[" + fmt_money(payment) + "]" + "/month"
        )
        return payment, explanation
    else:
        payment = parse_money(amounts.get("payment", "")) or 0.0
        explanation = debt_type["label"] + ": stated monthly payment = " + ":green[" + fmt_money(payment) + "]" + "/month"
        return payment, explanation


def get_rental_income_addresses():
    """Collects unique, non-empty rental property addresses entered anywhere under Income."""
    addresses = []
    for bidx, sources in st.session_state.income_amounts.items():
        rental_amounts = sources.get("rental")
        if rental_amounts:
            addr = rental_amounts.get("property_address", "").strip()
            if addr and addr not in addresses:
                addresses.append(addr)
    return addresses


def get_rental_income_details(address):
    """Returns (prop_type, status) entered under Income for a given rental property address, or ("", "") if not found."""
    for bidx, sources in st.session_state.income_amounts.items():
        rental_amounts = sources.get("rental")
        if rental_amounts and rental_amounts.get("property_address", "").strip() == address:
            return rental_amounts.get("prop_type", ""), rental_amounts.get("status", "")
    return "", ""


def render_debts():
    st.markdown("### Debts & Liabilities")
    st.write("Enter property debts and other liabilities for this application.")
    render_calculator_popover("debts")

    st.write("**Property Debts**")
    st.caption("Other properties the client owns besides the one being purchased/refinanced.")

    num_other_props = st.selectbox(
        "Number of Other Properties Owned", [0, 1, 2, 3, 4],
        index=min(len(st.session_state.properties), 4),
        key="num_other_properties_select",
    )
    if num_other_props != len(st.session_state.properties):
        current = st.session_state.properties
        if num_other_props > len(current):
            current = current + [empty_property() for _ in range(num_other_props - len(current))]
        else:
            current = current[:num_other_props]
        st.session_state.properties = current
        st.rerun()

    total_property_debt = 0.0
    total_mortgage_pi_proxy = 0.0
    total_taxes = 0.0
    total_heat = 0.0
    total_condo = 0.0
    property_errors_any = False

    for pidx, prop in enumerate(st.session_state.properties):
        with st.expander("Property " + str(pidx + 1), expanded=True):
            rental_addresses = get_rental_income_addresses()
            manual_entry_label = "Other property (enter address manually)"
            address_source_options = rental_addresses + [manual_entry_label]

            # Figure out which option this property is currently associated with,
            # so the dropdown reflects prior selections instead of resetting.
            if prop["address"] in rental_addresses:
                default_source = prop["address"]
            else:
                default_source = manual_entry_label

            picked_source = st.selectbox(
                "Property Address",
                address_source_options,
                index=address_source_options.index(default_source)
                if default_source in address_source_options else len(address_source_options) - 1,
                key="prop_addr_source_" + str(pidx),
            )

            sync_key = "prop_addr_synced_" + str(pidx)
            if picked_source == manual_entry_label:
                prop["address"] = st.text_area(
                    "Enter property address", value=prop["address"] if prop["address"] not in rental_addresses else "",
                    placeholder="Enter full property address (e.g. a cottage or second property)",
                    key="prop_addr_" + str(pidx), height=70,
                )
                st.session_state[sync_key] = None
            else:
                prop["address"] = picked_source
                st.caption("📍 Auto-filled from the rental income entered under Income: " + picked_source)
                # Only pull property type / status over from Income the first time this
                # address is selected here, so the broker can still override afterwards
                # without it being overwritten on every rerun.
                if st.session_state.get(sync_key) != picked_source:
                    inc_prop_type, inc_status = get_rental_income_details(picked_source)
                    if inc_prop_type:
                        prop["prop_type"] = inc_prop_type
                    if inc_status:
                        prop["status"] = inc_status
                    st.session_state[sync_key] = picked_source

            prop["prop_type"] = st.selectbox(
                "Property Type", PROPERTY_TYPES,
                index=PROPERTY_TYPES.index(prop["prop_type"]) if prop["prop_type"] in PROPERTY_TYPES else 0,
                key="prop_type_" + str(pidx),
            )
            if prop["prop_type"] == "Other":
                prop["other_type_desc"] = st.text_input(
                    "Describe property type", value=prop.get("other_type_desc", ""), key="prop_other_" + str(pidx)
                )

            prop["status"] = st.selectbox(
                "What's happening with this property?", PROPERTY_STATUS_OPTIONS,
                index=PROPERTY_STATUS_OPTIONS.index(prop.get("status", "")) if prop.get("status", "") in PROPERTY_STATUS_OPTIONS else 0,
                key="prop_status_" + str(pidx),
            )
            is_firm_sale = prop["status"] == "Being Sold — Firm (Unconditional) Sale Agreement"
            if is_firm_sale:
                st.caption(
                    "✅ Excluded from GDS/TDS — with a firm, unconditional sale agreement in place, "
                    "Canadian lenders generally exclude this property's carrying costs from qualifying "
                    "ratios since it won't be an ongoing obligation."
                )
            elif prop["status"] == "Being Sold — Not Yet Firm / Listed Only":
                st.caption(
                    "⚠️ Still included in GDS/TDS — without a firm, unconditional sale agreement, lenders "
                    "generally still count this property's carrying costs, since the sale isn't guaranteed "
                    "to close."
                )

            c1, c2 = st.columns(2)
            with c1:
                prop["mortgage_payment"] = money_text_input(
                    "Monthly Mortgage / Loan Payment ($)", prop["mortgage_payment"],
                    key="prop_mtg_" + str(pidx), placeholder="Enter monthly payment amount",
                )
                prop["condo_fees"] = money_text_input(
                    "Monthly Condo / Strata Fees ($)", prop["condo_fees"],
                    key="prop_condo_" + str(pidx), placeholder="Enter monthly fee amount (0 if none)",
                )
            with c2:
                prop["property_taxes"] = money_text_input(
                    "Monthly Property Taxes ($)", prop["property_taxes"],
                    key="prop_tax_" + str(pidx), placeholder="Enter monthly tax amount",
                )
                prop["heating"] = money_text_input(
                    "Monthly Heating Costs ($)", prop["heating"],
                    key="prop_heat_" + str(pidx), placeholder="Enter monthly heating amount",
                )

            c3, c4 = st.columns(2)
            with c3:
                prop["property_value"] = money_text_input(
                    "Current Property Value ($)", prop.get("property_value", ""),
                    key="prop_value_" + str(pidx), placeholder="Enter estimated value",
                )
            with c4:
                num_mtg_options = ["", "Free and Clear", "1", "2", "3", "4"]
                current_num = prop.get("num_mortgages", "")
                prop["num_mortgages"] = st.selectbox(
                    "Number of Mortgages on this Property", num_mtg_options,
                    index=num_mtg_options.index(current_num) if current_num in num_mtg_options else 0,
                    key="prop_num_mtg_" + str(pidx),
                )

            if prop["num_mortgages"] not in ("", "Free and Clear"):
                num_mtg = int(prop["num_mortgages"])
                mortgages = prop.get("mortgages", [])
                if len(mortgages) != num_mtg:
                    if len(mortgages) < num_mtg:
                        mortgages = mortgages + [{"lender": "", "balance": ""} for _ in range(num_mtg - len(mortgages))]
                    else:
                        mortgages = mortgages[:num_mtg]
                    prop["mortgages"] = mortgages
                for midx, mtg in enumerate(mortgages):
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        mtg["lender"] = st.text_input(
                            "Lender" + (" #" + str(midx + 1) if num_mtg > 1 else ""),
                            value=mtg.get("lender", ""), key="prop_mtg_lender_" + str(pidx) + "_" + str(midx),
                        )
                    with mc2:
                        mtg["balance"] = money_text_input(
                            "Outstanding Balance ($)" + (" #" + str(midx + 1) if num_mtg > 1 else ""),
                            mtg.get("balance", ""), key="prop_mtg_balance_" + str(pidx) + "_" + str(midx),
                            placeholder="Enter current balance owing",
                        )
                prop["mortgages"] = mortgages
            elif prop["num_mortgages"] == "Free and Clear":
                prop["mortgages"] = []
                st.caption(":green[✓ Free and clear — no mortgage lender or balance to enter.]")

            st.caption("Property value and mortgage balance feed the Combined LTV figure on the Analysis step.")

            prop_total, m, t, c, h = compute_property_total(prop)
            is_firm_sale = prop.get("status") == "Being Sold — Firm (Unconditional) Sale Agreement"
            if not is_firm_sale:
                total_property_debt += prop_total
                total_mortgage_pi_proxy += m
                total_taxes += t
                total_condo += c
                total_heat += h

            st.caption(
                "Mortgage/Loan " + fmt_money(m) + " + Taxes " + fmt_money(t)
                + " + Condo " + fmt_money(c) + " + Heat " + fmt_money(h)
                + " = " + fmt_money(prop_total) + "/month"
                + (" (excluded from GDS/TDS — firm sale)" if is_firm_sale else "")
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

    with st.container(key="card_other_debts"):
        st.write("**Select Other Debt Types**")
        st.caption("If the client has more than one account of the same type (e.g. two credit cards), check the type once and set how many below.")

        selected = st.session_state.debt_selected
        total_other_debt = 0.0
        other_debt_errors_any = False

        debt_types_by_label = {dt["label"]: dt for dt in DEBT_TYPES}
        debt_sorted_labels = sorted(debt_types_by_label.keys())
        current_debt_labels = [
            dt["label"] for dt in DEBT_TYPES if st.session_state.debt_type_checked.get(dt["key"], dt["key"] in selected)
        ]
        chosen_debt_labels = st.multiselect(
            "Other Debt Types", debt_sorted_labels, default=current_debt_labels,
            key="debt_types_multiselect", label_visibility="collapsed",
        )
        chosen_debt_keys = {debt_types_by_label[lbl]["key"] for lbl in chosen_debt_labels}

        for debt_type in DEBT_TYPES:
            dkey = debt_type["key"]
            new_checked = dkey in chosen_debt_keys
            st.session_state.debt_type_checked[dkey] = new_checked

            if new_checked:
                st.markdown(
                    "<div style='color:#2563eb; font-weight:700; font-size:15px; margin-top:8px;'>"
                    + debt_type["label"] + "</div>",
                    unsafe_allow_html=True,
                )
                indent_spacer, indent_content = st.columns([0.4, 9.6])
                with indent_content:
                    count = st.selectbox(
                        "How many separate " + debt_type["label"] + " accounts does the client have?",
                        [1, 2, 3, 4, 5],
                        index=st.session_state.debt_counts.get(dkey, 1) - 1,
                        key="debt_count_" + dkey,
                    )
                st.session_state.debt_counts[dkey] = count
            else:
                count = 0
                st.session_state.debt_counts.pop(dkey, None)

            instance_keys_for_type = [dkey if i == 1 else dkey + "#" + str(i) for i in range(1, count + 1)]

            # Drop any instances beyond the current count (or all, if unchecked).
            stale_instances = [
                k for k in list(st.session_state.debt_amounts.keys())
                if base_debt_key(k) == dkey and k not in instance_keys_for_type
            ]
            for k in stale_instances:
                st.session_state.debt_amounts.pop(k, None)
                st.session_state.debt_payout_selected.pop(k, None)
                st.session_state.debt_payout_balance.pop(k, None)
                st.session_state.debt_paid_from_own_funds.pop(k, None)
                if k in selected:
                    selected.remove(k)

            for instance_key in instance_keys_for_type:
                if instance_key not in selected:
                    selected.append(instance_key)

                if instance_key not in st.session_state.debt_amounts:
                    st.session_state.debt_amounts[instance_key] = {}
                amounts = st.session_state.debt_amounts[instance_key]

                indent_spacer, indent_content = st.columns([0.4, 9.6])
                with indent_content:
                    st.markdown(
                        "<div style='color:#2563eb; font-weight:400;'>"
                        + debt_instance_label(debt_type, instance_key, len(instance_keys_for_type)) + "</div>",
                        unsafe_allow_html=True,
                    )

                    if debt_type["calc"] == "percent_of_balance":
                        lender_col, bal_col, calc_col = st.columns([1.6, 1.6, 1.6])
                        with lender_col:
                            amounts["lender"] = st.text_input(
                                "Creditor/Bank Name *", value=amounts.get("lender", ""),
                                placeholder="e.g., Mass Mutual, RBC Visa, JP Morgan Chase, BMO", key="debt_lender_" + instance_key,
                            )
                            if amounts.get("lender", "").strip() == "":
                                other_debt_errors_any = True
                        with bal_col:
                            amounts["balance"] = money_text_input("Total Outstanding Balance ($)", amounts.get("balance", ""),
                                placeholder="Enter total balance", key="debt_bal_" + instance_key,
                            )
                        if amounts.get("balance", "").strip() == "":
                            other_debt_errors_any = True
                        _, debt_explanation = explain_debt_payment(debt_type, amounts)
                        with calc_col:
                            st.markdown("<div style='margin-top:1.9rem;'></div>", unsafe_allow_html=True)
                            st.caption(debt_explanation)
                    elif base_debt_key(instance_key) == "alimony":
                        amounts["payment"] = money_text_input("Monthly Payment Amount ($)", amounts.get("payment", ""),
                            placeholder="Enter monthly payment amount", key="debt_pay_" + instance_key,
                        )
                        if amounts.get("payment", "").strip() == "":
                            other_debt_errors_any = True
                        _, debt_explanation = explain_debt_payment(debt_type, amounts)
                        st.caption(debt_explanation)
                    else:
                        lender_col, pay_col, bal_col = st.columns([1.6, 1.6, 1.6])
                        with lender_col:
                            amounts["lender"] = st.text_input(
                                "Creditor/Bank Name *", value=amounts.get("lender", ""),
                                placeholder="e.g., Mass Mutual, RBC Visa, JP Morgan Chase, BMO", key="debt_lender_" + instance_key,
                            )
                            if amounts.get("lender", "").strip() == "":
                                other_debt_errors_any = True
                        with pay_col:
                            amounts["payment"] = money_text_input("Monthly Payment Amount ($)", amounts.get("payment", ""),
                                placeholder="Enter monthly payment amount", key="debt_pay_" + instance_key,
                            )
                            if amounts.get("payment", "").strip() == "":
                                other_debt_errors_any = True
                        with bal_col:
                            amounts["total_balance"] = money_text_input("Total Balance Owing ($)", amounts.get("total_balance", ""),
                                placeholder="Enter total balance owing", key="debt_totalbal_" + instance_key,
                            )
                        _, debt_explanation = explain_debt_payment(debt_type, amounts)
                        st.caption(debt_explanation)

                    payment_value = compute_debt_payment(debt_type, amounts)

                    payout_checked = False
                    with st.container(key="sub_checkbox_debt_" + instance_key):
                        payout_widget_key = "debt_payout_" + instance_key
                        prior_payout = st.session_state.get(payout_widget_key, st.session_state.debt_payout_selected.get(instance_key, False))
                        if is_refinance():
                            payout_checked = st.checkbox(
                                ":blue[Include in payout from mortgage proceeds]" if prior_payout else "Include in payout from mortgage proceeds",
                                value=prior_payout,
                                key=payout_widget_key,
                            )
                            st.session_state.debt_payout_selected[instance_key] = payout_checked
                            if payout_checked:
                                payout_bal = get_debt_balance(debt_type, amounts)
                                st.caption(
                                    "Balance included in payout: "
                                    + (fmt_money(payout_bal) if payout_bal is not None else "enter a balance above")
                                )

                        own_funds_widget_key = "debt_own_funds_" + instance_key
                        prior_own_funds = st.session_state.get(own_funds_widget_key, st.session_state.debt_paid_from_own_funds.get(instance_key, False))
                        own_funds_checked = st.checkbox(
                            ":blue[Being paid off from the client's own funds / gifted funds prior to closing]" if prior_own_funds
                            else "Being paid off from the client's own funds / gifted funds prior to closing",
                            value=prior_own_funds,
                            key=own_funds_widget_key,
                        )
                        st.session_state.debt_paid_from_own_funds[instance_key] = own_funds_checked
                        if own_funds_checked:
                            st.caption(
                                "Excluded from GDS/TDS — will require proof of payout (current statement "
                                "showing zero balance, or receipt) before closing."
                            )

                    excluded_from_debt_service = payout_checked or own_funds_checked

                    if not excluded_from_debt_service:
                        total_other_debt += payment_value

                    docs_html = ""
                    for d in debt_type["documents"]:
                        docs_html += "<li>" + d + "</li>"
                    st.markdown(
                        "<div class='doc-list'><b>Required Documentation</b>"
                        "<ul style='margin:6px 0 0 18px;'>" + docs_html + "</ul></div>",
                        unsafe_allow_html=True,
                    )
                    if debt_type["notes"]:
                        st.markdown("<div class='doc-list-note'>" + debt_type["notes"] + "</div>", unsafe_allow_html=True)

                st.session_state.debt_amounts[instance_key] = amounts

        st.session_state.debt_selected = selected

    st.divider()

    with st.container(key="card_debt_totals"):
        with st.expander("Show breakdown", expanded=False):
            any_property_shown = False
            property_subtotal_terms = []
            for prop in st.session_state.properties:
                if prop.get("status") == "Being Sold — Firm (Unconditional) Sale Agreement":
                    continue
                p_total, m, t, c, h = compute_property_total(prop)
                if not any_property_shown:
                    st.markdown(
                        "<div style='font-weight:700; margin-top:4px; margin-bottom:8px;'>1. Other Property Obligations</div>",
                        unsafe_allow_html=True,
                    )
                    any_property_shown = True
                addr = prop.get("address", "").strip() or "Unnamed property"
                st.caption("**" + addr + "**")
                st.caption("Mortgage payment: " + fmt_money(m))
                st.caption("Condo fee: " + fmt_money(c))
                st.caption("Property tax: " + fmt_money(t))
                st.caption("Heat: " + fmt_money(h))
                st.caption(
                    "Total: " + fmt_money_md(m) + " + " + fmt_money_md(c) + " + " + fmt_money_md(t) + " + " + fmt_money_md(h)
                    + " = **" + fmt_money_md(p_total) + "**/mo"
                )
                property_subtotal_terms.append(p_total)
            if any_property_shown:
                subtotal_math = " + ".join(fmt_money_md(v) for v in property_subtotal_terms)
                st.markdown("Subtotal — Properties: " + subtotal_math + " = **" + fmt_money_md(total_property_debt) + "**/mo")
                st.divider()

            other_debt_terms = []
            if selected:
                st.markdown(
                    "<div style='font-weight:700; margin-top:14px; margin-bottom:8px;'>"
                    + ("2" if any_property_shown else "1") + ". Other Debt Obligations</div>",
                    unsafe_allow_html=True,
                )
                for instance_key in selected:
                    dt = get_debt_type(instance_key)
                    amounts = st.session_state.debt_amounts.get(instance_key, {})
                    pay_val, exp = explain_debt_payment(dt, amounts)
                    if "#" in instance_key:
                        num_suffix = " #" + instance_key.split("#")[1]
                        exp = exp.replace(dt["label"] + ":", dt["label"] + num_suffix + ":", 1)
                    lender_note = " (" + amounts["lender"].strip() + ")" if amounts.get("lender", "").strip() else ""
                    excluded_note = ""
                    excluded = (
                        st.session_state.debt_payout_selected.get(instance_key, False)
                        or st.session_state.debt_paid_from_own_funds.get(instance_key, False)
                    )
                    if st.session_state.debt_payout_selected.get(instance_key, False):
                        excluded_note = " — excluded from GDS/TDS (paid out from mortgage proceeds)"
                    elif st.session_state.debt_paid_from_own_funds.get(instance_key, False):
                        excluded_note = " — excluded from GDS/TDS (paid from own/gifted funds)"
                    st.caption(exp + lender_note + excluded_note)
                    if not excluded:
                        other_debt_terms.append(pay_val)
                subtotal_math = " + ".join(fmt_money_md(v) for v in other_debt_terms)
                st.markdown("Subtotal — Other Debts: " + subtotal_math + " = **" + fmt_money_md(total_other_debt) + "**/mo")
                st.divider()

            total_monthly_debt = total_property_debt + total_other_debt
            st.markdown(
                "<div style='font-weight:700; margin-top:14px; margin-bottom:8px;'>"
                + ("3" if any_property_shown and selected else "2" if any_property_shown or selected else "1")
                + ". Combined Total</div>",
                unsafe_allow_html=True,
            )
            combined_math_parts = []
            if any_property_shown:
                combined_math_parts.append(fmt_money_md(total_property_debt))
            if selected:
                combined_math_parts.append(fmt_money_md(total_other_debt))
            combined_math = " + ".join(combined_math_parts) if len(combined_math_parts) > 1 else ""
            st.markdown(
                "#### Total Monthly Debt Obligations: " + (combined_math + " = " if combined_math else "")
                + fmt_money_md(total_monthly_debt)
            )
            st.caption("Note: the property you're purchasing is entered in the Property Details step, not here — this page is for your other existing debts.")
            st.caption("Full GDS/TDS qualification is calculated on the Analysis step, after financing terms are set.")

    if is_refinance():
        st.divider()
        with st.container(key="card_debt_payout"):
            st.markdown("#### Refinance Payout Summary")
            breakdown = get_switch_payout_breakdown()
            if breakdown:
                st.markdown("**Being paid out from proceeds:**")
                for item in breakdown:
                    st.markdown("- " + item["label"] + ": " + fmt_money(item["amount"]))
            st.markdown(
                "<div class='metric-row'>"
                "<div class='metric-card'><div class='metric-label' style='white-space:nowrap; font-size:12px;'>Loan Amount Requested</div>"
                "<div class='metric-value'>" + fmt_money(get_loan_amount()) + "</div></div>"
                "<div class='metric-card'><div class='metric-label' style='white-space:nowrap; font-size:12px;'>Mortgages/LOCs Paid Out</div>"
                "<div class='metric-value'>" + fmt_money(get_switch_total_mortgage_balance()) + "</div></div>"
                "<div class='metric-card'><div class='metric-label' style='white-space:nowrap; font-size:12px;'>Debts Paid Out</div>"
                "<div class='metric-value'>" + fmt_money(get_debts_payout_total()) + "</div></div>"
                "<div class='metric-card'><div class='metric-label' style='white-space:nowrap; font-size:12px;'>Net Proceeds Remaining</div>"
                "<div class='metric-value'>" + fmt_money(get_switch_net_proceeds()) + "</div></div>"
                "</div>",
                unsafe_allow_html=True,
            )
            if get_switch_net_proceeds() < 0:
                st.caption(":red[Requested loan amount is less than the mortgages/LOCs and debts being paid out — this shortfall needs to be resolved before proceeding.]")

    st.divider()

    has_any_debt = len(st.session_state.properties) > 0 or len(selected) > 0
    is_valid = has_any_debt and not property_errors_any and not other_debt_errors_any

    debts_missing_items = []
    if not has_any_debt:
        debts_missing_items.append("At least one property or debt type")
    if property_errors_any:
        debts_missing_items.append("Property address (see property section(s) above)")
    if other_debt_errors_any:
        debts_missing_items.append("Balance/payment amount for selected debt type(s) above")
    if st.session_state.get("p4_show_warning"):
        render_missing_fields_warning(debts_missing_items)

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p4_back"):
            st.session_state.step = 4
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p4_refresh"):
            st.session_state["p4_show_refresh_confirm"] = True

    if st.session_state.get("p4_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p4_confirm_refresh"):
                refresh_page4()
                st.session_state["p4_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p4_cancel_refresh"):
                st.session_state["p4_show_refresh_confirm"] = False
                st.rerun()

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p4_continue"):
            if is_valid:
                st.session_state["p4_show_warning"] = False
                st.session_state.step = 6
                st.rerun()
            else:
                st.session_state["p4_show_warning"] = True
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
    st.markdown("### Qualification Summary")
    st.write("This page aggregates data from all previous steps — nothing to re-enter here.")
    render_calculator_popover("analysis")

    # --- For switch/refinance deals, keep amortization synced to what the client indicated on the
    # Lender Details step, so a later change there flows through automatically. This only overrides
    # the field when the underlying source value itself changes — a manual edit made directly on
    # this page is left alone until the source changes again. ---
    if is_refinance():
        source_years = None
        if st.session_state.switch_amortization_changed == "Yes":
            source_years = parse_money(st.session_state.switch_amortization_change_years_raw)
        else:
            source_years = parse_money(st.session_state.switch_remaining_amortization)
        if source_years is not None:
            source_years = int(round(min(max(source_years, 1), 50)))
            if st.session_state.get("amortization_synced_from") != source_years:
                st.session_state.amortization_years = source_years
                st.session_state["amortization_synced_from"] = source_years

    # --- Financing Terms (moved here from Property Details) ---
    with st.container(key="card_financing_terms"):
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
                    "Amortization (years)", min_value=1, max_value=50,
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
    loan_amount = get_loan_amount()
    if is_refinance():
        purchase_price = parse_money(st.session_state.subject_property_value_raw) or 0.0
    else:
        purchase_price = parse_money(st.session_state.purchase_price_raw) or 0.0
    ltv_denominator = get_ltv_denominator()
    ltv = (loan_amount / ltv_denominator * 100) if ltv_denominator else None

    pi_payment, taxes, condo, heat, _ = get_subject_property_costs()

    other_debt_monthly = 0.0
    for dkey in st.session_state.debt_selected:
        dt = get_debt_type(dkey)
        amounts = st.session_state.debt_amounts.get(dkey, {})
        excluded = (
            st.session_state.debt_payout_selected.get(dkey, False)
            or st.session_state.debt_paid_from_own_funds.get(dkey, False)
        )
        if not excluded:
            other_debt_monthly += compute_debt_payment(dt, amounts)
    # All properties listed in the Debts step are treated as additional (non-subject) properties,
    # except those marked as a firm/unconditional sale (excluded per standard Canadian lending practice)
    for prop in st.session_state.properties:
        if prop.get("status") == "Being Sold — Firm (Unconditional) Sale Agreement":
            continue
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
    if ltv is None and is_refinance():
        st.caption(":red[LTV can't be calculated — enter the Current Estimated Property Value on the Property Details step.]")

    # --- Combined LTV: subject property + all other (non-firm-sale) properties from Debts ---
    combined_loan = loan_amount
    combined_value = purchase_price
    for prop in st.session_state.properties:
        if prop.get("status") == "Being Sold — Firm (Unconditional) Sale Agreement":
            continue
        for mtg in prop.get("mortgages", []):
            combined_loan += parse_money(mtg.get("balance", "")) or 0.0
        combined_value += parse_money(prop.get("property_value", "")) or 0.0
    combined_ltv = (combined_loan / combined_value * 100) if combined_value else None
    combined_ltv_display = "{:.2f}%".format(combined_ltv) if combined_ltv is not None else "—"

    def help_combined_ltv_text():
        return (
            "Combined LTV = (subject loan " + fmt_money(loan_amount) + " + other property mortgage balances "
            + fmt_money(combined_loan - loan_amount) + ") ÷ (subject purchase price " + fmt_money(purchase_price)
            + " + other property values " + fmt_money(combined_value - purchase_price) + "). Properties being "
            "sold under a firm agreement are excluded, matching how they're excluded from GDS/TDS. Enter "
            "property value and mortgage balance for each property under Debts & Liabilities to populate this."
        )

    ltv_header_col, ltv_help_col = st.columns([12, 1])
    with ltv_header_col:
        st.markdown("**Combined LTV (Subject + Other Properties)**")
    with ltv_help_col:
        with st.container(key="helpbtn_help_combined_ltv"):
            with st.popover("?", key="help_combined_ltv"):
                st.caption(help_combined_ltv_text())
    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-card' style='max-width:calc(50% - 6px);'>"
        "<div class='metric-label'>Combined LTV</div>"
        "<div class='metric-value'>" + combined_ltv_display + "</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    if is_refinance():
        st.markdown("**Refinance Payout Summary**")
        breakdown = get_switch_payout_breakdown()
        if breakdown:
            for item in breakdown:
                st.caption(item["label"] + ": " + fmt_money(item["amount"]))
        st.markdown(
            "<div class='metric-row'>"
            "<div class='metric-card'><div class='metric-label' style='white-space:nowrap; font-size:12px;'>Loan Amount Requested</div>"
            "<div class='metric-value'>" + fmt_money(get_loan_amount()) + "</div></div>"
            "<div class='metric-card'><div class='metric-label' style='white-space:nowrap; font-size:12px;'>Mortgages/LOCs Paid Out</div>"
            "<div class='metric-value'>" + fmt_money(get_switch_total_mortgage_balance()) + "</div></div>"
            "<div class='metric-card'><div class='metric-label' style='white-space:nowrap; font-size:12px;'>Debts Paid Out</div>"
            "<div class='metric-value'>" + fmt_money(get_debts_payout_total()) + "</div></div>"
            "<div class='metric-card'><div class='metric-label' style='white-space:nowrap; font-size:12px;'>Net Proceeds Remaining</div>"
            "<div class='metric-value'>" + fmt_money(get_switch_net_proceeds()) + "</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if get_switch_net_proceeds() < 0:
            st.caption(":red[Requested loan amount is less than the mortgages/LOCs and debts being paid out — this shortfall needs to be resolved before proceeding.]")

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
                def mo_yr(monthly_val):
                    return "**" + fmt_money(monthly_val) + "**/mo  ·  **" + fmt_money(monthly_val * 12) + "**/yr"

                st.markdown("**Housing costs (GDS numerator)**")
                st.markdown("- Principal & Interest (contract, " + "{:.2f}%".format(st.session_state.contract_rate) + "): " + mo_yr(pi_payment))
                st.markdown("- Principal & Interest (stressed, " + "{:.2f}%".format(qualifying_rate) + "): " + mo_yr(stressed_pi))
                st.markdown("- Property Taxes: " + mo_yr(taxes))
                st.markdown("- Heat: " + mo_yr(heat))
                st.markdown("- Condo Fees (50% counted): " + mo_yr(condo * 0.5) + "  (full fee: " + mo_yr(condo) + ")")
                st.divider()
                st.markdown("**Other debts (added for TDS only)**")
                any_debt_line = False
                for instance_key in st.session_state.debt_selected:
                    dt = get_debt_type(instance_key)
                    if not dt:
                        continue
                    amounts = st.session_state.debt_amounts.get(instance_key, {})
                    excluded = (
                        st.session_state.debt_payout_selected.get(instance_key, False)
                        or st.session_state.debt_paid_from_own_funds.get(instance_key, False)
                    )
                    if excluded:
                        continue
                    pay_val = compute_debt_payment(dt, amounts)
                    label = debt_instance_label(dt, instance_key)
                    lender = amounts.get("lender", "").strip()
                    st.markdown("- " + label + (" (" + lender + ")" if lender else "") + ": " + mo_yr(pay_val))
                    any_debt_line = True
                for prop in st.session_state.properties:
                    if prop.get("status") == "Being Sold — Firm (Unconditional) Sale Agreement":
                        continue
                    p_total, m, t, c, h = compute_property_total(prop)
                    prop_label = "Other Property (" + (prop.get("address", "").strip() or "unnamed") + ")"
                    st.markdown("- " + prop_label + " — total: " + mo_yr(p_total))
                    st.markdown("&nbsp;&nbsp;&nbsp;mortgage " + mo_yr(m) + "  ·  taxes " + mo_yr(t) + "  ·  condo " + mo_yr(c) + "  ·  heat " + mo_yr(h))
                    any_debt_line = True
                if not any_debt_line:
                    st.caption("No other debts counted toward TDS.")
                st.divider()
                st.markdown("**Totals**")
                st.markdown("- Total Housing Costs (GDS, contract): " + mo_yr(annual_housing / 12))
                st.markdown("- Total Housing Costs (GDS, stressed): " + mo_yr(stressed_annual_housing / 12))
                st.markdown("- Total Debt Obligations (TDS, contract): " + mo_yr((annual_housing + annual_other_debt) / 12))
                st.markdown("- Total Debt Obligations (TDS, stressed): " + mo_yr((stressed_annual_housing + stressed_annual_other_debt) / 12))
                st.markdown("- Combined Gross Annual Income: **" + fmt_money(total_income) + "**/yr  ·  **" + fmt_money(total_income / 12) + "**/mo")
                st.divider()
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

    def build_other_debt_rows():
        """Itemized (label, monthly, annual) rows for every debt/property counted toward TDS —
        rate-independent, so identical for both the contract-rate and stressed panels."""
        rows = []
        for instance_key in st.session_state.debt_selected:
            dt = get_debt_type(instance_key)
            if not dt:
                continue
            amounts = st.session_state.debt_amounts.get(instance_key, {})
            excluded = (
                st.session_state.debt_payout_selected.get(instance_key, False)
                or st.session_state.debt_paid_from_own_funds.get(instance_key, False)
            )
            if excluded:
                continue
            pay_val = compute_debt_payment(dt, amounts)
            label = debt_instance_label(dt, instance_key)
            lender = amounts.get("lender", "").strip()
            if lender:
                label += " (" + lender + ")"
            rows.append((label, pay_val, pay_val * 12))
        for prop in st.session_state.properties:
            if prop.get("status") == "Being Sold — Firm (Unconditional) Sale Agreement":
                continue
            p_total, _, _, _, _ = compute_property_total(prop)
            addr = prop.get("address", "").strip() or "Unnamed property"
            rows.append((addr + " (other property)", p_total, p_total * 12))
        return rows

    def render_ratio_breakdown(pi_amount, annual_housing_amount, annual_other_debt_amount, gds_disp, tds_disp, is_stressed):
        rows = [
            ("Principal + Interest (P + I)", pi_amount, pi_amount * 12),
            ("Property Taxes (T)", taxes, taxes * 12),
            ("Heating (H)", heat, heat * 12),
            ("50% Condo Fees (0.5 × C)", condo * 0.5, condo * 0.5 * 12),
        ]
        cell = "padding:4px 8px; border-bottom:1px solid #94a3b8 !important; color:#0f172a !important; background:#f1f5f9 !important; word-break:break-word; overflow-wrap:break-word;"
        head = "padding:4px 8px; color:#0f172a !important; background:#cbd5e1 !important; font-weight:700 !important; word-break:break-word; overflow-wrap:break-word;"
        total_cell = "padding:10px 8px; color:#78350f !important; background:#fde047 !important; font-weight:700 !important; word-break:break-word; overflow-wrap:break-word;"

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
                "<div style='border:1px solid #334155; border-radius:6px; overflow:hidden;'>"
                "<table style='width:100%; table-layout:fixed; border-collapse:collapse; font-size:13px; margin-bottom:0;'>"
                "<tr>"
                "<th style='" + head + " text-align:left;'>Housing Cost Component</th>"
                "<th style='" + head + " text-align:right;'>Monthly</th>"
                "<th style='" + head + " text-align:right;'>Annual</th></tr>"
                + table_rows_html +
                "<tr>"
                "<td style='" + total_cell + "'>Total Annual Housing Costs (PITH)</td>"
                "<td style='" + total_cell + "'></td>"
                "<td style='" + total_cell + " text-align:right;'>" + fmt_money(annual_housing_amount) + "</td></tr>"
                "</table></div>",
                unsafe_allow_html=True,
            )

        with tds_col:
            other_debt_rows = build_other_debt_rows()
            tds_component_rows = list(rows)  # carry over the same PITH components shown on the GDS side
            tds_rows_html = "".join(
                "<tr><td style='" + cell + "'>" + name + "</td>"
                "<td style='" + cell + " text-align:right;'>" + fmt_money(monthly) + "</td>"
                "<td style='" + cell + " text-align:right;'>" + fmt_money(annual) + "</td></tr>"
                for name, monthly, annual in tds_component_rows
            )
            pith_subtotal_cell = "padding:4px 8px; color:#0f172a !important; background:#e2e8f0 !important; font-weight:700 !important;"
            tds_rows_html += (
                "<tr><td style='" + pith_subtotal_cell + "'>Housing Costs Subtotal (PITH, from GDS)</td>"
                "<td style='" + pith_subtotal_cell + " text-align:right;'>" + fmt_money(annual_housing_amount / 12) + "</td>"
                "<td style='" + pith_subtotal_cell + " text-align:right;'>" + fmt_money(annual_housing_amount) + "</td></tr>"
            )
            if other_debt_rows:
                for name, monthly, annual in other_debt_rows:
                    tds_rows_html += (
                        "<tr><td style='" + cell + "'>" + name + "</td>"
                        "<td style='" + cell + " text-align:right;'>" + fmt_money(monthly) + "</td>"
                        "<td style='" + cell + " text-align:right;'>" + fmt_money(annual) + "</td></tr>"
                    )
            else:
                tds_rows_html += (
                    "<tr><td style='" + cell + "'>Other Monthly Debt Payments</td>"
                    "<td style='" + cell + " text-align:right;'>" + fmt_money(annual_other_debt_amount / 12) + "</td>"
                    "<td style='" + cell + " text-align:right;'>" + fmt_money(annual_other_debt_amount) + "</td></tr>"
                )
            tds_rows_html += (
                "<tr><td style='" + pith_subtotal_cell + "'>Other Debts Subtotal</td>"
                "<td style='" + pith_subtotal_cell + " text-align:right;'>" + fmt_money(annual_other_debt_amount / 12) + "</td>"
                "<td style='" + pith_subtotal_cell + " text-align:right;'>" + fmt_money(annual_other_debt_amount) + "</td></tr>"
            )
            grand_total_annual = annual_housing_amount + annual_other_debt_amount
            st.markdown(
                "<div style='border:1px solid #334155; border-radius:6px; overflow:hidden;'>"
                "<table style='width:100%; table-layout:fixed; border-collapse:collapse; font-size:13px; margin-bottom:0;'>"
                "<tr>"
                "<th style='" + head + " text-align:left;'>Debt Obligation Component</th>"
                "<th style='" + head + " text-align:right;'>Monthly</th>"
                "<th style='" + head + " text-align:right;'>Annual</th></tr>"
                + tds_rows_html +
                "<tr>"
                "<td style='" + total_cell + "'>Total Annual Debt Obligations</td>"
                "<td style='" + total_cell + "' colspan='2'>" + fmt_money(annual_housing_amount) + " + " + fmt_money(annual_other_debt_amount)
                + " = " + fmt_money(grand_total_annual) + "</td></tr>"
                "</table></div>",
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
    back_col, refresh_col, docs_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p5_back"):
            st.session_state.step = 5
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p5_refresh"):
            st.session_state["p5_show_refresh_confirm"] = True

    if st.session_state.get("p5_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data across all pages will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p5_confirm_refresh"):
                refresh_all()
                st.session_state["p5_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p5_cancel_refresh"):
                st.session_state["p5_show_refresh_confirm"] = False
                st.rerun()

    with docs_col:
        if st.button("Required Documents →", use_container_width=True, key="p5_to_docs"):
            st.session_state.step = 7
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

ALL_CHECKLIST_CATEGORIES = [
    "Application & Consent", "Identification", "Down Payment", "Income",
    "Property Being Purchased", "Other Properties Owned", "Other Debts & Liabilities",
    "Switch-In (Refinance - New Lender)", "Refinance (Existing Lender)", "Debts Paid from Own/Gifted Funds",
    "Builder Program", "Additional Documents",
]


def get_relevant_checklist_categories():
    """
    The subset of ALL_CHECKLIST_CATEGORIES that could plausibly apply to the
    CURRENT transaction type — used so edit mode doesn't offer categories
    like Builder Program or Switch-In on, say, a plain resale Purchase file.
    Categories that depend on other data (Other Properties Owned, Other
    Debts & Liabilities, Debts Paid from Own/Gifted Funds) stay available
    for every type, since any deal can have those.
    """
    relevant = [
        "Application & Consent", "Identification", "Income", "Other Properties Owned",
        "Other Debts & Liabilities", "Debts Paid from Own/Gifted Funds", "Additional Documents",
    ]
    if not is_refinance():
        relevant += ["Down Payment", "Property Being Purchased"]
    if st.session_state.transaction_type == "builder_purchase":
        relevant.append("Builder Program")
    if st.session_state.transaction_type == "refinance_new_lender":
        relevant.append("Switch-In (Refinance - New Lender)")
    if st.session_state.transaction_type == "refinance_existing_lender":
        relevant.append("Refinance (Existing Lender)")
    # Preserve the canonical ordering from ALL_CHECKLIST_CATEGORIES.
    return [c for c in ALL_CHECKLIST_CATEGORIES if c in relevant]


def borrower_display_name(idx):
    borrowers = st.session_state.borrowers
    if idx < len(borrowers) and borrowers[idx]["full_name"].strip():
        return borrowers[idx]["full_name"].strip().title()
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
        borrower = st.session_state.borrowers[idx] if idx < len(st.session_state.borrowers) else {}
        if borrower.get("marital_status") == "Divorced":
            id_items.append({
                "applicant": name,
                "text": "Divorce judgment/final order or separation agreement — confirms whether spousal/child "
                        "support is owed or received, since this affects TDS",
            })
    if id_items:
        categories.append({"name": "Identification", "items": id_items})

    # Down Payment — one item per selected source per its required document (purchase deals only;
    # switch/refinance deals have no down payment).
    if not is_refinance():
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

    if not is_refinance():
        subject_prop_items = []
        for d in SUBJECT_PROPERTY_DOCS:
            if d == "MLS listing or property summary, if available":
                if st.session_state.property_purchase_channel == "Private Sale - No MLS":
                    continue  # no MLS listing exists for a private sale — nothing to request
                elif st.session_state.property_purchase_channel == "MLS Listed":
                    subject_prop_items.append({"text": "MLS listing printout"})
                    continue
            subject_prop_items.append({"text": d})
        categories.append({
            "name": "Property Being Purchased",
            "items": subject_prop_items,
        })

    # Other Properties Owned — one item per property per standard doc label
    other_prop_items = []
    for pidx, prop in enumerate(st.session_state.properties):
        label = prop["address"].strip() if prop["address"].strip() else "Property " + str(pidx + 1)
        for doc in OTHER_PROPERTY_DOC_LABELS:
            other_prop_items.append({"subcategory": label, "text": doc})
    if other_prop_items:
        categories.append({"name": "Other Properties Owned", "items": other_prop_items})

    # Other Debts & Liabilities — one item per selected debt instance per document.
    # Debts paid from own/gifted funds skip the standard financing docs here — their only
    # requirement is proof of payout, already listed under its own category below.
    debt_items = []
    for key in st.session_state.debt_selected:
        dt = get_debt_type(key)
        if dt and not st.session_state.debt_paid_from_own_funds.get(key, False):
            lender_name = st.session_state.debt_amounts.get(key, {}).get("lender", "").strip()
            label = (dt["label"] + " — " + lender_name) if lender_name else debt_instance_label(dt, key)
            for doc in dt["documents"]:
                debt_items.append({"subcategory": label, "text": doc})
    if debt_items:
        categories.append({"name": "Other Debts & Liabilities", "items": debt_items})

    # Builder Purchase Program — standard documents plus conditional items driven by the
    # builder details entered on Property Details.
    if st.session_state.transaction_type == "builder_purchase":
        builder_items = []
        breqs = builder_document_requirements()
        for doc in breqs["documents"]:
            builder_items.append({"subcategory": "Builder Purchase", "text": doc})
        if st.session_state.builder_gst_hst_included == "No":
            builder_items.append({"subcategory": "GST/HST", "text": breqs["conditional"]["gst_hst_not_included"]})
        if st.session_state.builder_rate_buydown == "Yes":
            builder_items.append({"subcategory": "Interest Rate Buydown", "text": breqs["conditional"]["interest_rate_buydown"]})
        if st.session_state.builder_warranty_provider.strip():
            builder_items.append({"subcategory": "Warranty", "text": breqs["conditional"]["warranty_pending"]})
        if builder_items:
            categories.append({"name": "Builder Program", "items": builder_items})

    # Switch-In (Refinance - New Lender) — mandatory documents/business case notes from the
    # switch-in rules module, plus conditional items driven by the due-diligence answers.
    if st.session_state.transaction_type == "refinance_new_lender":
        switch_items = []
        reqs = switch_in_document_requirements()
        ofi_label = st.session_state.switch_ofi_name.strip() if st.session_state.switch_ofi_name.strip() else "OFI Mortgage Verification"
        for doc in reqs["documents"]:
            switch_items.append({"subcategory": ofi_label, "text": doc})
        for lender in get_switch_additional_lenders():
            label = lender["name"].strip() if lender["name"] and lender["name"].strip() else "Additional Lender"
            switch_items.append({
                "subcategory": label,
                "text": "Statement confirming balance ("
                + (fmt_money(lender["balance"]) if lender["balance"] is not None else "amount not specified")
                + "), registration (" + (lender["reg_type"] or "not specified")
                + ") and mortgage type (" + (lender["mortgage_type"] or "not specified") + ") for this mortgage/LOC",
            })
        if st.session_state.switch_mortgages_good_standing == "No":
            switch_items.append({
                "subcategory": "Standing", "text": "Written explanation for mortgage/LOC not in good standing",
            })
        if st.session_state.switch_taxes_up_to_date == "No":
            switch_items.append({
                "subcategory": "Property Taxes", "text": "Current property tax statement showing amount owing",
            })
        switch_items.append({"subcategory": "Property Insurance", "text": "Proof of current property insurance"})
        if switch_items:
            categories.append({"name": "Switch-In (Refinance - New Lender)", "items": switch_items})

    # Refinance (Existing Lender) — same lender staying on title; internal-refinance requirements
    # driven by the refinance rules module and the lender/standing/insurance answers.
    if st.session_state.transaction_type == "refinance_existing_lender":
        refi_items = []
        for lender in get_switch_additional_lenders():
            label = lender["name"].strip() if lender["name"] and lender["name"].strip() else "Additional Lender"
            refi_items.append({
                "subcategory": label,
                "text": "Statement confirming balance ("
                + (fmt_money(lender["balance"]) if lender["balance"] is not None else "amount not specified")
                + ") and mortgage type (" + (lender["mortgage_type"] or "not specified") + ") for this mortgage/LOC",
            })
        if st.session_state.switch_mortgages_good_standing == "No":
            refi_items.append({
                "subcategory": "Standing", "text": "Written explanation for mortgage/LOC not in good standing",
            })
        if st.session_state.switch_taxes_up_to_date == "No":
            refi_items.append({
                "subcategory": "Property Taxes", "text": "Current property tax statement showing amount owing",
            })
        if st.session_state.switch_borrowers_changed == "Yes":
            refi_items.append({
                "subcategory": "Change of Borrower",
                "text": "New refinance application in the name of all borrowers/guarantors who will be on the new mortgage, and confirmation of the title change",
            })
        refi_items.append({"subcategory": "Property Insurance", "text": "Proof of current property insurance"})
        refi_items.append({"subcategory": "Property Valuation", "text": "Current property valuation/appraisal (LTV is based on appraised value, not original purchase price)"})
        if refi_items:
            categories.append({"name": "Refinance (Existing Lender)", "items": refi_items})

    # Debts Paid from Own/Gifted Funds — applies to every transaction type, since a debt can be
    # paid off from the client's own resources ahead of closing regardless of deal type.
    own_funds_items = []
    for dkey, own_funds in st.session_state.debt_paid_from_own_funds.items():
        if own_funds:
            dt = get_debt_type(dkey)
            label = debt_instance_label(dt, dkey) if dt else dkey
            own_funds_items.append({
                "subcategory": label,
                "text": "Proof of payout (current statement showing zero balance, or payout receipt)",
            })
    if own_funds_items:
        categories.append({"name": "Debts Paid from Own/Gifted Funds", "items": own_funds_items})

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


def annotate_item_keys(data):
    """Stamps each item with a stable '_key' derived from its default (un-edited) text, before any overrides are applied.
    If two items genuinely produce the same key (e.g. identical text under the same subcategory), an
    occurrence suffix is appended so Streamlit widget keys never collide."""
    seen_counts = {}
    for category in data.get("categories", []):
        name = category.get("name", "")
        for item in category.get("items", []):
            base_key = checklist_item_key(name, item)
            seen_counts[base_key] = seen_counts.get(base_key, 0) + 1
            occurrence = seen_counts[base_key]
            item["_key"] = base_key if occurrence == 1 else base_key + "||#" + str(occurrence)
    return data


def apply_text_overrides(data, overrides):
    """Swaps in any broker-edited wording, matched by each item's stable _key (based on its original default text)."""
    for category in data.get("categories", []):
        for item in category.get("items", []):
            key = item.get("_key")
            if key and key in overrides:
                item["text"] = overrides[key]
    return data


def add_custom_items(data, custom_items_by_category, all_category_names):
    """
    Ensures every category in `all_category_names` exists (even if empty), then
    appends any broker-added custom document lines to their category.
    """
    categories_by_name = {c["name"]: c for c in data.get("categories", [])}
    for name in all_category_names:
        if name not in categories_by_name:
            new_cat = {"name": name, "items": []}
            data.setdefault("categories", []).append(new_cat)
            categories_by_name[name] = new_cat

    for cat_name, custom_texts in custom_items_by_category.items():
        if cat_name not in categories_by_name:
            continue
        for i, text in enumerate(custom_texts):
            item = {"text": text, "custom": True}
            item["_key"] = "CUSTOM||" + cat_name + "||" + str(i)
            categories_by_name[cat_name]["items"].append(item)

    # Preserve the original category ordering (all_category_names first, in order).
    ordered = [categories_by_name[n] for n in all_category_names if n in categories_by_name]
    for c in data.get("categories", []):
        if c["name"] not in all_category_names:
            ordered.append(c)
    data["categories"] = ordered
    return data


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
    _preview_count = sum(len(c.get("items", [])) for c in categories)
    st.caption(str(_preview_count) + " document(s) required for this file.")
    for cat_idx, category in enumerate(categories):
        items = category.get("items", [])
        cat_name = category.get("name", "")
        always_show = cat_name == "Additional Documents"
        if not items and not always_show:
            continue
        total_count += len(items)
        with st.container(key="card_doc_cat_" + str(cat_idx)):
            st.markdown(
                "<div style='font-size:15px; font-weight:700; margin-top:0; margin-bottom:4px;'>"
                + cat_name + " (" + str(len(items)) + ")</div>",
                unsafe_allow_html=True,
            )
            if not items:
                st.caption("N/A — no additional documents added for this file.")
                continue

            for (applicant, subcategory), group_items in group_checklist_items(items):
                if applicant or subcategory:
                    heading_parts = []
                    if applicant:
                        heading_parts.append("<b>" + applicant + "</b>")
                    if subcategory:
                        heading_parts.append(subcategory)
                    st.markdown(
                        "<div style='margin-left:20px; font-weight:600; margin-top:12px; margin-bottom:4px; font-size:14px;'>"
                        + " — ".join(heading_parts) + "</div>",
                        unsafe_allow_html=True,
                    )
                    item_indent = 40
                else:
                    item_indent = 20

                for item in group_items:
                    st.markdown(
                        "<div style='margin-left:" + str(item_indent) + "px; margin-bottom:4px; font-size:13px; "
                        "line-height:1.5; overflow-wrap:break-word; display:flex; align-items:flex-start; gap:8px;'>"
                        "<span style='flex-shrink:0; margin-top:2px; width:14px; height:14px; border:1.5px solid #6b7280; "
                        "border-radius:3px; display:inline-block;'></span>"
                        "<span>" + item["text"] + "</span></div>",
                        unsafe_allow_html=True,
                    )

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
        kept_items = [
            it for it in category.get("items", [])
            if it.get("_key", checklist_item_key(name, it)) not in removed_set
        ]
        filtered.append({"name": name, "items": kept_items})
    return {"categories": filtered}


def render_document_checklist_editable(data):
    """
    Edit-mode view: every item gets a checkbox (checked = keep) and an
    editable text field (so wording like "2 years financials" can become
    "3 years financials"). Every category also gets an "add a document"
    box, even if it currently has no items, so brokers can add a custom
    requirement to any category. Unchecking + saving permanently removes
    an item; editing text + saving permanently rewords it. Custom items
    are added immediately (not gated behind Save).

    Returns (unchecked_keys, text_edits) — the caller merges these into
    session state on Save.
    """
    unchecked_keys = set()
    text_edits = {}

    for cat_idx, category in enumerate(data.get("categories", [])):
        cat_name = category.get("name", "")
        items = category.get("items", [])
        with st.container(key="card_doc_edit_" + str(cat_idx)):
            st.markdown(
                "<div style='font-size:15px; font-weight:700; margin-top:0; margin-bottom:4px;'>"
                + cat_name + " (" + str(len(items)) + ")</div>",
                unsafe_allow_html=True,
            )

            if not items:
                st.caption("No documents in this category yet.")

            for (applicant, subcategory), group_items in group_checklist_items(items):
                if applicant or subcategory:
                    heading_parts = []
                    if applicant:
                        heading_parts.append("<b>" + applicant + "</b>")
                    if subcategory:
                        heading_parts.append(subcategory)
                    st.markdown(
                        "<div style='margin-left:20px; font-weight:600; margin-top:12px; margin-bottom:4px; font-size:14px;'>"
                        + " — ".join(heading_parts) + "</div>",
                        unsafe_allow_html=True,
                    )

                for item in group_items:
                    key = item.get("_key") or checklist_item_key(cat_name, item)
                    row_col, text_col = st.columns([1, 9])
                    with row_col:
                        keep = st.checkbox("", value=True, key="doc_edit_keep_" + key, label_visibility="collapsed")
                    with text_col:
                        edited_text = st.text_input(
                            "Document", value=item["text"], key="doc_edit_text_" + key, label_visibility="collapsed",
                        )
                    if not keep:
                        unchecked_keys.add(key)
                    if edited_text != item["text"]:
                        text_edits[key] = edited_text

            # Add a custom document line to this category — applies immediately.
            add_col, btn_col = st.columns([4, 1])
            new_doc_input_key = "doc_add_new_" + cat_name
            with add_col:
                new_doc_text = st.text_input(
                    "Add a document to " + cat_name, value="", key=new_doc_input_key,
                    placeholder="e.g. 3 years of financial statements", label_visibility="collapsed",
                )
            with btn_col:
                if st.button("+ Add", key="doc_add_btn_" + cat_name, use_container_width=True):
                    if new_doc_text.strip():
                        existing = dict(st.session_state.doc_custom_items)
                        existing.setdefault(cat_name, [])
                        existing[cat_name] = existing[cat_name] + [new_doc_text.strip()]
                        st.session_state.doc_custom_items = existing
                        st.rerun()

    return unchecked_keys, text_edits


def render_documents():
    render_calculator_popover("documents")
    raw_checklist_data = build_document_checklist_data()
    annotate_item_keys(raw_checklist_data)
    apply_text_overrides(raw_checklist_data, st.session_state.doc_text_overrides)
    add_custom_items(raw_checklist_data, st.session_state.doc_custom_items, get_relevant_checklist_categories())
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
    if st.session_state.doc_text_overrides:
        st.caption(str(len(st.session_state.doc_text_overrides)) + " item(s) reworded from their default text.")

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
            use_container_width=True,
        )

        st.divider()
        reviewed_checked = st.session_state.get("docs_reviewed_input", st.session_state.docs_reviewed)
        box_key = "docs_reviewed_box_done" if reviewed_checked else "docs_reviewed_box_pending"
        with st.container(key=box_key):
            reviewed_label = (
                ":green[**✓ I have reviewed the checklist**]" if reviewed_checked
                else "**⚠ I have reviewed the checklist**"
            )
            st.session_state.docs_reviewed = st.checkbox(
                reviewed_label, value=reviewed_checked, key="docs_reviewed_input",
            )
    else:
        st.warning(
            "**Edit mode:** uncheck an item to permanently remove it, edit its text to reword it (e.g. "
            "\"2 years financials\" → \"3 years financials\"), or use \"+ Add\" at the bottom of any "
            "category to add a document that isn't listed. Removals and rewording take effect on Save; "
            "additions apply immediately."
        )
        unchecked_keys, text_edits = render_document_checklist_editable(checklist_data)

        st.divider()
        save_col, cancel_col = st.columns(2)
        with save_col:
            if st.button("💾 Save Changes", type="primary", use_container_width=True, key="doc_save_edits"):
                st.session_state["doc_pending_removal"] = list(unchecked_keys)
                st.session_state["doc_pending_text_edits"] = text_edits
                st.session_state["doc_show_save_confirm"] = True
        with cancel_col:
            if st.button("Cancel", use_container_width=True, key="doc_cancel_edits"):
                st.session_state.doc_edit_mode = False
                st.rerun()

        if st.session_state.get("doc_show_save_confirm"):
            pending = st.session_state.get("doc_pending_removal", [])
            pending_edits = st.session_state.get("doc_pending_text_edits", {})
            if pending or pending_edits:
                msg_parts = []
                if pending:
                    msg_parts.append(str(len(pending)) + " item(s) permanently removed")
                if pending_edits:
                    msg_parts.append(str(len(pending_edits)) + " item(s) reworded")
                st.warning(
                    "This will save: " + " and ".join(msg_parts) + ". Removals cannot be undone from within "
                    "this page (short of a full Refresh)."
                )
            else:
                st.info("No changes were made — nothing to save.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm & Save", type="primary", use_container_width=True, key="doc_confirm_save"):
                    existing_removed = set(st.session_state.doc_removed_items)
                    existing_removed.update(pending)
                    st.session_state.doc_removed_items = list(existing_removed)

                    existing_overrides = dict(st.session_state.doc_text_overrides)
                    existing_overrides.update(pending_edits)
                    st.session_state.doc_text_overrides = existing_overrides

                    st.session_state.doc_edit_mode = False
                    st.session_state["doc_show_save_confirm"] = False
                    st.rerun()
            with c2:
                if st.button("Cancel", use_container_width=True, key="doc_cancel_save"):
                    st.session_state["doc_show_save_confirm"] = False
                    st.rerun()

    st.divider()

    back_col, refresh_col, notes_col = st.columns(3)
    with back_col:
        if st.button("← Back to Analysis", use_container_width=True, key="p6_back"):
            st.session_state.step = 6
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p6_refresh"):
            st.session_state["p6_show_refresh_confirm"] = True
    with notes_col:
        if st.button("Notes →", use_container_width=True, key="p6_to_notes"):
            st.session_state.step = 8
            st.rerun()

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


def extract_dollar_mentions(text, keywords):
    """
    Finds dollar-figure mentions near any of the given keywords in free text, e.g.
    'client earns 200K annual' with keywords ['earn','income','salary'] -> [200000.0].
    Handles '$200,000', '200,000', '200k', '200K'. Pattern-matching only — not AI,
    won't catch phrasing it doesn't recognize.
    """
    found = []
    lower_text = text.lower()
    for keyword in keywords:
        for m in re.finditer(re.escape(keyword), lower_text):
            window = lower_text[max(0, m.start() - 40): m.end() + 40]
            for num_match in re.finditer(r"\$?\s*([\d,]+(?:\.\d+)?)\s*(k)?", window):
                raw, k_suffix = num_match.groups()
                cleaned = raw.replace(",", "")
                if cleaned in ("", "."):
                    continue
                try:
                    value = float(cleaned)
                except ValueError:
                    continue
                if k_suffix:
                    value *= 1000
                if value >= 1000 or k_suffix:
                    found.append(value)
    return found






def detect_intake_discrepancies():
    """
    Pattern-matches the free-text Client Intake Notes against structured application
    data and flags obvious mismatches. This is regex/keyword matching, not AI — it
    only catches the phrasing patterns below and can miss or misfire; always confirm
    manually before relying on it. Also includes a couple of purely structured
    (non-text) internal consistency checks that don't depend on intake notes at all.
    """
    flags = []

    # --- Residence disposition vs rental income (structured — no intake notes needed) ---
    sold_dispositions = ("Sold — Firm Sale", "Sold — Conditional Sale", "Currently Listed for Sale", "To Be Listed / Sold")
    for idx, b in enumerate(st.session_state.borrowers[:st.session_state.borrower_count]):
        if b.get("residence_disposition") in sold_dispositions:
            bidx = str(idx)
            name = b.get("full_name", "").strip() or ("Borrower " + str(idx + 1))
            selected_base_keys = {base_income_key(k) for k in st.session_state.income_selected.get(bidx, [])}
            if "rental" in selected_base_keys:
                flags.append(
                    name + " indicated their current property is being sold/listed (\""
                    + b["residence_disposition"] + "\"), but Rental Property Income is included in their "
                    "income — confirm this rental income is from a different property, not the one being sold."
                )

    text = st.session_state.client_intake_notes
    if not text.strip():
        return flags

    lower_text = text.lower()

    # --- Income ---
    income_mentions = extract_dollar_mentions(text, ["earn", "income", "salary", "makes"])
    if income_mentions:
        app_income = compute_total_income()
        mentioned = income_mentions[0]
        if app_income == 0:
            flags.append(
                "Intake notes mention income of about " + fmt_money(mentioned)
                + ", but no income has been entered yet on the Income step."
            )
        elif abs(mentioned - app_income) / max(app_income, 1) > 0.10:
            flags.append(
                "Intake notes mention income of about " + fmt_money(mentioned)
                + ", but the Income step totals " + fmt_money(app_income) + "."
            )

    # --- Marital status ---
    marital_keywords = {
        "married": "Married", "single": "Single", "divorced": "Divorced",
        "widowed": "Widowed", "common-law": "Common-Law", "common law": "Common-Law",
    }
    for idx, b in enumerate(st.session_state.borrowers[:st.session_state.borrower_count]):
        name = b.get("full_name", "").strip() or ("Borrower " + str(idx + 1))
        app_marital = b.get("marital_status", "")
        for keyword, implied_status in marital_keywords.items():
            if keyword in lower_text and app_marital and implied_status != app_marital:
                flags.append(
                    "Intake notes mention \"" + keyword + "\", but " + name
                    + "'s Marital Status on Client Details is set to \"" + app_marital + "\"."
                )
                break

    # --- Employment type (salaried vs. self-employed) ---
    # Conservative by design: only flags when the notes clearly state ONE employment
    # type and NONE of that type's income sources were entered anywhere for that
    # borrower — never flags when both types are mentioned/entered, since having
    # both salaried and self-employed income is common and not a real conflict.
    salaried_phrases = ["salaried", "salary", "full-time employee", "full time employee", "works for", "employed at", "employed by"]
    self_employed_phrases = ["self-employed", "self employed", "own business", "runs a business", "owns a business", "sole proprietor", "freelance", "independent contractor"]
    self_employed_type_keys = ("self_employed", "self_employed_incorporated", "self_employed_professional")
    mentions_salaried = any(p in lower_text for p in salaried_phrases)
    mentions_self_employed = any(p in lower_text for p in self_employed_phrases)
    if mentions_salaried != mentions_self_employed:  # exactly one is mentioned, not both/neither
        for idx in range(st.session_state.borrower_count):
            bidx = str(idx)
            b = st.session_state.borrowers[idx] if idx < len(st.session_state.borrowers) else {}
            name = b.get("full_name", "").strip() or ("Borrower " + str(idx + 1))
            selected_base_keys = {base_income_key(k) for k in st.session_state.income_selected.get(bidx, [])}
            has_salaried = "salaried" in selected_base_keys
            has_self_employed = any(k in selected_base_keys for k in self_employed_type_keys)
            if mentions_salaried and not has_salaried and not has_self_employed:
                flags.append(
                    "Intake notes mention salaried employment, but " + name
                    + " has no Employed (Salaried) income entered on the Income step."
                )
            elif mentions_self_employed and not has_self_employed and not has_salaried:
                flags.append(
                    "Intake notes mention self-employment, but " + name
                    + " has no self-employed income source entered on the Income step."
                )

    # --- Down payment (purchase/builder purchase only) ---
    if not is_refinance():
        dp_mentions = extract_dollar_mentions(text, ["down payment", "downpayment"])
        if dp_mentions:
            app_dp = parse_money(st.session_state.down_payment_raw) or 0.0
            mentioned = dp_mentions[0]
            if app_dp == 0:
                flags.append(
                    "Intake notes mention a down payment of about " + fmt_money(mentioned)
                    + ", but no down payment has been entered yet on the Down Payment step."
                )
            elif abs(mentioned - app_dp) / max(app_dp, 1) > 0.10:
                flags.append(
                    "Intake notes mention a down payment of about " + fmt_money(mentioned)
                    + ", but the Down Payment step shows " + fmt_money(app_dp) + "."
                )

    # --- Property type ---
    # Naive keyword matching can't tell "buying a condo" from "selling my detached house" —
    # a bare first-match would wrongly flag the client's OLD home's type against the NEW
    # subject property. Instead, prefer a property-type keyword sitting near purchase-ish
    # language ("buying", "purchasing", "new home"), and skip any mention sitting near
    # "current/existing/selling" language, since that's describing a different property.
    property_type_keywords = {
        "detached": "Detached", "semi-detached": "Semi-Detached", "semi detached": "Semi-Detached",
        "townhouse": "Townhouse", "townhome": "Townhouse", "town home": "Townhouse",
        "condo": "Condominium", "condominium": "Condominium", "apartment": "Condominium",
        "duplex": "Duplex", "triplex": "Triplex", "fourplex": "Fourplex",
        "bungalow": "Detached", "single family": "Detached", "single-family": "Detached",
    }
    purchase_context_words = ["buying", "purchasing", "purchase of", "new home", "new property", "new place"]
    current_context_words = ["current", "existing", "currently liv", "selling my", "sell their", "sell his", "sell her", "my current", "their current"]

    purchase_match = None
    fallback_match = None
    for keyword, implied_type in property_type_keywords.items():
        for m in re.finditer(re.escape(keyword), lower_text):
            window = lower_text[max(0, m.start() - 40): m.start()]
            near_purchase = any(w in window for w in purchase_context_words)
            near_current = any(w in window for w in current_context_words)
            if near_purchase:
                purchase_match = (keyword, implied_type)
            elif not near_current and fallback_match is None:
                fallback_match = (keyword, implied_type)

    best_match = purchase_match or fallback_match
    if best_match:
        keyword, implied_type = best_match
        app_type = st.session_state.subject_prop_type
        if app_type and implied_type not in app_type and app_type not in implied_type:
            flags.append(
                "Intake notes mention \"" + keyword + "\" in the context of the purchase, but Property Details "
                "shows the property type as \"" + app_type + "\" — confirm which property this refers to."
            )

    # --- Rental unit / secondary suite ---
    rental_keywords = ["rental unit", "secondary suite", "basement suite", "basement apartment", "rented out", "in-law suite"]
    no_rental_phrases = ["no rental income", "no rental unit", "not rented", "no rental", "doesn't have a rental", "does not have a rental"]
    mentioned_rental = any(k in lower_text for k in rental_keywords)
    no_rental_stated = any(p in lower_text for p in no_rental_phrases)

    has_rental_income_entered = False
    for idx in range(st.session_state.borrower_count):
        for skey in st.session_state.income_selected.get(str(idx), []):
            if "rental" in skey:
                has_rental_income_entered = True

    if no_rental_stated and (st.session_state.subject_has_rental_component == "Yes" or has_rental_income_entered):
        flags.append(
            "Intake notes explicitly say there's no rental income, but the application has "
            + ("Property Details' Rental Component marked \"Yes\"" if st.session_state.subject_has_rental_component == "Yes" else "")
            + (" and " if st.session_state.subject_has_rental_component == "Yes" and has_rental_income_entered else "")
            + ("a rental income source entered on the Income step" if has_rental_income_entered else "")
            + " — this is a direct contradiction and should be confirmed with the client before proceeding."
        )
    elif mentioned_rental and st.session_state.subject_has_rental_component != "Yes":
        flags.append(
            "Intake notes mention a rental unit/secondary suite, but Property Details' Rental Component "
            "question isn't marked \"Yes\"."
        )
    elif not mentioned_rental and not no_rental_stated and st.session_state.subject_has_rental_component == "Yes":
        flags.append(
            "Property Details indicates a rental unit/secondary suite, but the intake notes don't mention one — confirm the client disclosed this."
        )

    return flags


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
    exceptions_bits = []

    # --- Purpose of Funds (mandatory — per business-case guidance, must be stated on every file) ---
    purpose_bits = []
    if st.session_state.transaction_type == "purchase":
        purpose_bits.append("Purchase of a resale property")
        if st.session_state.subject_prop_purpose:
            purpose_bits.append("intended use: " + st.session_state.subject_prop_purpose.lower())
    elif st.session_state.transaction_type == "builder_purchase":
        purpose_bits.append("Purchase of a newly constructed property from a builder")
        if st.session_state.subject_prop_purpose:
            purpose_bits.append("intended use: " + st.session_state.subject_prop_purpose.lower())
    elif is_refinance():
        debt_payout_bits = []
        for dkey, included in st.session_state.debt_payout_selected.items():
            if included:
                dt = get_debt_type(dkey)
                if dt:
                    debt_payout_bits.append(debt_instance_label(dt, dkey))
        if debt_payout_bits:
            purpose_bits.append("Debt consolidation — paying out " + ", ".join(debt_payout_bits) + " from proceeds")
        if st.session_state.switch_additional_funds == "Yes":
            purpose_bits.append("client is requesting additional funds (cash out)")
        if st.session_state.subject_has_rental_component == "Yes" and st.session_state.transaction_type == "refinance_existing_lender":
            purpose_bits.append("refinancing to add/formalize a secondary suite")
        if not purpose_bits:
            purpose_bits.append(
                "Renewal/refinance of existing mortgage financing"
                + (" with " + st.session_state.switch_ofi_name if st.session_state.switch_ofi_name.strip() else "")
            )
    if purpose_bits:
        lines.append("**PURPOSE OF FUNDS**\n" + ". ".join(purpose_bits) + ".")

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
            "**APPLICANT(S)**\nThis application includes " + str(st.session_state.borrower_count)
            + " borrower(s): " + "; ".join(borrower_bits) + "."
        )

    # --- Down payment source (Purchase / Builder Purchase only) ---
    if not is_refinance():
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
                "**DOWN PAYMENT / SOURCE OF FUNDS**\n" + fmt_money(dp_amount) + pct_str + " on a purchase price of " + fmt_money(purchase_price)
                + ". Source(s): " + source_str + ". Confirm date and manner of acquisition for AML purposes."
            )
    else:
        loan_amount_note = get_loan_amount()
        property_value_note = parse_money(st.session_state.subject_property_value_raw) or 0.0
        if loan_amount_note or property_value_note:
            ltv_note = " (LTV: {:.1f}%)".format(loan_amount_note / property_value_note * 100) if property_value_note else ""
            lines.append(
                "**LOAN AMOUNT & LTV**\nMortgage loan amount of " + fmt_money(loan_amount_note) + " against an estimated "
                "property value of " + fmt_money(property_value_note) + ltv_note + "."
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
            "**INCOME & EMPLOYMENT**\nCombined gross annual income of " + fmt_money(total_income) + ". "
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
        lines.append("**PROPERTY**\n" + ", ".join(prop_bits) + ".")
    if st.session_state.subject_has_rental_component == "Yes":
        self_contained = (
            st.session_state.subject_rental_kitchen and st.session_state.subject_rental_bathroom
            and st.session_state.subject_rental_entrance
        )
        lines.append(
            "Rental component: property has a rental unit. Self-contained (kitchen/bathroom/separate entrance): "
            + ("Yes — rental income usable for qualification." if self_contained
               else "No — rental income cannot be used for qualification.")
        )
        if not self_contained:
            exceptions_bits.append("Rental unit is not confirmed self-contained — its income was excluded from qualification; address whether the client can service the mortgage without it.")

    # --- GDS/TDS ---
    pi_payment, taxes, condo, heat, _ = get_subject_property_costs()
    other_debt_monthly = 0.0
    for dkey in st.session_state.debt_selected:
        dt = get_debt_type(dkey)
        amounts = st.session_state.debt_amounts.get(dkey, {})
        excluded = (
            st.session_state.debt_payout_selected.get(dkey, False)
            or st.session_state.debt_paid_from_own_funds.get(dkey, False)
        )
        if not excluded:
            other_debt_monthly += compute_debt_payment(dt, amounts)
    for prop in st.session_state.properties:
        if prop.get("status") == "Being Sold — Firm (Unconditional) Sale Agreement":
            continue
        p_total, _, _, _, _ = compute_property_total(prop)
        other_debt_monthly += p_total

    gds, tds, _, _ = compute_gds_tds(pi_payment, taxes, heat, condo, other_debt_monthly, total_income)
    qualifying_rate = max(st.session_state.contract_rate + STRESS_TEST_ADDON, st.session_state.benchmark_rate)
    loan_amount = get_loan_amount()
    stressed_pi = monthly_mortgage_payment(loan_amount, qualifying_rate, st.session_state.amortization_years)
    stressed_gds, stressed_tds, _, _ = compute_gds_tds(stressed_pi, taxes, heat, condo, other_debt_monthly, total_income)

    if gds is not None and tds is not None:
        qualifies = gds <= GDS_LIMIT and tds <= TDS_LIMIT
        stress_qualifies = stressed_gds is not None and stressed_tds is not None and stressed_gds <= GDS_LIMIT and stressed_tds <= TDS_LIMIT
        lines.append(
            "**CAPACITY (TDS/GDS)**\nAt the contract rate of {:.2f}%, GDS is {:.2f}% and TDS is {:.2f}% (limits: {:.0f}%/{:.0f}%) — {}. "
            "Stressed at the qualifying rate of {:.2f}%, GDS is {} and TDS is {} — {}.".format(
                st.session_state.contract_rate, gds, tds, GDS_LIMIT, TDS_LIMIT,
                "within limits" if qualifies else "exceeds limits",
                qualifying_rate,
                "{:.2f}%".format(stressed_gds) if stressed_gds is not None else "—",
                "{:.2f}%".format(stressed_tds) if stressed_tds is not None else "—",
                "within limits" if stress_qualifies else "exceeds limits",
            )
        )
        if not qualifies:
            exceptions_bits.append(
                "TDS/GDS at contract rate exceeds guidelines ({:.2f}%/{:.2f}% vs {:.0f}%/{:.0f}%) — explain the client's demonstrated ability to service this payment level.".format(gds, tds, GDS_LIMIT, TDS_LIMIT)
            )
        elif not stress_qualifies:
            exceptions_bits.append("TDS/GDS exceeds guidelines when stressed at the qualifying rate — address capacity at the stressed payment.")

    # --- Lender & Refinance Details (both refinance types) ---
    if is_refinance():
        if st.session_state.transaction_type == "refinance_new_lender":
            analysis = compute_switch_in_analysis()
            if analysis:
                path_label = "Straight Switch (no discharge/re-registration)" if analysis["straight_switch"] else \
                    "Discharge & Re-Registration Required"
                lines.append(
                    "**SWITCH-IN**\nClient is switching from " + (st.session_state.switch_ofi_name or "the current lender")
                    + ". Path: " + path_label + ". Qualifying Rate: " + analysis["qualifying_rate"] + ". "
                    + analysis["explanation"]
                )
        else:
            if st.session_state.switch_mortgage_type:
                _, credit_app_required, amort_note = determine_amortization_increase(
                    st.session_state.switch_mortgage_type, None,
                    st.session_state.switch_additional_funds == "Yes",
                )
                lines.append(
                    "**REFINANCE (EXISTING LENDER)**\nClient is refinancing with " + (st.session_state.switch_ofi_name or "the current lender")
                    + ". " + amort_note + " " + ltv_calculation_note()
                )
            if st.session_state.switch_borrowers_changed == "Yes":
                lines.append("**CHANGE OF BORROWER**\n" + change_of_borrower_note())

        due_diligence_bits = []
        additional_lenders = get_switch_additional_lenders()
        if additional_lenders:
            lender_bits = []
            for lender in additional_lenders:
                lender_name = lender["name"] or "unspecified lender"
                balance_str = fmt_money(lender["balance"]) if lender["balance"] is not None else "balance not specified"
                lender_bits.append(
                    lender_name + " (" + balance_str + ", " + (lender["reg_type"] or "registration not specified")
                    + ", " + (lender["mortgage_type"] or "type not specified") + ")"
                )
            due_diligence_bits.append("additional lenders on title: " + "; ".join(lender_bits))
        else:
            due_diligence_bits.append("no additional lenders on the property besides lender 1")
        if st.session_state.switch_mortgages_good_standing:
            due_diligence_bits.append(
                "mortgages/LOCs in good standing: " + st.session_state.switch_mortgages_good_standing
            )
            if st.session_state.switch_mortgages_good_standing == "No":
                exceptions_bits.append("An existing mortgage/LOC is not in good standing — explain the circumstances and current repayment status.")
        if st.session_state.switch_taxes_up_to_date:
            due_diligence_bits.append("property taxes up to date: " + st.session_state.switch_taxes_up_to_date)
            if st.session_state.switch_taxes_up_to_date == "No":
                exceptions_bits.append("Property taxes are not up to date — confirm how the arrears will be addressed.")
        if st.session_state.switch_insurance_provider or st.session_state.switch_insurance_good_standing:
            insurer = st.session_state.switch_insurance_provider or "unspecified insurer"
            insurer_bit = "insurance with " + insurer
            if st.session_state.switch_insurance_good_standing:
                insurer_bit += " (good standing: " + st.session_state.switch_insurance_good_standing + ")"
            due_diligence_bits.append(insurer_bit)
        if due_diligence_bits:
            lines.append("**LENDER DUE DILIGENCE**\n" + "; ".join(due_diligence_bits) + ".")

        breakdown = get_switch_payout_breakdown()
        breakdown_str = "; ".join(item["label"] + ": " + fmt_money(item["amount"]) for item in breakdown)
        lines.append(
            "**REFINANCE PAYOUT**\nRequested loan amount " + fmt_money(get_loan_amount())
            + ". Being paid out — " + (breakdown_str if breakdown_str else "nothing entered yet") + "."
            + " Total mortgages/LOCs paid out " + fmt_money(get_switch_total_mortgage_balance())
            + ", total debts paid out " + fmt_money(get_debts_payout_total())
            + ", net proceeds remaining " + fmt_money(get_switch_net_proceeds()) + "."
        )

    own_funds_bits = []
    for dkey, own_funds in st.session_state.debt_paid_from_own_funds.items():
        if own_funds:
            dt = get_debt_type(dkey)
            own_funds_bits.append(dt["label"] if dt else dkey)
    if own_funds_bits:
        lines.append(
            "**DEBTS PAID FROM OWN/GIFTED FUNDS** (excluded from GDS/TDS)\n" + ", ".join(own_funds_bits) + "."
        )

    if st.session_state.transaction_type == "builder_purchase":
        builder_bits = []
        if st.session_state.builder_name.strip():
            builder_bits.append("builder: " + st.session_state.builder_name.strip())
        if st.session_state.builder_type:
            builder_bits.append(st.session_state.builder_type)
        if st.session_state.builder_code.strip():
            builder_bits.append("code: " + st.session_state.builder_code.strip())
        if st.session_state.builder_mortgage_product:
            builder_bits.append("product: " + st.session_state.builder_mortgage_product)
        if st.session_state.builder_amortization_years.strip():
            builder_bits.append("amortization requested: " + st.session_state.builder_amortization_years.strip() + " years")
            amort_years_val = parse_money(st.session_state.builder_amortization_years)
            if amort_years_val is not None and st.session_state.builder_mortgage_product:
                b_valid, b_needs_approval, b_msg = is_amortization_valid(int(amort_years_val), st.session_state.builder_mortgage_product)
                if not b_valid:
                    exceptions_bits.append("Requested amortization is outside the standard range for this product — " + b_msg)
                elif b_needs_approval:
                    exceptions_bits.append("Requested amortization (31-35 years) requires special builder-code approval — " + b_msg)
        if st.session_state.builder_interest_rate_type:
            builder_bits.append("rate type: " + st.session_state.builder_interest_rate_type)
        if st.session_state.builder_rate_buydown:
            builder_bits.append("rate buydown: " + st.session_state.builder_rate_buydown)
        if st.session_state.builder_gst_hst_included:
            builder_bits.append("GST/HST included in price: " + st.session_state.builder_gst_hst_included)
        if st.session_state.builder_cashback_requested == "Yes":
            cb_program = st.session_state.builder_cashback_program or "program not specified"
            builder_bits.append("cashback requested (" + cb_program + ")")
        if builder_bits:
            lines.append("**BUILDER PROGRAM**\n" + "; ".join(builder_bits) + ".")

    if exceptions_bits:
        lines.append(
            "**EXCEPTIONS REQUIRING BUSINESS CASE RATIONALE**\nThe following need explanation and mitigating factors "
            "in the broker's notes before this file is submission-ready:\n- " + "\n- ".join(exceptions_bits)
        )

    if not lines:
        return "No application data entered yet — complete the earlier steps to generate a summary."
    return "\n\n".join(lines)


def render_notes():
    st.markdown("### Notes for Underwriter")
    render_calculator_popover("notes")
    st.write(
        "A system-compiled summary of the application below, plus space for the broker's own notes. "
        "Combine them into one final note for the file."
    )

    # --- 1. System-Generated Summary ---
    with st.expander("System-Generated Summary (from application data)", expanded=True):
        with st.container(key="notes_font_scope_summary"):
            system_notes = build_system_notes()
            st.markdown(system_notes.replace("\n", "  \n"))

    st.divider()

    # --- 2. Intake Notes ---
    st.markdown("#### Client Intake Notes")
    st.caption("What the client told you in the initial conversation, captured on the Deal step.")
    with st.container(key="card_intake_notes_readonly"):
        if st.session_state.client_intake_notes.strip():
            st.markdown(st.session_state.client_intake_notes.replace("\n", "  \n"))
        else:
            st.caption("No client intake notes were captured on the Deal step.")

    st.divider()

    # --- 3. Discrepancies ---
    disc_header_col, disc_help_col = st.columns([12, 1])
    with disc_header_col:
        st.markdown("#### ⚠️ Discrepancies")
    with disc_help_col:
        with st.container(key="helpbtn_help_discrepancies"):
            with st.popover("?", key="help_discrepancies"):
                st.caption(
                    "Compare the application data above against the Client Intake Notes. List anything that "
                    "doesn't match — these are flagged as a risk for underwriting to review."
                )
                st.divider()
                st.caption(
                    "Auto-flagged below by matching dollar figures and keywords in the intake notes against "
                    "the application data — this is pattern-matching, not AI (no live model is connected), "
                    "so it only catches the phrasing it recognizes. Always review manually."
                )
    auto_flags = detect_intake_discrepancies()
    existing_texts = {e["text"] for e in st.session_state.discrepancy_entries}
    for flag in auto_flags:
        if flag not in existing_texts:
            st.session_state.discrepancy_entries.append({"text": flag, "reason": "", "source": "auto"})

    if not st.session_state.discrepancy_entries and st.session_state.client_intake_notes.strip():
        st.caption("No pattern-based mismatches found.")

    with st.container(key="notes_font_scope_discrepancies"):
        to_remove = None
        for i, entry in enumerate(st.session_state.discrepancy_entries):
            num_col, text_col, del_col = st.columns([0.4, 5, 0.6])
            with num_col:
                st.markdown("**" + str(i + 1) + ".**")
            with text_col:
                st.markdown(entry["text"])
                entry["reason"] = st.text_input(
                    "Explanation", value=entry["reason"], key="disc_reason_" + str(i),
                    label_visibility="collapsed", placeholder="Explain or resolve this discrepancy...",
                )
            with del_col:
                if st.button("✕", key="disc_remove_" + str(i)):
                    to_remove = i
        if to_remove is not None:
            st.session_state.discrepancy_entries.pop(to_remove)
            st.rerun()

        add_col1, add_col2 = st.columns([5, 1])
        with add_col1:
            new_disc_text = st.text_input(
                "Add a discrepancy", key="new_discrepancy_input", label_visibility="collapsed",
                placeholder="Add another discrepancy manually...",
            )
        with add_col2:
            if st.button("+ Add", key="add_discrepancy_btn", use_container_width=True):
                if new_disc_text.strip():
                    st.session_state.discrepancy_entries.append({"text": new_disc_text.strip(), "reason": "", "source": "manual"})
                    st.rerun()

    st.divider()

    # --- 4. Broker Notes ---
    broker_header_col, broker_help_col = st.columns([12, 1])
    with broker_header_col:
        st.markdown("#### Broker Notes")
    with broker_help_col:
        with st.container(key="helpbtn_help_broker_notes"):
            with st.popover("?", key="help_broker_notes"):
                st.caption(
                    "Add any context the system can't infer — client's story, how any discrepancies above "
                    "were addressed, special circumstances, verbal explanations, etc."
                )
    with st.container(key="notes_font_scope_broker"):
        st.session_state.broker_notes = st.text_area(
            "Broker Notes to Underwriter",
            value=st.session_state.broker_notes, height=180, key="broker_notes_input",
        )

    st.divider()

    # --- 5. Combine Notes ---
    st.markdown("#### Combine Notes")
    st.caption(
        "Note: this app isn't connected to a live AI model — \"Combine Notes\" below merges the system "
        "summary, discrepancies, and broker notes into one final summary, using a fixed format, not "
        "generative rewriting."
    )
    if st.button("🧩 Combine Notes", type="primary", use_container_width=True, key="combine_notes_btn"):
        combined = "UNDERWRITER FILE NOTE\n" + "=" * 40 + "\n\n"
        combined += "SYSTEM-GENERATED SUMMARY\n" + "-" * 40 + "\n" + system_notes + "\n\n"
        combined += "DISCREPANCIES (RISK)\n" + "-" * 40 + "\n"
        if st.session_state.discrepancy_entries:
            disc_lines = []
            for i, entry in enumerate(st.session_state.discrepancy_entries):
                line = str(i + 1) + ". " + entry["text"]
                if entry["reason"].strip():
                    line += "\n   Explanation: " + entry["reason"].strip()
                disc_lines.append(line)
            combined += "\n".join(disc_lines) + "\n\n"
        else:
            combined += "(none noted)\n\n"
        combined += "BROKER'S NOTES TO UNDERWRITER\n" + "-" * 40 + "\n"
        combined += st.session_state.broker_notes.strip() if st.session_state.broker_notes.strip() else "(none provided)"
        st.session_state.combined_notes = combined
        st.success("Combined below — feel free to edit before downloading.")

    if st.session_state.combined_notes:
        st.markdown("#### Final Summary")
        with st.container(key="card_notes_preview"):
            st.caption("Formatted preview:")
            st.markdown(st.session_state.combined_notes.replace("=" * 40, "").replace("-" * 40, ""))
        with st.container(key="notes_font_scope_combined"):
            st.session_state.combined_notes = st.text_area(
                "Final note (editable)", value=st.session_state.combined_notes, height=350, key="combined_notes_editor",
                label_visibility="collapsed",
            )
        st.download_button(
            "Download / Save File Note (.txt)",
            data=st.session_state.combined_notes,
            file_name="underwriter_file_note.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.divider()

    back_col, refresh_col = st.columns(2)
    with back_col:
        if st.button("← Back to Documents", use_container_width=True, key="p7_back"):
            st.session_state.step = 7
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p7_refresh"):
            st.session_state["p7_show_refresh_confirm"] = True

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

    st.divider()

    submit_disabled = compute_total_income() <= 0
    if st.button("Submit Application", type="primary", use_container_width=True, key="p7_submit", disabled=submit_disabled):
        st.success("Application submitted. (Connect this button to your backend to persist the data.)")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

st.session_state.visited_steps.add(st.session_state.step)

if st.session_state.get("last_rendered_step") != st.session_state.step:
    st.session_state.last_rendered_step = st.session_state.step
    components.html(
        """
        <script>
          (function() {
            var doc = window.parent.document;
            doc.documentElement.scrollTop = 0;
            doc.body.scrollTop = 0;
            var main = doc.querySelector('section.main');
            if (main) { main.scrollTop = 0; }
            window.parent.scrollTo(0, 0);
          })();
        </script>
        """,
        height=0,
    )

if (
    st.session_state.app_start_time is not None
    and st.session_state.app_completed_seconds is None
    and not st.session_state.app_is_paused
    and is_step_fully_complete(8)
):
    st.session_state.app_completed_seconds = time.time() - st.session_state.app_start_time

with timer_placeholder.container():
    if st.session_state.app_completed_seconds is not None:
        _mins, _secs = divmod(int(st.session_state.app_completed_seconds), 60)
        st.markdown(
            "<div style='text-align:center; margin-top:6px; padding:6px 10px; border-radius:8px; "
            "background-color:#16a34a; border:1px solid #16a34a;'>"
            "<div style='font-size:10px; color:#dcfce7;'>Completed in</div>"
            "<div style='font-size:17px; font-weight:700; font-family:monospace; color:white;'>"
            + "{:02d}:{:02d}".format(_mins, _secs) + "</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    elif st.session_state.app_is_paused:
        _mins, _secs = divmod(int(st.session_state.app_paused_elapsed), 60)
        st.markdown(
            "<div style='text-align:center; margin-top:6px; padding:6px 10px; border-radius:8px; "
            "background-color:rgba(234,179,8,0.12); border:1px solid #eab308;'>"
            "<div style='font-size:10px; color:#fde68a;'>Paused</div>"
            "<div style='font-size:17px; font-weight:700; font-family:monospace; color:#fde68a;'>"
            + "{:02d}:{:02d}".format(_mins, _secs) + "</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Restart Timer", key="restart_timer_btn", use_container_width=True):
            st.session_state.app_start_time = time.time() - st.session_state.app_paused_elapsed
            st.session_state.app_is_paused = False
            st.rerun()
    else:
        _elapsed_now = time.time() - st.session_state.app_start_time
        _mins, _secs = divmod(int(_elapsed_now), 60)
        st.markdown(
            "<div style='text-align:center; margin-top:6px; padding:6px 10px; border-radius:8px; "
            "border:1px solid #ef4444; background-color:rgba(239,68,68,0.12);'>"
            "<div style='font-size:10px; color:#fca5a5;'>Time elapsed</div>"
            "<div style='font-size:17px; font-weight:700; font-family:monospace; color:#fecaca;'>"
            + "{:02d}:{:02d}".format(_mins, _secs) + "</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Stop Timer", key="stop_timer_btn", use_container_width=True):
            st.session_state.app_paused_elapsed = _elapsed_now
            st.session_state.app_is_paused = True
            st.rerun()

with stepper_placeholder.container():
    render_stepper(st.session_state.step)

if st.session_state.step == 0:
    render_transaction_type()
elif st.session_state.step == 1:
    render_client_details()
elif st.session_state.step == 2:
    if is_refinance():
        render_switch_in_step()
    else:
        render_down_payment()
elif st.session_state.step == 3:
    render_property_details()
elif st.session_state.step == 4:
    render_income()
elif st.session_state.step == 5:
    render_debts()
elif st.session_state.step == 6:
    render_analysis()
elif st.session_state.step == 7:
    render_documents()
elif st.session_state.step == 8:
    render_notes()
