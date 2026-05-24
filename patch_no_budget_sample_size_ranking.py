import re
from pathlib import Path

# ============================================================
# Target dashboard file
# ============================================================

html_path = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario.html")

backup_path = Path(
    "/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_sample_size_ranking_PATCH_BACKUP.html"
)

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created:\n{backup_path}")
else:
    print(f"Backup already exists:\n{backup_path}")


# ============================================================
# Helper: JS brace matcher
# ============================================================

def find_matching_brace(text, open_idx):
    """
    Finds matching closing brace for text[open_idx] == '{'.
    Ignores braces inside JS strings/template strings.
    """
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


# ============================================================
# 1) Add CSS for sample-size ranking cards
# ============================================================

html = re.sub(
    r"/\* === SAMPLE SIZE TOP-3 RANKING PATCH START === \*/[\s\S]*?/\* === SAMPLE SIZE TOP-3 RANKING PATCH END === \*/\s*",
    "",
    html
)

ranking_css = """
/* === SAMPLE SIZE TOP-3 RANKING PATCH START === */

.ranking-explain {
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--text-tertiary);
  font-style: italic;
  margin: 0 0 8px;
  padding: 8px 12px;
  background: var(--bg-tint);
  border-left: 2px solid var(--warning);
  border-radius: var(--radius-sm);
}

.ranking-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(280px, 1fr));
  gap: 16px;
}

.ranking-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.ranking-card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  background: var(--bg-tint);
  border-bottom: 1px solid var(--border-subtle);
}

.ranking-card-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.ranking-card-note {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.13em;
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
  background: var(--bg-surface);
  padding: 8px 6px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 8.5px;
  text-align: center;
}

.ranking-mini-table td {
  padding: 7px 6px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  text-align: center;
  white-space: nowrap;
}

.ranking-mini-table tr:last-child td {
  border-bottom: none;
}

.ranking-mini-table .rank-model {
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  width: 140px;
}

.ranking-mini-table th.rank-model {
  text-align: left;
}

.ranking-mini-table .rank-overall {
  font-weight: 700;
  color: var(--accent);
}

.rank-dot-model {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  margin-right: 7px;
  vertical-align: middle;
}

.rank-point {
  display: inline-block;
  width: 11px;
  height: 11px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--bg-surface);
  vertical-align: middle;
}

.rank-point.on {
  background: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(37, 99, 179, 0.10);
}

@media (max-width: 1400px) {
  .ranking-card-grid {
    grid-template-columns: repeat(2, minmax(280px, 1fr));
  }
}

@media (max-width: 900px) {
  .ranking-card-grid {
    grid-template-columns: 1fr;
  }
}

/* === SAMPLE SIZE TOP-3 RANKING PATCH END === */
"""

if "</style>" not in html:
    raise ValueError("Could not find </style> tag.")

html = html.replace("</style>", ranking_css + "\n</style>", 1)


# ============================================================
# 2) Replace renderRanking(...) method
# ============================================================

