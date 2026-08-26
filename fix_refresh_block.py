with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

target_line = "        with rc1:\n"
target_index = None
for i, line in enumerate(lines):
    if line == target_line and i > 0 and "sidebar_confirm_refresh" in lines[i + 1]:
        target_index = i
        break

if target_index is None:
    print("Could not find the exact target line. No changes made.")
else:
    insert_lines = [
        '    if st.session_state.get("sidebar_show_refresh_confirm"):\n',
        '        st.warning("Clear all data? Cannot be undone.")\n',
        '        rc1, rc2 = st.columns(2)\n',
    ]
    lines = lines[:target_index] + insert_lines + lines[target_index:]
    with open("app.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Inserted 3 lines before line", target_index + 1, "(original numbering).")