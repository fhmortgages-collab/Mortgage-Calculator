import re
from datetime import date, datetime

import streamlit as st

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")

GENDER_OPTIONS = ["", "Male", "Female", "Other", "Prefer not to say"]
MARITAL_OPTIONS = ["", "Single", "Married", "Divorced", "Widowed", "Common-Law"]

STEPS = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"]


def empty_borrower():
    return {
        "full_name": "",
        "dob": None,
        "gender": "",
        "marital_status": "",
        "phone": "",
        "email": "",
        "address": "",
    }


def validate_borrower(b):
    errors = {}
    if not b["full_name"].strip():
        errors["full_name"] = "Full name is required."

    if not b["dob"]:
        errors["dob"] = "Date of birth is required."
    elif b["dob"] > date.today():
        errors["dob"] = "Date of birth cannot be in the future."

    if not b["gender"]:
        errors["gender"] = "Please select an option."

    if not b["marital_status"]:
        errors["marital_status"] = "Please select an option."

    if not b["phone"].strip():
        errors["phone"] = "Phone number is required."
    elif not PHONE_RE.match(b["phone"].strip()):
        errors["phone"] = "Enter a valid 10-digit phone number."

    if not b["email"].strip():
        errors["email"] = "Email is required."
    elif not EMAIL_RE.match(b["email"].strip()):
        errors["email"] = "Enter a valid email address."

    if not b["address"].strip():
        errors["address"] = "Current address is required."

    return errors


# ---------------------------------------------------------------------------
# Session state setup
# ---------------------------------------------------------------------------

def init_state():
    if "borrower_count" not in st.session_state:
        st.session_state.borrower_count = 1
    if "borrowers" not in st.session_state:
        st.session_state.borrowers = [empty_borrower()]
    if "consent" not in st.session_state:
        st.session_state.consent = False
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "errors" not in st.session_state:
        st.session_state.errors = [{}]


def sync_borrower_count(new_count):
    borrowers = st.session_state.borrowers
    if new_count > len(borrowers):
        for _ in range(new_count - len(borrowers)):
            borrowers.append(empty_borrower())
    else:
        del borrowers[new_count:]
    st.session_state.borrowers = borrowers
    st.session_state.borrower_count = new_count

    errors = st.session_state.errors
    if new_count > len(errors):
        errors.extend({} for _ in range(new_count - len(errors)))
    else:
        del errors[new_count:]
    st.session_state.errors = errors


def do_refresh():
    st.session_state.borrower_count = 1
    st.session_state.borrowers = [empty_borrower()]
    st.session_state.errors = [{}]
    st.session_state.consent = False
    st.session_state.submitted = False


# ---------------------------------------------------------------------------
# Page config + styling
# ---------------------------------------------------------------------------

st.set_page_config(page_title="FH Mortgage Loan Wizard", page_icon="🏠", layout="centered")

