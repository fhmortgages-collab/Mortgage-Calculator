"""
Builder Purchase (New Home Construction) rules configuration.

Reflects general, industry-standard Canadian new-construction / builder-purchase
mortgage practice (amortization limits for uninsured vs. default insured builder
programs, eligible/ineligible products and interest rate types, GST/HST rebate
handling, and cashback eligibility). Nothing here references any specific
financial institution's internal policy, pricing grid, proprietary form numbers,
or internal codes.
"""

MORTGAGE_PRODUCT_OPTIONS = ["", "Conventional Mortgage", "Homeline Plan (Single Advance)", "Default Insured Mortgage"]
BUILDER_TYPE_OPTIONS = ["", "Preferred Builder", "Non-Preferred / Generic Builder"]
INTEREST_RATE_TYPE_OPTIONS = ["", "Fixed Rate Closed (up to 5-year term)", "Variable Rate Closed"]
INELIGIBLE_INTEREST_RATE_TYPES = ["Fixed Rate Closed (over 5-year term)", "Fixed Rate Open", "Variable Rate Open"]

# Amortization limits
UNINSURED_MIN_AMORTIZATION = 5
UNINSURED_MAX_AMORTIZATION = 35
UNINSURED_STANDARD_MAX_AMORTIZATION = 30  # eligible for buyers purchasing a newly built home
UNINSURED_EXTENDED_AMORTIZATION_MIN = 31  # 31-35 requires special builder-code approval
UNINSURED_EXTENDED_TDS_LIMIT = 44.0
UNINSURED_EXTENDED_GDS_LIMIT = 39.0

DEFAULT_INSURED_MIN_AMORTIZATION = 5
DEFAULT_INSURED_MAX_AMORTIZATION = 25

# GST/HST
GST_HST_ESTIMATED_RATE = 0.05  # used only when the exact percentage isn't documented

# Cashback eligibility
CASHBACK_ELIGIBLE_PROGRAMS = [
    "Investor Properties",
    "Seasonal Cottage Properties",
    "Residential Mortgages on Leasehold Land",
    "Leasehold Lending on First Nations Land",
    "Factory Constructed Homes (Permanently Affixed)",
]
CASHBACK_INELIGIBLE_PROGRAMS = [
    "Self Employed Stated Income",
    "Wealth Accumulator Equity",
    "Newcomer (Equity, High Net Worth and Standard)",
    "Foreign Income (US and All Other Countries)",
]
CASHBACK_PROGRAM_OPTIONS = [""] + CASHBACK_ELIGIBLE_PROGRAMS + CASHBACK_INELIGIBLE_PROGRAMS + ["Not Applicable / Standard"]

ELIGIBLE_BUILDER_TRANSACTION_TYPES = ["Purchase (new only)", "Construction", "Assumption (from mortgage in the name of the builder)"]
INELIGIBLE_BUILDER_TRANSACTION_TYPES = ["Switch", "Refinance", "Built-in add-on", "Assumption (from mortgage in the name of the client)"]

ELIGIBLE_BUILDER_PRODUCTS = ["Conventional Mortgage", "Homeline Plan (single advance, in the name of the borrower only)", "Default Insured Mortgage"]
INELIGIBLE_BUILDER_PRODUCTS = ["Homeline Plan (progress advances, in the name of the borrower)", "Secured Line of Credit"]


def is_amortization_valid(amortization_years, product):
    """
    Returns (is_valid, requires_special_approval, message).

    Default insured: 5-25 years.
    Uninsured (Conventional / Homeline single advance): 5-35 years, but 31-35
    requires a specific builder-code approval and caps TDS/GDS at 44%/39%.
    """
    if product == "Default Insured Mortgage":
        if DEFAULT_INSURED_MIN_AMORTIZATION <= amortization_years <= DEFAULT_INSURED_MAX_AMORTIZATION:
            return True, False, "Within the standard 5-25 year default insured amortization range."
        return False, False, (
            "Default insured amortization must be between " + str(DEFAULT_INSURED_MIN_AMORTIZATION)
            + " and " + str(DEFAULT_INSURED_MAX_AMORTIZATION) + " years."
        )

    if amortization_years < UNINSURED_MIN_AMORTIZATION or amortization_years > UNINSURED_MAX_AMORTIZATION:
        return False, False, (
            "Amortization must be between " + str(UNINSURED_MIN_AMORTIZATION) + " and "
            + str(UNINSURED_MAX_AMORTIZATION) + " years for this product."
        )

    if amortization_years >= UNINSURED_EXTENDED_AMORTIZATION_MIN:
        return True, True, (
            "Amortization of " + str(amortization_years) + " years (31-35) is only available for buyers "
            "purchasing a newly built home, under specific approved builder codes. TDS/GDS must be "
            "restricted to a maximum of " + str(UNINSURED_EXTENDED_TDS_LIMIT) + "%/"
            + str(UNINSURED_EXTENDED_GDS_LIMIT) + "%, and standard income verification applies."
        )

    return True, False, "Within the standard uninsured amortization range."


