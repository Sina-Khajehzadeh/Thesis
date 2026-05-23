from pathlib import Path

# ============================================================
# Target HTML file
# ============================================================

html_path = Path("FINAL_DASHBOARD_REVIEW_before_real_curve_override.html")
backup_path = Path("FINAL_DASHBOARD_REVIEW_before_budget_composition_permanent_BACKUP.html")

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created: {backup_path}")


# ============================================================
# Robust JS block finder
# ============================================================

def find_matching_paren(text, start_idx):
    if text[start_idx] != "(":
        raise ValueError("start_idx must point to '('")

    depth = 0
    in_string = False
    quote = None
    escape = False

    for i in range(start_idx, len(text)):
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

        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i

    raise ValueError("Could not find matching closing parenthesis.")


def replace_chart_register_block(html_text, chart_name, new_block):
    marker_single = f"charts.register('{chart_name}'"
    marker_double = f'charts.register("{chart_name}"'

    start = html_text.find(marker_single)
    if start == -1:
        start = html_text.find(marker_double)

    if start == -1:
        raise ValueError(f"Could not find charts.register('{chart_name}') block.")

    open_paren = html_text.find("(", start)
    close_paren = find_matching_paren(html_text, open_paren)

    end = close_paren + 1

    if end < len(html_text) and html_text[end] == ";":
        end += 1

    return html_text[:start] + new_block.strip() + html_text[end:]


# ============================================================
# Permanent corrected budget composition plot
# ============================================================

