import streamlit as st
import datetime

# --- CONFIG & STYLING ---
st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    .stButton>button { border-radius: 8px; border: 1px solid #30363d; background: #161b22; color: #ffffff; width: 100%; }
    .stButton>button:hover { border-color: #3b82f6; }
    div[data-testid="stExpander"] { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }
    input { background: #161b22 !important; border: 1px solid #30363d !important; color: white !important; border-radius: 8px !important; }
    .stMetric { background: #161b22; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# --- MASTER POLICY ENGINE ---
REQUIREMENTS = {
    "Employed (Salaried/Hourly)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed (Sole/Partnership)": ["📄 T1 General (2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"],
    "Self-Employed (Corporation)": ["📄 T1 General (Personal income only)", "📄 T4/T5A Slips"],
    "Self-Employed (Non-Standard)": ["📄 3 Years Accountant-prepared Financial Statements", "📄 Detailed Business Case"],
    "Canada Child Benefit (CCB)": ["📄 Annual CCB Notice", "📄 Birth Certificates (Children ≤ 12)"],
    "Market Rent": ["📄 Full Appraisal (Market Rent)", "📄 Lease Agreement"],
    "Cash Savings": ["📄 90-day Bank Statements (Evidence of Funds)", "📄 Verification of one-time deposits"],
    "Financial Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Gift of Equity": ["📄 Signed Gift of Equity Letter", "📄 Unconditional Purchase Agreement"],
    "Equity in Land": ["📄 Property Appraisal", "📄 Title Search (Confirmation of clear title)"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Evidence of Deposits"]
}

# --- CUMULATIVE STATE MANAGEMENT ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: 
    st.session_state.form = {
        'borrowers': [{}], 'inc_sources': {}, 'down_sources': {}, 'debts': {}, 
        'price': 0.0, 'down': 0.0, 'income_total': 0.0, 'debt_total': 0.0, 'consent': False
    }

# --- STEPPER NAVIGATION UI ---
st.title("FH Mortgage Loan Wizard")
st.caption("Residential Mortgage Application")
cols = st.columns(5)
steps = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]
for i in range(5):
    btn_type = "primary" if st.session_state.step == i+1 else "secondary"
    cols[i].button(str(i+1), disabled=(st.session_state.step != i+1), type=btn_type)
    cols[i].caption(steps[i])
st.divider()

# 1. CLIENT DETAILS (4-Borrower Support + Form 524 Consent)
if st.session_state.step == 1:
    st.header("Client Details")
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
    
    st.markdown("### Consent")
    st.info("I consent to the collection, use, and disclosure of my personal information for the purpose of processing my mortgage application. I understand that my information will be kept confidential and used solely for this purpose.")
    st.session_state.form['consent'] = st.checkbox("I acknowledge and consent to Form 524")
    
    if st.button("Next ➔"):
        if st.session_state.form['consent']: st.session_state.step = 2; st.rerun()
        else: st.error("Consent is required.")

# 2. MORTGAGE (LTV + Sources Validation)
elif st.session_state.step == 2:
    st.header("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=st.session_state.form['price'])
    down = st.number_input("Total Down Payment Requested ($)", value=st.session_state.form['down'])
    st.session_state.form['price'] = price
    st.session_state.form['down'] = down
    
    ltv = ((price - down) / price * 100) if price > 0 else 0
    st.metric("Loan Amount", f"${(price - down):,.2f}")
    st.metric("Loan-to-Value (LTV)", f"{ltv:.1f}%")
    
    st.write("### Breakdown of Sources")
    srcs = st.multiselect("Select Downpayment Sources", list(REQUIREMENTS.keys())[6:])
    sum_src = 0.0
    for src in srcs:
        amt = st.number_input(f"Amount for {src} ($)", key=f"dp_{src}")
        st.session_state.form['down_sources'][src] = amt
        sum_src += amt
        for doc in REQUIREMENTS.get(src, []): st.caption(f"✓ {doc}")
    
    if st.button("Next ➔"):
        if sum_src == down: st.session_state.step = 3; st.rerun()
        else: st.error("Error: The total downpayment amount does not match the sum of the sources.")

# 3. INCOME (Source Breakdown + Docs)
elif st.session_state.step == 3:
    st.header("Income Streams")
    total_inc = st.number_input("Total Annual Combined Income ($)", value=st.session_state.form['income_total'])
    st.session_state.form['income_total'] = total_inc
    
    srcs = st.multiselect("Select All Income Sources:", list(REQUIREMENTS.keys())[:6])
    sum_inc = 0.0
    for src in srcs:
        amt = st.number_input(f"Amount from {src} ($)", key=f"inc_{src}")
        st.session_state.form['inc_sources'][src] = amt
        sum_inc += amt
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    if st.button("Next ➔"):
        if sum_inc == total_inc: st.session_state.step = 4; st.rerun()
        else: st.error("Error: The total income does not match the sum of the sources.")

# 4. DEBT (Summation Calculator)
elif st.session_state.step == 4:
    st.header("Debt Obligations")
    cats = st.multiselect("Debt Categories:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    total_monthly = 0.0
    for cat in cats:
        val_str = st.text_input(f"Enter {cat} balance/payment (comma separated)", key=f"inp_{cat}")
        if val_str:
            vals = [float(x.strip()) for x in val_str.split(',')]
            monthly = sum(vals) * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (sum(vals) / 12)
            st.write(f"**Total: ${sum(vals):,.2f} | Monthly Impact: ${monthly:,.2f}**")
            total_monthly += monthly
    st.session_state.form['debt_total'] = total_monthly
    
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# 5. ANALYSIS (Policy Underwriting Logic)
elif st.session_state.step == 5:
    st.header("Underwriting Analysis")
    inc = st.session_state.form['income_total']
    loan = st.session_state.form['price'] - st.session_state.form['down']
    debts = st.session_state.form['debt_total']
    
    # Gross-up: 15% for Self-Employed categories
    se_keys = ["Self-Employed (Sole/Partnership)", "Self-Employed (Corporation)", "Self-Employed (Non-Standard)"]
    adj_inc = inc * 1.15 if any(s in st.session_state.form['inc_sources'] for s in se_keys) else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    c1, c2 = st.columns(2)
    c1.metric("Adjusted Annual Income", f"${adj_inc:,.2f}")
    c2.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("Finalize Submission"): st.success("Application successfully routed to underwriting.")
