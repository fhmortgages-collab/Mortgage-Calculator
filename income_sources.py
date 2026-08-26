"""
Income source configuration.

Reflects general, industry-standard mortgage income verification practice
(the kind of thing found in public CMHC guidelines and typical lender
disclosure documents). Nothing here references any specific financial
institution's internal policy, escalation paths, or proprietary program names.
"""

INCOME_SOURCES = [
    {
        "key": "salaried",
        "label": "Employed (Salaried)",
        "documents": [
            "T4 slips (or W-2, if applicable) for the last 2 years",
            "Pay stubs from the last 30 days",
            "Employment verification letter on company letterhead",
            "Notice of Assessment for the last 2 years",
        ],
        "notes": "",
        "special": None,
    },
    {
        "key": "commission",
        "label": "Commission-Based Income",
        "documents": [
            "T4 slips for the last 2 years",
            "Pay stubs from the last 30 days",
            "Employment verification letter confirming commission structure",
            "Notice of Assessment for the last 2 years",
        ],
        "notes": "If the most recent year is lower than the prior year, the lower (most recent) year is used. If the most recent year is higher, the 2-year average is used.",
        "special": "two_year_variable",
    },
    {
        "key": "hourly",
        "label": "Hourly Income (Variable Hours)",
        "documents": [
            "Pay stubs showing hourly rate and hours worked",
            "T4 slips for the last 2 years",
            "Employment verification letter confirming hourly rate (and guaranteed hours, if any)",
            "Notice of Assessment for the last 2 years",
        ],
        "notes": "If hours are guaranteed, treated like salary. If hours vary, if the most recent year is lower than the prior year, the lower (most recent) year is used; if higher, the 2-year average is used.",
        "special": "two_year_variable",
    },
    {
        "key": "bonus_overtime",
        "label": "Bonus / Overtime",
        "documents": [
            "T4 slips for the last 2 years",
            "Pay stubs showing bonus/overtime amounts",
            "Employment verification letter confirming this is a regular part of compensation",
            "Notice of Assessment for the last 2 years",
        ],
        "notes": "If the most recent year is lower than the prior year, the lower (most recent) year is used. If the most recent year is higher, the 2-year average is used.",
        "special": "two_year_variable",
    },
    {
        "key": "self_employed",
        "label": "Self-Employed",
        "documents": [
            "Personal tax returns for the last 2 years",
            "Notice of Assessment for the last 2 years",
            "Business license or registration",
            "6 months of business bank statements",
            "Financial statements (income statement and balance sheet), if available",
        ],
        "notes": "Net income is generally calculated as gross income less business expenses. If the most recent year is lower than the prior year, the lower (most recent) year is used; if higher, the 2-year average is used.",
        "special": "two_year_variable",
    },
    {
        "key": "dividend",
        "label": "Dividend Income",
        "documents": [
            "Investment or brokerage statements for the last 2 years",
            "Personal tax returns showing dividend income (T5 slips)",
            "Notice of Assessment for the last 2 years",
        ],
        "notes": "If the most recent year is lower than the prior year, the lower (most recent) year is used. If the most recent year is higher, the 2-year average is used.",
        "special": "two_year_variable",
    },
    {
        "key": "investment",
        "label": "Investment Income (Non-Dividend)",
        "documents": [
            "Investment or brokerage statements for the last 2 years",
            "Personal tax returns showing investment income",
        ],
        "notes": "",
        "special": None,
    },
    {
        "key": "rental",
        "label": "Rental Property Income",
        "documents": [
            "Signed lease agreement(s)",
            "Most recent Notice of Assessment or rental income schedule",
            "Property tax and expense statements",
            "3 months of bank statements confirming deposit of rental income",
        ],
        "notes": "Net rental income is generally calculated as gross rent less property expenses.",
        "special": "rental",
    },
    {
        "key": "rental_component_primary",
        "label": "Rental Income — Component of Primary Residence (e.g. basement suite)",
        "documents": [
            "Signed lease agreement for the rented portion of the home",
            "Appraisal or property assessment confirming a self-contained secondary suite",
            "3 months of bank statements confirming deposit of rental income",
        ],
        "notes": (
            "Only usable if the rented portion is a legally conforming, self-contained unit with its own "
            "kitchen, bathroom, and separate entrance — confirm this on the Property Details step. If any "
            "of those three are missing, this income cannot be used for qualification."
        ),
        "special": "rental",
    },
    {
        "key": "pension",
        "label": "Pension / Retirement Income",
        "documents": [
            "Pension statement or T4A slip",
            "Most recent Notice of Assessment",
        ],
        "notes": "",
        "special": None,
    },
    {
        "key": "government_benefits",
        "label": "Social Security / Government Benefits",
        "documents": [
            "Most recent government benefits statement",
        ],
        "notes": "Some government benefit income may be capped as a percentage of total qualifying income, depending on the program.",
        "special": None,
    },
    {
        "key": "alimony",
        "label": "Alimony / Child Support",
        "documents": [
            "Separation agreement or court order confirming amount and duration",
            "Proof of receipt for the last 12 months",
        ],
        "notes": "",
        "special": None,
    },
    {
        "key": "trust_inheritance",
        "label": "Trust Fund / Inheritance Income",
        "documents": [
            "Trust agreement or estate documentation",
            "Statement confirming distribution amount and frequency",
        ],
        "notes": "",
        "special": None,
    },
    {
        "key": "parttime",
        "label": "Part-Time Income",
        "documents": [
            "Pay stubs from the last 30 days",
            "T4 slips for the last 2 years",
            "Employment verification letter",
            "Notice of Assessment for the last 2 years",
        ],
        "notes": "Usable if consistent and ongoing; lenders are typically more cautious than with full-time salary and may discount it if the history is short or inconsistent.",
        "special": None,
    },
    {
        "key": "self_employed_incorporated",
        "label": "Self-Employed — Incorporated",
        "documents": [
            "2 years of personal tax returns",
            "2 years of Notices of Assessment",
            "T2 corporate tax returns",
            "Corporate financial statements",
            "Articles of incorporation",
            "Business bank statements",
            "T4/T5 slips",
        ],
        "notes": "Assessed using a mix of personal and corporate income (salary, dividends, and sometimes retained earnings). If the most recent year is lower than the prior year, the lower (most recent) year is used; if higher, the 2-year average is used.",
        "special": "two_year_variable",
    },
    {
        "key": "self_employed_professional",
        "label": "Self-Employed — Licensed Professional",
        "documents": [
            "Tax returns and Notices of Assessment (2 years)",
            "Professional license or registration",
            "Practice financial statements",
            "Business bank statements",
        ],
        "notes": "Licensed professionals (e.g. doctors, lawyers, accountants) are often treated somewhat more favourably since earning capacity is easier to support, but lenders still want proof of a consistent income pattern. If the most recent year is lower than the prior year, the lower (most recent) year is used; if higher, the 2-year average is used.",
        "special": "two_year_variable",
    },
    {
        "key": "disability",
        "label": "Disability Income",
        "documents": [
            "Benefit letters",
            "Insurance statements",
            "Bank deposit history",
        ],
        "notes": "Long-term disability income may be accepted if expected to continue; temporary benefits are usually treated more cautiously.",
        "special": None,
    },
    {
        "key": "ei_parental_benefits",
        "label": "EI / Maternity / Parental Benefits",
        "documents": [
            "Service Canada statements",
            "Benefit letters",
            "Deposit history",
            "Return-to-work evidence, if relevant",
        ],
        "notes": "Usually weaker for qualification since these benefits are temporary. May be considered only with a clear return-to-work plan and a stable broader income picture.",
        "special": None,
    },
    {
        "key": "foreign_income",
        "label": "Foreign Income",
        "documents": [
            "Foreign tax returns or slips",
            "Employment letters",
            "Bank statements",
            "Translation and currency conversion support, if needed",
        ],
        "notes": "May be usable if verifiable, ongoing, and acceptable to the lender. Lenders are usually conservative given currency and jurisdiction risk.",
        "special": None,
    },
    {
        "key": "capital_gains",
        "label": "Capital Gains",
        "documents": [
            "Investment statements",
            "Tax slips",
            "Capital gains reporting",
        ],
        "notes": "Not treated as stable, recurring income — generally excluded from standard mortgage qualification entirely, even if entered here.",
        "special": "excluded",
    },
    {
        "key": "board_director_fees",
        "label": "Trust / Board / Director Fees",
        "documents": [
            "Trust statements or trust deed",
            "T3 slips",
            "Board appointment records",
            "Bank statements",
        ],
        "notes": "May be counted if recurring and well documented, but treatment is highly case-specific — the main question is whether payments are stable enough to continue.",
        "special": None,
    },
    {
        "key": "foster_care",
        "label": "Foster Care Income",
        "documents": [
            "Current pay statement from the foster care agency",
            "Letter from the ministry confirming tenure, current status, and the last 2 years of income earned",
        ],
        "notes": "Maximum 6 children (including own), income cannot exceed 50% of total application income. Must be calculated using the 2-year average (or lesser of most recent year). Not eligible for gross‑up. Outside advisor's Delegated Lending Authority – requires underwriting review.",
        "special": "foster_care",
    },
    {
        "key": "ccb_qfa",
        "label": "Canada Child Benefit / Quebec Family Allowance",
        "documents": [
            "Most recent annual notice from the CRA or Revenu Québec confirming the benefit amount",
        ],
        "notes": "Only for children 12 years or younger. Cannot exceed 15% of total application income (excluding rental income). Not eligible for gross‑up. Outside advisor's Delegated Lending Authority – requires underwriting review.",
        "special": "ccb_qfa",
    },
    {
        "key": "foster_care",
        "label": "Foster Care Income",
        "documents": [
            "Current pay statement from the foster care agency",
            "Letter from the ministry confirming tenure, current status, and the last 2 years of income earned",
        ],
        "notes": "Maximum 6 children (including own), income cannot exceed 50% of total application income. Must be calculated using the 2-year average (or lesser of most recent year). Not eligible for gross‑up. Outside advisor's Delegated Lending Authority – requires underwriting review.",
        "special": "foster_care",
    },
    {
        "key": "ccb_qfa",
        "label": "Canada Child Benefit / Quebec Family Allowance",
        "documents": [
            "Most recent annual notice from the CRA or Revenu Québec confirming the benefit amount",
        ],
        "notes": "Only for children 12 years or younger. Cannot exceed 15% of total application income (excluding rental income). Not eligible for gross‑up. Outside advisor's Delegated Lending Authority – requires underwriting review.",
        "special": "ccb_qfa",
    },
    {
        "key": "other",
        "label": "Other",
        "documents": [
            "Documentation to be determined based on the specific source — please describe below",
        ],
        "notes": "Use this option for a source not listed above.",
        "special": None,
    },
]

