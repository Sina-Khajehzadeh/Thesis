# bundle.py
import re

def bundle():
    # 1. Read your dashboard HTML template
    with open("budget Scenario Summary dashboard.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # 2. Read your fresh, new JSON data file
    with open("dashboard_compatible_iter_data.json", "r", encoding="utf-8") as f:
        json_data = f.read()
    
    # 3. Robust replacement: This regex finds the 'iter-data' script tag 
    # and completely replaces everything inside it, even if old data is sitting there!
    pattern = r'(<script id="iter-data" type="application/json">)(.*?)(</script>)'
    replacement = f'\\1\n{json_data}\n\\3'
    
    updated_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    
    # 4. Save the final deliverable file
    with open("FINAL_DASHBOARD_REVIEW.html", "w", encoding="utf-8") as f:
        f.write(updated_html)
    
    print("Success! Overwrote and created a true 'FINAL_DASHBOARD_REVIEW.html' with fresh values.")

bundle()