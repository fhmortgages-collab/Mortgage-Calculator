import streamlit as st

st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="centered")

# --- DOCUMENT & POLICY MAPPING ---
REQUIREMENTS = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart", "📄 Accountant-prepared Financial Statements"],
    "Pension/CPP/OAS": ["📄 Pension Award Letter", "📄 T4A Statement"],
    "Rental Income": ["📄 T776 Statement of Real Estate Rentals", "📄 Current Lease Agreements"],
    "Support Payments": ["📄 Court Order / Legal Agreement", "📄 Proof of Receipt (Bank Statements)"],
    "Foster Care": ["📄 Letter from Ministry", "📄 2 Years Payment History"],
    "Canada Child Benefit": ["📄 Annual CCB/QFA Notice"],
    "Savings": ["📄 90-day Bank Statements (Evidence of Funds)"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Sale of Property": ["📄 Unconditional Sale Agreement", "📄 Statement of Adjustments"],
    "Equity in Land": ["📄 Property Appraisal", "📄 Title Search"],
    "Rent-to-Own": ["📄 Signed Lease Agreement", "📄 Market Rent Confirmation (Appraisal)"],
    "Builder Deposits": ["📄 Purchase Agreement", "📄 Evidence of Deposits"]
}

# --- STATE MANAGEMENT ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'debts': {}, 'loan_val': 0.0, 'income_val': 0.0, 'debt_total': 0.0
}

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# --- UI LOGIC ---
st.title("🏠 FH Mortgage Loan Wizard")
st.progress(st.session_state.step / 5)

# STEP 1: CLIENT DETAILS
if st.session_state.step == 1:
    st.subheader("1. Client Details")
    num = st.number_input("Number of Borrowers", 1, 4, len(st.session_state.form['borrowers']))
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1} Details"):
            st.session_state.form['borrowers'][i]['name'] = st.text_input(f"Name {i+1}", key=f"n{i}")
            st.session_state.form['borrowers'][i]['email'] = st.text_input(f"Email {i+1}", key=f"e{i}")
            st.session_state.form['borrowers'][i]['phone'] = st.text_input(f"Phone {i+1}", key=f"p{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input(f"Current Address {i+1}", key=f"a{i}")
            st.session_state.form['borrowers'][i]['dob'] = st.date_input(f"DOB {i+1}", key=f"d{i}")
            st.session_state.form['borrowers'][i]['sex'] = st.selectbox(f"Gender {i+1}", ["", "Male", "Female", "Prefer not to disclose"], key=f"s{i}")
            st.session_state.form['borrowers'][i]['ms'] = st.selectbox(f"Marital Status {i+1}", ["", "Single", "Married", "Common-Law"], key=f"ms{i}")
    
    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): next_step(); st.rerun()

# STEP 2: MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan_val']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property", "Equity in Land", "Rent-to-Own", "Builder Deposits"])
    for src in st.session_state.form['down_sources']:
        st.write(f"**Required Docs for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)

    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Next ➔", on_click=next_step)

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", list(REQUIREMENTS.keys())[:7])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    st.write("### 📄 Required Documentation")
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Documents for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Next ➔", on_click=next_step)

# STEP 4: DEBT CALCULATOR
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        st.write(f"### {cat}")
        val_str = st.text_input(f"Enter values for {cat} separated by comma (e.g. 400, 300)", key=f"inp_{cat}")
        if val_str:
            try:
                vals = [float(x.strip()) for x in val_str.split(',')]
                total = sum(vals)
                # RBC Policy Logic: 3% of balance for revolving debt, monthly amount for others
                monthly = total * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (total / 12)
                st.write(f"Total Balance/Amount: ${total:,.2f} | Monthly Impact: ${monthly:,.2f}")
                total_monthly += monthly
            except: st.error("Please enter numbers separated by comma.")
    
    st.session_state.form['debt_total'] = total_monthly
    st.write(f"### Total Monthly Debt: ${total_monthly:,.2f}")
    
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Calculate Analysis ➔", on_click=next_step)

# STEP 5: ANALYSIS
elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    # 15% Gross-up rule for Self-Employed per Income Policy
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("GDS Ratio", f"{gds:.1f}%")
    col2.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): prev_step(); st.rerun()
    if st.button("Finalize Submission"): st.success("Application successfully routed to underwriting.")
