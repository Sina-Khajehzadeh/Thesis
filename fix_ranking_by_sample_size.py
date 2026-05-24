from pathlib import Path
import re

# ============================================================
# Target dashboard file
# ============================================================

html_path = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_all_sizes_toggle.html")

backup_path = Path(
    "/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_samplewise_ranking_BACKUP.html"
)

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created:\n{backup_path}")
else:
    print(f"Backup already exists:\n{backup_path}")


# ============================================================
# Helper: find JS method block robustly
# ============================================================

def find_matching_brace(text, open_idx):
    if text[open_idx] != "{":
        raise ValueError("open_idx must point to '{'")

    depth = 0
    in_string = False
    quote = None
    escape = False

    for i in range(open_idx, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
            continue

        if ch in ["'", '"', "`"]:
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


def replace_method(html_text, method_signature, replacement_method):
    start = html_text.find(method_signature)

    if start == -1:
        raise ValueError(f"Could not find method signature: {method_signature}")

    open_brace = html_text.find("{", start)

    if open_brace == -1:
        raise ValueError(f"Could not find opening brace for: {method_signature}")

    close_brace = find_matching_brace(html_text, open_brace)

    return (
        html_text[:start]
        + replacement_method.strip()
        + html_text[close_brace + 1:]
    )


# ============================================================
# Add CSS for sample-size ranking cards
# ============================================================

html = re.sub(
    r"/\* === SAMPLEWISE RANKING FIX START === \*/[\s\S]*?/\* === SAMPLEWISE RANKING FIX END === \*/\s*",
    "",
    html
)

ranking_css = """
/* === SAMPLEWISE RANKING FIX START === */

.ranking-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
  gap: 14px;
}

.ranking-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  background: var(--bg-surface);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.ranking-card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-tint);
}

.ranking-card-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  font-style: italic;
  color: var(--text-primary);
}

.ranking-card-note {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.ranking-mini-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-family: var(--font-mono);
  font-size: 10px;
}

.ranking-mini-table th {
  position: static;
  padding: 7px 8px;
  font-size: 8.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}

.ranking-mini-table td {
  padding: 7px 8px;
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
}

.ranking-mini-table tr:last-child td {
  border-bottom: none;
}

.ranking-mini-table th:first-child,
.ranking-mini-table td:first-child {
  width: 48px;
  text-align: center;
}

.ranking-mini-table th:nth-child(2),
.ranking-mini-table td:nth-child(2) {
  text-align: left;
  width: 125px;
}

.ranking-mini-table th:not(:first-child):not(:nth-child(2)),
.ranking-mini-table td:not(:first-child):not(:nth-child(2)) {
  text-align: right;
}

.ranking-mini-table .model-cell {
  overflow: hidden;
  text-overflow: ellipsis;
}

.ranking-empty {
  font-family: var(--font-mono);
  color: var(--text-tertiary);
  font-size: 12px;
  padding: 16px;
}

/* === SAMPLEWISE RANKING FIX END === */
"""

if "</style>" not in html:
    raise ValueError("Could not find </style>.")

html = html.replace("</style>", ranking_css + "\n</style>", 1)


# ============================================================
# Replace renderRanking(summary)
# ============================================================

new_render_ranking = r"""
renderRanking(summary) {
    const fmtSize = n => {
      const v = Number(n);
      if (!Number.isFinite(v)) return String(n);
      if (v >= 1000) {
        const k = v / 1000;
        return Number.isInteger(k)
          ? `${k}k`
          : `${k.toFixed(1).replace(/\.0$/, '')}k`;
      }
      return String(v);
    };

    const fmtNum = (v, digits = 4) =>
      Number.isFinite(Number(v)) ? Number(v).toFixed(digits) : '—';

    const fmtTime = v =>
      Number.isFinite(Number(v)) ? Number(v).toFixed(2) : '—';

    const fmtEnergy = v => {
      const x = Number(v);
      if (!Number.isFinite(x)) return '—';
      return x < 0.001 ? x.toExponential(2) : x.toFixed(5);
    };

    const selectedSizes = [...new Set(
      summary
        .map(r => Number(r.Sample_Size))
        .filter(v => Number.isFinite(v))
    )].sort((a, b) => a - b);

    if (!selectedSizes.length) {
      document.getElementById('ranking-host').innerHTML =
        `<div class="ranking-empty">No rows available for the current filter selection.</div>`;
      return;
    }

    const medals = ['🥇', '🥈', '🥉'];

    const cards = selectedSizes.map(size => {
      const rows = summary
        .filter(r => Number(r.Sample_Size) === size)
        .map(r => ({
          Model: r.Model,
          AUC: Number(r.AUC_Mean),
          BalAcc: Number(r.BalancedAccuracy_Mean),
          Brier: Number(r.Brier_Mean),
          Time: Number(r.Time_Seconds_Mean),
          Energy: Number(r.Energy_kWh_Mean)
        }))
        .filter(r => Number.isFinite(r.AUC))
        .sort((a, b) => b.AUC - a.AUC)
        .slice(0, 3);

      const body = rows.length
        ? rows.map((r, i) => `
            <tr style="${i === 0 ? 'background: rgba(74,140,82,0.055);' : ''}">
              <td style="font-size:13px;">${medals[i] || i + 1}</td>
              <td class="model-cell">
                <span class="model-dot" style="background:${this.modelColors[r.Model]}"></span>${r.Model}
              </td>
              <td>${fmtNum(r.AUC)}</td>
              <td>${fmtNum(r.BalAcc)}</td>
              <td>${fmtNum(r.Brier)}</td>
              <td>${fmtTime(r.Time)}</td>
              <td>${fmtEnergy(r.Energy)}</td>
            </tr>
          `).join('')
        : `<tr><td colspan="7" class="ranking-empty">No model selected for this sample size.</td></tr>`;

      return `
        <div class="ranking-card">
          <div class="ranking-card-header">
            <span class="ranking-card-title">N = ${fmtSize(size)}</span>
            <span class="ranking-card-note">Top-3 by AUC</span>
          </div>

          <table class="ranking-mini-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Model</th>
                <th>AUC</th>
                <th>Bal.Acc</th>
                <th>Brier</th>
                <th>Time</th>
                <th>Energy</th>
              </tr>
            </thead>
            <tbody>
              ${body}
            </tbody>
          </table>
        </div>
      `;
    }).join('');

    document.getElementById('ranking-host').innerHTML =
      `<div class="ranking-grid">${cards}</div>`;
  }
"""

html = replace_method(
    html_text=html,
    method_signature="renderRanking(summary)",
    replacement_method=new_render_ranking
)


# ============================================================
# Update visible section title/subtitle
# ============================================================

html = html.replace(
    "Overall top-3 ranking",
    "Top-3 ranking by sample size"
)

html = html.replace(
    "aggregated across all sample sizes",
    "one top-3 table per selected sample size"
)


# ============================================================
# Save
# ============================================================

html_path.write_text(html, encoding="utf-8")

print("\nSuccess! Ranking section changed to one top-3 table per sample size.")
print(f"Updated file:\n{html_path}")
print(f"Backup file:\n{backup_path}")

# ============================================================
# Validation
# ============================================================

checks = {
    "New title added": "Top-3 ranking by sample size" in html,
    "Old aggregated subtitle removed": "aggregated across all sample sizes" not in html,
    "Ranking grid CSS added": "ranking-grid" in html,
    "Samplewise renderRanking added": "Top-3 by AUC" in html,
}

print("\nValidation:")
for label, ok in checks.items():
    print(f"{'OK' if ok else 'CHECK'}: {label}")