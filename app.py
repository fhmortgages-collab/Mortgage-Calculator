import streamlit as st

st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

# --- POLICY MAPPING ---
DOCS_MAP = {
    "Cash Savings/Investments": ["📄 Statements (RBC or External)", "📄 Minimum 90-day history", "📄 Verification of original source for one-time deposits"],
    "Financial Gift": ["📄 RBC Financial Gift Letter", "📄 Donor proof of funds (Bank stmt or confirmation letter)"],
    "Financial Gift (Foreign)": ["📄 Signed Gift Letter", "📄 Origin of funds/Accumulation notes", "📄 Confirmation funds on deposit in Canada"],
    "Gift of Equity": ["📄 Signed Gift of Equity Letter", "📄 Unconditional Purchase Agreement"],
    "Equity in Existing Property": ["📄 Signed unconditional Purchase/Sale Agreement", "📄 Equity calculation breakdown", "📄 Bridge financing (if applicable)"],
    "Equity in Land": ["📄 Property Appraisal (Land)", "📄 Lawyer confirmation of clear title"],
    "Rent-to-Own": ["📄 Signed Lease Agreement", "📄 Market rent confirmation (RBC-approved appraiser)"],
    "Personal Credit Facility": ["📄 Verification of ownership", "📄 Confirmation of sufficient available funds"],
    "Existing Unsecured Facility": ["📄 Credit Score confirmation (A/B only)", "📄 Payment history verification"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Evidence of Deposits"],
    "Affordable Housing/First Nation": ["📄 Grant/Program Approval Letter", "📄 Manual review by CAC required"]
}

INCOME_MAP = {
    "Employed (Salaried/Hourly)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Variable Income (Overtime/Bonus)": ["📄 Pay Statement (YTD)", "📄 2 Years T4 Slips"],
    "Self-Employed (Sole/Partnership)": ["📄 T1 General (2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"],
    "Self-Employed (Corporation)": ["📄 T1 General (Personal income only)", "📄 T4/T5A Slips"],
    "Self-Employed (Non-Standard)": ["📄 3 Years Accountant-prepared Financial Statements", "📄 Business Case"],
    "Canada Child Benefit (CCB)": ["📄 Annual CCB/QFA Notice", "📄 Birth Certificates (Children ≤ 12)"],
    "Foster Care": ["📄 Letter from Ministry", "📄 2 Years Payment History"],
    "Medical/Dental Practitioners": ["📄 Program-specific Certification"],
    "Market Rent": ["📄 Full Appraisal (Market Rent)", "📄 Lease Agreement"],
    "Foreign/Newcomer Income": ["📄 Refer to Newcomer/Foreign Income Policy"],
    "Pension/CPP/OAS": ["📄 Pension Award Letter", "📄 T4A Statement"]
}

# --- STATE MANAGEMENT ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'debts': {}, 'loan_val': 0.0, 'income_val': 0.0, 'debt_total': 0.0
}

# --- UI NAVIGATION ---
def render_stepper():
    st.write("###")
    cols = st.columns(5)
    steps = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]
    for i, step_name in enumerate(steps):
        cols[i].button(str(i+1), disabled=(st.session_state.step != i+1))
        cols[i].caption(step_name)

render_stepper()
st.divider()

# 1. CLIENT DETAILS
if st.session_state.step == 1:
    st.subheader("Client Details")
    num = st.radio("Number of Borrowers", [1, 2, 3, 4], index=len(st.session_state.form['borrowers'])-1)
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}"):
            col1, col2 = st.columns(2)
            st.session_state.form['borrowers'][i]['name'] = col1.text_input("Full Name", key=f"n{i}")
            st.session_state.form['borrowers'][i]['email'] = col2.text_input("Email Address", key=f"e{i}")
            st.session_state.form['borrowers'][i]['phone'] = col1.text_input("Phone Number", key=f"p{i}")
            st.session_state.form['borrowers'][i]['dob'] = col2.date_input("Date of Birth", key=f"d{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input("Current Address", key=f"a{i}")
            c3, c4 = st.columns(2)
            st.session_state.form['borrowers'][i]['sex'] = c3.selectbox("Gender", ["Male", "Female", "Prefer not to disclose"], key=f"s{i}")
            st.session_state.form['borrowers'][i]['ms'] = c4.selectbox("Marital Status", ["Single", "Married", "Common-Law"], key=f"m{i}")
    
    if st.button("Next ➔"): st.session_state.step += 1; st.rerun()

# 2. MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.subheader("Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan_val']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", list(DOCS_MAP.keys()))
    for src in st.session_state.form['down_sources']:
        st.write(f"**Required Docs for {src}:**")
        for doc in DOCS_MAP.get(src, []): st.info(doc)

    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=lambda: setattr(st.session_state, 'step', 1) or st.rerun())
    with c2: st.button("Next ➔", on_click=lambda: setattr(st.session_state, 'step', 3) or st.rerun())

# 3. INCOME
elif st.session_state.step == 3:
    st.subheader("Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", list(INCOME_MAP.keys()))
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Required Docs for {src}:**")
        for doc in INCOME_MAP.get(src, []): st.info(doc)
    
    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=lambda: setattr(st.session_state, 'step', 2) or st.rerun())
    with c2: st.button("Next ➔", on_click=lambda: setattr(st.session_state, 'step', 4) or st.rerun())

# 4. DEBTS
elif st.session_state.step == 4:
    st.subheader("Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        st.write(f"### {cat}")
        val_str = st.text_input(f"Enter {cat} balance/payment amounts separated by comma (e.g. 400, 300)", key=f"inp_{cat}")
        if val_str:
            try:
                vals = [float(x.strip()) for x in val_str.split(',')]
                total = sum(vals)
                monthly = total * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (total / 12)
                st.write(f"Total: ${total:,.2f} | Monthly Impact: ${monthly:,.2f}")
                total_monthly += monthly
            except: st.error("Please enter numbers separated by comma.")
    
    st.session_state.form['debt_total'] = total_monthly
    st.write(f"### Total Monthly Debt Impact: ${total_monthly:,.2f}")
    
    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=lambda: setattr(st.session_state, 'step', 3) or st.rerun())
    with c2: st.button("Calculate Analysis ➔", on_click=lambda: setattr(st.session_state, 'step', 5) or st.rerun())

# 5. ANALYSIS
elif st.session_state.step == 5:
    st.subheader("Underwriting Analysis")
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
    
    if st.button("⬅ Back to Debts"): setattr(st.session_state, 'step', 4); st.rerun()
    if st.button("Finalize Submission"): st.success("Application successfully routed to underwriting.")
