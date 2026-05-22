import json
import re
from pathlib import Path

# ============================================================
# File paths
# ============================================================

html_input_path = Path("FINAL_DASHBOARD_REVIEW.html")
json_input_path = Path("dashboard_compatible_ROC_Calibration_curve_data.json")
html_output_path = Path("FINAL_DASHBOARD_REVIEW.html")

print("Starting ROC & Calibration data injection...")

try:
    # Read the already dashboard-compatible JSON exactly as it is
    with open(json_input_path, "r", encoding="utf-8") as f:
        curve_records = json.load(f)

    # Basic schema validation
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

    missing_examples = []
    for i, rec in enumerate(curve_records[:20]):
        missing = required_keys - set(rec.keys())
        if missing:
            missing_examples.append((i, sorted(missing)))

    if missing_examples:
        raise ValueError(f"JSON schema mismatch. Missing keys in examples: {missing_examples}")

    # Read current HTML
    html_content = html_input_path.read_text(encoding="utf-8")

    # Compact JSON for embedding
    curve_json_str = json.dumps(curve_records, ensure_ascii=False, separators=(",", ":"))

    new_tag = f'<script id="roc-calibration-data" type="application/json">{curve_json_str}</script>\n'

    # Remove old roc-calibration-data block if it already exists
    html_content = re.sub(
        r'<script\s+id=["\']roc-calibration-data["\']\s+type=["\']application/json["\']>.*?</script>\s*',
        "",
        html_content,
        flags=re.DOTALL
    )

    # Insert BEFORE the main dashboard JS starts.
    # This is important because DataAdapter.fromEmbedded() must find it when the dashboard script runs.
    marker = "<script>\nclass DataAdapter"

    if marker not in html_content:
        raise ValueError("Could not find the main dashboard script marker: <script>\\nclass DataAdapter")

    html_content = html_content.replace(
        marker,
        new_tag + marker,
        1
    )

    html_output_path.write_text(html_content, encoding="utf-8")

    print("Success!")
    print(f"Embedded {len(curve_records)} ROC/Calibration rows into: {html_output_path}")

    # Quick diagnostics
    n_roc = sum(1 for r in curve_records if r.get("Plot_Type") == "ROC")
    n_cal = sum(1 for r in curve_records if r.get("Plot_Type") == "Calibration")
    n_ref = sum(1 for r in curve_records if r.get("Curve_Role") == "reference")

    print(f"ROC rows: {n_roc}")
    print(f"Calibration rows: {n_cal}")
    print(f"Reference-line rows: {n_ref}")

except Exception as e:
    print(f"An error occurred: {e}")