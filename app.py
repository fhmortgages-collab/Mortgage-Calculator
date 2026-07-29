import streamlit as st

st.set_page_config(page_title="Mortgage Loan Wizard", layout="centered")

# --- POLICY DEFINITIONS ---
DOCS_MAP = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart", "📄 Accountant-prepared Financial Statements"],
    "Pension": ["📄 Pension Award Letter", "📄 T4A/T4AP Statement"],
    "Rental": ["📄 T776 Statement of Real Estate Rentals", "📄 Current Lease Agreements"],
    "Support": ["📄 Court Order / Legal Agreement", "📄 Proof of Receipt (Bank Statements)"],
    "Savings": ["📄 90-day Bank Statements (Evidence of Funds)"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Bank Statements (Evidence of Funds)"],
    "Sale of Property": ["📄 Unconditional Sale Agreement", "📄 Statement of Adjustments"]
}

# --- STATE INITIALIZATION ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'debts': [], 'loan': 0.0, 'income': 0.0
}

# --- NAVIGATION CONTROLS ---
def next_step(): st.session_state.step += 1
def prev_step(): st.session_state.step -= 1

# --- WIZARD UI ---
st.title("🏠 FH Mortgage Loan Wizard")
st.progress(st.session_state.step / 5)

# STEP 1: CLIENT DETAILS
if st.session_state.step == 1:
    st.subheader("1. Client(s) Details")
    num = st.number_input("Number of Borrowers", 1, 4, len(st.session_state.form['borrowers']))
    if len(st.session_state.form['borrowers']) != num: st.session_state.form['borrowers'] = [{} for _ in range(num)]
    
    for i in range(num):
        with st.expander(f"Borrower {i+1}"):
            st.session_state.form['borrowers'][i]['name'] = st.text_input(f"Name {i+1}", key=f"n{i}")
            st.session_state.form['borrowers'][i]['email'] = st.text_input(f"Email {i+1}", key=f"e{i}")
            st.session_state.form['borrowers'][i]['phone'] = st.text_input(f"Phone {i+1}", key=f"p{i}")
            st.session_state.form['borrowers'][i]['dob'] = st.date_input(f"DOB {i+1}", key=f"d{i}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input(f"Address {i+1}", key=f"add{i}")
            st.session_state.form['borrowers'][i]['sex'] = st.text_input(f"Gender {i+1}", key=f"gen{i}")
            st.session_state.form['borrowers'][i]['ms'] = st.text_input(f"Marital Status {i+1}", key=f"ms{i}")
    
    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): next_step(); st.rerun()

# STEP 2: MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property"])
    for src in st.session_state.form['down_sources']:
        for doc in DOCS_MAP.get(src, []): st.info(doc)

    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Next ➔", on_click=next_step)

# STEP 3: INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Income Sources:", list(DOCS_MAP.keys())[:5])
    st.session_state.form['income'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Docs for {src}:**")
        for doc in DOCS_MAP.get(src, []): st.info(doc)
    
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Next ➔", on_click=next_step)

# STEP 4: DEBTS
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    cats = st.multiselect("Select Debt Categories:", ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    st.session_state.form['debts'] = {}
    for cat in cats:
        val = st.number_input(f"Balance for {cat} ($)", key=cat)
        # Policy: 3% for CC/LOC, Monthly payment for Loans
        st.session_state.form['debts'][cat] = val * 0.03 if cat in ["Credit Cards", "Line of Credit"] else val
    
    col1, col2 = st.columns(2)
    with col1: st.button("⬅ Back", on_click=prev_step)
    with col2: st.button("Calculate Analysis ➔", on_click=next_step)

# STEP 5: ANALYSIS
elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    inc = st.session_state.form['income']
    loan = st.session_state.form['loan']
    debts = sum(st.session_state.form['debts'].values())
    
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    st.metric("GDS Ratio", f"{gds:.1f}%")
    st.metric("TDS Ratio", f"{tds:.1f}%")
    
    st.button("⬅ Back to Debts", on_click=prev_step)
    
