import streamlit as st

st.set_page_config(page_title="FH Mortgages Loan Wizard", layout="wide")

# --- POLICY MAPPING ---
REQUIREMENTS = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart", "📄 Accountant-prepared Financial Statements"],
    "Pension/CPP/OAS": ["📄 Pension Award Letter", "📄 T4A Statement"],
    "Rental Income": ["📄 T776 Statement of Real Estate Rentals", "📄 Current Lease Agreements"],
    "Support Payments": ["📄 Court Order / Legal Agreement", "📄 Proof of Receipt (Bank Statements)"],
    "Savings": ["📄 90-day Bank Statements (Evidence of Funds)"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Sale of Property": ["📄 Unconditional Sale Agreement", "📄 Statement of Adjustments"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'debt_cats': {}, 'loan_val': 0.0, 'income_val': 0.0
}

# --- NAVIGATION ---
def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

st.title("🏠 FH Mortgages Loan Wizard")
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
            st.session_state.form['borrowers'][i]['sex'] = st.text_input(f"Gender {i+1}", key=f"g{i}")
            st.session_state.form['borrowers'][i]['ms'] = st.text_input(f"Marital Status {i+1}", key=f"m{i}")
    
    if st.button("Next ➔"): next_step(); st.rerun()

# STEP 2: MORTGAGE
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan_val']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", list(REQUIREMENTS.keys())[5:])
    for src in st.session_state.form['down_sources']:
        for doc in REQUIREMENTS.get(src, []): st.info(doc)

    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Next ➔", on_click=next_step)

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", list(REQUIREMENTS.keys())[:5])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Required Docs for {src}:**")
        for doc in REQUIREMENTS.get(src, []): st.info(doc)
    
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Next ➔", on_click=next_step)

# STEP 4: DEBT CALCULATOR
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    monthly_sum = 0.0
    for cat in cats:
        val_str = st.text_input(f"Enter {cat} amounts separated by comma (e.g. 400, 300)", key=f"inp_{cat}")
        if val_str:
            try:
                vals = [float(x.strip()) for x in val_str.split(',')]
                total = sum(vals)
                # Apply RBC policy math (3% for revolving)
                monthly = total * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (total / 12)
                st.write(f"Total: ${total:,.2f} | Monthly Impact: ${monthly:,.2f}")
                monthly_sum += monthly
            except: st.error("Please enter numbers separated by comma.")
    
    st.session_state.form['debt_total'] = monthly_sum
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Calculate Analysis ➔", on_click=next_step)

# STEP 5: ANALYSIS
elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("GDS Ratio", f"{gds:.1f}%")
    col2.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): prev_step(); st.rerun()
