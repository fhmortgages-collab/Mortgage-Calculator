import streamlit as st

st.set_page_config(page_title="FH Mortgages | Loan Wizard", layout="centered")

# --- POLICY MAPPING ---
DOCS_MAP = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (2 Years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"],
    "Pension": ["📄 Pension Award Letter", "📄 T4A/T4AP Statement"],
    "Rental": ["📄 T776 Statement of Real Estate Rentals"],
    "Savings": ["📄 90-day Bank Statements (Evidence of Funds)"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Sale of Property": ["📄 Unconditional Sale Agreement"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'debts': {}, 'loan': 0.0, 'income': 0.0
}

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# --- UI LOGIC ---
st.title("🏠 FH Mortgages Loan Wizard")
st.progress(st.session_state.step / 5)

# STEP 1: CLIENT DETAILS
if st.session_state.step == 1:
    st.subheader("1. Client Details")
    # ... (same dynamic borrower structure as before) ...
    if st.button("Next ➔"): next_step(); st.rerun()

# STEP 2: MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property"])
    for src in st.session_state.form['down_sources']:
        for doc in DOCS_MAP.get(src, []): st.info(doc)

    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Next ➔", on_click=next_step)

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    sources = st.multiselect("Select All Sources:", ["Employed (T4)", "Self-Employed", "Pension", "Rental"])
    st.session_state.form['income'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in sources:
        st.write(f"**Required Docs for {src}:**")
        for doc in DOCS_MAP.get(src, []): st.info(doc)
    
    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Next ➔", on_click=next_step)

# STEP 4: DEBT CALCULATOR
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan"])
    
    total_monthly_debt = 0.0
    for cat in cats:
        st.write(f"### {cat}")
        # Build mini-calculator for multiple instances
        count = st.number_input(f"How many {cat} accounts?", 1, 5, 1, key=f"c_{cat}")
        sub_balance = 0.0
        for j in range(count):
            sub_balance += st.number_input(f"Balance/Amount {j+1} ($)", key=f"b_{cat}_{j}")
        
        # Policy Calculation Logic
        monthly = sub_balance * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (sub_balance / 12)
        st.write(f"**Total {cat} Monthly Impact: ${monthly:,.2f}**")
        total_monthly_debt += monthly
    
    st.session_state.form['debt_val'] = total_monthly_debt
    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Calculate Analysis ➔", on_click=next_step)

# STEP 5: ANALYSIS
elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income']
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    loan = st.session_state.form['loan']
    debts = st.session_state.form['debt_val']
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    st.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): prev_step(); st.rerun()
