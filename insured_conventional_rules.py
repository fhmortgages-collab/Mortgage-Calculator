"""
Insured vs. Conventional Mortgage rules (Ontario / Canadian purchase-price LTV framework).

Covers:
- Minimum down payment by purchase price tier
- Maximum LTV by purchase price tier
- Mortgage insurance premium tiers (by base-mortgage LTV)
- Lending value (lower of purchase price / appraised value)
- Helper text for the "Insured vs Conventional" question mark tooltip

This module is purely computational/reference data — it does not touch or
change GDS/TDS qualification math, which stays entirely inside app.py's
compute_gds_tds().
"""

MORTGAGE_STRUCTURE_OPTIONS = ["", "Conventional", "Insured (High-Ratio)"]

CONVENTIONAL_MIN_DOWN_PERCENT = 0.20
CONVENTIONAL_MAX_LTV_PERCENT = 80.0

INSURED_TIER_1_MAX_PRICE = 500_000
INSURED_TIER_2_MAX_PRICE = 1_500_000  # insured eligibility ends at/above this price
INSURED_TIER_1_PERCENT = 0.05
INSURED_TIER_2_PERCENT = 0.10

# Mortgage insurance premium tiers, keyed by (min_ltv_exclusive, max_ltv_inclusive): premium_percent
# LTV here refers to the BASE MORTGAGE's LTV against lending value, not the purchase-price tier.
INSURANCE_PREMIUM_TIERS = [
    (0.0, 65.0, 0.60),
    (65.0, 75.0, 1.70),
    (75.0, 80.0, 2.40),
    (80.0, 85.0, 2.80),
    (85.0, 90.0, 3.10),
    (90.0, 95.0, 4.00),
]


def help_mortgage_structure_text():
    """Explanation text for the Insured vs Conventional question-mark tooltip on the Deal step."""
    return (
        "**Conventional Mortgage**\n"
        "The mortgage is at or below 80% of the property's lending value (the lower of purchase "
        "price or appraised value) — meaning at least 20% down. No mortgage default insurance is "
        "required, but the buyer must contribute more cash upfront.\n\n"
        "**Insured (High-Ratio) Mortgage**\n"
        "The mortgage exceeds 80% of the lending value — as low as 5% down on eligible purchases. "
        "The lender requires mortgage default insurance (protecting the lender, not the borrower), "
        "which comes with an insurance premium added to or paid on top of the mortgage. Insured "
        "mortgages are only available on purchase prices under $1,500,000, and the minimum down "
        "payment increases as the purchase price rises.\n\n"
        "**Which applies:** based on the purchase price and the down payment entered, this "
        "application will show whether the deal qualifies as insured or must be conventional, and "
        "flag if more cash is required to meet the minimum."
    )


def get_lending_value(purchase_price, appraised_value):
    """
    Lending Value = lower of Purchase Price or Appraised Value.
    Returns purchase_price if no appraisal has been entered yet.
    """
    if appraised_value is None or appraised_value <= 0:
        return purchase_price
    return min(purchase_price, appraised_value)


def get_min_down_payment(purchase_price):
    """
    Minimum down payment required by Canadian purchase-price rules, based on
    purchase price alone (not lending value / appraisal).
    Returns (min_down_payment, max_ltv_percent, is_insured_eligible).
    """
    if purchase_price <= 0:
        return 0.0, None, False

    if purchase_price <= INSURED_TIER_1_MAX_PRICE:
        min_down = purchase_price * INSURED_TIER_1_PERCENT
        max_ltv = 95.0
        return min_down, max_ltv, True

    if purchase_price < INSURED_TIER_2_MAX_PRICE:
        min_down = (
            INSURED_TIER_1_MAX_PRICE * INSURED_TIER_1_PERCENT
            + (purchase_price - INSURED_TIER_1_MAX_PRICE) * INSURED_TIER_2_PERCENT
        )
        max_base_mortgage = purchase_price - min_down
        max_ltv = (max_base_mortgage / purchase_price) * 100
        return min_down, max_ltv, True

    # $1,500,000 or more — conventional only
    min_down = purchase_price * CONVENTIONAL_MIN_DOWN_PERCENT
    return min_down, CONVENTIONAL_MAX_LTV_PERCENT, False


