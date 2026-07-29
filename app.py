import streamlit as st

st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

# --- CUSTOM CSS FOR UI MATCH ---
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    div[data-testid="stExpander"] { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }
    input { background: #161b22 !important; border: 1px solid #30363d !important; color: white !important; }
    .stMetric { background: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# --- POLICY DATA ---
DOCS = {
    "Employed (Salaried/Hourly)": ["📄 Letter of Employment", "📄 Pay Stubs", "📄 T4 Slips (2 yrs)"],
    "Self-Employed (Sole/Partnership)": ["📄 T1 General (2 yrs)", "📄 NOA", "📄 Org Chart"],
    "Self-Employed (Corporation)": ["📄 T1 General (Personal income)", "📄 T4/T5A Slips"],
    "Self-Employed (Non-Standard)": ["📄 3 Yr Accountant Financials", "📄 Business Case"],
    "Canada Child Benefit (CCB)": ["📄 Annual CCB Notice", "📄 Birth Certs (≤12 yrs)"],
    "Foster Care": ["📄 Letter from Ministry", "📄 2 Yr History"],
    "Market Rent": ["📄 Appraisal", "📄 Lease"],
    "Cash Savings": ["📄 90-day Bank Stmt"],
    "Financial Gift": ["📄 Gift Letter", "📄 Donor Bank Stmt"],
    "Equity in Land": ["📄 Property Appraisal", "📄 Title Search"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Proof of Deposit"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'loan_val': 0.0, 'income_val': 0.0, 'debt_total': 0.0
}

# --- STEPPER UI ---
cols = st.columns(5)
steps = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]
for i in range(5):
    cols[i].button(str(i+1), disabled=(st.session_state.step != i+1))
    cols[i].caption(steps[i])
st.divider()

# 1. CLIENT DETAILS
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
            st.session_state.form['borrowers'][i]['sex'] = col3.selectbox("Gender", ["Male", "Female"], key=f"s{i}")
            st.session_state.form['borrowers'][i]['ms'] = col4.selectbox("Marital Status", ["Single", "Married"], key=f"m{i}")
    
    if st.button("Next ➔"): st.session_state.step = 2; st.rerun()

# 2. MORTGAGE
elif st.session_state.step == 2:
    st.header("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.metric("Loan Amount", f"${st.session_state.form['loan_val']:,.2f}")
    
    srcs = st.multiselect("Source of Down Payment", list(DOCS.keys())[7:])
    for src in srcs:
        for doc in DOCS.get(src, []): st.info(doc)

    if st.button("⬅ Back"): st.session_state.step = 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# 3. INCOME
elif st.session_state.step == 3:
    st.header("Income Streams")
    srcs = st.multiselect("Select All Income Sources:", list(DOCS.keys())[:7])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in srcs:
        st.write(f"**Docs for {src}:**")
        for doc in DOCS.get(src, []): st.info(doc)
    
    if st.button("⬅ Back"): st.session_state.step = 2; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# 4. DEBTS
elif st.session_state.step == 4:
    st.header("Debt Obligations")
    cats = st.multiselect("Debt Categories:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        val_str = st.text_input(f"Enter values for {cat} (comma separated)", key=f"inp_{cat}")
        if val_str:
            try:
                vals = [float(x.strip()) for x in val_str.split(',')]
                monthly = sum(vals) * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (sum(vals) / 12)
                st.write(f"**Total Balance: ${sum(vals):,.2f} | Monthly Impact: ${monthly:,.2f}**")
                total_monthly += monthly
            except: st.error("Use commas for multiple values.")
    
    st.session_state.form['debt_total'] = total_monthly
    if st.button("⬅ Back"): st.session_state.step = 3; st.rerun()
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# 5. ANALYSIS
elif st.session_state.step == 5:
    st.header("Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    adj_inc = inc * 1.15 if any("Self-Employed" in s for s in st.session_state.form['inc_sources'] if "Self-Employed" in s) else inc
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    c1, c2 = st.columns(2)
    c1.metric("Adjusted Annual Income", f"${adj_inc:,.2f}")
    c2.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): st.session_state.step = 4; st.rerun()
