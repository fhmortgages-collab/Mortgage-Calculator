with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

original_content = content

replacements = [
(
'''PROPERTY_STYLE_TYPES = [
    "", "Detached", "Semi-Detached", "Townhouse / Row House", "Condo / Apartment",
    "Duplex", "Triplex / Fourplex", "Mobile / Manufactured Home", "Other",
]
PROPERTY_PURPOSE_OPTIONS = ["", "Owner-Occupied (Primary Residence)", "Second Home", "Investment / Rental Property"]
RURAL_URBAN_OPTIONS = ["", "Urban", "Suburban", "Rural", "Agricultural"]
HEATING_TYPE_OPTIONS = ["", "Forced Air (Natural Gas)", "Forced Air (Electric)", "Baseboard (Electric)", "Heat Pump", "Radiant", "Oil", "Propane", "Other"]
COOLING_OPTIONS = ["", "Central Air Conditioning", "Heat Pump", "Window/Wall Unit(s)", "None"]
SEWER_OPTIONS = ["", "Sanitary Sewer (Municipal)", "Septic System", "Other"]
WATER_OPTIONS = ["", "Municipal Water", "Well", "Other"]
TITLE_TYPE_OPTIONS = ["", "Freehold", "Condominium", "Leasehold", "Other"]
FOUNDATION_TYPE_OPTIONS = [
    "", "Poured Concrete", "Concrete Block", "Stone", "Preserved Wood (PWF)",
    "Slab-on-Grade", "Crawl Space", "Pier & Post", "Other",
]
EXTERIOR_FINISH_OPTIONS = [
    "", "Brick", "Brick Veneer", "Vinyl Siding", "Stucco", "Stone", "Stone Veneer",
    "Wood Siding", "Aluminum/Steel Siding", "Fiber Cement (Hardie Board)", "Other",
]
GARAGE_OPTIONS = ["", "None", "Attached", "Detached", "Carport", "Underground Parking", "Other"]''',
'''PROPERTY_STYLE_TYPES = [
    "", "Condo / Apartment", "Detached", "Duplex", "Mobile / Manufactured Home",
    "Semi-Detached", "Townhouse / Row House", "Triplex / Fourplex", "Other",
]
PROPERTY_PURPOSE_OPTIONS = [
    "", "Investment Property (Non-Owner-Occupied / Rental)",
    "Owner-Occupied (Primary Residence)", "Second Home / Vacation Home",
]
RURAL_URBAN_OPTIONS = ["", "Agricultural", "Rural", "Suburban", "Urban"]
HEATING_TYPE_OPTIONS = ["", "Baseboard (Electric)", "Forced Air (Electric)", "Forced Air (Natural Gas)", "Heat Pump", "Oil", "Propane", "Radiant", "Other"]
COOLING_OPTIONS = ["", "Central Air Conditioning", "Heat Pump", "None", "Window/Wall Unit(s)"]
SEWER_OPTIONS = ["", "Sanitary Sewer (Municipal)", "Septic System", "Other"]
WATER_OPTIONS = ["", "Municipal Water", "Well", "Other"]
TITLE_TYPE_OPTIONS = ["", "Condominium", "Freehold", "Leasehold", "Other"]
FOUNDATION_TYPE_OPTIONS = [
    "", "Concrete Block", "Crawl Space", "Pier & Post", "Poured Concrete",
    "Preserved Wood (PWF)", "Slab-on-Grade", "Stone", "Other",
]
EXTERIOR_FINISH_OPTIONS = [
    "", "Aluminum/Steel Siding", "Brick", "Brick Veneer", "Fiber Cement (Hardie Board)",
    "Stone", "Stone Veneer", "Stucco", "Vinyl Siding", "Wood Siding", "Other",
]
GARAGE_OPTIONS = ["", "Attached", "Carport", "Detached", "None", "Underground Parking", "Other"]'''
),
(
'''        with c2:
            st.session_state.subject_condo_raw = money_text_input(
                "Monthly Condo / Strata Fees ($)", st.session_state.subject_condo_raw,
                key="subject_condo_input", placeholder="Enter monthly fee amount (0 if none)",
            )''',
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