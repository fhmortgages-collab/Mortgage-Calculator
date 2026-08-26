# =============================================================================
# Portfolio limits and variable TDS thresholds (from FPHE1 and personal credit)
# =============================================================================

MAX_PROPERTIES_OWNED = 9
MAX_INVESTMENT_PROPERTIES = 5

VARIABLE_TDS_MAX = 52.0
VARIABLE_GDS_MAX = 39.0
"""
Internal Refinance (Refinance - Existing Lender) rules configuration.

Reflects general, industry-standard Canadian internal-refinance practice
(same lender staying on title): equity/down payment requirements, LTV
calculation basis, and amortization-increase rules by product. Nothing here
references any specific financial institution's internal policy, exception
codes, or proprietary system names.
"""

MIN_EQUITY_CONVENTIONAL = 20.0  # % of the lower of purchase price / as-improved value / current valuation
MIN_EQUITY_EXCEPTION_OWN_FUNDS = 10.0  # % from client's own accumulated resources, valued-connection exception

CONVENTIONAL_MAX_AMORTIZATION_INCREASE = 30
DEFAULT_INSURED_MAX_AMORTIZATION_INCREASE = 25  # port transactions with new funds only


def equity_requirement_note():
    return (
        "Standard conventional refinance requires a minimum of " + str(int(MIN_EQUITY_CONVENTIONAL))
        + "% equity in the lower of the purchase price/as-improved value or the current property valuation. "
        "Below that, the mortgage must be submitted under a default insured program with applicable premiums — "
        "or, for a valued client relationship, a minimum " + str(int(MIN_EQUITY_EXCEPTION_OWN_FUNDS))
        + "% from the client's own accumulated resources may be considered, subject to standard TDS/GDS."
    )


def ltv_calculation_note():
    return "Refinance LTV is calculated using the current appraised value of the property, not the original purchase price."


def determine_amortization_increase(product, ltv_percent, requesting_new_funds):
    """
    Returns (max_years, credit_app_required, note) for increasing amortization
    beyond the original scheduled remaining amortization, by product.
    """
    if product == "Conventional Mortgage":
        return (
            CONVENTIONAL_MAX_AMORTIZATION_INCREASE, True,
            "Conventional mortgages can be increased up to the lesser of "
            + str(CONVENTIONAL_MAX_AMORTIZATION_INCREASE) + " years or the maximum for the specific mortgage "
            "program — a completed and approved refinance application is required.",
        )
    if product == "Homeline Plan":
        return (
            None, False,
            "A Homeline Plan's amortization can be extended beyond the original scheduled remaining amortization "
            "up to the maximum permitted, with no credit application required — unless the request is to increase "
            "the Homeline Plan's authorized or registered limit, or the plan has a default insured segment "
            "(whose original scheduled remaining amortization cannot be exceeded).",
        )
    if product == "Default Insured Mortgage":
        return (
            DEFAULT_INSURED_MAX_AMORTIZATION_INCREASE, True,
            "Default insured mortgages can be increased up to a maximum of "
            + str(DEFAULT_INSURED_MAX_AMORTIZATION_INCREASE) + " years for port transactions with new funds "
            "only, regardless of LTV — a completed and approved application is required, and applicable mortgage "
            "insurer premiums are payable" + (
                " (based on the lesser of the premium on the additional funds or the total new loan amount)"
                if ltv_percent is not None and ltv_percent > 80 else ""
            ) + ".",
        )
    return (None, True, "Select a mortgage product to see the applicable amortization-increase rules.")


def change_of_borrower_note():
    return (
        "Adding or removing a borrower or guarantor requires a new refinance application in the name of all "
        "borrowers/guarantors who will be on the new mortgage, and the title must be changed accordingly. "
        "With no new funds, this can be completed without a new property valuation or the standard processing "
        "fee; with new funds, standard property valuation guidelines apply. For a default insured mortgage, the "
        "original scheduled remaining amortization must be retained and a resubmission to the insurer is not "
        "required, except when the borrower being added qualifies under a stated-income or newcomer-to-Canada "
        "program with certain insurers."
    )


def high_risk_review_note():
    return (
        "High-risk refinance transactions (e.g. multiple debts being paid out from the mortgage advance through "
        "a title insurer) require additional due diligence and a centralized payout process — unsecured debts and "
        "debts secured by the residential property are paid out by Operations, while other-financial-institution "
        "debt secured by the property is paid through the title insurer."
    )
# =============================================================================
# Additional policy rules – from FPHE1 and personal credit policy
# =============================================================================

