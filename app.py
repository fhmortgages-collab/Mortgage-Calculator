import streamlit as st

st.set_page_config(page_title="FH Mortgage Loan Wizard", layout="wide")

# --- DOCUMENT & CALC MAPPING ---
DOCS = {
    "Employed (T4)": ["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (Last 2 years)"],
    "Self-Employed": ["📄 T1 General (Last 2 years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"],
    "Pension/CPP/OAS": ["📄 Pension Award Letter", "📄 T4A/T4AP Statement"],
    "Rental Income": ["📄 T776 Statement of Real Estate Rentals", "📄 Current Lease Agreements"],
    "Savings": ["📄 90-day Bank Statements (Evidence of Funds)"],
    "Gift": ["📄 Signed Gift Letter", "📄 Donor Financials"],
    "Sale of Property": ["📄 Unconditional Sale Agreement"]
}

DEBT_TYPES = ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"]

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'borrowers': [{}], 'inc_sources': [], 'down_sources': [], 'debts': {}, 'income_val': 0.0, 'loan_val': 0.0
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
            st.session_state.form['borrowers'][i]['name'] = st.text_input(f"Name {i+1}")
            st.session_state.form['borrowers'][i]['email'] = st.text_input(f"Email {i+1}")
            st.session_state.form['borrowers'][i]['phone'] = st.text_input(f"Phone {i+1}")
            st.session_state.form['borrowers'][i]['addr'] = st.text_input(f"Current Address {i+1}")
            st.session_state.form['borrowers'][i]['dob'] = st.date_input(f"DOB {i+1}")
            st.session_state.form['borrowers'][i]['sex'] = st.text_input(f"Gender {i+1}")
            st.session_state.form['borrowers'][i]['ms'] = st.text_input(f"Marital Status {i+1}")
    
    if st.checkbox("I acknowledge the Consent Form 524"):
        if st.button("Next ➔"): next_step(); st.rerun()

# 2. MORTGAGE DETAILS
elif st.session_state.step == 2:
    st.subheader("2. Mortgage Details")
    price = st.number_input("Purchase Price ($)", value=0.0)
    down = st.number_input("Down Payment ($)", value=0.0)
    st.session_state.form['loan_val'] = price - down
    st.info(f"Calculated Loan Amount: ${st.session_state.form['loan_val']:,.2f}")
    
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property"])
    for src in st.session_state.form['down_sources']:
        for doc in DOCS.get(src, []): st.info(doc)

    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Next ➔", on_click=next_step)

# 3. INCOME
elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", list(DOCS.keys())[:5])
    st.session_state.form['income_val'] = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    for src in st.session_state.form['inc_sources']:
        st.write(f"**Required Docs for {src}:**")
        for doc in DOCS.get(src, []): st.info(doc)
    
    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Next ➔", on_click=next_step)

# 4. DEBT CALCULATOR
elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    cats = st.multiselect("Select Debt Types:", DEBT_TYPES)
    total_monthly = 0.0
    
    for cat in cats:
        st.write(f"### {cat}")
        vals = st.text_input(f"Enter values separated by commas (e.g. 400, 300) for {cat}", key=f"inp_{cat}")
        # Calculator logic
        if vals:
            try:
                nums = [float(x.strip()) for x in vals.split(",")]
                total_cat = sum(nums)
                monthly = total_cat * 0.03 if cat in ["Credit Cards", "Line of Credit"] else (total_cat / 12)
                st.write(f"Sum: ${total_cat:,.2f} | Monthly Impact: ${monthly:,.2f}")
                total_monthly += monthly
            except: st.error("Please enter numbers separated by commas.")
    
    st.session_state.form['debt_total'] = total_monthly
    c1, c2 = st.columns(2)
    with c1: st.button("⬅ Back", on_click=prev_step)
    with c2: st.button("Calculate Analysis ➔", on_click=next_step)

# 5. UNDERWRITING
elif st.session_state.step == 5:
    st.subheader("5. GDS/TDS Policy Analysis")
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_total']
    
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    gds = ((loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((loan * 0.05 / 12) + 500) + debts) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("GDS Ratio", f"{gds:.1f}%")
    col2.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("⬅ Back"): prev_step(); st.rerun()
