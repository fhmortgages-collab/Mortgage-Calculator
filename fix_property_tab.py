with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

original_content = content

replacements = [
(
'''        with c2:
            if (
                st.session_state.subject_prop_type
                and st.session_state.subject_prop_type != "Condo / Apartment"
                and st.session_state.subject_condo_raw.strip() == ""
            ):
                st.session_state.subject_condo_raw = "0"
            st.session_state.subject_condo_raw = money_text_input(
                "Monthly Condo / Strata Fees ($)", st.session_state.subject_condo_raw,
                key="subject_condo_input", placeholder="Enter monthly fee amount (0 if none)",
            )''',
'''        with c2:
            if (
                st.session_state.subject_prop_type
                and st.session_state.subject_prop_type != "Condo / Apartment"
                and st.session_state.get("subject_condo_input", "").strip() == ""
            ):
                st.session_state.subject_condo_raw = "0"
                st.session_state["subject_condo_input"] = "0"
            st.session_state.subject_condo_raw = money_text_input(
                "Monthly Condo / Strata Fees ($)", st.session_state.subject_condo_raw,
                key="subject_condo_input", placeholder="Enter monthly fee amount (0 if none)",
            )'''
),
]

applied = 0
missing = []
for old, new in replacements:
    if old in content:
        content = content.replace(old, new, 1)
        applied += 1
    else:
        missing.append(old.strip().splitlines()[0])

if content != original_content:
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)

print("Applied:", applied, "of", len(replacements))
if missing:
    print("Could NOT find (skipped, no change made for these):")
    for m in missing:
        print("  -", m)