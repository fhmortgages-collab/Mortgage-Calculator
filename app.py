import re
from datetime import date

import streamlit as st

from downpayment_sources import DOWN_PAYMENT_SOURCES
from income_sources import INCOME_SOURCES

# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")

GENDER_OPTIONS = ["", "Male", "Female", "Other", "Prefer not to say"]
MARITAL_OPTIONS = ["", "Single", "Married", "Divorced", "Widowed", "Common-Law"]

STEPS = ["Client Details", "Down Payment", "Income", "Debts", "Analysis"]


def fmt_money(value):
    try:
        return "${:,.0f}".format(value)
    except (TypeError, ValueError):
        return "—"


def parse_money(raw):
    if raw is None:
        return None
    cleaned = str(raw).replace("$", "").replace(",", "").strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


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


def init_state():
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "borrower_count" not in st.session_state:
        st.session_state.borrower_count = 1
    if "borrowers" not in st.session_state:
        st.session_state.borrowers = [empty_borrower()]
    if "consent" not in st.session_state:
        st.session_state.consent = False
    if "borrower_errors" not in st.session_state:
        st.session_state.borrower_errors = [{}]
    if "purchase_price_raw" not in st.session_state:
        st.session_state.purchase_price_raw = ""
    if "down_payment_raw" not in st.session_state:
        st.session_state.down_payment_raw = ""
    if "selected_sources" not in st.session_state:
        st.session_state.selected_sources = []
    if "source_amounts" not in st.session_state:
        st.session_state.source_amounts = {}
    if "other_source_desc" not in st.session_state:
        st.session_state.other_source_desc = ""
    if "dp_errors" not in st.session_state:
        st.session_state.dp_errors = {}
    if "income_selected" not in st.session_state:
        st.session_state.income_selected = {}
    if "income_amounts" not in st.session_state:
        st.session_state.income_amounts = {}
    if "income_special" not in st.session_state:
        st.session_state.income_special = {}
    if "income_other_desc" not in st.session_state:
        st.session_state.income_other_desc = {}
    if "income_errors" not in st.session_state:
        st.session_state.income_errors = {}


def render_stepper(active_index):
    stepper_html = "<div class='stepper-wrap'>"
    for i, label in enumerate(STEPS):
        active = "step-active" if i == active_index else ""
        circle_active = "step-circle-active" if i == active_index else ""
        stepper_html += (
            "<div class='step " + active + "'>"
            "<div class='step-circle " + circle_active + "'>" + str(i + 1) + "</div><br>" + label + "</div>"
        )
    stepper_html += "</div>"
    st.markdown(stepper_html, unsafe_allow_html=True)


