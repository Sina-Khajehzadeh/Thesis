import re
from pathlib import Path

# ============================================================
# Target dashboard file
# ============================================================

html_path = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_all_sizes_toggle.html")

backup_path = Path(
    "/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_table_alignment_BACKUP.html"
)

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created:\n{backup_path}")
else:
    print(f"Backup already exists:\n{backup_path}")

# ============================================================
# Remove old table-alignment patch if script is rerun
# ============================================================

html = re.sub(
    r"/\* === TABLE ALIGNMENT FIX START === \*/[\s\S]*?/\* === TABLE ALIGNMENT FIX END === \*/\s*",
    "",
    html
)

# ============================================================
# CSS fix
# ============================================================

table_alignment_css = """
/* === TABLE ALIGNMENT FIX START === */

/* Keep the table geometry stable */
.table-wrap table {
  table-layout: fixed;
  width: 100%;
  min-width: 1180px;
}

/* Use tabular numbers so digits align cleanly */
.table-wrap th,
.table-wrap td {
  font-variant-numeric: tabular-nums;
  vertical-align: middle;
}

/* First column is textual: keep left aligned */
.table-wrap th:first-child,
.table-wrap td:first-child {
  text-align: left;
  width: 170px;
}

/* All remaining columns are numeric: align headers with values */
.table-wrap th:not(:first-child),
.table-wrap td:not(:first-child) {
  text-align: right;
}

/* Keep the model-name column readable */
.table-wrap td.model-cell {
  text-align: left;
}

/* Give stable widths to each table column */
.table-wrap th:nth-child(2),
.table-wrap td:nth-child(2) {
  width: 85px;
}

.table-wrap th:nth-child(3),
.table-wrap td:nth-child(3),
.table-wrap th:nth-child(4),
.table-wrap td:nth-child(4),
.table-wrap th:nth-child(5),
.table-wrap td:nth-child(5),
.table-wrap th:nth-child(6),
.table-wrap td:nth-child(6),
.table-wrap th:nth-child(7),
.table-wrap td:nth-child(7) {
  width: 145px;
}

.table-wrap th:nth-child(8),
.table-wrap td:nth-child(8) {
  width: 110px;
}

.table-wrap th:nth-child(9),
.table-wrap td:nth-child(9) {
  width: 135px;
}

/* Make header labels visually centered over their numeric columns */
.table-wrap th {
  white-space: nowrap;
}

/* === TABLE ALIGNMENT FIX END === */
"""

# Insert before </style>
if "</style>" not in html:
    raise ValueError("Could not find </style> tag.")

html = html.replace("</style>", table_alignment_css + "\n</style>", 1)

# ============================================================
# Save
# ============================================================

html_path.write_text(html, encoding="utf-8")

print("\nSuccess! Table headers are now aligned with their column values.")
print(f"Updated file:\n{html_path}")
print(f"Backup file:\n{backup_path}")

# ============================================================
# Validation
# ============================================================

checks = {
    "table-layout fixed added": "table-layout: fixed" in html,
    "numeric headers right aligned": ".table-wrap th:not(:first-child)" in html,
    "model column left aligned": ".table-wrap th:first-child" in html,
}

print("\nValidation:")
for label, ok in checks.items():
    print(f"{'OK' if ok else 'CHECK'}: {label}")