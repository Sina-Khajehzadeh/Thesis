import re
from pathlib import Path

html_path = Path("FINAL_DASHBOARD_REVIEW.html")
backup_path = Path("FINAL_DASHBOARD_REVIEW_before_ROC_Calibration_wiring.html")

html = html_path.read_text(encoding="utf-8")

# ------------------------------------------------------------
# Safety checks
# ------------------------------------------------------------

if 'id="roc-calibration-data"' not in html:
    raise ValueError(
        "roc-calibration-data was not found. Run the JSON injection step first."
    )

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created: {backup_path}")

# ============================================================
# 1) Replace DataAdapter
# ============================================================

new_data_adapter = r"""
class DataAdapter {
  constructor(summary, iters, curves) {
    this.summary = summary;
    this.iters = iters;
    this.curves = curves;
  }

  static fromEmbedded() {
    return new DataAdapter(
      JSON.parse(document.getElementById('summary-data').textContent),
      JSON.parse(document.getElementById('iter-data').textContent),
      JSON.parse(document.getElementById('roc-calibration-data').textContent)
    );
  }

  allSummary() { return this.summary; }
  allIters() { return this.iters; }
  allCurves() { return this.curves; }

  uniqueValues(col) {
    return [...new Set(this.summary.map(r => r[col]).filter(v => v != null))];
  }
}
"""

html, n = re.subn(
    r"class DataAdapter\s*\{[\s\S]*?\n\}\n\nclass FilterStore",
    new_data_adapter.strip() + "\n\nclass FilterStore",
    html,
    count=1
)

if n != 1:
    raise ValueError("Could not replace DataAdapter cleanly.")

# ============================================================
# 2) Replace FilterStore
# ============================================================

new_filter_store = r"""
class FilterStore {
  constructor(initial) { this.state = initial; this.subs = []; }
  subscribe(fn) { this.subs.push(fn); }
  set(patch) { this.state = { ...this.state, ...patch }; this.subs.forEach(fn => fn(this.state)); }
  get() { return this.state; }

  applySummary(records) {
    const s = this.state;
    return records.filter(r => s.models.includes(r.Model) && s.sizes.includes(r.Sample_Size));
  }

  applyIters(records) {
    const s = this.state;
    return records.filter(r => s.models.includes(r.Model) && s.sizes.includes(r.Sample_Size));
  }

  applyCurves(records) {
    const s = this.state;

    return records.filter(r =>
      s.sizes.includes(r.Sample_Size) &&
      (
        r.Curve_Role === 'reference' ||
        s.models.includes(r.Model)
      )
    );
  }
}
"""

html, n = re.subn(
    r"class FilterStore\s*\{[\s\S]*?\n\}\n\nconst stat",
    new_filter_store.strip() + "\n\nconst stat",
    html,
    count=1
)

if n != 1:
    raise ValueError("Could not replace FilterStore cleanly.")

# ============================================================
# 3) Replace ROC + Calibration chart renderers
# ============================================================

