import streamlit as st

st.set_page_config(page_title="FH Mortgages | Loan Wizard", layout="centered")

# --- STATE MANAGEMENT ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'data' not in st.session_state: st.session_state.data = {'borrowers': {}, 'loan': {}, 'income': {}, 'debts': {}}

# --- HELPER: CONSENT FORM ---
def show_consent():
    st.markdown("### Client Consent Agreement")
    with st.expander("Read Client Agreement (Form 524)"):
        st.write("By checking the box below, you acknowledge that you have read, understood, and agreed to the collection, use, and disclosure of your personal information as outlined in the Client Agreement. You certify that the information provided is true and accurate.")
    return st.checkbox("I agree to the terms of the Client Agreement (Form 524).")

# --- UI LOGIC ---
st.title("🏠 FH Mortgages Loan Wizard")
st.progress(st.session_state.step / 5)

# STEP 1: CLIENT DETAILS (DYNAMIC)
if st.session_state.step == 1:
    st.subheader("1. Client(s) Details")
    num = st.number_input("Number of Borrowers", min_value=1, max_value=4, value=1)
    st.session_state.data['num_borrowers'] = num
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}"):
            st.session_state.data['borrowers'][i] = {
                'name': st.text_input(f"Name {i+1}", key=f"n{i}"),
                'dob': st.date_input(f"DOB {i+1}", key=f"d{i}"),
                'addr': st.text_input(f"Current Address {i+1}", key=f"a{i}"),
                'sex': st.selectbox(f"Sex {i+1}", ["", "Decline to answer", "Male", "Female"], key=f"s{i}"),
                'ms': st.selectbox(f"Marital Status {i+1}", ["", "Single", "Married", "Common-Law"], key=f"m{i}")
            }
    
    if show_consent():
        if st.button("Next ➔"): st.session_state.step = 2; st.rerun()
    else: st.warning("Please agree to the consent form to proceed.")

# STEP 2: LOAN DETAILS
elif st.session_state.step == 2:
    st.subheader("2. Loan Details")
    st.session_state.data['loan'] = {
        'amount': st.number_input("Mortgage Amount ($)"),
        'down': st.number_input("Down Payment ($)"),
        'down_src': st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property", "RRSP"])
    }
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 1; st.rerun()
    with col2: 
        if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Details")
    st.session_state.data['income'] = {
        'sources': st.multiselect("Income Categories", ["Salary/Wage", "Self-Employed", "Pension/CPP/OAS", "Rental", "Support Payments"]),
        'total': st.number_input("Total Annual Income ($)")
    }
    # Doc checklist based on policy
    if "Self-Employed" in st.session_state.data['income']['sources']:
        st.info("📄 Required: T1 General (2 years), NOA, Organization Chart")
    
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 2; st.rerun()
    with col2: 
        if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# STEP 4: DEBTS
elif st.session_state.step == 4:
    st.subheader("4. Current Debts")
    st.session_state.data['debts'] = {
        'cats': st.multiselect("Debt Categories", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"]),
        'monthly': st.number_input("Total Monthly Debt Obligations ($)")
    }
    col1, col2 = st.columns(2)
    with col1: 
        if st.button("⬅ Back"): st.session_state.step = 3; st.rerun()
    with col2: 
        if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# STEP 5: REVIEW
elif st.session_state.step == 5:
    st.subheader("5. Review & Submit")
    # Calculation Logic
    inc = st.session_state.data['income']['total']
    loan = st.session_state.data['loan']['amount']
    debts = st.session_state.data['debts']['monthly']
    
    # Policy Gross-up for Self-Employed (15% per policy)
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.data['income']['sources'] else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    st.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("Finalize Submission"):
        st.success("Application package completed and stored.")
