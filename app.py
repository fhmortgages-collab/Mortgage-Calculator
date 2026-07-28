import streamlit as st

st.set_page_config(page_title="FH Mortgages | Loan Wizard", layout="centered")

# --- CSS FOR FLASHING YELLOW ---
st.markdown("""
    <style>
    .flashing-yellow-field { border: 2px solid #FBC02D !important; box-shadow: 0 0 10px #FBC02D !important; }
    .yellow-warning-text { color: #856404; background-color: #fff3cd; padding: 5px; border-radius: 5px; font-size: 0.8rem; margin-top: -10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- STATE MGMT ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form' not in st.session_state: st.session_state.form = {}

def render_field(label, key, input_type="text", options=None):
    if key not in st.session_state.form: st.session_state.form[key] = ""
    
    # Validation check
    is_missing = st.session_state.get('submit') and not st.session_state.form[key]
    
    label_text = f"{label} *" if is_missing else label
    
    if input_type == "text":
        val = st.text_input(label_text, value=st.session_state.form[key], key=f"input_{key}")
    elif input_type == "number":
        val = st.number_input(label_text, value=float(st.session_state.form[key] or 0), key=f"input_{key}")
    elif input_type == "select":
        val = st.selectbox(label_text, options, key=f"input_{key}")
    
    st.session_state.form[key] = val
    if is_missing:
        st.markdown('<div class="yellow-warning-text">⚠️ This field is required</div>', unsafe_allow_html=True)

# --- WIZARD FLOW ---
st.title("🏠 FH Mortgages Wizard")

# Step 1: Client Details
if st.session_state.step == 1:
    st.subheader("1. Client Details")
    render_field("Full Name", "name")
    render_field("Date of Birth", "dob")
    render_field("Email", "email")
    render_field("Phone", "phone")
    if st.button("Next ➔"): st.session_state.step = 2; st.rerun()

# Step 2: Loan Details
elif st.session_state.step == 2:
    st.subheader("2. Mortgage & Down Payment")
    render_field("Mortgage Amount ($)", "loan", "number")
    render_field("Down Payment ($)", "down", "number")
    render_field("Source of Down Payment", "down_source", "select", 
                 ["Savings", "Gift", "Sale of Property", "RRSP"])
    st.write("### 📄 Documents Required")
    st.info("• Purchase Agreement\n• 3 Months Bank Statements (Source of Funds)")
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

# Step 3: Income
elif st.session_state.step == 3:
    st.subheader("3. Income Details")
    inc_type = st.selectbox("Source of Income", 
        ["Employed (T4)", "Self-Employed (Sole Prop/Partnership)", "Pension/CPP/OAS", "Rental Income", "Support Payments"])
    render_field("Gross Annual Income ($)", "income", "number")
    
    st.write("### 📄 Documents Required")
    if "Employed" in inc_type: st.info("• Letter of Employment, 2 Recent Pay Stubs, T4s")
    elif "Self-Employed" in inc_type: st.info("• T1 General / NOA (Last 2 years), Organization Chart")
    elif "Pension" in inc_type: st.info("• Award Letter, 2 Years T4A")
    
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

# Step 4: Debts
elif st.session_state.step == 4:
    st.subheader("4. Current Debts")
    debt_type = st.multiselect("Select your debt types:", 
        ["Credit Cards", "Line of Credit", "Auto Loan/Lease", "Student Loan", "Spousal/Child Support"])
    render_field("Monthly Debt Total ($)", "debts", "number")
    st.write("### 📄 Documents Required")
    st.info("• Credit Report\n• Loan Statements\n• Court Orders (if Support Payments)")
    if st.button("Calculate GDS/TDS ➔"): st.session_state.step = 5; st.rerun()

# Step 5: Calculator
elif st.session_state.step == 5:
    st.subheader("5. GDS/TDS Results")
    # Calculation Logic
    income = float(st.session_state.form.get('income', 0))
    loan = float(st.session_state.form.get('loan', 0))
    debts = float(st.session_state.form.get('debts', 0))
    
    gds = ((loan * 0.05 / 12) + 400 + 100) / (income / 12) * 100 # Simplified
    tds = (((loan * 0.05 / 12) + 400 + 100) + debts) / (income / 12) * 100
    
    st.metric("GDS Ratio", f"{gds:.2f}% (Limit: 32%)")
    st.metric("TDS Ratio", f"{tds:.2f}% (Limit: 40%)")
    
    if st.button("Finalize Loan Application"):
        st.balloons()
        st.success("Application Submitted to Underwriting!")
