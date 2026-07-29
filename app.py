import streamlit as st

st.set_page_config(page_title="FH Mortgages | Loan Wizard", layout="centered")

# --- POLICY DEFINITIONS ---
DEBT_TYPES = {
    "Credit Cards": {"calc": "3% of balance"},
    "Line of Credit": {"calc": "3% of balance"},
    "Auto Loan": {"calc": "Monthly payment amount"},
    "Installment Loan": {"calc": "Monthly payment amount"},
    "Support Payments": {"calc": "Monthly payment amount"}
}

REQUIREMENTS = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"],
    "Rental Income": ["📄 T776 Statement of Real Estate Rentals"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements"],
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [], 'inc_sources': [], 'down_sources': [], 'debts': [],
    'income_val': 0.0, 'loan_val': 0.0
}

# --- WIZARD UI ---
st.title("🏠 Mortgage Loan Wizard")
st.progress(st.session_state.step / 5)

# STEP 1: BORROWER DETAILS
if st.session_state.step == 1:
    st.subheader("1. Client Details & Consent")
    num = st.number_input("Number of Borrowers", 1, 4, len(st.session_state.form['borrowers']) or 1)
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}"):
            st.session_state.form['borrowers'][i] = {
                'name': st.text_input(f"Full Name {i+1}", key=f"n{i}"),
                'addr': st.text_input(f"Current Address {i+1}", key=f"a{i}"),
                'dob': st.date_input(f"DOB {i+1}", key=f"d{i}"),
                'sex': st.selectbox(f"Gender {i+1}", ["", "Male", "Female", "Other"], key=f"s{i}"),
                'ms': st.selectbox(f"Marital Status {i+1}", ["", "Single", "Married", "Common-Law"], key=f"m{i}")
            }
    
    if st.checkbox("I acknowledge the Consent Form 524 (Mandatory)"):
        if st.button("Next ➔"): st.session_state.step = 2; st.rerun()
    else: st.warning("Consent Form 524 acknowledgment required to proceed.")

# STEP 2: MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property"])
    
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", ["Employed (T4)", "Self-Employed", "Rental Income"])
    st.session_state.form['income_val'] = st.number_input("Total Annual Combined Income ($)", value=0.0)
    
    st.write("### 📄 Required Documentation")
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Documents for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# STEP 4: DEBT ENGINE
elif st.session_state.step == 4:
    st.subheader("4. Current Debt Obligations")
    st.write("Please list all active debts based on policy.")
    
    selected_debts = st.multiselect("Debt Categories:", list(DEBT_TYPES.keys()))
    debt_sum = 0.0
    
    for d in selected_debts:
        st.write(f"**{d}**")
        st.caption(f"Policy Calculation: {DEBT_TYPES[d]['calc']}")
        val = st.number_input(f"Monthly payment amount for {d} ($)", key=f"debt_{d}")
        debt_sum += val
        
    st.session_state.form['debt_total'] = debt_sum
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# STEP 5: UNDERWRITING ANALYSIS
elif st.session_state.step == 5:
    st.subheader("5. GDS/TDS Policy Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    # 15% Policy Gross-up for Self-Employed per Income Guide
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    st.metric("GDS Ratio", f"{gds:.1f}%", help="Threshold: 32%")
    st.metric("TDS Ratio", f"{tds:.1f}%", help="Threshold: 40%")
    
    if tds > 40:
        st.error("❌ TDS exceeds policy threshold. Business case/Mitigation required.")
    else:
        st.success("✅ Application falls within policy thresholds.")
        
