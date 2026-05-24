import re
from pathlib import Path

# ============================================================
# 1) Target HTML
# ============================================================

HTML_PATH = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario.html")
BACKUP_PATH = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_all_sizes_toggle.html")

html = HTML_PATH.read_text(encoding="utf-8")

if not BACKUP_PATH.exists():
    BACKUP_PATH.write_text(html, encoding="utf-8")
    print(f"Backup created:\n{BACKUP_PATH}")
else:
    print(f"Backup already exists:\n{BACKUP_PATH}")


# ============================================================
# 2) Helper: find matching JS brace
# ============================================================

def find_matching_brace(text, open_brace_idx):
    if text[open_brace_idx] != "{":
        raise ValueError("open_brace_idx must point to '{'.")

    depth = 0
    in_string = False
    quote = None
    escape = False

    for i in range(open_brace_idx, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
            continue

        if ch in ['"', "'", "`"]:
            in_string = True
            quote = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i

    raise ValueError("Could not find matching closing brace.")


def replace_class_method(html_text, method_name, new_method_code):
    """
    Replace a method inside a JS class, e.g. buildSizeFilter() { ... }
    """
    pattern = rf"\n\s*{re.escape(method_name)}\s*\([^)]*\)\s*\{{"
    match = re.search(pattern, html_text)

    if not match:
        raise ValueError(f"Could not find method: {method_name}")

    method_start = match.start()
    open_brace = html_text.find("{", match.start())
    close_brace = find_matching_brace(html_text, open_brace)

    return (
        html_text[:method_start]
        + "\n  "
        + new_method_code.strip()
        + html_text[close_brace + 1:]
    )


# ============================================================
# 3) Ensure All Sizes button exists in the sidebar
# ============================================================

if 'id="btn-toggle-all"' not in html and "id='btn-toggle-all'" not in html:
    button_html = '\n        <button class="btn-reset" id="btn-toggle-all" style="margin-top: 8px; background: var(--bg-tint);">All Sizes</button>'

    # Insert after Reset Filters button
    reset_button_pattern = r'(<button\s+class=["\']btn-reset["\']\s+id=["\']btn-reset["\'][\s\S]*?</button>)'

    html_new, n = re.subn(
        reset_button_pattern,
        r"\1" + button_html,
        html,
        count=1
    )

    if n != 1:
        raise ValueError("Could not find the Reset Filters button to insert All Sizes button.")

    html = html_new
    print("Inserted All Sizes button into sidebar.")
else:
    print("All Sizes button already exists. Keeping it.")


# ============================================================
# 4) Add optional active styling for All Sizes button
# ============================================================

css_marker = ".btn-reset:hover { color: var(--accent); border-color: var(--accent); }"

extra_css = """
.btn-reset.active-all {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
}
"""

if ".btn-reset.active-all" not in html:
    if css_marker in html:
        html = html.replace(css_marker, css_marker + "\n" + extra_css, 1)
        print("Added active styling for All Sizes button.")
    else:
        print("CSS marker not found. Skipped active button styling.")


# ============================================================
# 5) Replace buildSizeFilter() with toggle-aware version
# ============================================================

new_build_size_filter = r"""
buildSizeFilter() {
    const host = document.getElementById('filter-size');
    const toggleBtn = document.getElementById('btn-toggle-all');

    const sizes = this.adapter
      .uniqueValues('Sample_Size')
      .map(Number)
      .sort((a, b) => a - b);

    const fmt = n => {
      const value = Number(n);
      if (!Number.isFinite(value)) return String(n);
      if (value >= 1000) {
        const k = value / 1000;
        return Number.isInteger(k)
          ? `${k}k`
          : `${k.toFixed(1).replace(/\.0$/, '')}k`;
      }
      return String(value);
    };

    host.innerHTML = sizes.map(s => `
      <label class="check-item">
        <input type="checkbox" checked data-size="${s}">
        <span class="check-mark"></span>
        <span class="check-label">N = ${fmt(s)}</span>
      </label>`).join('');

    const getCheckedSizes = () =>
      [...host.querySelectorAll('input:checked')].map(x => +x.dataset.size);

    const syncSizeUI = () => {
      const checked = getCheckedSizes();
      const countEl = document.getElementById('count-size');

      if (countEl) {
        countEl.textContent = `${checked.length}/${sizes.length}`;
      }

      if (toggleBtn) {
        const allSelected = checked.length === sizes.length;

        toggleBtn.textContent = allSelected ? 'Clear Sizes' : 'All Sizes';
        toggleBtn.dataset.mode = allSelected ? 'clear' : 'select';
        toggleBtn.classList.toggle('active-all', allSelected);
        toggleBtn.setAttribute(
          'aria-label',
          allSelected ? 'Deselect all sample sizes' : 'Select all sample sizes'
        );
      }

      return checked;
    };

    host.querySelectorAll('input').forEach(input => {
      input.addEventListener('change', () => {
        const checked = syncSizeUI();
        this.store.set({ sizes: checked });
      });
    });

    if (toggleBtn) {
      toggleBtn.onclick = () => {
        const checkedNow = getCheckedSizes();
        const shouldSelectAll = checkedNow.length !== sizes.length;

        host.querySelectorAll('input').forEach(input => {
          input.checked = shouldSelectAll;
        });

        const checked = syncSizeUI();
        this.store.set({ sizes: checked });
      };
    }

    syncSizeUI();
  }
"""

html = replace_class_method(html, "buildSizeFilter", new_build_size_filter)
print("Replaced buildSizeFilter() with All Sizes toggle logic.")


# ============================================================
# 6) Replace bindReset() so Reset also refreshes All Sizes button
# ============================================================

new_bind_reset = r"""
bindReset(defaults) {
    document.getElementById('btn-reset').addEventListener('click', () => {
      document.querySelectorAll('.sidebar input[type="checkbox"]').forEach(i => {
        i.checked = true;
      });

      const modelInputs = [...document.querySelectorAll('#filter-model input')];
      const sizeInputs = [...document.querySelectorAll('#filter-size input')];

      document.getElementById('count-model').textContent =
        `${modelInputs.filter(i => i.checked).length}/${modelInputs.length}`;

      document.getElementById('count-size').textContent =
        `${sizeInputs.filter(i => i.checked).length}/${sizeInputs.length}`;

      const toggleBtn = document.getElementById('btn-toggle-all');
      if (toggleBtn) {
        toggleBtn.textContent = 'Clear Sizes';
        toggleBtn.dataset.mode = 'clear';
        toggleBtn.classList.add('active-all');
        toggleBtn.setAttribute('aria-label', 'Deselect all sample sizes');
      }

      document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));

      const defaultChip = document.querySelector(`.chip[data-metric="${defaults.metric}"]`);
      if (defaultChip) {
        defaultChip.classList.add('active');
      }

      this.store.set({ ...defaults });
    });
  }
"""

html = replace_class_method(html, "bindReset", new_bind_reset)
print("Replaced bindReset() so Reset Filters updates All Sizes button too.")


# ============================================================
# 7) Save
# ============================================================

HTML_PATH.write_text(html, encoding="utf-8")

print("\nSuccess!")
print("All Sizes / Clear Sizes toggle is now wired into the sidebar.")
print(f"Updated HTML:\n{HTML_PATH}")
print(f"Backup file:\n{BACKUP_PATH}")


# ============================================================
# 8) Validation
# ============================================================

checks = [
    'id="btn-toggle-all"',
    "Clear Sizes",
    "All Sizes",
    "this.store.set({ sizes: checked })",
    "syncSizeUI()",
    ".btn-reset.active-all"
]

print("\nValidation:")
for c in checks:
    print(f"{'OK' if c in html else 'MISSING'}: {c}")