import streamlit as st

st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="wide")

# --- INCOME & DOCUMENT MAPPING ---
# Comprehensive list based on your provided PDF requirements
INCOME_SOURCES = {
    "Employment (Salaried/Hourly)": ["📄 Letter of Employment", "📄 Recent Pay Statement (dated <60 days)", "📄 T4 Slips (Last 2 years)"],
    "Variable Income (Overtime/Bonus)": ["📄 Recent Pay Statement (w/ YTD)", "📄 T4 Slips (Last 2 years)", "📄 Business case for stability"],
    "Self-Employed (Sole/Partnership)": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"],
    "Self-Employed (Corporation)": ["📄 T1 General (Personally declared income)", "📄 T4 or T5A for Salary/Dividends"],
    "Self-Employed (Non-Standard)": ["📄 Accountant-prepared Financial Statements (3 years)", "📄 Business Case"],
    "CCB / QFA Income": ["📄 Most recent annual CCB/QFA notice", "📄 Birth certificates for children (12 or younger)"],
    "Foster Care Income": ["📄 Letter from Ministry", "📄 2 years payment history"],
    "Medical/Specialized Practitioner": ["📄 Refer to FPHE45-1-EN program requirements"],
    "Market Rent (Owner-Occupied)": ["📄 Full Appraisal (showing market rent)"],
    "Foreign/Newcomer Income": ["📄 Refer to Newcomer/Wealth Accumulator Policies"]
}

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_data': {}, 'loan_val': 0.0, 'debt_total': 0.0
}

def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

st.title("🏠 FH Mortgage Loan Wizard")
st.progress(st.session_state.step / 5)

# 1. CLIENT DETAILS
if st.session_state.step == 1:
    st.subheader("1. Client Details")
    num = st.number_input("Number of Borrowers", 1, 4, len(st.session_state.form['borrowers']))
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}"):
            st.session_state.form['borrowers'][i]['name'] = st.text_input("Name", key=f"n{i}")
            st.session_state.form['borrowers'][i]['email'] = st.text_input("Email", key=f"e{i}")
            st.session_state.form['borrowers'][i]['phone'] = st.text_input("Phone", key=f"ph{i}")
            st.session_state.form['borrowers'][i]['dob'] = st.date_input("DOB", key=f"d{i}")
            st.session_state.form['borrowers'][i]['sex'] = st.selectbox("Gender", ["Male", "Female", "Other"], key=f"s{i}")
            st.session_state.form['borrowers'][i]['ms'] = st.selectbox("Marital Status", ["Single", "Married", "Common-Law"], key=f"m{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input("Address", key=f"addr{i}")

    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): next_step(); st.rerun()

# 2. MORTGAGE
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan_val']:,.2f}")
    
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Next ➔", on_click=next_step)

# 3. INCOME ENGINE
elif st.session_state.step == 3:
    st.subheader("3. Income Sources & Documentation")
    sources = st.multiselect("Select All Income Sources:", list(INCOME_SOURCES.keys()))
    
    total_income = 0.0
    for src in sources:
        st.write(f"--- **{src}** ---")
        for doc in INCOME_SOURCES[src]: st.info(doc)
        
        # Capture income per source to handle Self-Employed Gross-up
        amount = st.number_input(f"Annual Income from {src} ($)", key=f"inc_{src}")
        st.session_state.form['inc_data'][src] = amount
        total_income += amount

    st.session_state.form['income_val'] = total_income
    
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Next ➔", on_click=next_step)

# 4. DEBT CALCULATOR
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    cats = st.multiselect("Select Debt Types:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    
    total_monthly = 0.0
    for cat in cats:
        st.write(f"### {cat}")
        val_str = st.text_input(f"Enter {cat} payment/balance values (comma separated)", key=f"inp_{cat}")
        if val_str:
            try:
                vals = [float(x.strip()) for x in val_str.split(',')]
                total = sum(vals)
                monthly = total * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (total / 12)
                st.write(f"Total: ${total:,.2f} | Monthly Impact: ${monthly:,.2f}")
                total_monthly += monthly
            except: st.error("Please enter numbers separated by comma.")
    
    st.session_state.form['debt_total'] = total_monthly
    st.write(f"### Total Monthly Debt: ${total_monthly:,.2f}")
    
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Calculate Analysis ➔", on_click=next_step)

# 5. ANALYSIS
elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    # 15% Policy Gross-up for Self-Employed Categories
    self_emp_cats = ["Self-Employed (Sole/Partnership)", "Self-Employed (Corporation)", "Self-Employed (Non-Standard)"]
    is_self_emp = any(s in st.session_state.form['inc_sources'] for s in self_emp_cats)
    
    adj_inc = inc * 1.15 if is_self_emp else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    st.metric("Adjusted Annual Income", f"${adj_inc:,.2f}")
    st.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back to Debts"): prev_step(); st.rerun()
    if st.button("Finalize Submission"): st.success("Application successfully routed to FH Mortgages.")