new_budget_util_block = r"""
charts.register('budget-util', { render(elId, summary, ctx) {

  const MODEL_ORDER = [
    "TabPFN",
    "L-SLR",
    "RandomForest",
    "XGBoost",
    "CatBoost",
    "Augmented_SLR"
  ];

  function safeNumber(v) {
    const x = Number(v);
    return Number.isFinite(x) ? x : null;
  }

  function rgbaFromHex(hex, alpha) {
    if (!hex || typeof hex !== "string" || !hex.startsWith("#") || hex.length !== 7) {
      return hex;
    }

    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);

    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function formatN(n) {
    const v = Number(n);

    if (!Number.isFinite(v)) return String(n);

    if (v >= 1000) {
      const k = v / 1000;
      return Number.isInteger(k) ? `${k}k` : `${k.toFixed(1)}k`;
    }

    return String(v);
  }

  const availableSizes = [...new Set(
    summary
      .map(r => Number(r.Sample_Size))
      .filter(v => Number.isFinite(v))
  )].sort((a, b) => a - b);

  if (!availableSizes.length) {
    Plotly.react(elId, [], LAYOUT_BASE, PLOT_CONFIG);
    return;
  }

  // Design choice:
  // Keep the plot readable by showing one sample size at a time.
  // If several sample-size chips are selected, use the largest selected N.
  const activeSize = availableSizes[availableSizes.length - 1];

  const rowsAtN = summary.filter(r =>
    Number(r.Sample_Size) === Number(activeSize)
  );

  const selectedModels = MODEL_ORDER.filter(model =>
    ctx.models.includes(model) &&
    rowsAtN.some(r => r.Model === model)
  );

  // Global denominator:
  // TabPFN-derived tuning budget at this sample size.
  // Prefer the TabPFN row. If TabPFN is filtered out, use the field available
  // inside any selected row, because TabPFN_Budget_Used_Mean is stored per row.
  const tabpfnRow = rowsAtN.find(r => r.Model === "TabPFN");

  const globalBudget =
    safeNumber(tabpfnRow?.TabPFN_Budget_Used_Mean) ??
    safeNumber(tabpfnRow?.Actual_Total_Runtime_Mean) ??
    safeNumber(tabpfnRow?.Budgeted_Total_Runtime_Mean) ??
    safeNumber(rowsAtN[0]?.TabPFN_Budget_Used_Mean);

  if (!Number.isFinite(globalBudget) || globalBudget <= 0) {
    Plotly.react(elId, [], LAYOUT_BASE, PLOT_CONFIG);
    console.warn("Invalid TabPFN budget denominator for budget-util plot.", {
      activeSize,
      globalBudget,
      rowsAtN
    });
    return;
  }

  const plotRows = selectedModels.map(model => {
    const row = rowsAtN.find(r => r.Model === model);

    const budgetedTotal = safeNumber(row?.Budgeted_Total_Runtime_Mean);
    const tuningRaw = safeNumber(row?.Optuna_Tuning_Time_Capped_Mean);
    const finalRaw = safeNumber(row?.Final_Fit_Predict_Time_Mean);

    let tuningSec = 0;
    let finalSec = 0;
    let totalSec = 0;

    if (model === "TabPFN") {
      // TabPFN is the reference budget.
      // It has no Optuna tuning loop, so display it as the 100% baseline.
      tuningSec = 0;
      finalSec = globalBudget;
      totalSec = globalBudget;
    } else {
      tuningSec = tuningRaw ?? 0;

      if (finalRaw != null) {
        finalSec = finalRaw;
      } else if (budgetedTotal != null) {
        finalSec = Math.max(budgetedTotal - tuningSec, 0);
      } else {
        finalSec = 0;
      }

      totalSec = budgetedTotal ?? (tuningSec + finalSec);
    }

    const tuningPct = (tuningSec / globalBudget) * 100;
    const finalPct = (finalSec / globalBudget) * 100;
    const totalPct = (totalSec / globalBudget) * 100;

    return {
      Model: model,
      Sample_Size: activeSize,
      TabPFN_Budget_Runtime: globalBudget,
      Optuna_Tuning_Time_Capped_Mean: tuningSec,
      Final_Fit_Predict_Time_Mean: finalSec,
      Budgeted_Total_Runtime_Mean: totalSec,
      Tuning_Share_pct: tuningPct,
      Final_Share_pct: finalPct,
      Total_Share_pct: totalPct
    };
  });

  const xModels = plotRows.map(r => r.Model);
  const tuningY = plotRows.map(r => r.Tuning_Share_pct);
  const finalY = plotRows.map(r => r.Final_Share_pct);
  const totalY = plotRows.map(r => r.Total_Share_pct);

  const tuningTrace = {
    x: xModels,
    y: tuningY,
    type: "bar",
    name: "Capped Optuna tuning",

    marker: {
      color: xModels.map(m => ctx.modelColors[m]),
      line: {
        color: "#ffffff",
        width: 0.8
      }
    },

    customdata: plotRows.map(r => [
      r.Sample_Size,
      r.Optuna_Tuning_Time_Capped_Mean,
      r.Final_Fit_Predict_Time_Mean,
      r.Budgeted_Total_Runtime_Mean,
      r.TabPFN_Budget_Runtime,
      r.Total_Share_pct
    ]),

    hovertemplate:
      `<b>%{x}</b><br>` +
      `N = %{customdata[0]:,}<br>` +
      `Component: capped Optuna tuning<br>` +
      `Tuning time = %{customdata[1]:.3f}s<br>` +
      `TabPFN budget = %{customdata[4]:.3f}s<br>` +
      `Tuning share = %{y:.1f}%<br>` +
      `Total runtime share = %{customdata[5]:.1f}%` +
      `<extra></extra>`
  };

  const finalTrace = {
    x: xModels,
    y: finalY,
    type: "bar",
    name: "Final fit/predict",

    marker: {
      color: xModels.map(m => rgbaFromHex(ctx.modelColors[m], 0.38)),
      line: {
        color: "#ffffff",
        width: 0.8
      }
    },

    customdata: plotRows.map(r => [
      r.Sample_Size,
      r.Optuna_Tuning_Time_Capped_Mean,
      r.Final_Fit_Predict_Time_Mean,
      r.Budgeted_Total_Runtime_Mean,
      r.TabPFN_Budget_Runtime,
      r.Total_Share_pct
    ]),

    hovertemplate:
      `<b>%{x}</b><br>` +
      `N = %{customdata[0]:,}<br>` +
      `Component: final fit/predict<br>` +
      `Final fit/predict time = %{customdata[2]:.3f}s<br>` +
      `TabPFN budget = %{customdata[4]:.3f}s<br>` +
      `Final share = %{y:.1f}%<br>` +
      `Total runtime share = %{customdata[5]:.1f}%` +
      `<extra></extra>`
  };

  const totalLabelTrace = {
    x: xModels,
    y: totalY,
    type: "scatter",
    mode: "text",
    text: totalY.map(v => `${v.toFixed(0)}%`),
    textposition: "top center",

    textfont: {
      family: "JetBrains Mono, monospace",
      size: 10,
      color: "#515b6e"
    },

    hoverinfo: "skip",
    showlegend: false
  };

  const referenceLine = {
    x: xModels,
    y: xModels.map(() => 100),
    type: "scatter",
    mode: "lines",
    name: "100% TabPFN tuning budget",

    line: {
      color: "#1a2030",
      width: 1.4,
      dash: "dash"
    },

    hovertemplate:
      `100% = TabPFN-derived tuning budget<extra></extra>`
  };

  const maxY = Math.max(120, ...totalY.map(v => v * 1.12));

  Plotly.react(elId, [tuningTrace, finalTrace, totalLabelTrace, referenceLine], {
    ...LAYOUT_BASE,

    barmode: "stack",
    bargap: 0.34,

    showlegend: true,

    legend: {
      font: FONT_MONO,
      orientation: "h",
      y: -0.30,
      x: 0.5,
      xanchor: "center"
    },

    margin: {
      ...LAYOUT_BASE.margin,
      b: 95
    },

    xaxis: {
      ...LAYOUT_BASE.xaxis,
      title: {
        text: `Models at N = ${formatN(activeSize)}`,
        font: FONT_AXIS_TITLE
      },
      tickangle: -18
    },

    yaxis: {
      ...LAYOUT_BASE.yaxis,
      title: {
        text: "Runtime share of TabPFN tuning budget (%)",
        font: FONT_AXIS_TITLE
      },
      range: [0, maxY]
    }

  }, PLOT_CONFIG);
}});
"""


