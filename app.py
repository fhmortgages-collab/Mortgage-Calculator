import streamlit as st

st.set_page_config(page_title="Mortgage Loan Wizard", layout="centered")

# --- POLICY ENGINE ---
def get_unified_doc_checklist(borrowers, inc_sources, down_sources):
    docs = set(["✅ Government Issued ID", "✅ Credit Bureau Consent (Form 524)"])
    
    # Income Docs
    for src in inc_sources:
        if src == "Self-Employed": docs.update(["📄 T1 General (2 Years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"])
        if src == "Employed (T4)": docs.update(["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (2 Years)"])
        if src == "Rental Income": docs.add("📄 T776 Statement of Real Estate Rentals")
    
    # Down Payment Docs
    if "Gift" in down_sources: docs.add("📄 Signed Gift Letter")
    
    return list(docs)

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'num_borrowers' not in st.session_state: st.session_state.num_borrowers = 1
if 'borrowers' not in st.session_state: st.session_state.borrowers = {}

# --- WIZARD UI ---
st.title("🏠 Mortgage Loan Wizard")
st.progress(st.session_state.step / 5)

if st.session_state.step == 1:
    st.subheader("1. Client & Borrower Info")
    st.session_state.num_borrowers = st.number_input("How many borrowers?", 1, 4, st.session_state.num_borrowers)
    for i in range(st.session_state.num_borrowers):
        with st.expander(f"Borrower {i+1} Details"):
            st.text_input(f"Name (Borrower {i+1})", key=f"name_{i}")
            st.date_input(f"DOB (Borrower {i+1})", key=f"dob_{i}")
            st.selectbox(f"Sex (Borrower {i+1})", ["Male", "Female", "Other"], key=f"sex_{i}")
            st.selectbox(f"Marital Status (Borrower {i+1})", ["Single", "Married", "Common-Law", "Divorced", "Widowed"], key=f"ms_{i}")
    
    if st.button("Next ➔"): st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.subheader("2. Loan Details")
    loan = st.number_input("Mortgage Amount ($)", value=0.0)
    down_src = st.multiselect("Source of Down Payment", ["Savings", "Gift", "Sale of Property", "RRSP"])
    if st.button("Next ➔"): 
        st.session_state.loan = loan; st.session_state.down_sources = down_src
        st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    inc_src = st.multiselect("Select all Income Sources:", 
        ["Employed (T4)", "Self-Employed", "Pension", "Rental Income", "Support Payments"])
    total_inc = st.number_input("Total Combined Annual Income ($)", value=0.0)
    
    st.session_state.inc_sources = inc_src
    st.session_state.income_val = total_inc
    
    st.write("### 📄 Required Documentation")
    for doc in get_unified_doc_checklist(st.session_state.num_borrowers, inc_src, st.session_state.down_sources):
        st.info(doc)
        
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    monthly_debt = st.number_input("Total Monthly Debt Payments ($)", value=0.0)
    st.session_state.debt_val = monthly_debt
    if st.button("Calculate ➔"): st.session_state.step = 5; st.rerun()

elif st.session_state.step == 5:
    st.subheader("5. Underwriting Analysis")
    # Logic: Apply 15% gross-up for Self-Employed per policy
    inc = st.session_state.income_val
    adj_inc = inc * 1.15 if "Self-Employed" in st.session_state.inc_sources else inc
    
    gds = ((st.session_state.loan * 0.05 / 12) + 500) / (adj_inc / 12) * 100
    tds = (((st.session_state.loan * 0.05 / 12) + 500) + st.session_state.debt_val) / (adj_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("GDS Ratio", f"{gds:.1f}%")
    col2.metric("TDS Ratio", f"{tds:.1f}%")
    
    if st.button("Submit Application"): st.success("Underwriting package complete.")
