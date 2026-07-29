import streamlit as st

st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

# --- POLICY MAPPING ---
REQUIREMENTS = {
    "Employed (Salaried/Hourly)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (2 years)"],
    "Self-Employed (Sole/Partnership)": ["📄 T1 General (2 years)", "📄 NOA", "📄 Organization Chart"],
    "Self-Employed (Corporation)": ["📄 T1 General (Personal income only)", "📄 T4/T5A Slips"],
    "Pension/CPP/OAS": ["📄 Pension Award Letter", "📄 T4A Statement"],
    "Rental Income": ["📄 T776 Statement of Real Estate Rentals", "📄 Lease Agreements"],
    "Support Payments": ["📄 Court Order", "📄 Proof of Receipt"],
    "Savings": ["📄 90-day Bank Statements"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements"],
    "Sale of Property": ["📄 Unconditional Sale Agreement"],
    "Equity in Land": ["📄 Property Appraisal", "📄 Title Search"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Evidence of Deposits"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'debts': {}, 'loan_val': 0.0, 'income_val': 0.0, 'debt_total': 0.0
}

# --- NAVIGATION UI (STEPPER) ---
def render_stepper():
    cols = st.columns(5)
    steps = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]
    for i, step_name in enumerate(steps):
        cols[i].button(str(i+1), disabled=(st.session_state.step != i+1))
        cols[i].caption(step_name)

render_stepper()

# --- WIZARD LOGIC ---

# 1. CLIENT DETAILS
if st.session_state.step == 1:
    st.subheader("Client Details")
    st.write("Enter information for each borrower on this application.")
    num = st.radio("Number of Borrowers", [1, 2, 3, 4], index=len(st.session_state.form['borrowers'])-1)
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}"):
            c1, c2 = st.columns(2)
            st.session_state.form['borrowers'][i]['name'] = c1.text_input("Full Name", key=f"n{i}")
            st.session_state.form['borrowers'][i]['email'] = c2.text_input("Email Address", key=f"e{i}")
            st.session_state.form['borrowers'][i]['phone'] = c1.text_input("Phone Number", key=f"p{i}")
            st.session_state.form['borrowers'][i]['dob'] = c2.date_input("Date of Birth", key=f"d{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input("Current Address", key=f"a{i}")
            c3, c4 = st.columns(2)
            st.session_state.form['borrowers'][i]['sex'] = c3.selectbox("Gender", ["Male", "Female", "Other"], key=f"s{i}")
            st.session_state.form['borrowers'][i]['ms'] = c4.selectbox("Marital Status", ["Single", "Married", "Common-Law"], key=f"m{i}")
    
    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): st.session_state.step += 1; st.rerun()

# 2. MORTGAGE
elif st.session_state.step == 2:
    st.subheader("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan_val']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", list(REQUIREMENTS.keys())[7:])
    for src in st.session_state.form['down_sources']:
        for doc in REQUIREMENTS.get(src, []): st.info(doc)

    if st.button("⬅ Back"): st.session_state.step -= 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step += 1; st.rerun()

# 3. INCOME
elif st.session_state.step == 3:
    st.subheader("Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", list(REQUIREMENTS.keys())[:7])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Required Docs for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    if st.button("⬅ Back"): st.session_state.step -= 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step += 1; st.rerun()

# 4. DEBT CALCULATOR
elif st.session_state.step == 4:
    st.subheader("Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        st.write(f"### {cat}")
        val_str = st.text_input(f"Enter {cat} balance/payment amounts (comma separated)", key=f"inp_{cat}")
        if val_str:
            try:
                vals = [float(x.strip()) for x in val_str.split(',')]
                total = sum(vals)
                monthly = total * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (total / 12)
                st.write(f"**Total: ${total:,.2f} | Monthly Impact: ${monthly:,.2f}**")
                total_monthly += monthly
            except: st.error("Please enter numbers separated by comma.")
    
    st.session_state.form['debt_total'] = total_monthly
    st.write(f"### Total Monthly Debt Impact: ${total_monthly:,.2f}")
    
    if st.button("⬅ Back"): st.session_state.step -= 1; st.rerun()
    if st.button("Calculate Analysis ➔"): st.session_state.step += 1; st.rerun()

# 5. ANALYSIS
elif st.session_state.step == 5:
    st.subheader("Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    adj_inc = inc * 1.15 if any("Self-Employed" in s for s in st.session_state.form['inc_sources']) else inc
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    st.metric("Adjusted Annual Income", f"${adj_inc:,.2f}")
    st.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): st.session_state.step -= 1; st.rerun()
    if st.button("Finalize Submission"): st.success("Application successfully routed to underwriting.")
