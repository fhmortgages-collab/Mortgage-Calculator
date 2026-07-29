import streamlit as st

st.set_page_config(page_title="FH Mortgages Loan Wizard", layout="centered")

# --- POLICY-BASED DOCUMENT MAPPING (FROM PROVIDED PDFs) ---
REQUIREMENTS = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart", "📄 Accountant-prepared Financial Statements"],
    "Pension": ["📄 Pension Award Letter", "📄 T4A Statement"],
    "Rental": ["📄 T776 Statement of Real Estate Rentals", "📄 Current Lease Agreements"],
    "Support": ["📄 Court Order / Legal Agreement", "📄 Proof of Receipt (Bank Statements)"],
    "Savings": ["📄 90-day Bank Statements (Evidence of Funds)"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Sale of Property": ["📄 Unconditional Sale Agreement", "📄 Statement of Adjustments"],
    "Credit Cards": ["📄 Credit Card Statements (Last 2 months)"],
    "Line of Credit": ["📄 Line of Credit Statement"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'debts': {}, 'income_val': 0.0, 'loan_val': 0.0
}

# --- NAVIGATION ---
def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

st.title("🏠 FH Mortgage Loan Wizard")
st.progress(st.session_state.step / 5)

# 1. CLIENT DETAILS
if st.session_state.step == 1:
    st.subheader("1. Client(s) Details")
    num = st.number_input("Number of Borrowers", 1, 4, len(st.session_state.form['borrowers']))
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}"):
            st.session_state.form['borrowers'][i]['name'] = st.text_input("Name", key=f"n{i}")
            st.session_state.form['borrowers'][i]['email'] = st.text_input("Email", key=f"e{i}")
            st.session_state.form['borrowers'][i]['phone'] = st.text_input("Phone", key=f"p{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input("Address", key=f"a{i}")
            st.session_state.form['borrowers'][i]['dob'] = st.date_input("Date of Birth", key=f"d{i}")
            st.session_state.form['borrowers'][i]['sex'] = st.selectbox("Gender", ["", "Male", "Female", "Decline to answer"], key=f"g{i}")
            st.session_state.form['borrowers'][i]['ms'] = st.selectbox("Marital Status", ["", "Single", "Married", "Common-Law"], key=f"ms{i}")
    
    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): next_step(); st.rerun()
    else: st.warning("Consent required.")

# 2. MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan_val']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property"])
    for src in st.session_state.form['down_sources']:
        for doc in REQUIREMENTS.get(src, []): st.info(doc)

    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Next ➔", on_click=next_step)

# 3. INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Income Sources:", list(REQUIREMENTS.keys())[:5])
    st.session_state.form['income_val'] = st.number_input("Total Annual Income ($)", value=0.0)
    
    st.write("### 📄 Required Documentation")
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Documents for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Next ➔", on_click=next_step)

# 4. DEBT CALCULATOR
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly_debt = 0.0
    for cat in cats:
        val = st.number_input(f"Balance/Payment for {cat} ($)", key=cat)
        # Policy: 3% of balance for Revolving, Full payment for Loans
        monthly = val * 0.03 if cat in ["Credit Cards", "Line of Credit"] else val
        st.caption(f"Estimated Monthly Obligation for {cat}: ${monthly:,.2f}")
        total_monthly_debt += monthly
    
    st.session_state.form['debt_val'] = total_monthly_debt
    st.write(f"### Total Monthly Debt: ${total_monthly_debt:,.2f}")
    
    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Calculate Analysis ➔", on_click=next_step)

# 5. ANALYSIS
elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_val']
    
    # 15% Policy Gross-up for Self-Employed
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    st.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): prev_step(); st.rerun()
    if st.button("Finalize Submission"): st.success("Package sent to underwriting.")
