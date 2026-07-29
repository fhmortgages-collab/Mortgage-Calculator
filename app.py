import streamlit as st
import datetime

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="FH Mortgage Loan Wizard - Final", layout="wide")

# --- CUSTOM CSS FOR EXACT UI MATCH ---
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    .stButton>button { border-radius: 8px; border: 1px solid #30363d; background: #161b22; color: #ffffff; }
    div[data-testid="stExpander"] { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }
    input { background: #161b22 !important; border: 1px solid #30363d !important; color: white !important; }
    .stMetric { background: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
    .css-1r6slb0 { background-color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# --- POLICY-BASED DOCUMENT MAPPING ---
REQUIREMENTS = {
    "Employed (Salaried/Hourly)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (2 years)"],
    "Self-Employed (Sole/Partnership)": ["📄 T1 General (2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"],
    "Self-Employed (Corporation)": ["📄 T1 General (Personal income only)", "📄 T4/T5A Slips"],
    "Self-Employed (Non-Standard)": ["📄 3 Years Accountant-prepared Financial Statements", "📄 Business Case"],
    "Canada Child Benefit (CCB)": ["📄 Annual CCB Notice", "📄 Birth Certificates (Children ≤ 12)"],
    "Foster Care": ["📄 Letter from Ministry", "📄 2 Years Payment History"],
    "Market Rent": ["📄 Full Appraisal (Market Rent)", "📄 Lease Agreement"],
    "Cash Savings": ["📄 90-day Bank Statements (Evidence of Funds)"],
    "Financial Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Gift of Equity": ["📄 Signed Gift of Equity Letter", "📄 Unconditional Purchase Agreement"],
    "Equity in Land": ["📄 Property Appraisal", "📄 Title Search (Confirmation of clear title)"],
    "Rent-to-Own": ["📄 Signed Lease Agreement", "📄 Market Rent Confirmation (Appraisal)"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Evidence of Deposits"]
}

# --- STATE MANAGEMENT ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': {}, 'debts': {}, 'loan_val': 0.0, 'income_val': 0.0, 'debt_total': 0.0
}

# --- UI NAVIGATION (STEPPER) ---
st.title("🏠 FH Mortgage Loan Wizard")
cols = st.columns(5)
steps = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]
for i in range(5):
    # Highlight current step
    btn_type = "primary" if st.session_state.step == i+1 else "secondary"
    cols[i].button(str(i+1), disabled=(st.session_state.step != i+1), type=btn_type)
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
            st.session_state.form['borrowers'][i]['email'] = col2.text_input("Email", key=f"e{i}")
            st.session_state.form['borrowers'][i]['phone'] = col1.text_input("Phone", key=f"p{i}")
            st.session_state.form['borrowers'][i]['dob'] = col2.date_input("Date of Birth", key=f"d{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input("Address", key=f"a{i}")
            col3, col4 = st.columns(2)
            st.session_state.form['borrowers'][i]['sex'] = col3.selectbox("Gender", ["Male", "Female"], key=f"s{i}")
            st.session_state.form['borrowers'][i]['ms'] = col4.selectbox("Marital Status", ["Single", "Married"], key=f"m{i}")
    
    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): st.session_state.step = 2; st.rerun()

# 2. MORTGAGE
elif st.session_state.step == 2:
    st.header("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.metric("Loan Amount", f"${st.session_state.form['loan_val']:,.2f}")
    
    st.write("### Down Payment Sources")
    srcs = st.multiselect("Select all sources:", list(DOCS.keys())[7:])
    for src in srcs:
        st.session_state.form['down_sources'][src] = st.number_input(f"Amount ($) for {src}", key=f"dp_{src}")
        for doc in DOCS.get(src, []): st.info(doc)

    if st.button("⬅ Back"): st.session_state.step = 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# 3. INCOME
elif st.session_state.step == 3:
    st.header("Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", list(DOCS.keys())[:7])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Required Docs for {src}:**")
        for doc in DOCS.get(src, []): st.info(doc)
    
    if st.button("⬅ Back"): st.session_state.step = 2; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# 4. DEBTS
elif st.session_state.step == 4:
    st.header("Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        st.write(f"### {cat}")
        val_str = st.text_input(f"Enter {cat} balance/payment amounts (comma separated)", key=f"inp_{cat}")
        if val_str:
            try:
                vals = [float(x.strip()) for x in val_str.split(',')]
                total = sum(vals)
                # Policy Math: 3% for revolving, 100% of payment for others
                monthly = total * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (total / 12)
                st.write(f"**Total: ${total:,.2f} | Monthly Impact: ${monthly:,.2f}**")
                total_monthly += monthly
            except: st.error("Please enter numbers separated by comma.")
    
    st.session_state.form['debt_total'] = total_monthly
    st.write(f"### Total Monthly Debt Impact: ${total_monthly:,.2f}")
    
    if st.button("⬅ Back"): st.session_state.step = 3; st.rerun()
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# 5. ANALYSIS
elif st.session_state.step == 5:
    st.header("Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    # 15% Policy Gross-up for Self-Employed categories
    self_emp = ["Self-Employed (Sole/Partnership)", "Self-Employed (Corporation)", "Self-Employed (Non-Standard)"]
    adj_inc = inc * 1.15 if any(s in st.session_state.form['inc_sources'] for s in self_emp) else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("Adjusted Annual Income", f"${adj_inc:,.2f}")
    col2.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): st.session_state.step = 4; st.rerun()
    if st.button("Finalize Submission"): st.success("Application successfully routed to underwriting.")
