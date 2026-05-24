import re
from pathlib import Path

# ============================================================
# Target dashboard file
# ============================================================

html_path = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_all_sizes_toggle.html")

backup_path = Path(
    "/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_table_kneedle_columns_removal_BACKUP.html"
)

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created:\n{backup_path}")
else:
    print(f"Backup already exists:\n{backup_path}")

# ============================================================
# Remove Kneedle-related columns from renderTable() cols array
# ============================================================

patterns = [
    # Trials column
    r"\s*\{\s*k:\s*['\"]Kneedle_Total_Completed_Trials_Mean['\"]\s*,\s*label:\s*['\"]Trials['\"][\s\S]*?\},?\n",

    # Knee trial column
    r"\s*\{\s*k:\s*['\"]Kneedle_Selected_Trial_Number_Mean['\"]\s*,\s*label:\s*['\"]Knee trial['\"][\s\S]*?\},?\n",

    # Kneedle % column
    r"\s*\{\s*k:\s*['\"]Kneedle_Pct['\"]\s*,\s*label:\s*['\"]Kneedle %['\"][\s\S]*?\},?\n",
]

removed_total = 0

for pattern in patterns:
    html, n = re.subn(pattern, "\n", html, count=1)
    removed_total += n

if removed_total != 3:
    print(f"Warning: expected to remove 3 table columns, but removed {removed_total}.")
    print("This may mean one or more columns were already removed or formatted differently.")
else:
    print("Removed Trials, Knee trial, and Kneedle % columns from table.")

# ============================================================
# Clean possible extra blank lines inside cols array
# ============================================================

html = re.sub(
    r"\n\s*\n\s*\{ k: 'Energy_kWh_Mean'",
    "\n      { k: 'Energy_kWh_Mean'",
    html
)

# ============================================================
# Save
# ============================================================

html_path.write_text(html, encoding="utf-8")

print("\nSuccess! Table preview no longer includes Kneedle columns.")
print(f"Updated file:\n{html_path}")
print(f"Backup file:\n{backup_path}")

# ============================================================
# Validation
# ============================================================

checks = {
    "Trials column removed from table label": "label: 'Trials'" not in html and 'label: "Trials"' not in html,
    "Knee trial column removed": "Knee trial" not in html,
    "Kneedle % table column removed": "label: 'Kneedle %'" not in html and 'label: "Kneedle %"' not in html,
}

print("\nValidation:")
for label, ok in checks.items():
    print(f"{'OK' if ok else 'CHECK'}: {label}")