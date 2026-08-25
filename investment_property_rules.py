"""
Investment Properties Program rules configuration.

Reflects general, industry-standard Canadian investment/rental-property
mortgage practice (portfolio LTV tiering, maximum property counts, market
rent eligibility, debt-servicing/DCR mechanics, and rental income inclusion
rates). Nothing here references any specific financial institution's
internal policy, exception codes, business-segment/SIC codes, or
proprietary system names.
"""

# ---------------------------------------------------------------------------
# Program scope / eligibility
# ---------------------------------------------------------------------------

ELIGIBLE_TRANSACTION_TYPES = ["Purchase", "Refinance", "Switch", "Built-in Add-on", "Ports", "Assumptions"]
INELIGIBLE_TRANSACTION_TYPES = ["Construction", "Pre-Approval (Subject Investor Only)"]

ELIGIBLE_PRODUCTS = ["Conventional Mortgage", "Homeline Plan"]

CREDIT_SCORE_MIN_GRADE_OPTIONS = ["A", "B"]  # only A/B clients eligible

# ---------------------------------------------------------------------------
# Down payment
# ---------------------------------------------------------------------------

DOWNPAYMENT_INELIGIBLE_SOURCES = ["Rent to Own", "Sweat Equity"]

GIFT_MIN_OWN_RESOURCES_PERCENT = 25.0   # client must contribute at least this % from own resources
GIFT_MAX_PERCENT_OF_DOWNPAYMENT = 75.0  # gift(s) can cover up to this % of total down payment
GIFT_ELIGIBLE_DONOR_RELATION = "Immediate Family Member"

# ---------------------------------------------------------------------------
# Property / portfolio limits
# ---------------------------------------------------------------------------

MAX_TOTAL_PROPERTIES = 9          # financed or free-and-clear, subject + non-subject
MAX_INVESTMENT_PROPERTIES = 5     # of the above, financed or free-and-clear

MAX_AMORTIZATION_YEARS = 30
MAX_LTV_PERCENT = 80.0            # standard max LTV / loan amount cap for the program

# Portfolio LTV limit, keyed by (total_properties_min, total_properties_max) -> list of
# (financing_exposure_max, max_portfolio_ltv_percent) tiers, evaluated in order.
# financing_exposure_max of None means "no upper bound within this properties bracket".
PORTFOLIO_LTV_TABLE = [
    {
        "properties_range": (1, 3),
        "tiers": [
            (1_200_000, None),        # <= $1.2M exposure: no additional portfolio LTV limit
            (2_400_000, 75.0),
            (4_200_000, 65.0),
        ],
    },
    {
        "properties_range": (4, 5),
        "tiers": [
            (2_400_000, 75.0),
            (4_200_000, 65.0),
        ],
    },
    {
        "properties_range": (6, 7),
        "tiers": [
            (4_200_000, 65.0),
        ],
    },
    {
        "properties_range": (8, 9),
        "tiers": [
            (4_200_000, 50.0),
        ],
    },
]

PORTFOLIO_LTV_EXPOSURE_OVER_MAX_PERCENT = 50.0  # exposure > $4.2M => 50% regardless of property count

GUARANTOR_ELIGIBLE = True

# ---------------------------------------------------------------------------
# Debt servicing / DCR
# ---------------------------------------------------------------------------

DCR_TARGET_PERCENT = 110.0  # Debt Coverage Ratio target for non-subject investment properties
VARIABLE_TDS_GDS_ELIGIBLE = True

PROPERTY_EXPENSE_VACANCY_BAD_DEBT_PERCENT = 3.0   # % of gross rental income
PROPERTY_EXPENSE_INSURANCE_PERCENT = 5.0          # % of gross rental income
PROPERTY_EXPENSE_REPAIRS_MAINTENANCE_PERCENT = 5.0  # % of gross rental income

# ---------------------------------------------------------------------------
# Rental income inclusion rates (kept per existing product logic)
# ---------------------------------------------------------------------------
# The percentage of gross/eligible rental income that can be added to
# qualifying income depends on how well documented and how established the
# rental income is. Existing rental income with strong verification (lease +
# tax filing history) supports the highest inclusion rate; newly-rented or
# thinly-documented income is included at a lower rate.

RENTAL_INCOME_INCLUSION_RATES = {
    "established_verified": 100.0,   # existing rental, 1+ year history, full documentation (tax filings/NOA + lease)
    "recent_or_partial": 80.0,       # existing rental under 1 year, or partial/incomplete verification
    "unverified_or_market_rent": 50.0,  # new-to-rental-market / appraised market rent, or weakest documentation tier
}


def get_rental_income_inclusion_rate(verification_level):
    """
    verification_level: one of 'established_verified', 'recent_or_partial',
    'unverified_or_market_rent'.
    Returns the inclusion rate (%) to apply to gross rental income, or None
    if the level isn't recognized.
    """
    return RENTAL_INCOME_INCLUSION_RATES.get(verification_level)


