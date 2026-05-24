import re
from pathlib import Path

# ============================================================
# Target dashboard file
# ============================================================

html_path = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario.html")

backup_path = Path(
    "/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_header_pills_cleanup_BACKUP.html"
)

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created:\n{backup_path}")
else:
    print(f"Backup already exists:\n{backup_path}")


# ============================================================
# 1) Change Scenario pill
# ============================================================

html, n_scenario = re.subn(
    r'<span class="meta-pill">\s*Scenario:\s*<strong>.*?</strong>\s*</span>',
    '<span class="meta-pill">Scenario: <strong>No Budgeting Runtime</strong></span>',
    html,
    count=1,
    flags=re.DOTALL
)

if n_scenario != 1:
    print("Warning: Scenario pill was not replaced. It may have a different structure.")


# ============================================================
# 2) Remove MCAR pill
# ============================================================

html, n_mcar = re.subn(
    r'\s*<span class="meta-pill">\s*MCAR:\s*<strong>.*?</strong>\s*</span>',
    '',
    html,
    count=1,
    flags=re.DOTALL
)


# ============================================================
# 3) Remove raw iterations pill
#    Example: <span class="meta-pill"><strong>750</strong> raw iterations</span>
# ============================================================

html, n_raw_1 = re.subn(
    r'\s*<span class="meta-pill">\s*<strong>\s*\d+\s*</strong>\s*raw iterations\s*</span>',
    '',
    html,
    count=1,
    flags=re.DOTALL
)

# Fallback if the number is not inside <strong>
html, n_raw_2 = re.subn(
    r'\s*<span class="meta-pill">\s*\d+\s*raw iterations\s*</span>',
    '',
    html,
    count=1,
    flags=re.DOTALL
)


# ============================================================
# 4) Keep Iterations and cells untouched
# ============================================================
# This script intentionally keeps:
# - Iterations: 10
# - 72 / 72 cells


# ============================================================
# 5) Save updated HTML
# ============================================================

html_path.write_text(html, encoding="utf-8")

print("\nSuccess! Top header pills cleaned.")
print(f"Updated file:\n{html_path}")
print(f"Backup file:\n{backup_path}")

print("\nChanges:")
print(f"Scenario pill replaced: {n_scenario}")
print(f"MCAR pill removed: {n_mcar}")
print(f"Raw iterations pill removed: {n_raw_1 + n_raw_2}")

print("\nValidation:")
print("Scenario: No Budgeting Runtime:", "No Budgeting Runtime" in html)
print("MCAR removed:", "MCAR:" not in html)
print("raw iterations removed:", "raw iterations" not in html)
print("Iterations kept:", "Iterations:" in html)
print("cells kept:", "cells" in html)