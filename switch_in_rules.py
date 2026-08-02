"""
Switch-in (Refinance - New Lender) rules configuration.

Reflects general, industry-standard Canadian switch-in mortgage practice
(FRFI switch rules, straight-switch vs. discharge/re-registration,
AMQR/MQR qualifying-rate logic, and standard fee caps). Nothing here
references any specific financial institution's internal policy,
proprietary formulas, or product names.
"""

REGISTRATION_TYPES = ["", "Traditional Mortgage", "Collateral Mortgage"]
MORTGAGE_TYPES = ["", "Conventional", "Default Insured"]
SWITCH_TIMING_OPTIONS = ["", "At Maturity", "Prior to Maturity"]

SWITCH_IN_ELIGIBLE_PROGRAMS = [
    "Investment Properties",
    "Rural Estates",
    "Seasonal Cottage",
    "Second Homes",
    "Newcomer Equity and High Net Worth",
    "Foreign Income - U.S. and All Other Countries",
    "Self Employed Stated Income (Conventional)",
    "Temporary Residents on Work Permit",
    "Wealth Accumulator",
    "Cash Back",
]

SWITCH_IN_INELIGIBLE_PROGRAMS = [
    "Factory Constructed Homes",
    "First Nations Ministerial Loan Guarantee (MLG) Program",
    "Leasehold Lending on First Nations Land",
    "Switch Add On",
    "Private Mortgages or Lenders",
    "Self Employed Stated Income (Default Insured)",
]

SWITCH_IN_PROGRAM_OPTIONS = [""] + SWITCH_IN_ELIGIBLE_PROGRAMS + SWITCH_IN_INELIGIBLE_PROGRAMS + ["Other / Not Listed"]

# Fee caps
MAX_FEES_ADDED_AT_MATURITY = 3000       # switch-related fees/costs addable to balance at maturity
MAX_DISCHARGE_SWITCH_OUT_FEE = 300      # title insurance / discharge / switch-out fee exception cap
MAX_PER_DIEM_AUTO_ADJUST = 1500         # Ops Centre can auto-adjust balance for per diem up to this without re-approval

# Debt-service limits (default insured)
DEFAULT_INSURED_TDS_LIMIT = 40.0
DEFAULT_INSURED_GDS_LIMIT = 32.0

CONVENTIONAL_MAX_LTV = 80.0  # % — conventional switch-in balance must not exceed this of appraised value


def is_straight_switch(reg_type, mortgage_type, timing, ofi_is_frfi, amount_unchanged, amortization_unchanged):
    """
    A 'straight switch' can be completed through a title insurer without
    discharge/re-registration. All of the following must hold:
    - at maturity
    - OFI is a Federally Regulated Financial Institution (FRFI)
    - traditional registration (not collateral) on both sides
    - conventional or default insured product
    - amount and amortization unchanged from the OFI
    """
    return (
        timing == "At Maturity"
        and ofi_is_frfi
        and reg_type == "Traditional Mortgage"
        and mortgage_type in ("Conventional", "Default Insured")
        and amount_unchanged
        and amortization_unchanged
    )


def requires_discharge_and_reregistration(reg_type, straight_switch):
    """Collateral registrations always require discharge/re-registration; so does any non-straight-switch transfer."""
    if reg_type == "Collateral Mortgage":
        return True
    return not straight_switch


def determine_qualifying_path(
    mortgage_type,
    timing,
    additional_funds_requested,
    amortization_changed,
    amortization_unchanged_from_ofi,
    borrowers_changed,
):
    """
    Returns (qualifying_rate_label, requires_refinance_registration, explanation).

    qualifying_rate_label is one of: 'MQR', 'AMQR', 'Contract Rate (subject to confirmation)'.
    """
    if borrowers_changed:
        return (
            "MQR",
            True,
            "Borrowers/guarantors on title have changed from the original mortgage charge — this requires "
            "a new mortgage charge and must be processed as a refinance/re-registration at the MQR.",
        )

    if additional_funds_requested:
        return (
            "MQR",
            True,
            "Additional funds requested — this is a refinance transaction requiring full MQR qualification "
            "and discharge/re-registration.",
        )

    if amortization_changed:
        return (
            "MQR",
            True,
            "Extended or reduced amortization requested — the full MQR must be applied and the mortgage "
            "discharged and re-registered.",
        )

    if timing != "At Maturity":
        return (
            "MQR",
            True,
            "Switching prior to maturity requires a full discharge and re-registration, qualified at the MQR.",
        )

    if mortgage_type == "Conventional":
        if amortization_unchanged_from_ofi:
            return (
                "AMQR",
                False,
                "Conventional mortgage, switching at maturity, no additional funds, amortization unchanged — "
                "meets Adjusted Minimum Qualifying Rate (contract rate + 1%) eligibility.",
            )
        return (
            "MQR",
            True,
            "Amortization does not match the OFI's remaining amortization — AMQR eligibility is lost; "
            "MQR applies and the mortgage must be discharged and re-registered.",
        )

    if mortgage_type == "Default Insured":
        return (
            "Contract Rate (subject to confirmation)",
            False,
            "Default insured mortgage, direct switch at maturity — may be eligible to qualify at the contract "
            "rate, subject to confirming mandatory documents and business case requirements with the insurer.",
        )

    return ("MQR", True, "Insufficient information to determine an exempt qualifying path — defaulting to MQR.")


def switch_in_document_requirements():
    """Standard mandatory documents/business case notes for verifying the OFI mortgage."""
    return {
        "documents": [
            "Verification of the client's current outstanding balance and remaining amortization at the OFI "
            "(current mortgage statement, renewal document, or online banking screenshot)",
        ],
        "business_case_notes": [
            "Type of product being switched in (e.g. conventional mortgage registered as a collateral "
            "mortgage vs. registered as a standard mortgage)",
            "Confirmation that the amount and amortization align with the client's renewal information",
            "Verification comments confirming the mortgage being switched in is from a Federally Regulated "
            "Financial Institution (FRFI)",
        ],
    }
