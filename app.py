import streamlit as st

st.set_page_config(page_title="FH Mortgages | Loan Wizard", layout="centered")

# --- POLICY ENGINE ---
def get_policy_docs(form_data):
    docs = ["✅ Government Issued ID"]
    # Income Requirements
    if "Self-Employed" in form_data.get('inc_sources', []):
        docs.extend(["📄 T1 General (2 Years)", "📄 Notice of Assessment (NOA)", "📄 Organization Chart"])
    if "Employed (T4)" in form_data.get('inc_sources', []):
        docs.extend(["📄 Letter of Employment", "📄 Recent Pay Stubs", "📄 T4 Slips (2 Years)"])
    if "Rental Income" in form_data.get('inc_sources', []):
        docs.extend(["📄 T776 Statement of Real Estate Rentals"])
    
    # Debt/Collateral Requirements
    if "Credit Cards" in form_data.get('debt_cats', []): docs.append("📄 Credit Card Statements")
    if "Auto Loan" in form_data.get('debt_cats', []): docs.append("📄 Auto Loan Agreement/Statement")
    
    return list(set(docs))

# --- STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {
    'inc_sources': [], 'down_sources': [], 'debt_cats': [],
    'income_val': 0.0, 'loan_val': 0.0, 'debt_val': 0.0
}

# --- WIZARD UI ---
st.title("🏠 FH Mortgages Wizard")
st.progress(st.session_state.step / 5)

if st.session_state.step == 1:
    st.subheader("1. Client Details")
    st.session_state.form['name'] = st.text_input("Full Legal Name", st.session_state.form.get('name', ''))
    st.session_state.form['email'] = st.text_input("Email Address", st.session_state.form.get('email', ''))
    if st.button("Next ➔"): st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.subheader("2. Property & Down Payment")
    st.session_state.form['loan_val'] = st.number_input("Mortgage Amount ($)", value=float(st.session_state.form.get('loan_val', 0)))
    st.session_state.form['down_sources'] = st.multiselect("Source of Down Payment", 
        ["Savings", "Gift", "Sale of Property", "RRSP", "Borrowed Funds"])
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.subheader("3. Income Streams")
    st.session_state.form['inc_sources'] = st.multiselect("Select All Income Sources:", 
        ["Employed (T4)", "Self-Employed", "Pension", "Rental Income", "Support Payments"])
    st.session_state.form['income_val'] = st.number_input("Total Annual Income ($)", value=float(st.session_state.form.get('income_val', 0)))
    
    st.write("### 📄 Required Documentation")
    for doc in get_policy_docs(st.session_state.form): st.info(doc)
    
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.subheader("4. Debt Obligations")
    st.session_state.form['debt_cats'] = st.multiselect("Debt Categories:", 
        ["Credit Cards", "Line of Credit", "Auto Loan", "Installment Loan", "Support Payments"])
    st.session_state.form['debt_val'] = st.number_input("Total Monthly Debt Payments ($)", value=float(st.session_state.form.get('debt_val', 0)))
    if st.button("Calculate Analysis ➔"): st.session_state.step = 5; st.rerun()

elif st.session_state.step == 5:
    st.subheader("5. GDS/TDS Underwriting")
    # Policy Logic
    inc = st.session_state.form['income_val']
    loan = st.session_state.form['loan_val']
    debts = st.session_state.form['debt_val']
    
    # 15% Gross up for Self-Employed (if checked)
    final_inc = inc * 1.15 if "Self-Employed" in st.session_state.form['inc_sources'] else inc
    
    gds = ((loan * 0.05 / 12) + 500) / (final_inc / 12) * 100 # Standard proxy
    tds = (((loan * 0.05 / 12) + 500) + debts) / (final_inc / 12) * 100
    
    col1, col2 = st.columns(2)
    col1.metric("GDS Ratio", f"{gds:.1f}%", help="Policy limit: 32% (Max 39%)")
    col2.metric("TDS Ratio", f"{tds:.1f}%", help="Policy limit: 40% (Max 44%)")
    
    if gds <= 39 and tds <= 44:
        st.success("✅ Application falls within policy thresholds.")
    else:
        st.error("❌ Application exceeds threshold. Exception Business Case required.")
        
    if st.button("Submit Application"): st.balloons()
