with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

original_content = content

replacements = [
(
'''from refinance_rules import (
    equity_requirement_note,
    ltv_calculation_note,
    determine_amortization_increase,
    change_of_borrower_note,
    high_risk_review_note,
)''',
'''from refinance_rules import (
    equity_requirement_note,
    ltv_calculation_note,
    determine_amortization_increase,
    change_of_borrower_note,
    high_risk_review_note,
)
from insured_conventional_rules import (
    MORTGAGE_STRUCTURE_OPTIONS,
    help_mortgage_structure_text,
    get_lending_value,
    get_min_down_payment,
    get_max_base_mortgage,
    calculate_insurance_premium,
    explain_insured_vs_conventional,
)'''
),
(
'''    if "purchase_price_raw" not in st.session_state:
        st.session_state.purchase_price_raw = ""''',
'''    if "purchase_price_raw" not in st.session_state:
        st.session_state.purchase_price_raw = ""
    if "mortgage_structure" not in st.session_state:
        st.session_state.mortgage_structure = ""'''
),
(
'''    "step", "transaction_type", "borrower_count", "borrowers", "consent", "borrower_errors",
    "purchase_price_raw", "down_payment_raw", "selected_sources", "source_amounts", "source_details",''',
'''    "step", "transaction_type", "borrower_count", "borrowers", "consent", "borrower_errors",
    "purchase_price_raw", "down_payment_raw", "mortgage_structure", "selected_sources", "source_amounts", "source_details",'''
),
(
'''    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.refinance_balance_raw = ""''',
'''    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.mortgage_structure = ""
    st.session_state.refinance_balance_raw = ""'''
),
(
'''    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.selected_sources = []''',
'''    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.mortgage_structure = ""
    st.session_state.selected_sources = []'''
),
(
'''    col1, col2 = st.columns(2)
    with col1:
        st.session_state.purchase_price_raw = money_text_input(
            "Purchase Price ($)", st.session_state.purchase_price_raw, key="purchase_price_input",
            placeholder="e.g., 500,000",
        )
    with col2:
        st.session_state.down_payment_raw = money_text_input(
            "Down Payment Amount ($)", st.session_state.down_payment_raw, key="down_payment_input",
            placeholder="e.g., 100,000",
        )''',
'''    col1, col2 = st.columns(2)
    with col1:
        st.session_state.purchase_price_raw = money_text_input(
            "Purchase Price ($)", st.session_state.purchase_price_raw, key="purchase_price_input",
            placeholder="e.g., 500,000",
        )
    with col2:
        st.session_state.down_payment_raw = money_text_input(
            "Down Payment Amount ($)", st.session_state.down_payment_raw, key="down_payment_input",
            placeholder="e.g., 100,000",
        )

    st.session_state.mortgage_structure = st.selectbox(
        "Mortgage Structure", MORTGAGE_STRUCTURE_OPTIONS,
        index=MORTGAGE_STRUCTURE_OPTIONS.index(st.session_state.mortgage_structure)
        if st.session_state.mortgage_structure in MORTGAGE_STRUCTURE_OPTIONS else 0,
        key="mortgage_structure_input", help=help_mortgage_structure_text(),
    )
    if st.session_state.mortgage_structure:
        purchase_price_for_ltv = parse_money(st.session_state.purchase_price_raw) or 0.0
        appraised_for_ltv = parse_money(st.session_state.get("property_appraisal_value_raw", ""))
        down_payment_for_ltv = parse_money(st.session_state.down_payment_raw)
        st.caption(
            explain_insured_vs_conventional(
                purchase_price_for_ltv, appraised_for_ltv, down_payment_for_ltv,
                st.session_state.mortgage_structure,
            )
        )'''
),
]

applied = 0
missing = []
for old, new in replacements:
    if old in content:
        content = content.replace(old, new, 1)
        applied += 1
    else:
        missing.append(old.strip().splitlines()[0])

if content != original_content:
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)

print("Applied:", applied, "of", len(replacements))
if missing:
    print("Could NOT find (skipped, no change made for these):")
    for m in missing:
        print("  -", m)