import streamlit as st

st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

# --- CUSTOM CSS FOR EXACT UI MATCH ---
st.markdown("""
    <style>
    /* Background and containers */
    .stApp { background-color: #0d1117; color: #ffffff; }
    .css-1r6slb0, .stApp { background-color: #0d1117; }
    
    /* Stepper Bar Styling */
    .stepper-container { display: flex; justify-content: space-between; margin-bottom: 30px; }
    .step-circle { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: #1f2937; color: #60a5fa; font-weight: bold; border: 2px solid #3b82f6; }
    
    /* Card/Cell Style */
    div[data-testid="stExpander"] { background: #161b22; border-radius: 12px; border: 1px solid #30363d; }
    input { background: #161b22 !important; border: 1px solid #30363d !important; color: white !important; border-radius: 8px !important; }
    label { color: #c9d1d9 !important; font-weight: 500 !important; }
    </style>
""", unsafe_allow_html=True)

# --- POLICY DATA ---
REQUIREMENTS = {
    "Employed (Salaried/Hourly)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (2 years)"],
    "Self-Employed (Sole/Partnership)": ["📄 T1 General (2 years)", "📄 NOA", "📄 Organization Chart"],
    "Financial Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Cash Savings": ["📄 90-day Bank Statements (Evidence of Funds)"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'loan_val': 0.0, 'income_val': 0.0, 'debt_total': 0.0
}

# --- NAVIGATION UI ---
st.markdown("## 🏠 FH Mortgage Loan Wizard")
cols = st.columns(5)
for i in range(1, 6):
    cols[i-1].button(str(i), disabled=(st.session_state.step != i), key=f"btn_{i}")
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
            st.session_state.form['borrowers'][i]['sex'] = col3.selectbox("Gender", ["Select...", "Male", "Female"], key=f"s{i}")
            st.session_state.form['borrowers'][i]['ms'] = col4.selectbox("Marital Status", ["Select...", "Single", "Married"], key=f"m{i}")
    
    if st.button("Next ➔"): st.session_state.step = 2; st.rerun()

# 2. MORTGAGE
elif st.session_state.step == 2:
    st.header("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.metric("Loan Amount", f"${st.session_state.form['loan_val']:,.2f}")
    
    srcs = st.multiselect("Source of Down Payment", list(REQUIREMENTS.keys())[-4:])
    for src in srcs:
        for doc in REQUIREMENTS.get(src, []): st.info(doc)

    if st.button("⬅ Back"): st.session_state.step = 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# 3. INCOME
elif st.session_state.step == 3:
    st.header("Income Details")
    srcs = st.multiselect("Select All Income Sources:", list(REQUIREMENTS.keys())[:6])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in srcs:
        st.write(f"**Docs for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    if st.button("⬅ Back"): st.session_state.step = 2; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# 4. DEBTS
elif st.session_state.step == 4:
    st.header("Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        val_str = st.text_input(f"Enter values for {cat} (comma separated)", key=f"inp_{cat}")
        if val_str:
            vals = [float(x.strip()) for x in val_str.split(',')]
            monthly = sum(vals) * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (sum(vals) / 12)
            st.write(f"**Total Balance: ${sum(vals):,.2f} | Monthly Impact: ${monthly:,.2f}**")
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
    
    gds = ((loan * 0.05 / 12) + 500) / (inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (inc / 12) * 100
    
    c1, c2 = st.columns(2)
    c1.metric("Income", f"${inc:,.2f}")
    c2.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): st.session_state.step = 4; st.rerun()