new_render_ranking_method = r"""
renderRanking(summary) {
    const container =
      document.getElementById('ranking-table') ||
      document.getElementById('ranking-output') ||
      document.getElementById('ranking-cards');

    if (!container) {
      console.warn('Ranking container not found.');
      return;
    }

    const finite = (v) => Number.isFinite(Number(v));

    const fmt = (v, digits = 4) => {
      const n = Number(v);
      return Number.isFinite(n) ? n.toFixed(digits) : '—';
    };

    const sampleLabel = (n) => {
      const v = Number(n);
      if (!Number.isFinite(v)) return String(n);
      if (v >= 1000) {
        const k = v / 1000;
        return Number.isInteger(k) ? `${k}k` : `${k.toFixed(1)}k`;
      }
      return String(v);
    };

    const metrics = [
      {
        key: 'AUC_Mean',
        label: 'AUC',
        short: 'AUC',
        direction: 'higher',
        digits: 4
      },
      {
        key: 'Brier_Mean',
        label: 'Brier',
        short: 'Brier',
        direction: 'lower',
        digits: 4
      },
      {
        key: 'BalancedAccuracy_Mean',
        label: 'Balanced accuracy',
        short: 'BalAcc',
        direction: 'higher',
        digits: 4
      },
      {
        key: 'Sensitivity_Mean',
        label: 'Sensitivity',
        short: 'Sens',
        direction: 'higher',
        digits: 4
      },
      {
        key: 'Precision_Mean',
        label: 'Precision',
        short: 'Prec',
        direction: 'higher',
        digits: 4
      },
      {
        key: 'Time_Seconds_Mean',
        label: 'Runtime',
        short: 'Time',
        direction: 'lower',
        digits: 2
      },
      {
        key: 'Energy_kWh_Mean',
        label: 'Energy',
        short: 'Energy',
        direction: 'lower',
        digits: 5
      }
    ];

    const sizes = [...new Set(
      summary
        .map(r => Number(r.Sample_Size))
        .filter(Number.isFinite)
    )].sort((a, b) => a - b);

    const cardsHtml = sizes.map(size => {
      const rows = summary
        .filter(r => Number(r.Sample_Size) === size)
        .map(r => ({ ...r, OverallPoints: 0, Top3Flags: {} }));

      metrics.forEach(metric => {
        const sorted = [...rows]
          .filter(r => finite(r[metric.key]))
          .sort((a, b) => {
            const av = Number(a[metric.key]);
            const bv = Number(b[metric.key]);
            return metric.direction === 'higher'
              ? bv - av
              : av - bv;
          });

        const top3 = new Set(sorted.slice(0, 3).map(r => r.Model));

        rows.forEach(r => {
          const isTop3 = top3.has(r.Model);
          r.Top3Flags[metric.short] = isTop3;

          if (isTop3) {
            r.OverallPoints += 1;
          }
        });
      });

      rows.sort((a, b) => {
        if (b.OverallPoints !== a.OverallPoints) {
          return b.OverallPoints - a.OverallPoints;
        }

        const aucA = Number(a.AUC_Mean);
        const aucB = Number(b.AUC_Mean);

        if (Number.isFinite(aucA) && Number.isFinite(aucB) && aucB !== aucA) {
          return aucB - aucA;
        }

        return String(a.Model).localeCompare(String(b.Model));
      });

      const bodyRows = rows.map(r => {
        const metricCells = metrics.map(metric => {
          const active = r.Top3Flags[metric.short];
          const value = fmt(r[metric.key], metric.digits);
          const title = `${metric.label}: ${value}`;

          return `
            <td title="${title}">
              <span class="rank-point ${active ? 'on' : ''}"></span>
            </td>
          `;
        }).join('');

        const color = this.modelColors[r.Model] || '#7a8294';

        return `
          <tr>
            <td class="rank-model">
              <span class="rank-dot-model" style="background:${color};"></span>
              ${r.Model}
            </td>
            ${metricCells}
            <td class="rank-overall">${r.OverallPoints}</td>
          </tr>
        `;
      }).join('');

      return `
        <div class="ranking-card">
          <div class="ranking-card-header">
            <div class="ranking-card-title">N = ${sampleLabel(size)}</div>
            <div class="ranking-card-note">Top-3 count</div>
          </div>

          <table class="ranking-mini-table">
            <thead>
              <tr>
                <th class="rank-model">Model</th>
                ${metrics.map(m => `<th>${m.short}</th>`).join('')}
                <th>Overall</th>
              </tr>
            </thead>
            <tbody>
              ${bodyRows}
            </tbody>
          </table>
        </div>
      `;
    }).join('');

    container.innerHTML = `
      <div class="ranking-explain">
        Blue point = model ranked in the top 3 among all six models for that metric within the same sample size.
        For Brier, Time, and Energy, lower is better; for AUC, balanced accuracy, sensitivity, and precision, higher is better.
        Overall = sum of top-3 points across all metrics.
      </div>
      <div class="ranking-card-grid">
        ${cardsHtml}
      </div>
    `;
  }
"""

method_match = re.search(r"\brenderRanking\s*\([^)]*\)\s*\{", html)

if not method_match:
    raise ValueError("Could not find renderRanking(...) method in the HTML.")

method_start = method_match.start()
open_brace = html.find("{", method_match.start())
close_brace = find_matching_brace(html, open_brace)

html = (
    html[:method_start]
    + new_render_ranking_method.strip()
    + html[close_brace + 1:]
)


# ============================================================
# 3) Update visible heading/note text
# ============================================================

html = html.replace(
    "AGGREGATED ACROSS ALL SAMPLE SIZES",
    "PERFORMANCE POINTS × SELECTED SAMPLE SIZES"
)

html = html.replace(
    "aggregated across all sample sizes",
    "summarized separately for each selected sample size"
)

# Keep the main section title if it exists.
# You can change this manually later if desired.


# ============================================================
# 4) Save updated HTML
# ============================================================

html_path.write_text(html, encoding="utf-8")

print("\nSuccess! Ranking section changed to sample-size-specific top-3 cards.")
print(f"Updated file:\n{html_path}")
print(f"Backup file:\n{backup_path}")

print("\nNew ranking logic:")
print("AUC, BalAcc, Sens, Prec: higher is better")
print("Brier, Time, Energy: lower is better")
print("Overall = number of top-3 points per model within each sample size")

# ============================================================
# 5) Validation
# ============================================================

checks = {
    "ranking CSS added": "SAMPLE SIZE TOP-3 RANKING PATCH START" in html,
    "ranking cards added": "ranking-card-grid" in html,
    "Time metric included": "Time_Seconds_Mean" in html,
    "Energy metric included": "Energy_kWh_Mean" in html,
    "new explanation included": "Blue point = model ranked in the top 3" in html,
}

print("\nValidation:")
for label, ok in checks.items():
    print(f"{'OK' if ok else 'CHECK'}: {label}")