def get_max_base_mortgage(purchase_price, appraised_value, mortgage_structure):
    """
    Returns (max_base_mortgage, max_ltv_percent, cash_required, notes).
    mortgage_structure: "Conventional" or "Insured (High-Ratio)".
    LTV is applied against lending value (lower of price/appraisal); cash required
    is calculated against the full purchase price, since a low appraisal doesn't
    reduce what's owed to the seller.
    """
    lending_value = get_lending_value(purchase_price, appraised_value)
    notes = []

    if mortgage_structure == "Conventional":
        max_base_mortgage = lending_value * (CONVENTIONAL_MAX_LTV_PERCENT / 100.0)
        max_ltv = CONVENTIONAL_MAX_LTV_PERCENT
    else:
        min_down, max_ltv_for_price, is_insured_eligible = get_min_down_payment(purchase_price)
        if not is_insured_eligible:
            notes.append(
                "This purchase price is $1,500,000 or more, which is not eligible for an insured "
                "mortgage — a conventional mortgage (minimum 20% down) is required."
            )
            max_base_mortgage = lending_value * (CONVENTIONAL_MAX_LTV_PERCENT / 100.0)
            max_ltv = CONVENTIONAL_MAX_LTV_PERCENT
        else:
            max_ltv = max_ltv_for_price
            max_base_mortgage = lending_value * (max_ltv / 100.0)

    cash_required = purchase_price - max_base_mortgage

    if appraised_value is not None and appraised_value > 0 and appraised_value < purchase_price:
        notes.append(
            "Appraised value (" + _fmt(appraised_value) + ") is below the purchase price ("
            + _fmt(purchase_price) + ") — the lender uses the lower lending value for LTV, which "
            "increases the cash required toward closing since the seller is still owed the full "
            "purchase price."
        )

    return max_base_mortgage, max_ltv, cash_required, notes


def get_insurance_premium_percent(base_mortgage_ltv_percent):
    """Returns the applicable insurance premium percent for a given base-mortgage LTV, or None if out of range."""
    for min_ltv, max_ltv, premium in INSURANCE_PREMIUM_TIERS:
        if min_ltv < base_mortgage_ltv_percent <= max_ltv:
            return premium
    if base_mortgage_ltv_percent <= 0:
        return INSURANCE_PREMIUM_TIERS[0][2]
    return None  # LTV above 95% is not eligible for standard insured premium tiers


def calculate_insurance_premium(base_mortgage, base_mortgage_ltv_percent):
    """
    Returns (premium_amount, premium_percent, financed_balance) for an insured mortgage.
    financed_balance = base_mortgage + premium_amount, if the premium is added to the mortgage
    (the more common option) rather than paid in cash.
    """
    premium_percent = get_insurance_premium_percent(base_mortgage_ltv_percent)
    if premium_percent is None:
        return None, None, None
    premium_amount = base_mortgage * (premium_percent / 100.0)
    financed_balance = base_mortgage + premium_amount
    return premium_amount, premium_percent, financed_balance


def _fmt(value):
    try:
        return "${:,.2f}".format(value)
    except (TypeError, ValueError):
        return "—"


def explain_insured_vs_conventional(purchase_price, appraised_value, down_payment, mortgage_structure):
    """
    Given the deal's numbers, returns a human-readable explanation string (for a st.caption)
    of how the mortgage structure was evaluated — mirroring the math a broker would walk
    through manually. Does not raise; returns a plain-language message if inputs are incomplete.
    """
    if not purchase_price or purchase_price <= 0:
        return "Enter a purchase price to see LTV and minimum down payment guidance."

    lending_value = get_lending_value(purchase_price, appraised_value)
    min_down, max_ltv_for_price, is_insured_eligible = get_min_down_payment(purchase_price)

    lines = []
    lines.append(
        "Lending Value = lower of Purchase Price (" + _fmt(purchase_price) + ") or Appraised Value ("
        + (_fmt(appraised_value) if appraised_value else "not yet entered") + ") = " + _fmt(lending_value) + "."
    )

    if not is_insured_eligible:
        lines.append(
            "Purchase price is $1,500,000 or more — only a conventional mortgage (min. 20% down, "
            "max. 80% LTV) is available."
        )
    else:
        lines.append(
            "Minimum down payment for this purchase price: " + _fmt(min_down)
            + " (max. base LTV ~{:.2f}%).".format(max_ltv_for_price)
        )

    if down_payment is not None and down_payment > 0:
        shortfall = min_down - down_payment
        if shortfall > 0.01:
            lines.append(
                "Entered down payment (" + _fmt(down_payment) + ") is " + _fmt(shortfall)
                + " below the minimum required — additional cash is needed to proceed."
            )
        else:
            lines.append("Entered down payment (" + _fmt(down_payment) + ") meets the minimum requirement.")

    return " ".join(lines)
