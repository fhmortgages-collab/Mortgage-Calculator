import streamlit as st

st.set_page_config(page_title="FH Mortgages | Loan Wizard", layout="centered")

# --- POLICY-BASED DOCUMENT MAPPING ---
DOC_REQUIREMENTS = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart", "📄 Accountant-prepared Financial Statements (3 years if >$1M exposure)"],
    "Pension": ["📄 Pension Award Letter", "📄 T4A/T4AP Statement"],
    "Rental Income": ["📄 T776 Statement of Real Estate Rentals", "📄 Current Lease Agreements", "📄 Opinion of Market Rent"],
    "Support Payments": ["📄 Court Order / Legal Agreement", "📄 Proof of Receipt (Bank Statements)"],
    "Savings": ["📄 90-day Bank Statements (Own Resources)"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (to verify liquidity)"],
    "Sale of Property": ["📄 Unconditional Purchase & Sale Agreement", "📄 Statement of Adjustments"],
    "RRSP": ["📄 RRSP Statement (Last 90 days)"]
}

# --- STATE MANAGEMENT ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [], 'inc_sources': [], 'down_sources': [], 'debt_cats': [],
    'income_vals': {}, 'loan_val': 0.0, 'debt_val': 0.0
}

# --- WIZARD UI ---
st.title("🏠 FH Mortgages Loan Wizard")
st.progress(st.session_state.step / 5)

# STEP 1: BORROWER DETAILS
if st.session_state.step == 1:
    st.subheader("1. Borrower Information")
    num = st.number_input("Number of Borrowers", 1, 4, len(st.session_state.form['borrowers']) or 1)
    
    # Reset/Resize borrower list
    if len(st.session_state.form['borrowers']) != num:
        st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1} Details"):
            st.session_state.form['borrowers'][i]['name'] = st.text_input(f"Name {i+1}", key=f"n{i}")
            st.session_state.form['borrowers'][i]['dob'] = st.date_input(f"DOB {i+1}", key=f"d{i}")
            st.session_state.form['borrowers'][i]['sex'] = st.selectbox(f"Sex {i+1}", ["", "Decline to answer", "Male", "Female"], key=f"s{i}")
    
    if st.checkbox("I acknowledge and agree to the Consent Form 524"):
        if st.button("Next ➔"): st.session_state.step = 2; st.rerun()
    else: st.warning("Consent Form 524 acknowledgment required.")

# STEP 2: LOAN DETAILS
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    st.session_state.form['loan_val'] = st.number_input("Mortgage Amount ($)", value=0.0)
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", list(DOC_REQUIREMENTS.keys())[5:])
    
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 1; st.rerun()
    with col2: 
        if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Sources")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Sources:", ["Employed (T4)", "Self-Employed", "Pension", "Rental Income", "Support Payments"])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    st.write("### 📄 Required Documentation")
    for src in st.session_state.form['inc_sources']:
        st.write(f"**For {src}:**")
        for doc in DOC_REQUIREMENTS.get(src, []): st.info(doc)
    
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 2; st.rerun()
    with col2: 
        if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# STEP 4: DEBTS
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    st.session_state.form['debt_cats'] = st.multiselect("Debt Categories:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    st.session_state.form['debt_val'] = st.number_input("Total Monthly Debt Obligations ($)", value=0.0)
    
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 3; st.rerun()
    with col2: 
        if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# STEP 5: SUMMARY
elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_val']
    
    # RBC BFS Policy: 15% Gross-up for Self-Employed
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("GDS Ratio", f"{gds:.1f}%")
    col2.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): st.session_state.step = 4; st.rerun()
    if st.button("Finalize Submission"): st.success("Application package completed and stored.")
