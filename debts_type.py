"""
Debt type configuration.

Reflects general, industry-standard mortgage debt-servicing practice
(the kind of thing published by CMHC and used broadly across Canadian
lenders). Nothing here references any specific financial institution's
internal policy, proprietary formulas, or product names.
"""

DEBT_TYPES = [
    {
        "key": "installment",
        "label": "Installment Loans (Car Loan, Student Loan, Personal Loan)",
        "calc": "stated_payment",
        "documents": [
            "Loan agreement or payment schedule showing the monthly payment",
            "Recent statement showing payment history",
        ],
        "notes": "Uses the regular monthly payment as per the loan agreement.",
    },
    {
        "key": "credit_card",
        "label": "Credit Cards",
        "calc": "percent_of_balance",
        "percent": 0.03,
        "documents": [
            "Most recent statements for all credit cards",
            "Statement showing outstanding balance and minimum payment",
        ],
        "notes": "Monthly payment is commonly estimated as 3% of the total outstanding balance.",
    },
    {
        "key": "line_of_credit",
        "label": "Lines of Credit (Secured or Unsecured)",
        "calc": "percent_of_balance",
        "percent": 0.03,
        "documents": [
            "Recent line of credit statement showing balance and limit",
        ],
        "notes": "Monthly payment is commonly estimated as 3% of the outstanding balance, or calculated as interest-only if a rate is provided.",
    },
    {
        "key": "alimony",
        "label": "Alimony / Child Support Payments",
        "calc": "stated_payment",
        "documents": [
            "Court order or separation agreement confirming the payment amount",
        ],
        "notes": "Uses the monthly payment amount as per the court order or agreement.",
    },
    {
        "key": "other",
        "label": "Other Monthly Obligations",
        "calc": "stated_payment",
        "documents": [
            "Supporting documentation or agreement describing the obligation",
        ],
        "notes": "Use this option for a recurring obligation not listed above.",
    },
]
