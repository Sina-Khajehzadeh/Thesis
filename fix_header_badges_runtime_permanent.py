from pathlib import Path
import re

html_path = Path("FINAL_DASHBOARD_Budget_Scenario_Summary.html")
backup_path = Path("FINAL_DASHBOARD_Budget_Scenario_Summary_before_header_runtime_fix.html")

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created: {backup_path}")

# Remove older version if you run this more than once
html = re.sub(
    r"<script\s+id=[\"']header-badge-runtime-fix[\"']>[\s\S]*?</script>\s*",
    "",
    html,
    flags=re.DOTALL
)

header_fix_script = r"""
<script id="header-badge-runtime-fix">
(() => {
  function deepestMatchingElement(pattern) {
    const candidates = [...document.querySelectorAll("body *")]
      .filter(el => {
        const text = (el.textContent || "").trim();
        return pattern.test(text);
      });

    return candidates.find(el =>
      ![...el.children].some(child =>
        pattern.test((child.textContent || "").trim())
      )
    );
  }

  function fixHeaderBadges() {
    const scenarioEl = deepestMatchingElement(/^Scenario:\s*MCAR_Full$/);

    if (scenarioEl) {
      scenarioEl.textContent = "Scenario: TabPFN Budgeting Runtime";
    }

    const mcarEl = deepestMatchingElement(/^MCAR:\s*0%$/);

    if (mcarEl) {
      mcarEl.remove();
    }
  }

  // Run immediately
  fixHeaderBadges();

  // Run again after dashboard scripts finish rendering
  setTimeout(fixHeaderBadges, 100);
  setTimeout(fixHeaderBadges, 500);
  setTimeout(fixHeaderBadges, 1200);

  // Keep it fixed if dashboard rerenders the header
  const observer = new MutationObserver(() => {
    fixHeaderBadges();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true
  });
})();
</script>
"""

if "</body>" not in html:
    raise ValueError("Could not find </body> in the HTML file.")

html = html.replace("</body>", header_fix_script + "\n</body>", 1)

html_path.write_text(html, encoding="utf-8")

print("Success! Runtime header badge fix injected permanently.")
print(f"Updated file: {html_path}")
print(f"Backup file: {backup_path}")
print("\nExpected visible result:")
print("Scenario: TabPFN Budgeting Runtime")
print("MCAR: 0% badge removed")