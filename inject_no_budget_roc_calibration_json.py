import json
import re
from pathlib import Path
from collections import Counter

# ============================================================
# 1) Paths
# ============================================================

BASE_DIR = Path("/workspaces/Thesis")

HTML_PATH = BASE_DIR / "No_Budget_FINAL_DASHBOARD_No_Budget_Scenario.html"

JSON_DIR = BASE_DIR / "JSON no_budget files"

ROC_CAL_JSON_PATH = JSON_DIR / "no_budget_ROC_Calibration_curve_data.json"

BACKUP_PATH = BASE_DIR / "No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_ROC_Calibration_json_injection.html"

# ============================================================
# 2) Safety checks
# ============================================================

if not HTML_PATH.exists():
    raise FileNotFoundError(f"HTML file not found:\n{HTML_PATH}")

if not ROC_CAL_JSON_PATH.exists():
    print("Expected ROC/Calibration JSON was not found.")
    print("Looking for possible curve JSON files in:")
    print(JSON_DIR)

    candidates = (
        list(JSON_DIR.glob("*ROC*.json")) +
        list(JSON_DIR.glob("*Calibration*.json")) +
        list(JSON_DIR.glob("*curve*.json"))
    )

    if candidates:
        print("\nPossible candidates:")
        for c in candidates:
            print(" -", c.name)

    raise FileNotFoundError(f"ROC/Calibration JSON not found:\n{ROC_CAL_JSON_PATH}")

# ============================================================
# 3) Load ROC/Calibration JSON
# ============================================================

with open(ROC_CAL_JSON_PATH, "r", encoding="utf-8") as f:
    curve_rows = json.load(f)

if not isinstance(curve_rows, list):
    raise ValueError("ROC/Calibration JSON must be a list of row dictionaries.")

print(f"Loaded ROC/Calibration rows: {len(curve_rows)}")

# ============================================================
# 4) Validate schema
# ============================================================

required_keys = {
    "Scenario",
    "Source_File",
    "Sample_Size",
    "Model",
    "Plot_Type",
    "Curve_Role",
    "Point_Index",
    "X_Value",
    "Y_Value",
}

for idx, row in enumerate(curve_rows[:50]):
    missing = required_keys - set(row.keys())
    if missing:
        raise ValueError(
            f"Row {idx} is missing required keys: {sorted(missing)}\n"
            f"Row preview: {row}"
        )

# ============================================================
# 5) Diagnostics
# ============================================================

plot_counter = Counter(r.get("Plot_Type") for r in curve_rows)
role_counter = Counter(r.get("Curve_Role") for r in curve_rows)
sample_counter = Counter(r.get("Sample_Size") for r in curve_rows)

models = sorted({
    r.get("Model")
    for r in curve_rows
    if r.get("Curve_Role") == "model"
})

print("\nRows by plot type:")
print(dict(plot_counter))

print("\nRows by curve role:")
print(dict(role_counter))

print("\nModels found:")
for m in models:
    print(" -", m)

print("\nSample sizes found:")
print(sorted(sample_counter.keys()))

# ============================================================
# 6) Read HTML and create backup
# ============================================================

html = HTML_PATH.read_text(encoding="utf-8")

if not BACKUP_PATH.exists():
    BACKUP_PATH.write_text(html, encoding="utf-8")
    print(f"\nBackup created:\n{BACKUP_PATH}")
else:
    print(f"\nBackup already exists:\n{BACKUP_PATH}")

# ============================================================
# 7) Build script block
# ============================================================

json_string = json.dumps(
    curve_rows,
    ensure_ascii=False,
    separators=(",", ":")
)

json_string = json_string.replace("</script>", "<\\/script>")

new_curve_block = (
    f'<script id="roc-calibration-data" type="application/json">'
    f'{json_string}'
    f'</script>\n'
)

# Remove existing roc-calibration-data block if present
html = re.sub(
    r'<script\s+id=["\']roc-calibration-data["\']\s+type=["\']application/json["\']>'
    r'[\s\S]*?'
    r'</script>\s*',
    "",
    html,
    flags=re.DOTALL
)

# Insert before main dashboard JS
marker = "<script>\nclass DataAdapter"

if marker not in html:
    raise ValueError(
        "Could not find main dashboard script marker: <script>\\nclass DataAdapter"
    )

html_new = html.replace(marker, new_curve_block + marker, 1)

# ============================================================
# 8) Write updated HTML
# ============================================================

HTML_PATH.write_text(html_new, encoding="utf-8")

print("\nSuccess!")
print("Embedded ROC/Calibration JSON into the dashboard HTML.")
print(f"Updated HTML:\n{HTML_PATH}")

print("\nThis only injects the data block.")
print("Next step: wire the ROC and calibration renderers to read roc-calibration-data.")