new_roc_calibration_block = r"""
function meanFinite(values) {
  const clean = values
    .map(Number)
    .filter(v => Number.isFinite(v));

  return clean.length
    ? clean.reduce((a, b) => a + b, 0) / clean.length
    : NaN;
}

function curvePoints(curves, plotType, model) {
  const rows = curves.filter(r =>
    r.Plot_Type === plotType &&
    r.Curve_Role === 'model' &&
    r.Model === model
  );

  const byPoint = new Map();

  rows.forEach(r => {
    const p = Number(r.Point_Index);

    if (!byPoint.has(p)) {
      byPoint.set(p, {
        x: [],
        y: [],
        auc: [],
        brier: []
      });
    }

    const obj = byPoint.get(p);

    if (r.X_Value != null) obj.x.push(Number(r.X_Value));
    if (r.Y_Value != null) obj.y.push(Number(r.Y_Value));
    if (r.AUC != null) obj.auc.push(Number(r.AUC));
    if (r.MeanBrier != null) obj.brier.push(Number(r.MeanBrier));
  });

  return [...byPoint.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([point, obj]) => ({
      point,
      x: meanFinite(obj.x),
      y: meanFinite(obj.y),
      auc: meanFinite(obj.auc),
      brier: meanFinite(obj.brier)
    }))
    .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
}

function referenceCurve(curves, plotType) {
  const rows = curves.filter(r =>
    r.Plot_Type === plotType &&
    r.Curve_Role === 'reference'
  );

  const byPoint = new Map();

  rows.forEach(r => {
    const p = Number(r.Point_Index);

    if (!byPoint.has(p)) {
      byPoint.set(p, {
        x: [],
        y: []
      });
    }

    if (r.X_Value != null) byPoint.get(p).x.push(Number(r.X_Value));
    if (r.Y_Value != null) byPoint.get(p).y.push(Number(r.Y_Value));
  });

  const points = [...byPoint.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([point, obj]) => ({
      point,
      x: meanFinite(obj.x),
      y: meanFinite(obj.y)
    }))
    .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));

  return {
    x: points.map(d => d.x),
    y: points.map(d => d.y)
  };
}

function selectedSampleLabel(curves, plotType, model) {
  const sizes = [...new Set(
    curves
      .filter(r =>
        r.Plot_Type === plotType &&
        r.Curve_Role === 'model' &&
        r.Model === model
      )
      .map(r => r.Sample_Size)
      .filter(v => v != null)
  )].sort((a, b) => a - b);

  if (sizes.length === 1) {
    return `N = ${Number(sizes[0]).toLocaleString()}`;
  }

  return `${sizes.length} selected sample sizes`;
}

charts.register('roc', {
  render(elId, curves, ctx) {
    const traces = [];

    const ref = referenceCurve(curves, 'ROC');

    if (ref.x.length && ref.y.length) {
      traces.push({
        x: ref.x,
        y: ref.y,
        mode: 'lines',
        type: 'scatter',
        line: { color: '#c9cdd6', width: 1.5, dash: 'dot' },
        name: 'Chance',
        hoverinfo: 'skip'
      });
    }

    ctx.models.forEach(model => {
      const pts = curvePoints(curves, 'ROC', model);

      if (!pts.length) return;

      const auc = meanFinite(pts.map(d => d.auc));
      const sampleLabel = selectedSampleLabel(curves, 'ROC', model);

      traces.push({
        x: pts.map(d => d.x),
        y: pts.map(d => d.y),
        mode: 'lines',
        type: 'scatter',
        name: Number.isFinite(auc)
          ? `${model} (AUC=${auc.toFixed(3)})`
          : model,
        line: {
          color: ctx.modelColors[model],
          width: 2.4
        },
        hovertemplate:
          `<b>${model}</b><br>` +
          `${sampleLabel}<br>` +
          `AUC: ${Number.isFinite(auc) ? auc.toFixed(4) : '—'}<br>` +
          `FPR: %{x:.3f}<br>` +
          `Mean TPR: %{y:.3f}` +
          `<extra></extra>`
      });
    });

    Plotly.react(elId, traces, {
      ...LAYOUT_BASE,
      showlegend: true,
      legend: {
        font: FONT_MONO,
        x: 0.98,
        xanchor: 'right',
        y: 0.02,
        yanchor: 'bottom',
        bgcolor: 'rgba(255,255,255,0.85)',
        bordercolor: '#e3e6ec',
        borderwidth: 1
      },
      xaxis: {
        ...LAYOUT_BASE.xaxis,
        title: { text: 'False Positive Rate', font: FONT_AXIS_TITLE },
        range: [0, 1],
        dtick: 0.2
      },
      yaxis: {
        ...LAYOUT_BASE.yaxis,
        title: { text: 'Mean True Positive Rate', font: FONT_AXIS_TITLE },
        range: [0, 1],
        dtick: 0.2
      }
    }, PLOT_CONFIG);
  }
});

charts.register('calibration', {
  render(elId, curves, ctx) {
    const traces = [];

    const ref = referenceCurve(curves, 'Calibration');

    if (ref.x.length && ref.y.length) {
      traces.push({
        x: ref.x,
        y: ref.y,
        mode: 'lines',
        type: 'scatter',
        line: { color: '#c9cdd6', width: 1.5, dash: 'dot' },
        name: 'Perfect calibration',
        hoverinfo: 'skip'
      });
    }

    ctx.models.forEach(model => {
      const pts = curvePoints(curves, 'Calibration', model);

      if (!pts.length) return;

      const meanBrier = meanFinite(pts.map(d => d.brier));
      const sampleLabel = selectedSampleLabel(curves, 'Calibration', model);

      traces.push({
        x: pts.map(d => d.x),
        y: pts.map(d => d.y),
        mode: 'lines+markers',
        type: 'scatter',
        name: Number.isFinite(meanBrier)
          ? `${model} (Brier=${meanBrier.toFixed(3)})`
          : model,
        line: {
          color: ctx.modelColors[model],
          width: 2.4
        },
        marker: {
          color: ctx.modelColors[model],
          size: 5.5,
          line: { color: '#fff', width: 1 }
        },
        hovertemplate:
          `<b>${model}</b><br>` +
          `${sampleLabel}<br>` +
          `Mean Brier: ${Number.isFinite(meanBrier) ? meanBrier.toFixed(4) : '—'}<br>` +
          `Predicted probability: %{x:.3f}<br>` +
          `Observed probability: %{y:.3f}` +
          `<extra></extra>`
      });
    });

    Plotly.react(elId, traces, {
      ...LAYOUT_BASE,
      showlegend: true,
      legend: {
        font: FONT_MONO,
        x: 0.02,
        xanchor: 'left',
        y: 0.98,
        yanchor: 'top',
        bgcolor: 'rgba(255,255,255,0.85)',
        bordercolor: '#e3e6ec',
        borderwidth: 1
      },
      xaxis: {
        ...LAYOUT_BASE.xaxis,
        title: { text: 'Predicted probability', font: FONT_AXIS_TITLE },
        range: [0, 1],
        dtick: 0.2
      },
      yaxis: {
        ...LAYOUT_BASE.yaxis,
        title: { text: 'Observed probability', font: FONT_AXIS_TITLE },
        range: [0, 1],
        dtick: 0.2
      }
    }, PLOT_CONFIG);
  }
});
"""

