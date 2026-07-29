import streamlit as st

st.set_page_config(page_title="Mortgage Loan Wizard", layout="centered")

# --- INITIALIZE STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'num_borrowers' not in st.session_state: st.session_state.num_borrowers = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': {}, 'inc_sources': [], 'down_sources': [], 'debt_cats': [],
    'income_val': 0.0, 'loan_val': 0.0, 'debt_val': 0.0
}

# --- POLICY-DRIVEN DOCUMENT ENGINE ---
def get_policy_docs(form):
    docs = ["✅ Government Issued ID (All Borrowers)", "✅ Credit Bureau Consent (Form 524)"]
    
    # Income Docs based on Employment/Income Guide
    sources = form.get('inc_sources', [])
    if "Self-Employed" in sources: docs.extend(["📄 T1 General / POI (2 Years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"])
    if "Employed (T4)" in sources: docs.extend(["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (2 Years)"])
    if "Rental Income" in sources: docs.append("📄 T776 Statement of Real Estate Rentals")
    if "Pension/CPP/OAS" in sources: docs.append("📄 T4A/T4AP Statement")
    
    # Down Payment Docs (FPHE1 Policy)
    if "Gift" in form.get('down_sources', []): docs.append("📄 Signed Gift Letter & Donor Financials")
    
    # Debt/Collateral (FPHE1 Policy)
    if "Credit Cards" in form.get('debt_cats', []): docs.append("📄 Credit Card Statements")
    
    return list(set(docs))

# --- UI LOGIC ---
st.title("🏠 Mortgage Loan Wizard")
st.progress(st.session_state.step / 5)

# Step 1: Borrower Details (Dynamic)
if st.session_state.step == 1:
    st.subheader("1. Borrower Information")
    st.session_state.num_borrowers = st.number_input("Number of Borrowers", 1, 4, st.session_state.num_borrowers)
    for i in range(st.session_state.num_borrowers):
        with st.expander(f"Borrower {i+1} Details"):
            st.session_state.form['borrowers'][i] = {
                'name': st.text_input(f"Name {i+1}", key=f"n{i}"),
                'dob': st.date_input(f"DOB {i+1}", key=f"d{i}"),
                'sex': st.selectbox(f"Sex {i+1}", ["", "Decline to answer", "Male", "Female"], key=f"s{i}"),
                'ms': st.selectbox(f"Marital Status {i+1}", ["", "Single", "Married", "Common-Law", "Divorced"], key=f"m{i}")
            }
    if st.checkbox("I acknowledge and agree to the Consent Form 524"):
        if st.button("Next ➔"): st.session_state.step = 2; st.rerun()
    else: st.warning("You must agree to the Consent Form to proceed.")

# Step 2: Loan Details
elif st.session_state.step == 2:
    st.subheader("2. Property & Down Payment")
    st.session_state.form['loan_val'] = st.number_input("Mortgage Amount ($)", value=0.0)
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property", "RRSP"])
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 1; st.rerun()
    with col2: 
        if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# Step 3: Income
elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", 
        ["Employed (T4)", "Self-Employed", "Pension/CPP/OAS", "Rental Income", "Support Payments"])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    st.write("### 📄 Required Documentation")
    for doc in get_policy_docs(st.session_state.form): st.info(doc)
    
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 2; st.rerun()
    with col2: 
        if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# Step 4: Debts
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    st.session_state.form['debt_cats'] = st.multiselect("Debt Categories:", 
        ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    st.session_state.form['debt_val'] = st.number_input("Total Monthly Debt Obligations ($)", value=0.0)
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 3; st.rerun()
    with col2: 
        if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# Step 5: Underwriting
elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_val']
    
    # 15% Self-Employed Gross-up per Policy
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    st.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): st.session_state.step = 4; st.rerun()
    if st.button("Finalize Submission"): st.success("Application package completed and stored.")