# =============================================================================
# Geographic LTV Tiers (from FPHE1, pages 32-34)
# =============================================================================

GEOGRAPHIC_LTV_TIERS = {
    # British Columbia
    "Abbotsford": {"single_family": 2_000_000, "condo": 750_000},
    "Central Saanich": {"single_family": 1_800_000, "condo": 750_000},
    "Chilliwack": {"single_family": 1_500_000, "condo": 750_000},
    "Coldstream": {"single_family": 1_500_000, "condo": 750_000},
    "Delta (Ladner/Tsawwassen)": {"single_family": 2_000_000, "condo": 1_250_000},
    "Greater Vancouver Area": {"single_family": 3_000_000, "condo": 1_500_000},
    "Kelowna": {"single_family": 1_800_000, "condo": 1_000_000},
    "Lake Country": {"single_family": 1_800_000, "condo": 750_000},
    "Langley": {"single_family": 2_500_000, "condo": 1_000_000},
    "Maple Ridge": {"single_family": 1_800_000, "condo": 750_000},
    "Mission": {"single_family": 1_800_000, "condo": 750_000},
    "Pitt Meadows": {"single_family": 1_800_000, "condo": 750_000},
    "Sidney": {"single_family": 1_800_000, "condo": 750_000},
    "Squamish": {"single_family": 2_000_000, "condo": 750_000},
    "Sunshine Coast": {"single_family": 1_500_000, "condo": 750_000},
    "Victoria (incl. Esquimalt)": {"single_family": 1_800_000, "condo": 1_250_000},
    "Whistler": {"single_family": 1_800_000, "condo": 1_000_000},
    "Vernon": {"single_family": 1_500_000, "condo": 750_000},
    "Rest of British Columbia": {"single_family": 1_400_000, "condo": 750_000},
    # Alberta
    "Calgary": {"single_family": 1_250_000, "condo": 750_000},
    "Edmonton": {"single_family": 1_000_000, "condo": 500_000},
    "Canmore": {"single_family": 1_500_000, "condo": 750_000},
    "Fort McMurray": {"single_family": 750_000, "condo": 500_000},
    "Airdrie": {"single_family": 900_000, "condo": 500_000},
    "Cochrane": {"single_family": 1_000_000, "condo": 500_000},
    "Okotoks": {"single_family": 1_250_000, "condo": 500_000},
    "Rest of Alberta": {"single_family": 900_000, "condo": 500_000},
    # Saskatchewan
    "Regina": {"single_family": 750_000, "condo": 500_000},
    "Saskatoon": {"single_family": 750_000, "condo": 500_000},
    "Rest of Saskatchewan": {"single_family": 600_000, "condo": 500_000},
    # Manitoba
    "Winnipeg": {"single_family": 750_000, "condo": 500_000},
    "Rest of Manitoba": {"single_family": 600_000, "condo": 500_000},
    # Ontario (full list)
    "Ajax": {"single_family": 1_500_000, "condo": 750_000},
    "Aurora": {"single_family": 2_400_000, "condo": 750_000},
    "Bradford West Gwillimbury": {"single_family": 1_500_000, "condo": 750_000},
    "Brampton": {"single_family": 1_800_000, "condo": 800_000},
    "Burlington": {"single_family": 2_000_000, "condo": 1_000_000},
    "Caledon": {"single_family": 2_000_000, "condo": 750_000},
    "East Gwillimbury": {"single_family": 1_800_000, "condo": 750_000},
    "Greater Toronto Area": {"single_family": 2_700_000, "condo": 1_250_000},
    "Halton Hills": {"single_family": 1_800_000, "condo": 750_000},
    "Hamilton": {"single_family": 1_500_000, "condo": 750_000},
    "King Township": {"single_family": 2_500_000, "condo": 750_000},
    "Kitchener/Waterloo": {"single_family": 1_400_000, "condo": 750_000},
    "Kleinburg": {"single_family": 2_500_000, "condo": 750_000},
    "Milton": {"single_family": 1_500_000, "condo": 800_000},
    "Newmarket": {"single_family": 1_800_000, "condo": 750_000},
    "Ottawa": {"single_family": 1_250_000, "condo": 750_000},
    "Pickering": {"single_family": 1_800_000, "condo": 750_000},
    "Springwater": {"single_family": 1_500_000, "condo": 750_000},
    "Whitby": {"single_family": 1_500_000, "condo": 750_000},
    "Rest of Ontario": {"single_family": 1_250_000, "condo": 750_000},
    # Quebec
    "Montreal (incl. West Island)": {"single_family": 1_700_000, "condo": 1_000_000},
    "Quebec City": {"single_family": 750_000, "condo": 550_000},
    "Montreal South Shore and North": {"single_family": 1_250_000, "condo": 750_000},
    "Hudson - Saint Lazare": {"single_family": 1_000_000, "condo": 500_000},
    "Saint-Jean-sur-Richelieu": {"single_family": 850_000, "condo": 500_000},
    "Gatineau-Hull": {"single_family": 750_000, "condo": 500_000},
    "Rest of Quebec": {"single_family": 750_000, "condo": 500_000},
    # Atlantic Canada
    "New Brunswick (All)": {"single_family": 600_000, "condo": 500_000},
    "Halifax": {"single_family": 900_000, "condo": 750_000},
    "Rest of Nova Scotia": {"single_family": 650_000, "condo": 400_000},
    "Prince Edward Island (All)": {"single_family": 700_000, "condo": 500_000},
    "St. John's": {"single_family": 600_000, "condo": 500_000},
    "Rest of Newfoundland": {"single_family": 450_000, "condo": 400_000},
    # Territories
    "Whitehorse": {"single_family": 750_000, "condo": 500_000},
    "Rest of Yukon": {"single_family": 500_000, "condo": 500_000},
    "Yellowknife": {"single_family": 750_000, "condo": 500_000},
    "Rest of NWT": {"single_family": 500_000, "condo": 500_000},
    "Nunavut (All)": {"single_family": 500_000, "condo": 500_000},
}

