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