import streamlit as st

st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

# --- UI STYLE: DARK MODE FINTECH ---
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; font-family: sans-serif; }
    .stButton>button { border-radius: 8px; border: 1px solid #30363d; background: #161b22; color: #ffffff; width: 100%; }
    .card { background: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 20px; }
    input { background: #161b22 !important; border: 1px solid #30363d !important; color: white !important; border-radius: 8px !important; }
    .stMetric { background: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# --- POLICY MAPPING ---
DOCS = {
    "Cash Savings": ["📄 90-day History", "📄 Account Statements", "📄 Verification of one-time deposits"],
    "Financial Gift (Domestic)": ["📄 Signed Gift Letter", "📄 Donor Bank Stmt/Confirmation Letter"],
    "Financial Gift (Foreign)": ["📄 Signed Gift Letter", "📄 Origin of Funds/Accumulation Notes", "📄 AML/GES Review Docs"],
    "Gift of Equity": ["📄 Signed Gift of Equity Letter", "📄 Unconditional Purchase Agreement"],
    "Equity in Existing Property": ["📄 Unconditional P&S Agreement", "📄 Liabilities Statement"],
    "Equity in Land": ["📄 Property Appraisal", "📄 Title Search"],
    "Rent-to-Own": ["📄 Signed Lease Agreement", "📄 Appraiser Market Rent Confirmation"],
    "Personal Credit Facility": ["📄 Verification of Ownership", "📄 Available Funds Confirmation"],
    "Existing Unsecured Facility": ["📄 Credit Score Verification (A/B Only)", "📄 Repayment History"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Proof of Deposit"],
    "Affordable Housing/Band Grant": ["📄 Grant Approval Letter", "📄 Forgivable Loan Terms Confirmation"]
}

INCOME_CATS = {
    "Employment": ["📄 Letter of Employment", "📄 Pay Stubs", "📄 T4 Slips"],
    "Variable Income (OT/Bonus)": ["📄 Pay Stubs (YTD)", "📄 2 Years T4 Slips"],
    "Self-Employed (Sole/Corp)": ["📄 2 Years T1 General", "📄 NOA"],
    "Foster Care": ["📄 Ministry Letter", "📄 2 Years History"],
    "Rental Income": ["📄 Appraisal", "📄 Lease Agreement"]
}

# --- STATE MANAGEMENT ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'dp_sources': {}, 'debts': {}, 'loan_val': 0.0, 'income_val': 0.0, 'debt_total': 0.0
}

# --- NAVIGATION STEPPER ---
st.markdown("## FH Mortgage Loan Wizard")
cols = st.columns(5)
steps = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]
for i in range(5):
    btn_type = "primary" if st.session_state.step == i+1 else "secondary"
    cols[i].button(str(i+1), disabled=(st.session_state.step != i+1), type=btn_type)
    cols[i].caption(steps[i])
st.divider()

# 1. CLIENT DETAILS
if st.session_state.step == 1:
    st.header("Client Details")
    st.write("Enter information for each borrower.")
    num = st.radio("Number of Borrowers", [1, 2, 3, 4], index=len(st.session_state.form['borrowers'])-1)
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}", expanded=True):
            col1, col2 = st.columns(2)
            st.session_state.form['borrowers'][i]['name'] = col1.text_input("Full Name", key=f"n{i}")
            st.session_state.form['borrowers'][i]['email'] = col2.text_input("Email", key=f"e{i}")
            st.session_state.form['borrowers'][i]['dob'] = col1.date_input("Date of Birth", key=f"d{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input("Address", key=f"a{i}")

    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): st.session_state.step = 2; st.rerun()

# 2. MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.header("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.metric("Loan Amount", f"${st.session_state.form['loan_val']:,.2f}")
    
    srcs = st.multiselect("Select Down Payment Sources:", list(DOCS.keys()))
    for src in srcs:
        st.session_state.form['dp_sources'][src] = st.number_input(f"Amount for {src} ($)", key=f"dp_{src}")
        for doc in DOCS.get(src, []): st.caption(f"• {doc}")
    
    if st.button("⬅ Back"): st.session_state.step = 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# 3. INCOME
elif st.session_state.step == 3:
    st.header("Income Streams")
    srcs = st.multiselect("Select All Income Sources:", list(INCOME_CATS.keys()))
    st.session_state.form['income_val'] = st.number_input("Total Annual Income ($)", value=0.0)
    
    for src in srcs:
        st.write(f"**Documentation for {src}:**")
        for doc in INCOME_CATS.get(src, []): st.info(doc)
    
    if st.button("⬅ Back"): st.session_state.step = 2; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# 4. DEBTS
elif st.session_state.step == 4:
    st.header("Debt Obligations")
    cats = st.multiselect("Debt Categories:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support"])
    
    total_monthly = 0.0
    for cat in cats:
        vals = st.text_input(f"Enter {cat} balance/payment (comma separated)", key=f"inp_{cat}")
        if vals:
            nums = [float(x.strip()) for x in vals.split(',')]
            monthly = sum(nums) * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (sum(nums) / 12)
            st.write(f"**Monthly Impact: ${monthly:,.2f}**")
            total_monthly += monthly
            
    st.session_state.form['debt_total'] = total_monthly
    if st.button("⬅ Back"): st.session_state.step = 3; st.rerun()
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# 5. ANALYSIS
elif st.session_state.step == 5:
    st.header("Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    # Gross-up: 15% for Self-Employed per policy
    is_se = any("Self-Employed" in s for s in st.session_state.form['inc_sources'])
    adj_inc = inc * 1.15 if is_se else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("Adjusted Income", f"${adj_inc:,.2f}")
    col2.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back"): st.session_state.step = 4; st.rerun()
