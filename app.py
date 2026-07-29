import streamlit as st
import datetime

# --- CONFIGURATION & MODERN FINTECH STYLING ---
st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    .card { background: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 20px; }
    input, select { background: #161b22 !important; border: 1px solid #30363d !important; color: white !important; border-radius: 8px !important; }
    .stButton>button { border-radius: 8px; border: 1px solid #30363d; background: #161b22; color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# --- POLICY DATA ---
DOCS = {
    "Cash Savings": ["📄 90-day Bank Stmt", "📄 Source of one-time deposits"],
    "Financial Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Stmt"],
    "Equity in Property": ["📄 Unconditional P&S Agreement", "📄 Liabilities Statement"],
    "Rent-to-Own": ["📄 Signed Lease", "📄 Appraisal"],
    "Employment": ["📄 Letter of Employment", "📄 Pay Stubs", "📄 T4 Slips"],
    "Self-Employed": ["📄 T1 General (2 yrs)", "📄 NOA"],
    "Rental Income": ["📄 Appraisal", "📄 Lease Agreement"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'data' not in st.session_state: 
    st.session_state.data = {
        'borrowers': [{'name': '', 'email': '', 'phone': '', 'addr': '', 'dob': datetime.date(1990,1,1)}],
        'mortgage': {'price': 0.0, 'down': 0.0, 'sources': []},
        'income': {'total': 0.0, 'sources': []},
        'debts': {'total': 0.0},
        'consent': False
    }

# --- STEPPER UI ---
st.title("🏠 FH Mortgage Loan Wizard")
cols = st.columns(5)
steps = ["Client", "Mortgage", "Income", "Debts", "Analysis"]
for i in range(5):
    btn_type = "primary" if st.session_state.step == i+1 else "secondary"
    cols[i].button(str(i+1), disabled=(st.session_state.step != i+1), type=btn_type)
    cols[i].caption(steps[i])
st.divider()

# 1. CLIENT DETAILS
if st.session_state.step == 1:
    st.header("Client Details")
    for i in range(len(st.session_state.data['borrowers'])):
        with st.expander(f"Borrower {i+1}", expanded=True):
            st.session_state.data['borrowers'][i]['name'] = st.text_input("Full Name", key=f"n{i}")
            c1, c2 = st.columns(2)
            st.session_state.data['borrowers'][i]['email'] = c1.text_input("Email (Valid format)", key=f"e{i}")
            st.session_state.data['borrowers'][i]['phone'] = c2.text_input("Phone (10 digits)", key=f"p{i}")
            st.session_state.data['borrowers'][i]['addr'] = st.text_area("Address", key=f"a{i}")
    
    st.markdown("### Consent")
    st.write("I consent to the collection, use, and disclosure of my personal information for the purpose of processing my mortgage application. I understand that my information will be kept confidential and used solely for this purpose.")
    st.session_state.data['consent'] = st.checkbox("I acknowledge and consent")
    
    if st.button("Next ➔"):
        if st.session_state.data['consent']: st.session_state.step = 2; st.rerun()
        else: st.error("You must consent to proceed.")

# 2. DOWN PAYMENT
elif st.session_state.step == 2:
    st.header("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=st.session_state.data['mortgage']['price'])
    down = st.number_input("Total Downpayment ($)", value=st.session_state.data['mortgage']['down'])
    ltv = ((price - down) / price * 100) if price > 0 else 0
    st.metric("Loan-to-Value (LTV)", f"{ltv:.1f}%")
    
    # Dynamic Breakdown
    src_list = st.multiselect("Select Sources", list(DOCS.keys()))
    sum_src = 0.0
    for src in src_list:
        amt = st.number_input(f"Amount for {src}", key=f"dp_{src}")
        sum_src += amt
        for doc in DOCS.get(src, []): st.caption(f"✓ {doc}")
    
    if st.button("Next ➔"):
        if sum_src == down: st.session_state.step = 3; st.rerun()
        else: st.error("Error: The total downpayment amount does not match the sum of the sources.")

# 3. INCOME
elif st.session_state.step == 3:
    st.header("Income Details")
    total_inc = st.number_input("Total Annual Income ($)", value=st.session_state.data['income']['total'])
    srcs = st.multiselect("Income Sources", list(DOCS.keys()))
    
    sum_inc = 0.0
    for src in srcs:
        amt = st.number_input(f"Amount for {src}", key=f"inc_{src}")
        sum_inc += amt
        for doc in DOCS.get(src, []): st.info(doc)
        
    if st.button("Next ➔"):
        if sum_inc == total_inc: st.session_state.step = 4; st.rerun()
        else: st.error("Error: The total income does not match the sum of the sources.")

# 4. DEBTS
elif st.session_state.step == 4:
    st.header("Debt Obligations")
    cats = st.multiselect("Debt Categories:", ["Credit Cards", "Line of Credit", "Installment Loan"])
    total_monthly = 0.0
    for cat in cats:
        val = st.text_input(f"Enter {cat} balance/payment (comma separated)", key=f"inp_{cat}")
        if val:
            nums = [float(x) for x in val.split(',')]
            monthly = sum(nums) * 0.03 if cat in ["Credit Cards", "Line of Credit"] else sum(nums)/12
            total_monthly += monthly
    
    st.session_state.data['debts']['total'] = total_monthly
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

# 5. ANALYSIS
elif st.session_state.step == 5:
    st.header("Underwriting Analysis")
    inc = st.session_state.data['income_total']
    loan = st.session_state.data['mortgage']['price'] - st.session_state.data['mortgage']['down']
    debts = st.session_state.data['debts']['total']
    
    gds = ((loan * 0.05 / 12) + 500) / (inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (inc / 12) * 100
    
    st.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
