import re
from pathlib import Path

# ============================================================
# Target dashboard file
# ============================================================

html_path = Path("/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario.html")

backup_path = Path(
    "/workspaces/Thesis/No_Budget_FINAL_DASHBOARD_No_Budget_Scenario_before_six_metric_boxplots_BACKUP.html"
)

html = html_path.read_text(encoding="utf-8")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created:\n{backup_path}")
else:
    print(f"Backup already exists:\n{backup_path}")


# ============================================================
# Helper: robust JS chart registration replacement
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
# 1) Add permanent CSS for six-panel metric boxplots
# ============================================================

html = re.sub(
    r"/\* === SIX METRIC BOXPLOT PANELS START === \*/[\s\S]*?/\* === SIX METRIC BOXPLOT PANELS END === \*/\s*",
    "",
    html,
    flags=re.DOTALL
)

six_panel_css = """
/* === SIX METRIC BOXPLOT PANELS START === */

#chart-allmetrics-box {
  height: auto !important;
  min-height: 0 !important;
  padding-bottom: 0 !important;
  margin-bottom: 0 !important;
}

.metric-boxplot-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(320px, 1fr));
  gap: 12px;
  width: 100%;
  margin: 0;
  padding: 0;
}

.metric-boxplot-panel {
  height: clamp(245px, 27vh, 310px);
  min-height: 245px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  background: var(--bg-surface);
  padding: 2px;
  overflow: hidden;
}

.metric-boxplot-panel .js-plotly-plot,
.metric-boxplot-panel .plot-container,
.metric-boxplot-panel .svg-container {
  width: 100% !important;
  height: 100% !important;
}

@media (max-width: 1350px) {
  .metric-boxplot-grid {
    grid-template-columns: repeat(2, minmax(340px, 1fr));
  }
}

@media (max-width: 850px) {
  .metric-boxplot-grid {
    grid-template-columns: 1fr;
  }

  .metric-boxplot-panel {
    height: 285px;
  }
}

/* === SIX METRIC BOXPLOT PANELS END === */
"""

if "</style>" not in html:
    raise ValueError("Could not find </style> tag.")

html = html.replace("</style>", six_panel_css + "\n</style>", 1)


# ============================================================
# 2) Replace allmetrics-box chart renderer
# ============================================================