def calculate_includable_rental_income(gross_annual_rent, verification_level):
    """
    Returns (includable_amount, rate_percent, note). Returns (None, None, note)
    if verification_level isn't recognized.
    """
    rate = get_rental_income_inclusion_rate(verification_level)
    if rate is None:
        return None, None, "Unrecognized rental income verification level."
    if gross_annual_rent is None or gross_annual_rent <= 0:
        return 0.0, rate, "No gross rental income entered."
    includable = gross_annual_rent * (rate / 100.0)
    return includable, rate, (
        "{:.0f}% of gross rental income (${:,.2f}) included based on '{}' verification level = ${:,.2f}."
        .format(rate, gross_annual_rent, verification_level, includable)
    )


# ---------------------------------------------------------------------------
# Appraised / market rent
# ---------------------------------------------------------------------------

MAX_APPRAISED_MARKET_RENT_PER_UNIT_MONTHLY = 6000.0
APPRAISED_MARKET_RENT_LOW_END_PERCENT = 100.0  # low end of appraised range usable as eligible income
APPRAISED_MARKET_RENT_PURCHASE_ONLY = True     # not eligible on refinance transactions

APPRAISED_MARKET_RENT_MIN_LIQUID_ASSET_MONTHS = 6  # months of rental income coverage required in higher-risk locations

APPRAISED_MARKET_RENT_RESTRICTED_LOCATIONS = [
    "Wood Buffalo, AB (Fort McMurray)",
    "Fort St. John, BC",
    "Hanover, MB",
    "Gravenhurst, ON",
    "South Huron, ON",
    "Brockville, ON",
    "Estevan, SK",
    "Prince Albert, SK",
    "Swift Current, SK",
]


def is_rural_postal_code(postal_code):
    """Rural properties are those with a postal code ending in '0' (Canadian FSA convention)."""
    if not postal_code:
        return False
    stripped = postal_code.strip().replace(" ", "")
    return len(stripped) > 0 and stripped[-1] == "0"


def is_appraised_market_rent_restricted(postal_code, city_region=None):
    """
    Returns True if appraised market rent is subject to the higher-risk-location
    liquid asset requirement, based on rural postal code or a matching named region.
    """
    if is_rural_postal_code(postal_code):
        return True
    if city_region and city_region.strip() in APPRAISED_MARKET_RENT_RESTRICTED_LOCATIONS:
        return True
    return False


# ---------------------------------------------------------------------------
# Portfolio LTV lookup
# ---------------------------------------------------------------------------

def get_max_portfolio_ltv(total_properties, property_financing_exposure):
    """
    Returns (max_ltv_percent_or_None, note).
    max_ltv_percent of None means no additional portfolio LTV cap applies
    (i.e. only the standard MAX_LTV_PERCENT / product LTV rules apply).
    """
    if total_properties is None or total_properties <= 0:
        return None, "Enter the total number of properties to determine the portfolio LTV limit."

    if property_financing_exposure is not None and property_financing_exposure > 4_200_000:
        return PORTFOLIO_LTV_EXPOSURE_OVER_MAX_PERCENT, (
            "Property financing exposure exceeds $4,200,000 — maximum portfolio LTV is "
            + "{:.0f}%".format(PORTFOLIO_LTV_EXPOSURE_OVER_MAX_PERCENT) + " regardless of property count."
        )

    exposure = property_financing_exposure or 0.0

    for bracket in PORTFOLIO_LTV_TABLE:
        low, high = bracket["properties_range"]
        if low <= total_properties <= high:
            for exposure_max, ltv in bracket["tiers"]:
                if exposure <= exposure_max:
                    if ltv is None:
                        return None, "No additional portfolio LTV limit applies at this exposure level."
                    return ltv, (
                        "{:.0f} propert{} / exposure up to ${:,.0f} — maximum portfolio LTV is {:.0f}%."
                        .format(
                            total_properties, "y" if total_properties == 1 else "ies", exposure_max, ltv
                        )
                    )
            # exposure exceeds all tiers for this bracket but is still <= $4.2M edge case
            last_ltv = bracket["tiers"][-1][1]
            return last_ltv, "Maximum portfolio LTV is {:.0f}%.".format(last_ltv) if last_ltv else (
                None, "No additional portfolio LTV limit applies."
            )

    return None, "Total property count is outside the standard table — refer for manual review."


def is_property_count_within_limits(total_properties, investment_properties):
    """Returns (is_valid, note)."""
    issues = []
    if total_properties is not None and total_properties > MAX_TOTAL_PROPERTIES:
        issues.append("Total properties ({}) exceeds the maximum of {}.".format(total_properties, MAX_TOTAL_PROPERTIES))
    if investment_properties is not None and investment_properties > MAX_INVESTMENT_PROPERTIES:
        issues.append("Investment properties ({}) exceeds the maximum of {}.".format(investment_properties, MAX_INVESTMENT_PROPERTIES))
    if issues:
        return False, " ".join(issues)
    return True, "Within standard property count limits."