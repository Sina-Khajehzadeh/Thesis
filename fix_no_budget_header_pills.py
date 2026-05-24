import re
from pathlib import Path

# ============================================================
# Target dashboard file
# ============================================================

html_path = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_all_sizes_toggle.html")

backup_path = Path(
    "/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_header_pill_fix_BACKUP.html"
)

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created:\n{backup_path}")
else:
    print(f"Backup already exists:\n{backup_path}")

# ============================================================
# 1) Replace Scenario pill text
# ============================================================

html = re.sub(
    r'<span class="meta-pill">\s*Scenario:\s*<strong>.*?</strong>\s*</span>',
    '<span class="meta-pill">Scenario: <strong>No Budgeting on Runtime</strong></span>',
    html,
    count=1,
    flags=re.DOTALL
)

# ============================================================
# 2) Remove MCAR: 0% pill
# ============================================================

html = re.sub(
    r'\s*<span class="meta-pill">\s*MCAR:\s*<strong>.*?</strong>\s*</span>',
    '',
    html,
    count=1,
    flags=re.DOTALL
)

# ============================================================
# 3) Remove raw-iterations pill, e.g. "60 raw iterations"
# ============================================================

html = re.sub(
    r'\s*<span class="meta-pill">\s*<strong>\s*\d+\s*</strong>\s*raw iterations\s*</span>',
    '',
    html,
    count=1,
    flags=re.DOTALL
)

# Also handle possible non-strong version, just in case
html = re.sub(
    r'\s*<span class="meta-pill">\s*\d+\s*raw iterations\s*</span>',
    '',
    html,
    count=1,
    flags=re.DOTALL
)

# ============================================================
# Save updated HTML
# ============================================================

html_path.write_text(html, encoding="utf-8")

print("\nSuccess! Header pills updated.")
print(f"Updated file:\n{html_path}")

# ============================================================
# Validation
# ============================================================

checks = {
    "Scenario changed": "No Budgeting on Runtime" in html,
    "MCAR pill removed": "MCAR:" not in html,
    "raw iterations pill removed": "raw iterations" not in html,
}

print("\nValidation:")
for label, ok in checks.items():
    print(f"{'OK' if ok else 'CHECK'}: {label}")