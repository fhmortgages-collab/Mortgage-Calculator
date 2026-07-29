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
        ],
        "notes": "Typically calculated using the lesser of the 2-year average or the most recent year's income.",
        "special": "two_year_avg",
    },
    {
        "key": "bonus_overtime",
        "label": "Bonus / Overtime",
        "documents": [
            "T4 slips for the last 2 years",
            "Pay stubs showing bonus/overtime amounts",
            "Employment verification letter confirming this is a regular part of compensation",
        ],
        "notes": "Typically calculated using the lesser of the 2-year average or the most recent year's income.",
        "special": "two_year_avg",
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
        "notes": "Net income is generally calculated as gross income less business expenses, using the lesser of the 2-year average or most recent year.",
        "special": "self_employed",
    },
    {
        "key": "investment",
        "label": "Investment / Dividend Income",
        "documents": [
            "Investment or brokerage statements for the last 2 years",
            "Personal tax returns showing investment/dividend income",
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
        ],
        "notes": "Net rental income is generally calculated as gross rent less property expenses.",
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
        "key": "other",
        "label": "Other",
        "documents": [
            "Documentation to be determined based on the specific source — please describe below",
        ],
        "notes": "Use this option for a source not listed above.",
        "special": None,
    },
]
