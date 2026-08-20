with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

original_content = content

replacements = [
(
'''                for midx, mtg in enumerate(mortgages):
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        mtg["lender"] = st.text_input(
                            "Lender" + (" #" + str(midx + 1) if num_mtg > 1 else ""),
                            value=mtg.get("lender", ""), key="prop_mtg_lender_" + str(pidx) + "_" + str(midx),
                        )
                    with mc2:
                        mtg["balance"] = money_text_input(
                            "Outstanding Balance ($)" + (" #" + str(midx + 1) if num_mtg > 1 else ""),
                            mtg.get("balance", ""), key="prop_mtg_balance_" + str(pidx) + "_" + str(midx),
                            placeholder="Enter current balance owing",
                        )''',
'''                for midx, mtg in enumerate(mortgages):
                    mc1, mc2, mc3 = st.columns(3)
                    with mc1:
                        mtg["lender"] = st.text_input(
                            "Lender" + (" #" + str(midx + 1) if num_mtg > 1 else ""),
                            value=mtg.get("lender", ""), key="prop_mtg_lender_" + str(pidx) + "_" + str(midx),
                        )
                    with mc2:
                        mtg["balance"] = money_text_input(
                            "Outstanding Balance ($)" + (" #" + str(midx + 1) if num_mtg > 1 else ""),
                            mtg.get("balance", ""), key="prop_mtg_balance_" + str(pidx) + "_" + str(midx),
                            placeholder="Enter current balance owing",
                        )
                    with mc3:
                        st.write("")'''
),
(
'''                    else:
                        lender_col, pay_col, bal_col = st.columns([1.6, 1.6, 1.6])''',
'''                    else:
                        lender_col, pay_col, bal_col = st.columns(3)'''
),
(
'''                        lender_col, bal_col, calc_col = st.columns([1.6, 1.6, 1.6])''',
'''                        lender_col, bal_col, calc_col = st.columns(3)'''
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