# =============================================================================
# Additional income policy rules – from FPHE1
# =============================================================================

# --- Canada Child Benefit (CCB) and Quebec Family Allowance (QFA) (FPHE1, pp. 24-25) ---
CCB_MAX_CHILD_AGE = 12                      # children must be 12 or younger
CCB_MAX_PERCENT_OF_TOTAL_INCOME = 15.0      # cannot exceed 15% of total income (excluding rental)
CCB_QFA_GROSS_UP_INELIGIBLE = True          # not eligible for gross‑up
CCB_QFA_OUTSIDE_DLA = True                  # outside advisor's Delegated Lending Authority

# --- Foster Care Income (FPHE1, p. 25) ---
FOSTER_CARE_MAX_CHILDREN = 6                # including own children
FOSTER_CARE_MAX_INCOME_PERCENT = 50.0       # cannot exceed 50% of total income (excluding rental)
FOSTER_CARE_CALCULATION_RULE = "two_year_average_or_lesser"  # use lesser of 2‑year average or most recent year
FOSTER_CARE_OUTSIDE_DLA = True

# --- Foreign Income AML Risk Ratings (FPHE1, p. 7-8) ---
AML_ACCEPTABLE_RATINGS = ["Standard", "Medium", "High 1", "High 2"]
AML_HIGH2_EXCEPTIONS = ["China", "India"]   # High 2 is only accepted for China or India

def is_foreign_income_acceptable(country_code, aml_risk_rating):
    """
    Returns True if foreign income from a given country is acceptable.
    """
    if aml_risk_rating not in AML_ACCEPTABLE_RATINGS:
        return False
    if aml_risk_rating == "High 2":
        return country_code in AML_HIGH2_EXCEPTIONS
    return True

# --- Appraised Market Rent (FPHE1, pp. 25-27) ---
OWNER_OCCUPIED_RENT_INCLUSION_RATE = 0.80   # use 80% of lowest appraised market rent
MAX_APPRAISED_RENT_PER_UNIT = 6_000         # $6,000 per month per unit max

# High‑vacancy locations requiring 6 months of liquid assets to cover rental income used
HIGH_VACANCY_LOCATIONS = [
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
# Rural properties with postal code ending in '0' are also considered high‑vacancy.

def is_high_vacancy_location(city, province, postal_code):
    """
    Returns True if the location qualifies as high‑vacancy.
    """
    location_key = f"{city}, {province}".strip()
    if location_key in HIGH_VACANCY_LOCATIONS:
        return True
    if postal_code and postal_code.strip().endswith("0"):
        return True
    return False