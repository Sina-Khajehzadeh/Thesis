import json
import re
from pathlib import Path
from collections import Counter, defaultdict

# ============================================================
# 1) Paths
# ============================================================

BASE_DIR = Path("/workspaces/Thesis")

HTML_PATH = BASE_DIR / "No_Budget_FINAL_DASHBOARD_No_Budget_Scenario.html"

JSON_DIR = BASE_DIR / "JSON no_budget files"

PERFORMANCE_JSON_PATH = JSON_DIR / "no_budget_performance_metrics_iter_data.json"

BACKUP_PATH = BASE_DIR / "No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_performance_json_injection.html"

# ============================================================
# 2) Safety checks
# ============================================================

if not HTML_PATH.exists():
    raise FileNotFoundError(f"HTML file not found:\n{HTML_PATH}")

if not PERFORMANCE_JSON_PATH.exists():
    print("Expected performance JSON was not found.")
    print("Looking for possible performance JSON files in:")
    print(JSON_DIR)

    candidates = list(JSON_DIR.glob("*performance*.json")) + list(JSON_DIR.glob("*Performance*.json"))

    if candidates:
        print("\nPossible candidates:")
        for c in candidates:
            print(" -", c.name)
    else:
        print("\nNo performance JSON candidates found.")

    raise FileNotFoundError(f"Performance JSON not found:\n{PERFORMANCE_JSON_PATH}")

# ============================================================
# 3) Load performance JSON
# ============================================================

with open(PERFORMANCE_JSON_PATH, "r", encoding="utf-8") as f:
    performance_rows = json.load(f)

if not isinstance(performance_rows, list):
    raise ValueError("Performance JSON must be a list of row dictionaries.")

print(f"Loaded performance rows: {len(performance_rows)}")

# ============================================================
# 4) Validate and normalize schema
# ============================================================

required_keys = {
    "Scenario",
    "Sample_Size",
    "Model",
    "iteration",
    "AUC",
    "Brier",
    "BalancedAccuracy",
    "Sensitivity",
    "Precision",
}

normalized_rows = []

for idx, row in enumerate(performance_rows):
    if not isinstance(row, dict):
        raise ValueError(f"Row {idx} is not a dictionary.")

    # Normalize possible alternate iteration key
    if "iteration" not in row and "Iteration" in row:
        row["iteration"] = row["Iteration"]

    missing = required_keys - set(row.keys())
    if missing:
        raise ValueError(
            f"Row {idx} is missing required keys: {sorted(missing)}\n"
            f"Row preview: {row}"
        )

    # Keep the row, but make sure core numeric fields are clean
    clean_row = dict(row)

    clean_row["Sample_Size"] = int(clean_row["Sample_Size"])
    clean_row["iteration"] = int(clean_row["iteration"])

    for key in ["AUC", "Brier", "BalancedAccuracy", "Sensitivity", "Precision"]:
        clean_row[key] = None if clean_row[key] is None else float(clean_row[key])

    # Optional runtime/energy fields can stay if present
    for key in ["Time_Seconds", "Time_Without_Kneedle", "Kneedle_Selection_Time", "Energy_kWh"]:
        if key in clean_row and clean_row[key] is not None:
            clean_row[key] = float(clean_row[key])

    normalized_rows.append(clean_row)

performance_rows = normalized_rows

# ============================================================
# 5) Diagnostics
# ============================================================

models = sorted({r["Model"] for r in performance_rows})
sizes = sorted({r["Sample_Size"] for r in performance_rows})

print("\nModels found:")
for m in models:
    print(" -", m)

print("\nSample sizes found:")
print(sizes)

cell_counter = Counter((r["Model"], r["Sample_Size"]) for r in performance_rows)

print("\nIteration counts per model/sample-size cell:")
unusual_cells = []

for size in sizes:
    counts_at_size = {
        model: cell_counter[(model, size)]
        for model in models
    }
    unique_counts = sorted(set(counts_at_size.values()))
    print(f"N={size}: {counts_at_size}")

    if len(unique_counts) != 1 or unique_counts[0] != 10:
        unusual_cells.append((size, counts_at_size))

if unusual_cells:
    print("\nNote: Some cells are not exactly 10 iterations.")
    print("This is not automatically wrong if your PKL contains more/less completed iterations.")
else:
    print("\nAll model/sample-size cells have exactly 10 iterations.")

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
# 7) Replace embedded iter-data block
# ============================================================

json_string = json.dumps(
    performance_rows,
    ensure_ascii=False,
    separators=(",", ":")
)

# Avoid accidentally closing the script tag if JSON ever contains this string
json_string = json_string.replace("</script>", "<\\/script>")

new_iter_block = (
    f'<script id="iter-data" type="application/json">'
    f'{json_string}'
    f'</script>'
)

pattern = (
    r'<script\s+id=["\']iter-data["\']\s+type=["\']application/json["\']>'
    r'[\s\S]*?'
    r'</script>'
)

html_new, n_replaced = re.subn(
    pattern,
    new_iter_block,
    html,
    count=1
)

if n_replaced != 1:
    raise ValueError(
        "Could not replace the existing iter-data block. "
        "Check that the HTML contains <script id=\"iter-data\" type=\"application/json\">."
    )

# ============================================================
# 8) Update visible box-plot note
# ============================================================

html_new = html_new.replace(
    "720 raw iterations · 10 per cell",
    f"{len(performance_rows)} raw PKL iterations · observed values"
)

html_new = html_new.replace(
    "Source file provides raw per-iteration values, so these box plots are computed directly from observed data — medians, IQRs and whiskers reflect the true distribution.",
    "PKL-derived per-iteration values are embedded directly, so these box plots are computed from the real observed iteration-level metrics."
)

# ============================================================
# 9) Write updated HTML
# ============================================================

HTML_PATH.write_text(html_new, encoding="utf-8")

print("\nSuccess!")
print("Replaced the dashboard iter-data block with the PKL-derived performance JSON.")
print(f"Updated HTML:\n{HTML_PATH}")

print("\nThis updates the performance box-plots for:")
print("AUC, Brier, Balanced Accuracy, Sensitivity, and Precision.")