import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

original_content = content

replacements = [
(
'''    def render_two_year_income_fields(amounts, field_prefix, label="Annual Income"):
        c1, c2 = st.columns(2)
        with c1:
            amounts["recent_year"] = st.text_input(
                "Most Recent Year — " + label + " ($)", value=amounts.get("recent_year", ""),
                placeholder="Enter amount", key=field_prefix + "recent_year",
            )
        with c2:
            amounts["prior_year"] = st.text_input(
                "Prior Year — " + label + " ($)", value=amounts.get("prior_year", ""),
                placeholder="Enter amount", key=field_prefix + "prior_year",
            )''',
'''    def render_two_year_income_fields(amounts, field_prefix, label="Annual Income"):
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["recent_year"] = st.text_input(
                "Most Recent Year — " + label + " ($)", value=amounts.get("recent_year", ""),
                placeholder="Enter amount", key=field_prefix + "recent_year",
            )
        with c2:
            amounts["prior_year"] = st.text_input(
                "Prior Year — " + label + " ($)", value=amounts.get("prior_year", ""),
                placeholder="Enter amount", key=field_prefix + "prior_year",
            )
        with c3:
            st.write("")'''
),
(
'''    elif skey == "hourly":
        c1, c2 = st.columns(2)
        with c1:
            amounts["employer_name"] = st.text_input("Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            guaranteed_options = ["", "Guaranteed Hours", "Variable Hours"]
            cur_g = amounts.get("hours_type", "")
            amounts["hours_type"] = st.selectbox(
                "Hours Type", guaranteed_options,
                index=guaranteed_options.index(cur_g) if cur_g in guaranteed_options else 0,
                key=prefix + "hours_type",
            )
        render_two_year_income_fields(amounts, prefix, "Hourly Income")''',
'''    elif skey == "hourly":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["employer_name"] = st.text_input("Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            guaranteed_options = ["", "Guaranteed Hours", "Variable Hours"]
            cur_g = amounts.get("hours_type", "")
            amounts["hours_type"] = st.selectbox(
                "Hours Type", guaranteed_options,
                index=guaranteed_options.index(cur_g) if cur_g in guaranteed_options else 0,
                key=prefix + "hours_type",
            )
        with c3:
            st.write("")
        render_two_year_income_fields(amounts, prefix, "Hourly Income")'''
),
(
'''    elif skey == "bonus_overtime":
        c1, c2 = st.columns(2)
        with c1:
            amounts["employer_name"] = st.text_input("Primary Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            st.write("")
        render_two_year_income_fields(amounts, prefix, "Bonus/Overtime Income")''',
'''    elif skey == "bonus_overtime":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["employer_name"] = st.text_input("Primary Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            st.write("")
        with c3:
            st.write("")
        render_two_year_income_fields(amounts, prefix, "Bonus/Overtime Income")'''
),
(
'''    elif skey == "dividend":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Financial Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
        with c2:
            amounts["account_number"] = st.text_input("Account Number", value=amounts.get("account_number", ""), key=prefix + "account_number")
        render_two_year_income_fields(amounts, prefix, "Dividend Income")''',
'''    elif skey == "dividend":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["institution_name"] = st.text_input("Financial Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
        with c2:
            amounts["account_number"] = st.text_input("Account Number", value=amounts.get("account_number", ""), key=prefix + "account_number")
        with c3:
            st.write("")
        render_two_year_income_fields(amounts, prefix, "Dividend Income")'''
),
(
'''    elif skey == "parttime":
        c1, c2 = st.columns(2)
        with c1:
            amounts["employer_name"] = st.text_input("Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")''',
'''    elif skey == "parttime":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["employer_name"] = st.text_input("Employer Name", value=amounts.get("employer_name", ""), key=prefix + "employer_name")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c3:
            st.write("")'''
),
(
'''    elif skey == "ei_parental_benefits":
        c1, c2 = st.columns(2)
        with c1:
            amounts["return_to_work_date"] = st.text_input("Expected Return-to-Work Date (MM/YYYY)", value=amounts.get("return_to_work_date", ""), key=prefix + "return_to_work_date")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Benefit Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        st.caption("Note: EI/maternity/parental benefits are usually weaker for qualification since they're temporary.")''',
'''    elif skey == "ei_parental_benefits":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["return_to_work_date"] = st.text_input("Expected Return-to-Work Date (MM/YYYY)", value=amounts.get("return_to_work_date", ""), key=prefix + "return_to_work_date")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Benefit Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c3:
            st.write("")
        st.caption("Note: EI/maternity/parental benefits are usually weaker for qualification since they're temporary.")'''
),
(
'''    elif skey == "foreign_income":
        c1, c2 = st.columns(2)
        with c1:
            amounts["country"] = st.text_input("Country of Income Source", value=amounts.get("country", ""), key=prefix + "country")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($, CAD equivalent)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        st.caption("Note: lenders are usually conservative with foreign income due to currency and jurisdiction risk.")''',
'''    elif skey == "foreign_income":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["country"] = st.text_input("Country of Income Source", value=amounts.get("country", ""), key=prefix + "country")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($, CAD equivalent)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c3:
            st.write("")
        st.caption("Note: lenders are usually conservative with foreign income due to currency and jurisdiction risk.")'''
),
(
'''    elif skey == "capital_gains":
        c1, c2 = st.columns(2)
        with c1:
            amounts["description"] = st.text_input("Source / Description", value=amounts.get("description", ""), key=prefix + "description")
        with c2:
            amounts["amount"] = money_text_input("Amount ($, for reference only)", amounts.get("amount", ""), placeholder="Enter amount", key=prefix + "amount")
        st.caption("⚠️ Capital gains are not recurring income — this amount is recorded for reference only and is excluded from GDS/TDS qualification.")''',
'''    elif skey == "capital_gains":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["description"] = st.text_input("Source / Description", value=amounts.get("description", ""), key=prefix + "description")
        with c2:
            amounts["amount"] = money_text_input("Amount ($, for reference only)", amounts.get("amount", ""), placeholder="Enter amount", key=prefix + "amount")
        with c3:
            st.write("")
        st.caption("⚠️ Capital gains are not recurring income — this amount is recorded for reference only and is excluded from GDS/TDS qualification.")'''
),
(
'''    elif skey == "board_director_fees":
        c1, c2 = st.columns(2)
        with c1:
            amounts["organization_name"] = st.text_input("Organization Name", value=amounts.get("organization_name", ""), key=prefix + "organization_name")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")''',
'''    elif skey == "board_director_fees":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["organization_name"] = st.text_input("Organization Name", value=amounts.get("organization_name", ""), key=prefix + "organization_name")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c3:
            st.write("")'''
),
(
'''    elif skey == "pension":
        c1, c2 = st.columns(2)
        with c1:
            amounts["institution_name"] = st.text_input("Provider / Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")''',
'''    elif skey == "pension":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["institution_name"] = st.text_input("Provider / Institution Name", value=amounts.get("institution_name", ""), key=prefix + "institution_name")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c3:
            st.write("")'''
),
(
'''    elif skey == "government_benefits":
        c1, c2 = st.columns(2)
        with c1:
            amounts["benefit_type"] = st.text_input("Benefit Type", value=amounts.get("benefit_type", ""), key=prefix + "benefit_type")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")''',
'''    elif skey == "government_benefits":
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["benefit_type"] = st.text_input("Benefit Type", value=amounts.get("benefit_type", ""), key=prefix + "benefit_type")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Income ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c3:
            st.write("")'''
),
(
'''    else:  # "other"
        c1, c2 = st.columns(2)
        with c1:
            amounts["source_desc"] = st.text_input("Source Description", value=amounts.get("source_desc", ""), key=prefix + "source_desc")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")''',
'''    else:  # "other"
        c1, c2, c3 = st.columns(3)
        with c1:
            amounts["source_desc"] = st.text_input("Source Description", value=amounts.get("source_desc", ""), key=prefix + "source_desc")
        with c2:
            amounts["amount"] = money_text_input("Gross Annual Amount ($)", amounts.get("amount", ""), placeholder="Enter annual amount", key=prefix + "amount")
        with c3:
            st.write("")'''
),
(
'''            pc1, pc2 = st.columns(2)
            with pc1:
                amounts["prev_employer_name"] = st.text_input("Employer Name", value=amounts.get("prev_employer_name", ""), key=prefix + "prev_employer_name")
                amounts["prev_phone"] = st.text_input("Phone", value=amounts.get("prev_phone", ""), key=prefix + "prev_phone")
                amounts["prev_start_date"] = st.text_input("Start Date (MM/YYYY)", value=amounts.get("prev_start_date", ""), key=prefix + "prev_start_date")
            with pc2:
                amounts["prev_employer_address"] = st.text_input("Address", value=amounts.get("prev_employer_address", ""), key=prefix + "prev_employer_address")
                amounts["prev_title"] = st.text_input("Title", value=amounts.get("prev_title", ""), key=prefix + "prev_title")
                amounts["prev_end_date"] = st.text_input("End Date (MM/YYYY)", value=amounts.get("prev_end_date", ""), key=prefix + "prev_end_date")''',
'''            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                amounts["prev_employer_name"] = st.text_input("Employer Name", value=amounts.get("prev_employer_name", ""), key=prefix + "prev_employer_name")
                amounts["prev_start_date"] = st.text_input("Start Date (MM/YYYY)", value=amounts.get("prev_start_date", ""), key=prefix + "prev_start_date")
            with pc2:
                amounts["prev_employer_address"] = st.text_input("Address", value=amounts.get("prev_employer_address", ""), key=prefix + "prev_employer_address")
                amounts["prev_title"] = st.text_input("Title", value=amounts.get("prev_title", ""), key=prefix + "prev_title")
            with pc3:
                amounts["prev_phone"] = st.text_input("Phone", value=amounts.get("prev_phone", ""), key=prefix + "prev_phone")
                amounts["prev_end_date"] = st.text_input("End Date (MM/YYYY)", value=amounts.get("prev_end_date", ""), key=prefix + "prev_end_date")'''
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