def get_max_ltv_tier(region, property_type):
    """
    Return the LTV tier value (the amount up to which 80% LTV is allowed)
    for a given region and property type ('single_family' or 'condo').
    Falls back to the nearest 'Rest of' region if the exact region isn't found.
    """
    region_key = region.strip()
    if region_key not in GEOGRAPHIC_LTV_TIERS:
        # Try to match a "Rest of" key
        for key in GEOGRAPHIC_LTV_TIERS:
            if key.startswith("Rest of") and region_key.endswith(key.replace("Rest of", "").strip()):
                region_key = key
                break
    tiers = GEOGRAPHIC_LTV_TIERS.get(region_key, {})
    if property_type.lower() in ("single_family", "townhouse", "detached", "semi-detached"):
        return tiers.get("single_family", 1_000_000)
    elif property_type.lower() in ("condo", "apartment", "condominium"):
        return tiers.get("condo", 500_000)
    return tiers.get("single_family", 1_000_000)

def max_ltv_for_property(purchase_price, region, property_type):
    """
    Calculate the maximum loan amount based on the LTV tiering formula:
    80% of tier value + 50% of the amount exceeding the tier value.
    Returns (max_loan_amount, effective_ltv_percent).
    """
    tier_value = get_max_ltv_tier(region, property_type)
    if purchase_price <= tier_value:
        max_loan = purchase_price * 0.80
    else:
        max_loan = tier_value * 0.80 + (purchase_price - tier_value) * 0.50
    effective_ltv = (max_loan / purchase_price) * 100 if purchase_price > 0 else 0
    return max_loan, effective_ltv

# =============================================================================
# Property Eligibility (from FPHE1, pages 34-37)
# =============================================================================

ELIGIBLE_HOUSING_TYPES = [
    "owner occupied single family detached",
    "owner occupied single family detached with laneway home",
    "owner occupied semi-detached",
    "owner occupied semi-detached with laneway home",
    "owner occupied condominium units",
    "owner occupied stacked townhouse",
    "owner occupied townhouse",
    "owner occupied townhouse with laneway home",
    "owner occupied duplex",
    "owner occupied triplex",
    "owner occupied fourplex",
]

