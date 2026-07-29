import streamlit as st
import datetime

# --- UI CONFIG & MODERN FINTECH STYLING ---
st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

st.markdown("""
    <style>
    /* Modern FinTech Look */
    .stApp { background-color: #f3f4f6; }
    .main .block-container { 
        background: #ffffff; padding: 40px; border-radius: 20px; 
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); 
    }
    h1 { color: #111827; }
    .stButton>button { border-radius: 8px; border: 1px solid #e5e7eb; background: #ffffff; color: #374151; }
    .stButton>button:hover { border-color: #3b82f6; color: #3b82f6; }
    .step-active { color: #3b82f6; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- COMPREHENSIVE POLICY DATA ---
# This dictionary contains all requirements from your uploaded policy PDF.
# To extend, simply add a key and a list of strings.
POLICY_REQUIREMENTS = {
    "Employment (Salaried)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed (Sole/Corp)": ["📄 T1 General (2 years)", "📄 Notice of Assessment", "📄 Organization Chart"],
    "Financial Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Cash Savings": ["📄 90-day Bank Statements", "📄 Verification of one-time deposits"],
    "Equity in Property": ["📄 Unconditional Sale Agreement", "📄 Equity Calculation Breakdown"],
    "Equity in Land": ["📄 Property Appraisal", "📄 Title Search"],
    "Rent-to-Own": ["📄 Signed Lease Agreement", "📄 Appraisal by RBC-approved Appraiser"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Evidence of Deposits"]
}

# --- STATE INITIALIZATION ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: 
    st.session_state.form = {
        'borrowers': [{'name': '', 'email': ''}], 
        'inc_data': {}, 'dp_data': {}, 'debt_data': {}, 
        'loan_val': 0.0, 'income_total': 0.0, 'debt_total': 0.0
    }

# --- NAVIGATION STEPPER ---
st.markdown("### FH Mortgage Loan Wizard")
st.caption("Residential Mortgage Application")
cols = st.columns(5)
steps = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]
for i in range(5):
    btn_type = "primary" if st.session_state.step == i+1 else "secondary"
    cols[i].button(str(i+1), disabled=True, type=btn_type)
    cols[i].caption(steps[i])
st.divider()

# --- APP WORKFLOW ---

# STEP 1: CLIENT DETAILS
if st.session_state.step == 1:
    st.header("Client Details")
    st.write("Enter information for each borrower on this application.")
    num = st.radio("Number of Borrowers", [1, 2, 3, 4], index=len(st.session_state.form['borrowers'])-1)
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}", expanded=True):
            st.session_state.form['borrowers'][i]['name'] = st.text_input("Full Name", key=f"n{i}")
            c1, c2 = st.columns(2)
            st.session_state.form['borrowers'][i]['email'] = c1.text_input("Email Address", key=f"e{i}")
            st.session_state.form['borrowers'][i]['dob'] = c2.date_input("Date of Birth", key=f"d{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input("Current Address", key=f"a{i}")
    
    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): st.session_state.step = 2; st.rerun()

# STEP 2: MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.header("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    
    # LTV Calculation
    ltv = (st.session_state.form['loan_val'] / price * 100) if price > 0 else 0
    st.metric("Loan-to-Value (LTV)", f"{ltv:.1f}%")
    st.metric("Loan Amount", f"${st.session_state.form['loan_val']:,.2f}")
    
    st.write("### Down Payment Sources")
    sources = st.multiselect("Select all sources:", list(POLICY_REQUIREMENTS.keys())[7:])
    for src in sources:
        st.session_state.form['dp_data'][src] = st.number_input(f"Amount ($) for {src}", key=f"dp_{src}")
        with st.expander(f"Required Docs: {src}"):
            for doc in POLICY_REQUIREMENTS.get(src, []): st.caption(f"✓ {doc}")

    if st.button("⬅ Back"): st.session_state.step = 1; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.header("Income Details")
    srcs = st.multiselect("Select All Income Sources:", list(POLICY_REQUIREMENTS.keys())[:7])
    st.session_state.form['income_total'] = st.number_input("Total Annual Income ($)", value=0.0)
    
    for src in srcs:
        with st.expander(f"Required Docs for {src}"):
            for doc in POLICY_REQUIREMENTS.get(src, []): st.write(doc)
    
    if st.button("⬅ Back"): st.session_state.step = 2; st.rerun()
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# STEP 4: DEBTS
elif st.session_state.step == 4:
    st.header("Debt Obligations")
    cats = st.multiselect("Debt Categories:", ["Credit Cards", "Line of Credit", "Installment Loans", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        vals = st.text_input(f"Enter {cat} balance/payment amounts (comma separated)", key=f"inp_{cat}")
        if vals:
            try:
                nums = [float(x.strip()) for x in vals.split(',')]
                monthly = sum(nums) * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (sum(nums) / 12)
                st.write(f"**Monthly Impact for {cat}: ${monthly:,.2f}**")
                total_monthly += monthly
            except: st.error("Please enter numbers separated by commas.")
    
    st.session_state.form['debt_total'] = total_monthly
    if st.button("⬅ Back"): st.session_state.step = 3; st.rerun()
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# STEP 5: ANALYSIS
elif st.session_state.step == 5:
    st.header("Underwriting Analysis")
    inc = st.session_state.form['income_total']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    # Gross-up for self-employed
    adj_inc = inc * 1.15 if any("Self-Employed" in s for s in st.session_state.form['inc_sources']) else inc
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("Adjusted Annual Income", f"${adj_inc:,.2f}")
    col2.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back"): st.session_state.step = 4; st.rerun()