new_allmetrics_box_block = r"""
charts.register('allmetrics-box', {
  render(elId, iters, ctx) {
    const root = document.getElementById(elId);

    if (!root) {
      console.warn(`Missing chart container: ${elId}`);
      return;
    }

    const modelOrder = [
      'TabPFN',
      'L-SLR',
      'Augmented_SLR',
      'RandomForest',
      'XGBoost',
      'CatBoost'
    ];

    const selectedModels = modelOrder.filter(model =>
      ctx.models.includes(model) &&
      iters.some(r => r.Model === model)
    );

    const metrics = [
      {
        key: 'BalancedAccuracy',
        title: 'Balanced Accuracy',
        yTitle: 'Balanced Accuracy',
        axisType: 'linear',
        hoverDigits: 4
      },
      {
        key: 'AUC',
        title: 'AUC',
        yTitle: 'AUC',
        axisType: 'linear',
        hoverDigits: 4
      },
      {
        key: 'Brier',
        title: 'Brier Score',
        yTitle: 'Brier',
        axisType: 'linear',
        hoverDigits: 4
      },
      {
        key: 'Sensitivity',
        title: 'Sensitivity',
        yTitle: 'Sensitivity',
        axisType: 'linear',
        hoverDigits: 4
      },
      {
        key: 'Precision',
        title: 'Precision',
        yTitle: 'Precision',
        axisType: 'linear',
        hoverDigits: 4
      },
      {
        key: 'Time_Seconds',
        title: 'Runtime',
        yTitle: 'Time (s, log)',
        axisType: 'log',
        hoverDigits: 3
      }
    ];

    const finiteValues = (rows, key) =>
      rows.map(r => Number(r[key])).filter(Number.isFinite);

    const axisRange = (values, metric) => {
      if (!values.length) return undefined;

      if (metric.axisType === 'log') {
        const positive = values.filter(v => v > 0);

        if (!positive.length) return undefined;

        const min = Math.min(...positive);
        const max = Math.max(...positive);

        const logMin = Math.log10(min);
        const logMax = Math.log10(max);
        const span = logMax - logMin;
        const pad = Math.max(span * 0.14, 0.08);

        return [logMin - pad, logMax + pad];
      }

      const min = Math.min(...values);
      const max = Math.max(...values);

      let span = max - min;

      if (span === 0) {
        span = Math.max(Math.abs(max) * 0.02, 0.005);
      }

      const pad = Math.max(span * 0.28, 0.004);

      let lo = min - pad;
      let hi = max + pad;

      lo = Math.max(0, lo);
      hi = Math.min(1, hi);

      if (hi <= lo) {
        hi = lo + 0.01;
      }

      return [lo, hi];
    };

    const currentRows = Array.isArray(iters) ? iters : [];

    const existingPanel = root.closest('.panel');

    if (existingPanel) {
      const panelTitle = existingPanel.querySelector('.panel-title');
      const panelNote = existingPanel.querySelector('.panel-note');
      const caveat = existingPanel.querySelector('.panel-note-good, .panel-caveat');

      if (panelTitle) {
        panelTitle.textContent = 'Metric-specific boxplots';
      }

      if (panelNote) {
        panelNote.textContent = '6 separate panels · selected models and sample sizes';
      }

      if (caveat) {
        caveat.textContent =
          'Each metric is shown in its own boxplot panel with an independent y-axis. Runtime is shown on a log scale.';
      }
    }

    if (!currentRows.length || !selectedModels.length) {
      root.innerHTML = `
        <div style="padding: 18px; font-family: var(--font-mono); color: var(--text-tertiary);">
          No iteration-level data available for the selected filters.
        </div>
      `;
      return;
    }

    // Clean old Plotly content and old observers
    if (root.__metricBoxResizeObserver) {
      root.__metricBoxResizeObserver.disconnect();
      root.__metricBoxResizeObserver = null;
    }

    try {
      Plotly.purge(root);
    } catch (err) {
      // ignore if no existing Plotly instance
    }

    root.innerHTML = `
      <div class="metric-boxplot-grid">
        ${metrics.map((metric, index) => `
          <div id="metric-boxplot-${index}" class="metric-boxplot-panel"></div>
        `).join('')}
      </div>
    `;

    const plotConfig = {
      ...PLOT_CONFIG,
      responsive: true,
      displaylogo: false
    };

    const plots = [];

    metrics.forEach((metric, metricIndex) => {
      const plotId = `metric-boxplot-${metricIndex}`;
      const valuesForRange = finiteValues(currentRows, metric.key);

      const traces = selectedModels.map(model => {
        const vals = currentRows
          .filter(r => r.Model === model)
          .map(r => Number(r[metric.key]))
          .filter(Number.isFinite);

        return {
          type: 'box',
          name: model,
          legendgroup: model,
          y: vals,
          x: vals.map(() => model),

          boxpoints: 'outliers',
          boxmean: true,

          marker: {
            color: ctx.modelColors[model],
            size: 4,
            opacity: 0.58
          },

          line: {
            color: ctx.modelColors[model],
            width: 1.9
          },

          fillcolor: 'rgba(255,255,255,0.25)',

          hovertemplate:
            `<b>${model}</b><br>` +
            `${metric.title}<br>` +
            `Value: %{y:.${metric.hoverDigits}f}` +
            `<extra></extra>`,

          showlegend: false
        };
      });

      const layout = {
        title: {
          text: `<b>${metric.title}</b>`,
          font: {
            family: 'Fraunces, Georgia, serif',
            size: 15,
            color: '#1a2030'
          },
          x: 0.04,
          xanchor: 'left'
        },

        margin: {
          l: 52,
          r: 14,
          t: 40,
          b: 68
        },

        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: '#ffffff',

        boxmode: 'group',
        boxgap: 0.22,
        boxgroupgap: 0.04,

        xaxis: {
          type: 'category',

          // Critical: this prevents Plotly from hiding model categories
          // when the browser is zoomed in or the panel becomes narrow.
          tickmode: 'array',
          tickvals: selectedModels,
          ticktext: selectedModels,

          categoryorder: 'array',
          categoryarray: selectedModels,

          tickangle: -32,
          automargin: true,

          tickfont: {
            family: 'JetBrains Mono, monospace',
            size: selectedModels.length > 5 ? 8 : 9,
            color: '#515b6e'
          },

          gridcolor: '#eef1f5',
          zeroline: false
        },

        yaxis: {
          title: {
            text: metric.yTitle,
            font: {
              family: 'Inter, sans-serif',
              size: 11,
              color: '#1a2030'
            }
          },

          type: metric.axisType,
          range: axisRange(valuesForRange, metric),
          automargin: true,

          tickfont: {
            family: 'JetBrains Mono, monospace',
            size: 9,
            color: '#515b6e'
          },

          gridcolor: '#dfe4ec',
          zeroline: false
        }
      };

      const panel = document.getElementById(plotId);

      if (panel) {
        Plotly.newPlot(panel, traces, layout, plotConfig);
        plots.push(panel);
      }
    });

    // Dynamic resizing for browser zoom, sidebar changes, or container width changes.
    const resizeAll = () => {
      plots.forEach(plot => {
        if (plot && plot.offsetParent !== null) {
          Plotly.Plots.resize(plot);
        }
      });
    };

    root.__metricBoxResizeObserver = new ResizeObserver(() => {
      window.requestAnimationFrame(resizeAll);
    });

    root.__metricBoxResizeObserver.observe(root);

    window.requestAnimationFrame(resizeAll);
    setTimeout(resizeAll, 150);
    setTimeout(resizeAll, 450);
  }
});
"""

html = replace_chart_register_block(
    html_text=html,
    chart_name="allmetrics-box",
    new_block=new_allmetrics_box_block
)


# ============================================================
# 3) Optional visible text cleanup
# ============================================================

html = html.replace(
    "All metrics × all models",
    "Metric-specific boxplots"
)

html = html.replace(
    "BOX PLOTS · ALL MODELS · SIDE-BY-SIDE",
    "6 SEPARATE PANELS · SELECTED MODELS AND SAMPLE SIZES"
)

html = html.replace(
    "Median and IQR for Monte Carlo's 10 iterations.",
    "Each metric is shown in its own boxplot panel with an independent y-axis. Runtime is shown on a log scale."
)


# ============================================================
# 4) Save
# ============================================================

html_path.write_text(html, encoding="utf-8")

print("\nSuccess! Six separate metric-specific boxplots are now permanent.")
print(f"Updated file:\n{html_path}")
print(f"Backup file:\n{backup_path}")

print("\nWhat changed:")
print("- Replaced the combined all-metrics boxplot with 6 separate panels")
print("- Added Runtime / Time (s) as the sixth boxplot")
print("- Each metric has an independent y-axis")
print("- Runtime uses a log y-axis")
print("- All selected model names are forced to show on the x-axis")
print("- Plotly resize handling was added for browser zoom and layout changes")