INELIGIBLE_PROPERTY_TYPES = [
    "zoned as commercial",
    "residential properties containing any type of commercial activity",
    "resort properties",
    "rental pool properties",
    "bed and breakfast",
    "buildings containing more than 6 units",
    "units in co-ownership projects and undivided co-ownership",
    "units in co-operative projects (co-ops)",
    "not-for-profit homes",
    "fractional interest",
    "illegal grow-ops",
    "time shares",
    "rooming houses",
    "hotel-condos outside of designated markets",
]

STANDARD_ZONING = ["residential", "rural residential", "country residential", "agricultural"]

def is_eligible_property_type(property_type, has_commercial=False):
    """
    Check if a property type is eligible.
    Returns (eligible, reason).
    """
    if has_commercial:
        return False, "Properties containing commercial activity are ineligible."
    if property_type in INELIGIBLE_PROPERTY_TYPES:
        return False, f"Property type '{property_type}' is ineligible."
    return True, "Eligible"
# =============================================================================
# Additional policy rules – from FPHE1
# =============================================================================

# --- Non-Conforming Mortgages (FPHE1, pp. 5-6) ---
NON_CONFORMING_MAX_LTV = 65.0          # standard cap for non‑conforming
NON_CONFORMING_EXCEPTION_LTV = 80.0    # allowed when consolidating only existing debt

def is_non_conforming(credit_score, program, is_existing_debt_only=False):
    """
    Determines if an application is non‑conforming based on credit score and program.
    Returns (is_non_conforming, max_ltv_allowed).
    """
    # Low credit score (0 or E) – common trigger
    if credit_score in (0, "E", "0", "e"):
        # Exception: existing debt consolidation
        if is_existing_debt_only:
            return True, NON_CONFORMING_EXCEPTION_LTV
        return True, NON_CONFORMING_MAX_LTV
    # Add other triggers: stated income programs, special property types
    if program in ("Self Employed Stated Income", "Wealth Accumulator", "Newcomer and Foreign Income"):
        return True, NON_CONFORMING_MAX_LTV
    return False, None

# --- Down Payment Verification Exception (FPHE1, p. 24) ---
DOWN_PAYMENT_VERIFICATION_EXCEPTION_PCT = 10.0   # up to 10% of down payment can be confirmed by deposit
DOWN_PAYMENT_CLEAN_HISTORY_MIN_YEARS = 1         # must have clean repayment history for ≥1 year

# --- Student Housing & Condo-Hotel (FPHE1, pp. 37-39) ---
STUDENT_HOUSING_INSURED_INELIGIBLE = True
CONDO_HOTEL_ALLOWED_CITIES = [
    "Greater Toronto Area",
    "Greater Vancouver Area",
    "Calgary",
    "Montreal",
]
CONDO_HOTEL_REQUIREMENTS = {
    "must_be_high_rise": True,
    "must_have_separate_strata": True,
    "no_rental_pool": True,
}
# Note: No exceptions outside CONDO_HOTEL_ALLOWED_CITIES.

# --- Survey / Title Insurance Waivers (FPHE1, pp. 29-30) ---
SURVEY_WAIVER_LTV_CAP = 50.0   # LTV must be <50% to waive survey/title insurance
SURVEY_WAIVER_EXISTING_ONLY = True   # only allowed for existing mortgages

def can_waive_survey(mortgage_type, ltv_percent, is_existing_mortgage):
    """
    Returns (can_waive, reason).
    Survey cannot be waived for default insured, LTV > 50%, or if not an existing mortgage.
    """
    if mortgage_type == "Default Insured":
        return False, "Survey waiver not permitted for default insured mortgages."
    if ltv_percent > SURVEY_WAIVER_LTV_CAP:
        return False, f"LTV {ltv_percent:.1f}% exceeds the {SURVEY_WAIVER_LTV_CAP}% waiver cap."
    if not is_existing_mortgage:
        return False, "Survey waiver only allowed for existing mortgages."
    return True, "Survey waiver is permitted."

# --- Purchase Incentives (FPHE1, pp. 49-50) ---
def adjust_purchase_price_for_incentives(purchase_price, incentives):
    """
    Subtract the value of any non‑value‑adding incentives (cashback, fee waivers,
    interest buydowns) from the purchase price for LTV calculation.
    incentives: list of incentive amounts that do NOT contribute to the property's value.
    Returns adjusted_price.
    """
    total_incentive = sum(amt for amt in incentives if amt > 0)
    return max(purchase_price - total_incentive, 0)