def calculate_gst_hst_adjusted_price(purchase_price, gst_hst_included, gst_hst_percent=None):
    """
    If the agreement's purchase price already includes GST/HST, use it as-is.
    If not, and an exact percentage is documented, add that percentage.
    If not, and no percentage is documented, estimate using the standard rate
    (a real transaction should always get written confirmation of the exact
    percentage from the builder, their lawyer, or notary).

    Returns (adjusted_price, note).
    """
    if gst_hst_included:
        return purchase_price, "Purchase price already includes applicable GST/HST, per the agreement."

    if gst_hst_percent is not None:
        adjusted = purchase_price * (1 + gst_hst_percent)
        return adjusted, (
            "GST/HST of {:.2f}%".format(gst_hst_percent * 100) + " added to the purchase price per "
            "documentation from the builder, their lawyer, or notary."
        )

    adjusted = purchase_price * (1 + GST_HST_ESTIMATED_RATE)
    return adjusted, (
        "No exact GST/HST percentage documented — estimated at " + "{:.0f}%".format(GST_HST_ESTIMATED_RATE * 100)
        + " and added to the purchase price. Obtain written confirmation of the exact percentage from the "
        "builder, their lawyer, or notary before submitting."
    )


def is_interest_rate_type_eligible(rate_type_description):
    return rate_type_description not in INELIGIBLE_INTEREST_RATE_TYPES


def is_cashback_eligible(program):
    return program in CASHBACK_ELIGIBLE_PROGRAMS


def builder_document_requirements():
    """Standard documents typically required for a builder-purchase file."""
    return {
        "documents": [
            "Agreement of Purchase and Sale with the builder, including all amendments and addendums",
            "Client commitment/approval letter, signed by the purchaser(s)",
            "Proof of new home warranty enrollment (e.g. a warranty registration or Home ID number)",
            "Completion Certificate (or Certificate of Possession) once available",
        ],
        "conditional": {
            "gst_hst_not_included": "Written confirmation from the builder, their lawyer, or notary of the exact GST/HST percentage applicable",
            "interest_rate_buydown": "Signed builder interest rate buydown agreement/letter of direction",
            "warranty_pending": "Builder's warranty registration confirmation once the home has been enrolled",
        },
    }
# ---------------------------------------------------------------------------
# New Home Construction - Builder Program (FPHE24) — policy reference data
# Added Nov 2025. Source: RBC Policy & Procedure Library, FPHE24-1-EN.
# ---------------------------------------------------------------------------

BUILDER_ELIGIBLE_TRANSACTION_TYPES = [
    "Purchase (new only)", "Construction", "Assumption (from mortgages in the name of the builder)",
]
BUILDER_INELIGIBLE_TRANSACTION_TYPES = [
    "Switch", "Refinance", "Built-in add-on", "Assumption (from mortgages in the name of the client)",
]

BUILDER_ELIGIBLE_PRODUCTS = [
    "Conventional Mortgage", "RBC Homeline Plan (single advance in the name of borrower only)",
    "Default Insured Mortgage", "RBC Homeline Plan (progress advances in the name of borrower)",
]
BUILDER_INELIGIBLE_PRODUCTS = ["Secured Royal Credit Line"]

BUILDER_ELIGIBLE_PROGRAMS = [
    "Temporary Residents on Work Permit (single advance builder mortgages only)",
    "Investor Properties", "Seasonal Cottage Properties", "Residential Mortgages on Leasehold Land",
    "Leasehold Lending on First Nations Land", "Factory Constructed Homes (Permanently Affixed)",
    "Self Employed Stated Income", "Wealth Accumulator Equity",
    "Newcomer (Equity, High Net Worth and Standard)", "Foreign Income (US and All Other Countries)",
]
BUILDER_INELIGIBLE_PROGRAMS = [
    "Temporary Residents on Work Permit (construction draw mortgages)", "Rural Estates",
    "Collateral Mortgages on Leasehold Land", "First Nation On Reserve Housing Loan Program",
    "First Nations Ministerial Loan Guarantee (MLG)", "Factory Constructed Homes (not permanently affixed)",
]