st.set_page_config(page_title="Mortgage Application Wizard", page_icon="🏠", layout="centered")

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
    .consent-box, .calc-box {
        border-top: 1px solid #e5e7eb; padding-top: 1.2rem; margin-top: 0.5rem;
        font-size: 13px; color: #6b7280; line-height:1.6;
    }
    .doc-list {
        background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px;
        padding: 10px 14px; margin-top: 6px; font-size: 13px; color:#374151;
    }
    .metric-row {display:flex; gap: 16px; margin: 10px 0 4px;}
    .metric-card {
        flex:1; border:1px solid #e5e7eb; border-radius:10px; padding: 14px 16px; background:#f9fafb;
    }
    .metric-label {font-size:12px; color:#6b7280; margin-bottom:4px;}
    .metric-value {font-size:20px; font-weight:700; color:#111827;}
    .borrower-total {
        font-weight:600; font-size:15px; margin: 10px 0 4px; color:#111827;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_state()

st.markdown("## 🏠 Mortgage Loan Wizard")
st.caption("Residential Mortgage Application")

render_stepper(st.session_state.step)


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


def sync_borrower_count(new_count):
    borrowers = st.session_state.borrowers
    if new_count > len(borrowers):
        borrowers.extend(empty_borrower() for _ in range(new_count - len(borrowers)))
    else:
        del borrowers[new_count:]
    st.session_state.borrowers = borrowers
    st.session_state.borrower_count = new_count

    errors = st.session_state.borrower_errors
    if new_count > len(errors):
        errors.extend({} for _ in range(new_count - len(errors)))
    else:
        del errors[new_count:]
    st.session_state.borrower_errors = errors


def refresh_page1():
    st.session_state.borrower_count = 1
    st.session_state.borrowers = [empty_borrower()]
    st.session_state.borrower_errors = [{}]
    st.session_state.consent = False


def render_client_details():
    st.markdown("### Client Details")
    st.write("Enter information for each borrower on this application.")

    st.write("**Number of Borrowers**")
    cols = st.columns(4)
    for i, n in enumerate([1, 2, 3, 4]):
        btn_type = "primary" if st.session_state.borrower_count == n else "secondary"
        if cols[i].button(str(n), key="count_" + str(n), type=btn_type, use_container_width=True):
            sync_borrower_count(n)
            st.rerun()

    st.divider()

    for idx in range(st.session_state.borrower_count):
        borrower = st.session_state.borrowers[idx]
        errors = st.session_state.borrower_errors[idx] if idx < len(st.session_state.borrower_errors) else {}

        with st.expander("Borrower " + str(idx + 1), expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                borrower["full_name"] = st.text_input(
                    "Full Name", value=borrower["full_name"], placeholder="Jane Smith", key="name_" + str(idx)
                )
                if errors.get("full_name"):
                    st.caption(":red[" + errors["full_name"] + "]")

                borrower["phone"] = st.text_input(
                    "Phone Number", value=borrower["phone"], placeholder="(416) 555-0100", key="phone_" + str(idx)
                )
                if errors.get("phone"):
                    st.caption(":red[" + errors["phone"] + "]")

                borrower["gender"] = st.selectbox(
                    "Gender", GENDER_OPTIONS,
                    index=GENDER_OPTIONS.index(borrower["gender"]) if borrower["gender"] in GENDER_OPTIONS else 0,
                    key="gender_" + str(idx),
                )
                if errors.get("gender"):
                    st.caption(":red[" + errors["gender"] + "]")

            with col2:
                borrower["email"] = st.text_input(
                    "Email Address", value=borrower["email"], placeholder="jane@example.com", key="email_" + str(idx)
                )
                if errors.get("email"):
                    st.caption(":red[" + errors["email"] + "]")

                borrower["dob"] = st.date_input(
                    "Date of Birth",
                    value=borrower["dob"] or date(1990, 1, 1),
                    min_value=date(1900, 1, 1),
                    max_value=date.today(),
                    key="dob_" + str(idx),
                )
                if errors.get("dob"):
                    st.caption(":red[" + errors["dob"] + "]")

                borrower["marital_status"] = st.selectbox(
                    "Marital Status", MARITAL_OPTIONS,
                    index=MARITAL_OPTIONS.index(borrower["marital_status"]) if borrower["marital_status"] in MARITAL_OPTIONS else 0,
                    key="marital_" + str(idx),
                )
                if errors.get("marital_status"):
                    st.caption(":red[" + errors["marital_status"] + "]")

            borrower["address"] = st.text_area(
                "Current Address", value=borrower["address"], placeholder="123 Main St, Toronto, ON M5V 1A1",
                key="address_" + str(idx), height=80,
            )
            if errors.get("address"):
                st.caption(":red[" + errors["address"] + "]")

        st.session_state.borrowers[idx] = borrower

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

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p1_back"):
            st.info("This is the first screen.")
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p1_refresh"):
            st.session_state["p1_show_refresh_confirm"] = True

    if st.session_state.get("p1_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p1_confirm_refresh"):
                refresh_page1()
                st.session_state["p1_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p1_cancel_refresh"):
                st.session_state["p1_show_refresh_confirm"] = False
                st.rerun()

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p1_continue"):
            all_errors = [validate_borrower(b) for b in st.session_state.borrowers]
            st.session_state.borrower_errors = all_errors
            is_valid = all(len(e) == 0 for e in all_errors)

            if not st.session_state.consent:
                consent_error_slot.markdown(":red[You must acknowledge and consent before continuing.]")

            if is_valid and st.session_state.consent:
                st.session_state.step = 1
                st.rerun()
            else:
                st.rerun()


def refresh_page2():
    st.session_state.purchase_price_raw = ""
    st.session_state.down_payment_raw = ""
    st.session_state.selected_sources = []
    st.session_state.source_amounts = {}
    st.session_state.other_source_desc = ""
    st.session_state.dp_errors = {}


def render_down_payment():
    st.markdown("### Down Payment")
    st.write("Enter property price, down payment, and the sources funding it.")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.purchase_price_raw = st.text_input(
            "Purchase Price ($)", value=st.session_state.purchase_price_raw, placeholder="e.g., 500,000"
        )
    with col2:
        st.session_state.down_payment_raw = st.text_input(
            "Down Payment Amount ($)", value=st.session_state.down_payment_raw, placeholder="e.g., 100,000"
        )

    purchase_price = parse_money(st.session_state.purchase_price_raw)
    down_payment = parse_money(st.session_state.down_payment_raw)

    price_error = None
    dp_error = None
    if st.session_state.purchase_price_raw.strip() and purchase_price is None:
        price_error = "Enter a valid number."
    elif purchase_price is not None and purchase_price <= 0:
        price_error = "Purchase price must be greater than zero."

    if st.session_state.down_payment_raw.strip() and down_payment is None:
        dp_error = "Enter a valid number."
    elif down_payment is not None and down_payment < 0:
        dp_error = "Down payment cannot be negative."
    elif purchase_price is not None and down_payment is not None and down_payment > purchase_price:
        dp_error = "Down payment cannot exceed the purchase price."

    if price_error:
        st.caption(":red[" + price_error + "]")
    if dp_error:
        st.caption(":red[" + dp_error + "]")

    if purchase_price and down_payment is not None and not price_error and not dp_error:
        loan_amount = purchase_price - down_payment
        ltv = (loan_amount / purchase_price) * 100
        loan_display = fmt_money(loan_amount)
        ltv_display = "{:.2f}%".format(ltv)
    else:
        loan_display = "—"
        ltv_display = "—"

    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-card'><div class='metric-label'>Mortgage Loan Amount</div>"
        "<div class='metric-value'>" + loan_display + "</div></div>"
        "<div class='metric-card'><div class='metric-label'>LTV Ratio</div>"
        "<div class='metric-value'>" + ltv_display + "</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    st.write("**Select Down Payment Sources**")

    selected = st.session_state.selected_sources
    for source in DOWN_PAYMENT_SOURCES:
        checked = source["key"] in selected
        new_checked = st.checkbox(source["label"], value=checked, key="src_" + source["key"])

        if new_checked and source["key"] not in selected:
            selected.append(source["key"])
        elif not new_checked and source["key"] in selected:
            selected.remove(source["key"])
            st.session_state.source_amounts.pop(source["key"], None)

        if new_checked:
            if not source["eligible"]:
                st.markdown(
                    "<div class='doc-list'>⚠️ " + source["notes"] + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                amount_raw = st.text_input(
                    source["label"] + " Amount ($)",
                    value=st.session_state.source_amounts.get(source["key"], ""),
                    placeholder="Enter amount",
                    key="amt_" + source["key"],
                )
                st.session_state.source_amounts[source["key"]] = amount_raw

                if source["key"] == "other":
                    st.session_state.other_source_desc = st.text_input(
                        "Describe the other source",
                        value=st.session_state.other_source_desc,
                        key="other_source_desc_input",
                    )

                docs_html = ""
                for d in source["documents"]:
                    docs_html += "<li>" + d + "</li>"
                notes_html = "<div style='margin-top:6px;'>" + source["notes"] + "</div>" if source["notes"] else ""
                st.markdown(
                    "<div class='doc-list'><b>Required Documentation</b>"
                    "<ul style='margin:6px 0 0 18px;'>" + docs_html + "</ul>" + notes_html + "</div>",
                    unsafe_allow_html=True,
                )

    st.session_state.selected_sources = selected

    st.divider()

    eligible_selected = []
    for s in selected:
        for src in DOWN_PAYMENT_SOURCES:
            if src["key"] == s and src["eligible"]:
                eligible_selected.append(s)

    total_sources = 0.0
    for key in eligible_selected:
        amt = parse_money(st.session_state.source_amounts.get(key, ""))
        total_sources += amt or 0.0

    st.write("**Total from Sources: " + fmt_money(total_sources) + "**")

    totals_match = False
    if not selected:
        st.caption(":red[Please select at least one source.]")
    elif down_payment is None:
        st.caption(":gray[Enter a down payment amount above to check totals.]")
    else:
        if round(total_sources, 2) == round(down_payment, 2):
            st.success("✓ Source amounts match the down payment amount.")
            totals_match = True
        else:
            st.error(
                "✗ The total down payment amount (" + fmt_money(down_payment) + ") does not match "
                "the sum of the sources (" + fmt_money(total_sources) + "). Please adjust your entries."
            )

    st.divider()

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p2_back"):
            st.session_state.step = 0
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p2_refresh"):
            st.session_state["p2_show_refresh_confirm"] = True

    if st.session_state.get("p2_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p2_confirm_refresh"):
                refresh_page2()
                st.session_state["p2_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p2_cancel_refresh"):
                st.session_state["p2_show_refresh_confirm"] = False
                st.rerun()

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p2_continue"):
            valid = (
                purchase_price is not None and purchase_price > 0 and not price_error
                and down_payment is not None and not dp_error
                and len(selected) > 0
                and totals_match
            )
            if valid:
                st.session_state.step = 2
                st.rerun()
            else:
                st.error("Please resolve the issues above before continuing.")


def refresh_page3():
    st.session_state.income_selected = {}
    st.session_state.income_amounts = {}
    st.session_state.income_special = {}
    st.session_state.income_other_desc = {}
    st.session_state.income_errors = {}


def get_income_source(key):
    for src in INCOME_SOURCES:
        if src["key"] == key:
            return src
    return None


def compute_borrower_income(borrower_idx):
    bidx = str(borrower_idx)
    selected_keys = st.session_state.income_selected.get(bidx, [])
    total = 0.0
    breakdown = {}

    for key in selected_keys:
        source = get_income_source(key)
        special = source["special"]
        amounts = st.session_state.income_amounts.get(bidx, {}).get(key, {})

        if special == "two_year_avg":
            year1 = parse_money(amounts.get("year1", "")) or 0.0
            year2 = parse_money(amounts.get("year2", "")) or 0.0
            avg = (year1 + year2) / 2
            value = min(year1, avg) if year1 > 0 else avg
        elif special == "self_employed":
            gross = parse_money(amounts.get("gross", "")) or 0.0
            expenses = parse_money(amounts.get("expenses", "")) or 0.0
            value = max(gross - expenses, 0.0)
        elif special == "rental":
            gross_rent = parse_money(amounts.get("gross_rent", "")) or 0.0
            expenses = parse_money(amounts.get("expenses", "")) or 0.0
            value = max(gross_rent - expenses, 0.0)
        else:
            value = parse_money(amounts.get("amount", "")) or 0.0

        breakdown[key] = value
        total += value

    return total, breakdown


def render_income():
    st.markdown("### Income Details")
    st.write("Enter income information for each borrower on this application.")

    borrower_count = st.session_state.borrower_count
    borrowers = st.session_state.borrowers
    all_valid = True
    grand_total = 0.0

    for idx in range(borrower_count):
        bidx = str(idx)
        borrower_name = borrowers[idx]["full_name"].strip() if idx < len(borrowers) else ""
        header = "Borrower " + str(idx + 1)
        if borrower_name:
            header += ": " + borrower_name
        header += " - Income Details"

        if bidx not in st.session_state.income_selected:
            st.session_state.income_selected[bidx] = []
        if bidx not in st.session_state.income_amounts:
            st.session_state.income_amounts[bidx] = {}
        if bidx not in st.session_state.income_errors:
            st.session_state.income_errors[bidx] = {}

        with st.expander(header, expanded=True):
            st.write("**Select Income Sources**")
            selected = st.session_state.income_selected[bidx]

            for source in INCOME_SOURCES:
                skey = source["key"]
                checked = skey in selected
                new_checked = st.checkbox(
                    source["label"], value=checked, key="inc_src_" + bidx + "_" + skey
                )

                if new_checked and skey not in selected:
                    selected.append(skey)
                elif not new_checked and skey in selected:
                    selected.remove(skey)
                    st.session_state.income_amounts[bidx].pop(skey, None)

                if new_checked:
                    if skey not in st.session_state.income_amounts[bidx]:
                        st.session_state.income_amounts[bidx][skey] = {}
                    amounts = st.session_state.income_amounts[bidx][skey]

                    if source["special"] == "two_year_avg":
                        c1, c2 = st.columns(2)
                        with c1:
                            amounts["year1"] = st.text_input(
                                "Most Recent Year Amount ($)",
                                value=amounts.get("year1", ""),
                                placeholder="Enter annual amount",
                                key="inc_amt_" + bidx + "_" + skey + "_year1",
                            )
                        with c2:
                            amounts["year2"] = st.text_input(
                                "Prior Year Amount ($)",
                                value=amounts.get("year2", ""),
                                placeholder="Enter annual amount",
                                key="inc_amt_" + bidx + "_" + skey + "_year2",
                            )
                    elif source["special"] == "self_employed":
                        c1, c2 = st.columns(2)
                        with c1:
                            amounts["gross"] = st.text_input(
                                "Annual Gross Income ($)",
                                value=amounts.get("gross", ""),
                                placeholder="Enter annual amount",
                                key="inc_amt_" + bidx + "_" + skey + "_gross",
                            )
                        with c2:
                            amounts["expenses"] = st.text_input(
                                "Annual Business Expenses ($)",
                                value=amounts.get("expenses", ""),
                                placeholder="Enter annual amount",
                                key="inc_amt_" + bidx + "_" + skey + "_expenses",
                            )
                        gross_v = parse_money(amounts.get("gross", "")) or 0.0
                        exp_v = parse_money(amounts.get("expenses", "")) or 0.0
                        st.caption("Net Self-Employed Income: " + fmt_money(max(gross_v - exp_v, 0.0)))
                    elif source["special"] == "rental":
                        c1, c2 = st.columns(2)
                        with c1:
                            amounts["gross_rent"] = st.text_input(
                                "Gross Annual Rent ($)",
                                value=amounts.get("gross_rent", ""),
                                placeholder="Enter annual amount",
                                key="inc_amt_" + bidx + "_" + skey + "_grossrent",
                            )
                        with c2:
                            amounts["expenses"] = st.text_input(
                                "Annual Property Expenses ($)",
                                value=amounts.get("expenses", ""),
                                placeholder="Enter annual amount",
                                key="inc_amt_" + bidx + "_" + skey + "_propexp",
                            )
                        rent_v = parse_money(amounts.get("gross_rent", "")) or 0.0
                        exp_v = parse_money(amounts.get("expenses", "")) or 0.0
                        st.caption("Net Rental Income: " + fmt_money(max(rent_v - exp_v, 0.0)))
                    else:
                        amounts["amount"] = st.text_input(
                            source["label"] + " Amount ($)",
                            value=amounts.get("amount", ""),
                            placeholder="Enter annual amount",
                            key="inc_amt_" + bidx + "_" + skey + "_amount",
                        )

                    if skey == "other":
                        if bidx not in st.session_state.income_other_desc:
                            st.session_state.income_other_desc[bidx] = ""
                        st.session_state.income_other_desc[bidx] = st.text_input(
                            "Describe the other income source",
                            value=st.session_state.income_other_desc[bidx],
                            key="inc_other_desc_" + bidx,
                        )

                    docs_html = ""
                    for d in source["documents"]:
                        docs_html += "<li>" + d + "</li>"
                    notes_html = "<div style='margin-top:6px;'>" + source["notes"] + "</div>" if source["notes"] else ""
                    st.markdown(
                        "<div class='doc-list'><b>Required Documentation</b>"
                        "<ul style='margin:6px 0 0 18px;'>" + docs_html + "</ul>" + notes_html + "</div>",
                        unsafe_allow_html=True,
                    )

                    st.session_state.income_amounts[bidx][skey] = amounts

            st.session_state.income_selected[bidx] = selected

            borrower_total, breakdown = compute_borrower_income(idx)
            grand_total += borrower_total

            label_name = borrower_name if borrower_name else ("Borrower " + str(idx + 1))
            st.markdown(
                "<div class='borrower-total'>" + label_name + " Total Income: " + fmt_money(borrower_total) + "</div>",
                unsafe_allow_html=True,
            )

            errors = {}
            if not selected:
                errors["no_sources"] = "Please select at least one income source for " + label_name + "."
            else:
                for skey in selected:
                    val = breakdown.get(skey, 0.0)
                    if val <= 0:
                        source = get_income_source(skey)
                        errors[skey] = "Please enter an amount for " + source["label"] + " for " + label_name + "."

            st.session_state.income_errors[bidx] = errors
            if errors:
                all_valid = False
                for msg in errors.values():
                    st.caption(":red[" + msg + "]")

    st.divider()
    st.markdown("#### Total Combined Income: " + fmt_money(grand_total))
    st.divider()

    back_col, refresh_col, continue_col = st.columns(3)
    with back_col:
        if st.button("← Back", use_container_width=True, key="p3_back"):
            st.session_state.step = 1
            st.rerun()
    with refresh_col:
        if st.button("Refresh", use_container_width=True, key="p3_refresh"):
            st.session_state["p3_show_refresh_confirm"] = True

    if st.session_state.get("p3_show_refresh_confirm"):
        st.warning("Are you sure you want to refresh? All entered data on this page will be permanently cleared.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", use_container_width=True, key="p3_confirm_refresh"):
                refresh_page3()
                st.session_state["p3_show_refresh_confirm"] = False
                st.rerun()
        with c2:
            if st.button("Cancel", use_container_width=True, key="p3_cancel_refresh"):
                st.session_state["p3_show_refresh_confirm"] = False
                st.rerun()

    with continue_col:
        if st.button("Continue →", type="primary", use_container_width=True, key="p3_continue"):
            if all_valid:
                st.session_state.step = 3
                st.rerun()
            else:
                st.error("Please resolve the issues above before continuing.")


def render_placeholder_step(step_name):
    st.markdown("### " + step_name)
    st.info("The '" + step_name + "' step is not yet built. Your data from previous steps has been saved.")
    if st.button("← Back", key="back_from_" + step_name):
        st.session_state.step -= 1
        st.rerun()


if st.session_state.step == 0:
    render_client_details()
elif st.session_state.step == 1:
    render_down_payment()
elif st.session_state.step == 2:
    render_income()
else:
    render_placeholder_step(STEPS[st.session_state.step])