# --- Portfolio & Lending Minimums (FPHE1, p. 30, p. 34) ---
MAX_PROPERTIES_OWNED = 9
MAX_INVESTMENT_PROPERTIES = 5
MIN_MORTGAGE_AMOUNT = 25_000           # $25,000 for a residential mortgage or Homeline Plan
MIN_RCL_SEGMENT = 5_000                # each RCL segment within a Homeline Plan

# --- Self-Employed Income Gross-up (Personal Credit policy) ---
SELF_EMPLOYED_GROSS_UP = 1.15          # net income can be grossed up by 15%

# --- Variable TDS/GDS Program Eligibility (FPHE1, pp. 51-52) ---
# Programs that are eligible for variable TDS (up to 52% TDS / 39% GDS)
VARIABLE_TDS_ELIGIBLE_PROGRAMS = [
    "Newcomer Standard",
    "Second Homes",
    "Mortgage Assistance Program",
    "Rural Estates",
    "Investment Properties",
    "New Home Construction - Builder Program",
    "Construction Mortgages",
    "First Nations Ministerial Loan Program",
    "First Nations on Reserve Housing Loan Program",
]

# Programs that are specifically ineligible for variable TDS
VARIABLE_TDS_INELIGIBLE_PROGRAMS = [
    "US Foreign Income",
    "Foreign Income (all other eligible countries)",
    "Newcomer Default Insured",
    "Newcomer High Net Worth",
    "Self Employed Stated Income (Conventional and Default Insured)",
    "Wealth Accumulator Conforming and Non-Conforming",
    "Temporary Resident on Work Permit (Conventional and Default Insured)",
    "Seasonal Cottages",
    "Factory Constructed Homes",
    "Residential and Collateral Mortgages on Leasehold Land",
    "Leasehold Lending on First Nations Lands",
    "Risk Based Pricing",
]

def is_variable_tds_allowed(program_label):
    """
    Returns True if the given program is eligible for variable TDS/GDS.
    If the program is not in either list, returns False as a safe default.
    """
    if program_label in VARIABLE_TDS_ELIGIBLE_PROGRAMS:
        return True
    if program_label in VARIABLE_TDS_INELIGIBLE_PROGRAMS:
        return False
    return False  # safe default

# --- Guarantor Rules (FPHE1, pp. 13-14) ---
# Non-spousal guarantors must be immediate family and qualify on their own.
# This is a validation helper; use it in business logic if needed.
def is_guarantor_eligible(guarantor_type, is_immediate_family=True):
    """
    guarantor_type: 'spousal' or 'non_spousal'
    Returns True if eligible.
    """
    if guarantor_type == "spousal":
        return True
    if guarantor_type == "non_spousal":
        return is_immediate_family
    return False
# =============================================================================
# Additional policy rules – from FPHE1 and personal credit policy
# =============================================================================

MAX_PROPERTIES_OWNED = 9
MAX_INVESTMENT_PROPERTIES = 5
MIN_MORTGAGE_AMOUNT = 25_000
MIN_RCL_SEGMENT = 5_000
SELF_EMPLOYED_GROSS_UP = 1.15

VARIABLE_TDS_ELIGIBLE_PROGRAMS = [
    "Newcomer Standard",
    "Second Homes",
    "Mortgage Assistance Program",
    "Rural Estates",
    "Investment Properties",
    "New Home Construction - Builder Program",
    "Construction Mortgages",
    "First Nations Ministerial Loan Program",
    "First Nations on Reserve Housing Loan Program",
]

VARIABLE_TDS_INELIGIBLE_PROGRAMS = [
    "US Foreign Income",
    "Foreign Income (all other eligible countries)",
    "Newcomer Default Insured",
    "Newcomer High Net Worth",
    "Self Employed Stated Income (Conventional and Default Insured)",
    "Wealth Accumulator Conforming and Non-Conforming",
    "Temporary Resident on Work Permit (Conventional and Default Insured)",
    "Seasonal Cottages",
    "Factory Constructed Homes",
    "Residential and Collateral Mortgages on Leasehold Land",
    "Leasehold Lending on First Nations Lands",
    "Risk Based Pricing",
]

def is_variable_tds_allowed(program_label):
    if program_label in VARIABLE_TDS_ELIGIBLE_PROGRAMS:
        return True
    if program_label in VARIABLE_TDS_INELIGIBLE_PROGRAMS:
        return False
    return False

def is_guarantor_eligible(guarantor_type, is_immediate_family=True):
    if guarantor_type == "spousal":
        return True
    if guarantor_type == "non_spousal":
        return is_immediate_family
    return False