html, n = re.subn(
    r"charts\.register\('roc'[\s\S]*?charts\.register\('scaling'",
    new_roc_calibration_block.strip() + "\n\ncharts.register('scaling'",
    html,
    count=1
)

if n != 1:
    raise ValueError("Could not replace ROC/Calibration chart blocks cleanly.")

# ============================================================
# 4) Replace Dashboard.refresh()
# ============================================================

new_refresh = r"""
refresh() {
    const summary = this.store.applySummary(this.adapter.allSummary());
    const iters = this.store.applyIters(this.adapter.allIters());
    const curves = this.store.applyCurves(this.adapter.allCurves());

    const state = this.store.get();
    const ctx = { metric: state.metric, models: state.models, modelColors: this.modelColors };

    document.getElementById('cell-count').textContent = summary.length;
    document.getElementById('scaling-metric').textContent = state.metric;

    this.renderKPIs(summary);
    charts.get('allmetrics-box').render('chart-allmetrics-box', iters, ctx);
    charts.get('roc').render('chart-roc', curves, ctx);
    charts.get('calibration').render('chart-calibration', curves, ctx);
    charts.get('scaling').render('chart-scaling', summary, ctx);
    charts.get('runtime-scaling').render('chart-runtime-scaling', summary, ctx);
    charts.get('budget-util').render('chart-budget-util', summary, ctx);
    charts.get('trials').render('chart-trials', summary, ctx);
    charts.get('tradeoff').render('chart-tradeoff', summary, ctx);
    charts.get('energy').render('chart-energy', summary, ctx);
    this.renderTable(summary);
  }
"""

html, n = re.subn(
    r"refresh\(\)\s*\{[\s\S]*?this\.renderTable\(summary\);\s*\n\s*\}",
    new_refresh.strip(),
    html,
    count=1
)

if n != 1:
    raise ValueError("Could not replace Dashboard.refresh() cleanly.")

# ============================================================
# 5) Update the ROC/Calibration section labels
# ============================================================

html = html.replace(
    "AUC-anchored theoretical curves · for visual comparison",
    "extracted ROC and calibration curves · original Plotly data"
)

html = html.replace(
    "binormal · anchored to reported AUC",
    "extracted FPR ↔ mean TPR"
)

html = html.replace(
    "Reconstructed from each model's AUC using the binormal-equal-variance model (TPR = Φ(Φ⁻¹(FPR) + d')), since per-prediction scores aren't in the file. Curve area equals the reported AUC exactly.",
    "Extracted directly from the original Plotly ROC HTML files. Each curve shows false-positive rate versus mean true-positive rate."
)

html = html.replace(
    "predicted ↔ observed · Brier-anchored",
    "extracted predicted ↔ observed"
)

html = html.replace(
    "Reconstructed from each model's Brier score and Sensitivity using a logistic-distortion model around the identity line; lower Brier → closer to perfect calibration. Diagonal = perfect calibration.",
    "Extracted directly from the original Plotly calibration HTML files. Each curve shows predicted probability versus observed probability."
)

# ============================================================
# 6) Write back
# ============================================================

html_path.write_text(html, encoding="utf-8")

print("Success! ROC and Calibration JSON is now wired into the dashboard.")
print(f"Updated file: {html_path}")
print(f"Backup file: {backup_path}")

# Basic validation
checks = [
    'id="roc-calibration-data"',
    "allCurves()",
    "applyCurves(records)",
    "charts.get('roc').render('chart-roc', curves, ctx)",
    "charts.get('calibration').render('chart-calibration', curves, ctx)",
    "Extracted directly from the original Plotly ROC HTML files",
    "Extracted directly from the original Plotly calibration HTML files"
]

print("\nValidation:")
for c in checks:
    print(f"{'OK' if c in html else 'MISSING'}: {c}")