BUILDER_CASHBACK_CAN_COMBINE = [
    "Investor Properties", "Seasonal Cottage Properties", "Residential Mortgages on Leasehold Land",
    "Leasehold Lending on First Nations Land", "Factory Constructed Homes (Permanently Affixed)",
]
BUILDER_CASHBACK_CANNOT_COMBINE = [
    "Self Employed Stated Income", "Wealth Accumulator Equity",
    "Newcomer (Equity, High Net Worth and Standard)", "Foreign Income (US and All Other Countries)",
]

# Eligible/ineligible interest rate types differ depending on whether the
# mortgage is in the name of the purchaser(s) or in the name of the builder.
BUILDER_RATE_TYPES_BORROWER_NAME = {
    "eligible": ["Fixed rate closed (up to a maximum of 5-year term)", "Variable rate closed"],
    "ineligible": ["Fixed rate closed (over 5-year term)", "Fixed rate open", "Variable rate open"],
}
BUILDER_RATE_TYPES_BUILDER_NAME = {
    "eligible": ["Variable rate closed or open (not available through CMHC)", "6 month open term"],
    "ineligible": ["Fixed rate closed", "Fixed rate open"],
}

# Amortization by program (Green Home Mortgage Program table)
GREEN_HOME_AMORTIZATION = {
    "uninsured": {"min": 5, "max": 35, "note": "31-35 years only for specific approved builder codes; TDS/GDS capped at 44%/39%."},
    "default_insured": {"min": 5, "max": 25, "note": "30 years eligible for buyers purchasing a newly built home."},
}
STANDARD_BUILDER_AMORTIZATION_MAX_DEFAULT_INSURED = 30  # newly built home, effective Dec 15 2024
STANDARD_BUILDER_AMORTIZATION_MAX_UNINSURED_GREEN = 35  # Green Home Mortgage Program only

# Standard builder commitment periods
BUILDER_COMMITMENT_PERIODS_FIXED = [6, 12]  # months; >12 not permitted, even on exception
BUILDER_COMMITMENT_PERIODS_VARIABLE = [6, 12, 24, 36]  # months; >36 needs special approval


def is_transaction_type_builder_eligible(transaction_type_label):
    """Returns (eligible: bool, note: str) for a given transaction type label."""
    if transaction_type_label in BUILDER_ELIGIBLE_TRANSACTION_TYPES:
        return True, ""
    if transaction_type_label in BUILDER_INELIGIBLE_TRANSACTION_TYPES:
        return False, transaction_type_label + " is not eligible under the New Home Construction - Builder Program."
    return None, "Not a recognized builder-program transaction type."


def is_program_cashback_eligible(program_label):
    """Returns True/False/None (None = program not found in either list)."""
    if program_label in BUILDER_CASHBACK_CAN_COMBINE:
        return True
    if program_label in BUILDER_CASHBACK_CANNOT_COMBINE:
        return False
    return None


def get_eligible_rate_types(mortgage_in_name_of):
    """mortgage_in_name_of: 'borrower' or 'builder'. Returns dict with eligible/ineligible lists."""
    if mortgage_in_name_of == "builder":
        return BUILDER_RATE_TYPES_BUILDER_NAME
    return BUILDER_RATE_TYPES_BORROWER_NAME


def gst_hst_adjusted_price_from_offer(purchase_price, gst_hst_included, exact_percentage=None):
    """
    Wraps existing calculate_gst_hst_adjusted_price() logic per the APS review checklist:
    if the offer indicates GST/HST is NOT included and gives an exact percentage, add it;
    otherwise flag that documentation from the builder/lawyer/notary is required to confirm
    the percentage before it can be added.
    """
    if gst_hst_included:
        return purchase_price, "Purchase price already includes GST/HST — use as entered."
    if exact_percentage is not None:
        adjusted = purchase_price * (1 + exact_percentage)
        return adjusted, "Added {:.2f}% GST/HST per the offer to purchase.".format(exact_percentage * 100)
    return purchase_price, (
        "Offer does not indicate the exact GST/HST percentage — obtain documentation from the "
        "builder, lawyer, or notary confirming the percentage before adding it to the purchase price."
    )