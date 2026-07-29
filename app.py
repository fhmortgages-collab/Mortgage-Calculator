import streamlit as st

# --- MODERN STYLING ---
st.markdown("""
    <style>
    /* Global styles for the clean look */
    .stApp { background-color: #f8f9fa; }
    .stButton>button { border-radius: 8px; border: 1px solid #dee2e6; background: #fff; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>select {
        border-radius: 8px; border: 1px solid #dee2e6;
    }
    .css-1r6slb0 { background-color: #ffffff; border-radius: 12px; padding: 20px; border: 1px solid #eaeaea; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- POLICY MAPPING ---
REQUIREMENTS = {
    "Employed (Salaried/Hourly)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (2 years)"],
    "Self-Employed (Sole/Partnership)": ["📄 T1 General (2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"],
    "Self-Employed (Corporation)": ["📄 T1 General (Personal income only)", "📄 T4/T5A Slips"],
    "Self-Employed (Non-Standard)": ["📄 3 Years Accountant-prepared Financial Statements", "📄 Business Case"],
    "Canada Child Benefit (CCB)": ["📄 Annual CCB/QFA Notice", "📄 Birth Certificates (Children ≤ 12)"],
    "Foster Care": ["📄 Letter from Ministry", "📄 2 Years Payment History"],
    "Market Rent": ["📄 Full Appraisal (Market Rent)", "📄 Lease Agreement"],
    "Cash Savings": ["📄 90-day Bank Statements (Evidence of Funds)"],
    "Financial Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements"],
    "Equity in Land": ["📄 Property Appraisal", "📄 Title Search"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Evidence of Deposits"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'loan_val': 0.0, 'income_val': 0.0, 'debt_total': 0.0
}

# --- STEPPER UI ---
def render_stepper():
    st.write("###")
    cols = st.columns([1, 1, 1, 1, 1])
    steps = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]
    for i in range(5):
        # Stepper indicator logic
        state = "primary" if st.session_state.step == i+1 else "secondary"
        cols[i].button(str(i+1), key=f"step_{i}", type=state)
        cols[i].caption(steps[i])
    st.divider()

render_stepper()

# --- APP PAGES ---

# STEP 1: CLIENT DETAILS
if st.session_state.step == 1:
    st.header("Client Details")
    st.write("Enter information for each borrower on this application.")
    num = st.radio("Number of Borrowers", [1, 2, 3, 4], index=len(st.session_state.form['borrowers'])-1)
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}", expanded=True):
            col1, col2 = st.columns(2)
            st.session_state.form['borrowers'][i]['name'] = col1.text_input("Full Name", key=f"n{i}")
            st.session_state.form['borrowers'][i]['email'] = col2.text_input("Email Address", key=f"e{i}")
            st.session_state.form['borrowers'][i]['phone'] = col1.text_input("Phone Number", key=f"p{i}")
            st.session_state.form['borrowers'][i]['dob'] = col2.date_input("Date of Birth", key=f"d{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input("Current Address", key=f"a{i}")
            col3, col4 = st.columns(2)
            st.session_state.form['borrowers'][i]['sex'] = col3.selectbox("Gender", ["Select...", "Male", "Female"], key=f"s{i}")
            st.session_state.form['borrowers'][i]['ms'] = col4.selectbox("Marital Status", ["Select...", "Single", "Married", "Common-Law"], key=f"m{i}")
    
    if st.button("Next ➔"): st.session_state.step += 1; st.rerun()

# STEP 2: MORTGAGE
elif st.session_state.step == 2:
    st.header("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.metric("Loan Amount", f"${st.session_state.form['loan_val']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", list(REQUIREMENTS.keys())[6:])
    for src in st.session_state.form['down_sources']:
        st.write(f"**Required Docs for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)

    if st.button("⬅ Back"): st.session_state.step -= 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step += 1; st.rerun()

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.header("Income Details")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", list(REQUIREMENTS.keys())[:6])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Docs for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    if st.button("⬅ Back"): st.session_state.step -= 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step += 1; st.rerun()

# STEP 4: DEBT
elif st.session_state.step == 4:
    st.header("Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        st.write(f"### {cat}")
        val_str = st.text_input(f"Enter values (comma separated) for {cat}", key=f"inp_{cat}")
        if val_str:
            try:
                vals = [float(x.strip()) for x in val_str.split(',')]
                total = sum(vals)
                monthly = total * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (total / 12)
                st.write(f"**Sum: ${total:,.2f} | Monthly Impact: ${monthly:,.2f}**")
                total_monthly += monthly
            except: st.error("Use commas for multiple values.")
    
    st.session_state.form['debt_total'] = total_monthly
    if st.button("⬅ Back"): st.session_state.step -= 1; st.rerun()
    if st.button("Calculate Analysis ➔"): st.session_state.step += 1; st.rerun()

# STEP 5: ANALYSIS
elif st.session_state.step == 5:
    st.header("Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    adj_inc = inc * 1.15 if any("Self-Employed" in s for s in st.session_state.form['inc_sources']) else inc
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("Adjusted Income", f"${adj_inc:,.2f}")
    col2.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back"): st.session_state.step -= 1; st.rerun()
