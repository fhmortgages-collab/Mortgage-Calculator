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