# ============================================================
# Apply replacement
# ============================================================

html_new = replace_chart_register_block(
    html_text=html,
    chart_name="budget-util",
    new_block=new_budget_util_block
)

# ============================================================
# Update visible panel title and note
# ============================================================

html_new = html_new.replace(
    "Budget utilization (%)",
    "Runtime composition vs TabPFN tuning budget"
)

html_new = html_new.replace(
    "Budgeted runtime share vs TabPFN tuning budget",
    "Runtime composition vs TabPFN tuning budget"
)

html_new = html_new.replace(
    "100% = ON-BUDGET",
    "STACKED BARS · SELECTED N"
)

html_new = html_new.replace(
    "100% = TABPFN TUNING BUDGET",
    "STACKED BARS · SELECTED N"
)

html_new = html_new.replace(
    "TOTAL SHARE · HOVER SHOWS DECOMPOSITION",
    "STACKED BARS · SELECTED N"
)

html_new = html_new.replace(
    "TUNING + FINAL FIT/PREDICT VS TABPFN BUDGET",
    "STACKED BARS · SELECTED N"
)

html_path.write_text(html_new, encoding="utf-8")

print("Success! Budget composition plot is now permanent.")
print(f"Updated file: {html_path}")
print(f"Backup file: {backup_path}")

print("\nPermanent plot behavior:")
print("If one sample size is selected: shows that N.")
print("If multiple sample sizes are selected: shows the largest selected N.")
print("TabPFN is fixed as the 100% budget reference.")
print("Other models are decomposed into capped tuning + final fit/predict.")