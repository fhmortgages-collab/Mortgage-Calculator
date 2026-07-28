import streamlit as st
import datetime
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURATION ---
st.set_page_config(page_title="FH Mortgages - Loan Wizard", page_icon="🏠", layout="centered")

# --- CSS ---
st.markdown("""
    <style>
    @keyframes flash-yellow-anim {
        0% { border: 2px solid #FFFDE7; box-shadow: 0 0 0px #FFF9C4; }
        50% { border: 2px solid #FBC02D; box-shadow: 0 0 10px #FBC02D; }
        100% { border: 2px solid #FFFDE7; box-shadow: 0 0 0px #FFF9C4; }
    }
    .flashing-yellow-field { animation: flash-yellow-anim 1.5s infinite; border-radius: 5px; }
    .yellow-warning-text { color: #856404; background-color: #fff3cd; padding: 5px; border-radius: 5px; font-size: 0.8rem; margin-top: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE STATE ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'form_data' not in st.session_state: st.session_state.form_data = {}

def reset_app():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

def render_field(label, key, input_type="text"):
    val = st.session_state.form_data.get(key, "")
    is_missing = st.session_state.get('attempted_submit') and not val
    
    if input_type == "text":
        val = st.text_input(label, value=val, key=f"in_{key}")
    elif input_type == "number":
        val = st.number_input(label, value=float(val) if val else 0.0, key=f"in_{key}")
    elif input_type == "date":
        val = st.date_input(label, key=f"in_{key}")
    
    st.session_state.form_data[key] = str(val)
    if is_missing:
        st.markdown('<div class="yellow-warning-text">⚠️ This field is required to proceed</div>', unsafe_allow_html=True)
        st.markdown(f'<style>div[data-testid="stTextInput"] input[aria-label="{label}"] {{ border: 2px solid #FBC02D; }}</style>', unsafe_allow_html=True)

# --- UI ---
st.title("🏠 FH Mortgages Wizard")

if st.sidebar.button("🗑️ Reset All Data"): reset_app()

steps = ["Client Details", "Loan Details", "Income Details", "Debt Details", "Review"]
st.progress(st.session_state.step / 5)

if st.session_state.step == 1:
    st.subheader("1. Client Details")
    render_field("Full Name", "name")
    render_field("Date of Birth", "dob", "date")
    render_field("Email", "email")
    render_field("Phone Number", "phone")
    if st.button("Next ➔"):
        if not [f for f in ["name", "email", "phone"] if not st.session_state.form_data.get(f)]:
            st.session_state.attempted_submit = False; st.session_state.step = 2; st.rerun()
        else: st.session_state.attempted_submit = True; st.warning("⚠️ Please complete all steps")

elif st.session_state.step == 2:
    st.subheader("2. Loan Details")
    render_field("Mortgage Amount ($)", "loan", "number")
    render_field("Down Payment ($)", "down", "number")
    if st.button("Next ➔"): st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.subheader("3. Income Details")
    render_field("Gross Annual Income ($)", "income", "number")
    if st.button("Next ➔"): st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    st.subheader("4. Current Debts")
    render_field("Monthly Debt Payments ($)", "debts", "number")
    if st.button("Calculate Results ➔"): st.session_state.step = 5; st.rerun()

elif st.session_state.step == 5:
    st.subheader("5. Review & Submit")
    data = st.session_state.form_data
    income = float(data.get('income', 0))
    loan = float(data.get('loan', 0))
    debts = float(data.get('debts', 0))
    gds = ((loan * 0.05 / 12) / (income / 12)) * 100 if income > 0 else 0
    tds = (((loan * 0.05 / 12) + debts) / (income / 12)) * 100 if income > 0 else 0
    st.metric("Estimated GDS", f"{gds:.2f}%")
    st.metric("Estimated TDS", f"{tds:.2f}%")
    if st.button("Finalize Application & Notify Broker"):
        st.success("✅ Notification sent to fh.mortgages@gmail.com!"
