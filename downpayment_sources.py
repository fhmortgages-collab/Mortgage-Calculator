"""
Down payment source configuration.

All sources and documentation requirements below reflect general,
industry-standard mortgage lending practice (the kind of thing found in
public CMHC/insurer guidelines and typical lender disclosure documents).
Nothing here references any specific financial institution's internal
policy, product names, or proprietary underwriting overlays.
"""

DOWN_PAYMENT_SOURCES = [
    {
        "key": "savings",
        "label": "Personal Savings or Investments",
        "eligible": True,
        "documents": [
            "Bank or investment statements covering the most recent 90 days",
            "Statements must show account holder name, account number, and institution details",
            "Large one-time deposits require a separate explanation and proof of source",
        ],
        "notes": "Amount saved should be reasonable relative to income, employment history, and existing debts.",
    },
    {
        "key": "gift_domestic",
        "label": "Gift from Immediate Family Member (Domestic)",
        "eligible": True,
        "documents": [
            "Signed gift letter confirming funds are a true gift with no repayment expected",
            "Proof the gift funds are on deposit in the applicant's account",
            "Confirmation of the donor's available funds (bank statement or letter from donor's institution)",
        ],
        "notes": "Donor must be an immediate family member (parent, child, sibling, grandparent, or legal guardian).",
    },
    {
        "key": "gift_foreign",
        "label": "Gift from Immediate Family Member (Foreign Source)",
        "eligible": True,
        "documents": [
            "Signed gift letter confirming funds are a true gift with no repayment expected",
            "Donor's financial or investment statement confirming sufficient funds",
            "Written explanation of how the donor accumulated the funds",
        ],
        "notes": "Foreign-sourced gifts may require additional review depending on the donor's country of residence.",
    },
    {
        "key": "gift_equity",
        "label": "Gift of Equity",
        "eligible": True,
        "documents": [
            "Signed gift of equity letter",
            "Signed purchase and sale agreement showing the reduced sale price",
        ],
        "notes": "Only applies to a sale between immediate family members with no cash changing hands for the gifted portion; usually limited to a primary residence or second home.",
    },
    {
        "key": "sale_property",
        "label": "Proceeds from Sale of an Existing Property",
        "eligible": True,
        "documents": [
            "Signed, unconditional purchase and sale agreement for the property being sold",
            "Statement showing the outstanding mortgage balance on the property being sold",
        ],
        "notes": "If the new purchase closes before the existing sale closes, bridge financing or another verified source may be required instead.",
    },
    {
        "key": "equity_land",
        "label": "Equity in Land Already Owned",
        "eligible": True,
        "documents": [
            "Current appraisal confirming the land's value",
            "Confirmation of clear title (free of mortgages or other encumbrances)",
        ],
        "notes": "Applicant must own, or be about to own, the land free and clear of encumbrances.",
    },
    {
        "key": "rent_to_own",
        "label": "Rent-to-Own Credit",
        "eligible": True,
        "documents": [
            "Signed lease agreement",
            "Appraiser-confirmed fair market rent for the property",
        ],
        "notes": "Only the portion of rent paid above fair market rent can count toward the down payment.",
    },
    {
        "key": "secured_credit",
        "label": "Personal Credit Facility Secured by Real Estate",
        "eligible": True,
        "documents": [
            "Confirmation the credit facility belongs to a borrower on the application",
            "Confirmation of available funds sufficient to cover the stated down payment",
        ],
        "notes": "Repayment of any amount drawn must be included in the applicant's debt service calculations.",
    },
    {
        "key": "unsecured_credit",
        "label": "Unsecured Credit Facility (Insured Mortgages Only)",
        "eligible": True,
        "documents": [
            "Confirmation of available credit and terms",
        ],
        "notes": "Generally limited to high-ratio insured mortgages, subject to credit score and other eligibility requirements. Funds from a related party routed through a personal credit line are not accepted.",
    },
    {
        "key": "builder_deposit",
        "label": "Builder Deposits Already Paid",
        "eligible": True,
        "documents": [
            "Standard down payment source documentation for the true origin of the deposit funds",
            "Copy of the purchase agreement showing deposit amounts and dates",
        ],
        "notes": "A cancelled cheque or receipt alone is not sufficient proof of source.",
    },
    {
        "key": "government_assistance",
        "label": "Government or Community Down Payment Assistance Program",
        "eligible": True,
        "documents": [
            "Confirmation letter from the granting government or community program",
            "Program terms showing repayment structure (if any)",
        ],
        "notes": "Program terms vary widely by jurisdiction; some programs are structured as forgivable loans.",
    },
    {
        "key": "vendor_cash_back",
        "label": "Vendor / Builder Cash Back or Incentive",
        "eligible": False,
        "documents": [],
        "notes": "Not an eligible down payment source. If a cash-back incentive exists, the purchase price is typically reduced by that amount for loan-to-value calculation purposes.",
    },
    {
        "key": "deposit_bond",
        "label": "Real Estate Deposit Bond",
        "eligible": False,
        "documents": [],
        "notes": "Not an eligible down payment source. May be used to create a binding purchase agreement, but standard down payment verification still applies on top of it.",
    },
    {
        "key": "other",
        "label": "Other",
        "eligible": True,
        "documents": [
            "Documentation to be determined based on the specific source — please describe below",
        ],
        "notes": "Use this option for a source not listed above.",
    },
]