st.markdown(
    """
    <style>
    .stepper-wrap {display:flex; justify-content:space-between; margin-bottom: 1.5rem;}
    .step {text-align:center; flex:1; font-size:13px; color:#9ca3af;}
    .step-active {color:#111827; font-weight:600;}
    .step-circle {
        width:32px; height:32px; border-radius:50%; background:#e5e7eb; color:#6b7280;
        display:inline-flex; align-items:center; justify-content:center; font-weight:600; margin-bottom:4px;
    }
    .step-circle-active {background:#2563eb; color:#fff;}
    .consent-box {
        border-top: 1px solid #e5e7eb; padding-top: 1.2rem; margin-top: 0.5rem;
        font-size: 13px; color: #6b7280; line-height:1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_state()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("## 🏠 FH Mortgage Loan Wizard")
st.caption("Residential Mortgage Application")

# Stepper (visual only — this app implements Step 1)
stepper_html = "<div class='stepper-wrap'>"
for i, label in enumerate(STEPS):
    active = "step-active" if i == 0 else ""
    circle_active = "step-circle-active" if i == 0 else ""
    stepper_html += (
        f"<div class='step {active}'>"
        f"<div class='step-circle {circle_active}'>{i + 1}</div><br>{label}</div>"
    )
stepper_html += "</div>"
st.markdown(stepper_html, unsafe_allow_html=True)

st.markdown("### Client Details")
st.write("Enter information for each borrower on this application.")

# ---------------------------------------------------------------------------
# Borrower count selector
# ---------------------------------------------------------------------------

st.write("**Number of Borrowers**")
cols = st.columns(4)
for i, n in enumerate([1, 2, 3, 4]):
    btn_type = "primary" if st.session_state.borrower_count == n else "secondary"
    if cols[i].button(str(n), key=f"count_{n}", type=btn_type, use_container_width=True):
        sync_borrower_count(n)
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Borrower sections
# ---------------------------------------------------------------------------

for idx in range(st.session_state.borrower_count):
    borrower = st.session_state.borrowers[idx]
    errors = st.session_state.errors[idx] if idx < len(st.session_state.errors) else {}

    with st.expander(f"Borrower {idx + 1}", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            borrower["full_name"] = st.text_input(
                "Full Name", value=borrower["full_name"], placeholder="Jane Smith", key=f"name_{idx}"
            )
            if errors.get("full_name"):
                st.caption(f":red[{errors['full_name']}]")

            borrower["phone"] = st.text_input(
                "Phone Number", value=borrower["phone"], placeholder="(416) 555-0100", key=f"phone_{idx}"
            )
            if errors.get("phone"):
                st.caption(f":red[{errors['phone']}]")

            borrower["gender"] = st.selectbox(
                "Gender", GENDER_OPTIONS, index=GENDER_OPTIONS.index(borrower["gender"]) if borrower["gender"] in GENDER_OPTIONS else 0,
                key=f"gender_{idx}",
            )
            if errors.get("gender"):
                st.caption(f":red[{errors['gender']}]")

        with col2:
            borrower["email"] = st.text_input(
                "Email Address", value=borrower["email"], placeholder="jane@example.com", key=f"email_{idx}"
            )
            if errors.get("email"):
                st.caption(f":red[{errors['email']}]")

            borrower["dob"] = st.date_input(
                "Date of Birth",
                value=borrower["dob"] or date(1990, 1, 1),
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                key=f"dob_{idx}",
            )
            if errors.get("dob"):
                st.caption(f":red[{errors['dob']}]")

            borrower["marital_status"] = st.selectbox(
                "Marital Status", MARITAL_OPTIONS,
                index=MARITAL_OPTIONS.index(borrower["marital_status"]) if borrower["marital_status"] in MARITAL_OPTIONS else 0,
                key=f"marital_{idx}",
            )
            if errors.get("marital_status"):
                st.caption(f":red[{errors['marital_status']}]")

        borrower["address"] = st.text_area(
            "Current Address", value=borrower["address"], placeholder="123 Main St, Toronto, ON M5V 1A1",
            key=f"address_{idx}", height=80,
        )
        if errors.get("address"):
            st.caption(f":red[{errors['address']}]")

    st.session_state.borrowers[idx] = borrower

# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="consent-box">
    <b>Consent</b><br><br>
    By proceeding, you acknowledge and consent to the collection, use, and disclosure
    of your personal information for the purpose of processing this application.
    Your information will be kept confidential and used solely for this purpose.
    You have the right to access and correct your personal information at any time.
    </div>
    """,
    unsafe_allow_html=True,
)

st.session_state.consent = st.checkbox(
    "I acknowledge and consent to the above terms", value=st.session_state.consent
)
consent_error_slot = st.empty()

# ---------------------------------------------------------------------------
# Navigation buttons
# ---------------------------------------------------------------------------

back_col, refresh_col, continue_col = st.columns(3)

with back_col:
    if st.button("← Back", use_container_width=True):
        st.info("This is the first screen.")

with refresh_col:
    if st.button("Refresh", use_container_width=True):
        st.session_state["show_refresh_confirm"] = True

if st.session_state.get("show_refresh_confirm"):
    st.warning("Are you sure you want to refresh? All entered data will be permanently cleared.")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Confirm", type="primary", use_container_width=True, key="confirm_refresh"):
            do_refresh()
            st.session_state["show_refresh_confirm"] = False
            st.rerun()
    with cancel_col:
        if st.button("Cancel", use_container_width=True, key="cancel_refresh"):
            st.session_state["show_refresh_confirm"] = False
            st.rerun()

with continue_col:
    if st.button("Continue →", type="primary", use_container_width=True):
        all_errors = [validate_borrower(b) for b in st.session_state.borrowers]
        st.session_state.errors = all_errors
        is_valid = all(len(e) == 0 for e in all_errors)

        consent_ok = st.session_state.consent
        if not consent_ok:
            consent_error_slot.markdown(":red[You must acknowledge and consent before continuing.]")

        if is_valid and consent_ok:
            st.session_state.submitted = True
            st.rerun()
        else:
            st.rerun()

if st.session_state.submitted:
    st.success("Client Details validated. Proceeding to Mortgage step (not yet implemented).")
