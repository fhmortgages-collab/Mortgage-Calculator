import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

original_content = content

# Remove every CSS rule block that references the old purple color (#a855f7),
# regardless of which selector it's attached to. This finds each "selector { ... }"
# block containing a855f7 and deletes the whole block.
pattern = re.compile(
    r'[ \t]*[^\n{}]*\{[^{}]*a855f7[^{}]*\}\s*',
    re.IGNORECASE
)
content, purple_removed = pattern.subn('', content)

# Also remove any leftover purple-only rule fragments like:
#   [data-testid="stSelectbox"] input {
#       color: #d8b4fe !important;
#   }
pattern2 = re.compile(
    r'[ \t]*\[data-testid="stSelectbox"\] input \{[^{}]*d8b4fe[^{}]*\}\s*',
    re.IGNORECASE
)
content, extra_removed = pattern2.subn('', content)

if content != original_content:
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)

print("Purple blocks removed:", purple_removed)
print("Extra purple-text blocks removed:", extra_removed)
print("Done. Amber blocks (d4a017) should be the only color-coding left.")