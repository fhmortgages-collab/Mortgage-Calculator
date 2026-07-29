import streamlit as st

st.set_page_config(page_title="Mortgage Loan Wizard", layout="centered")

# --- DOCUMENT & POLICY MAPPING ---
REQUIREMENTS = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart", "📄 Accountant-prepared Financial Statements"],
    "Pension/CPP/OAS": ["📄 Pension Award Letter", "📄 T4A Statement"],
    "Rental Income": ["📄 T776 Statement of Real Estate Rentals", "📄 Current Lease Agreements"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Sale of Property": ["📄 Unconditional Sale Agreement", "📄 Statement of Adjustments"],
    "Savings": ["📄 90-day Bank Statements (Evidence of Funds)"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [], 'inc_sources': [], 'down_sources': [], 'income_val': 0.0, 'loan_val': 0.0
}

# --- WIZARD UI ---
st.title("🏠 Mortgage Loan Wizard")
st.progress(st.session_state.step / 5)

if st.session_state.step == 1:
    st.subheader("1. Client(s) Details")
    num = st.number_input("Number of Borrowers", 1, 4, len(st.session_state.form['borrowers']) or 1)
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}"):
            st.session_state.form['borrowers'][i]['name'] = st.text_input(f"Name {i+1}", key=f"n{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input(f"Address {i+1}", key=f"a{i}")
            st.session_state.form['borrowers'][i]['dob'] = st.date_input(f"DOB {i+1}", key=f"d{i}")
            st.session_state.form['borrowers'][i]['sex'] = st.selectbox(f"Sex {i+1}", ["", "Male", "Female", "Prefer not to disclose"], key=f"s{i}")
    
    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): st.session_state.step = 2; st.rerun()
    else: st.warning("Consent required.")

elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property", "RRSP"])
    
    st.write("### 📄 Down Payment Requirements")
    for src in st.session_state.form['down_sources']:
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Income Sources:", list(REQUIREMENTS.keys())[:4])
    st.session_state.form['income_val'] = st.number_input("Total Annual Income ($)", value=0.0)
    
    st.write("### 📄 Income Documentation")
    for src in st.session_state.form['inc_sources']:
        st.write(f"**For {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
        
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    st.session_state.form['debt_val'] = st.number_input("Total Monthly Debt ($)", value=0.0)
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    
    # 15% Policy Gross-up for Self-Employed
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    st.metric("Adjusted Annual Income (with Gross-up)", f"${adj_inc:,.2f}")
    st.metric("Estimated GDS Ratio", f"{gds:.1f}%")
    
    if st.button("Finalize Submission"): st.success("Application package completed.")
