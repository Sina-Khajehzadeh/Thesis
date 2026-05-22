import re
from pathlib import Path

html_path = Path("FINAL_DASHBOARD_REVIEW.html")
backup_path = Path("FINAL_DASHBOARD_REVIEW_before_real_curve_override.html")

html = html_path.read_text(encoding="utf-8")

if 'id="roc-calibration-data"' not in html:
    raise ValueError("Missing embedded roc-calibration-data JSON block. Inject the JSON first.")

if not backup_path.exists():
    backup_path.write_text(html, encoding="utf-8")
    print(f"Backup created: {backup_path}")

# Remove old override if you run this script multiple times
html = re.sub(
    r"/\* === REAL ROC CALIBRATION OVERRIDE START === \*/[\s\S]*?/\* === REAL ROC CALIBRATION OVERRIDE END === \*/\s*",
    "",
    html
)

override_js = r"""
/* === REAL ROC CALIBRATION OVERRIDE START === */

function getEmbeddedCurveRows() {
  const el = document.getElementById('roc-calibration-data');

  if (!el) {
    console.error('Missing <script id="roc-calibration-data"> block.');
    return [];
  }

  try {
    return JSON.parse(el.textContent || '[]');
  } catch (err) {
    console.error('Could not parse roc-calibration-data JSON:', err);
    return [];
  }
}

function meanFiniteReal(values) {
  const clean = values
    .map(Number)
    .filter(v => Number.isFinite(v));

  return clean.length
    ? clean.reduce((a, b) => a + b, 0) / clean.length
    : NaN;
}

function selectedSizesFromSummary(summary) {
  return [...new Set(
    summary
      .map(r => Number(r.Sample_Size))
      .filter(v => Number.isFinite(v))
  )];
}

function filteredCurveRows(summary, ctx, plotType) {
  const allRows = getEmbeddedCurveRows();
  const selectedSizes = selectedSizesFromSummary(summary);

  return allRows.filter(r =>
    r.Plot_Type === plotType &&
    selectedSizes.includes(Number(r.Sample_Size)) &&
    (
      r.Curve_Role === 'reference' ||
      ctx.models.includes(r.Model)
    )
  );
}

function groupedCurvePoints(rows, modelName = null) {
  const selectedRows = modelName
    ? rows.filter(r => r.Curve_Role === 'model' && r.Model === modelName)
    : rows.filter(r => r.Curve_Role === 'reference');

  const byPoint = new Map();

  selectedRows.forEach(r => {
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
      x: meanFiniteReal(obj.x),
      y: meanFiniteReal(obj.y),
      auc: meanFiniteReal(obj.auc),
      brier: meanFiniteReal(obj.brier)
    }))
    .filter(d => Number.isFinite(d.x) && Number.isFinite(d.y));
}

function curveSampleLabel(summary) {
  const sizes = selectedSizesFromSummary(summary).sort((a, b) => a - b);

  if (sizes.length === 1) {
    return `N = ${sizes[0].toLocaleString()}`;
  }

  return `${sizes.length} selected sample sizes`;
}

charts.register('roc', {
  render(elId, summary, ctx) {
    const rows = filteredCurveRows(summary, ctx, 'ROC');
    const traces = [];

    const refPts = groupedCurvePoints(
      rows.filter(r => r.Curve_Role === 'reference')
    );

    if (refPts.length) {
      traces.push({
        x: refPts.map(d => d.x),
        y: refPts.map(d => d.y),
        mode: 'lines',
        type: 'scatter',
        name: 'Chance',
        line: { color: '#9aa3b2', width: 1.5, dash: 'dash' },
        hoverinfo: 'skip'
      });
    }

    ctx.models.forEach(model => {
      const pts = groupedCurvePoints(rows, model);

      if (!pts.length) return;

      const auc = meanFiniteReal(pts.map(d => d.auc));

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
          `${curveSampleLabel(summary)}<br>` +
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
        bgcolor: 'rgba(255,255,255,0.88)',
        bordercolor: '#e3e6ec',
        borderwidth: 1
      },
      xaxis: {
        ...LAYOUT_BASE.xaxis,
        title: { text: 'False positive rate', font: FONT_AXIS_TITLE },
        range: [0, 1],
        dtick: 0.2
      },
      yaxis: {
        ...LAYOUT_BASE.yaxis,
        title: { text: 'Mean true positive rate', font: FONT_AXIS_TITLE },
        range: [0, 1],
        dtick: 0.2
      }
    }, PLOT_CONFIG);
  }
});

charts.register('calibration', {
  render(elId, summary, ctx) {
    const rows = filteredCurveRows(summary, ctx, 'Calibration');
    const traces = [];

    const refPts = groupedCurvePoints(
      rows.filter(r => r.Curve_Role === 'reference')
    );

    if (refPts.length) {
      traces.push({
        x: refPts.map(d => d.x),
        y: refPts.map(d => d.y),
        mode: 'lines',
        type: 'scatter',
        name: 'Perfectly calibrated',
        line: { color: '#111827', width: 1.6, dash: 'dash' },
        hoverinfo: 'skip'
      });
    }

    ctx.models.forEach(model => {
      const pts = groupedCurvePoints(rows, model);

      if (!pts.length) return;

      const meanBrier = meanFiniteReal(pts.map(d => d.brier));

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
          size: 5.8,
          line: { color: '#fff', width: 1 }
        },
        hovertemplate:
          `<b>${model}</b><br>` +
          `${curveSampleLabel(summary)}<br>` +
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
        bgcolor: 'rgba(255,255,255,0.88)',
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

/* === REAL ROC CALIBRATION OVERRIDE END === */
"""

# Insert override after the old ROC/Calibration registration block,
# immediately before the scaling chart registration.
marker = "charts.register('scaling'"

if marker not in html:
    raise ValueError("Could not find charts.register('scaling') marker.")

html = html.replace(marker, override_js + "\n\n" + marker, 1)

# Update visible labels/caveats so you can confirm the real renderer is active
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

html_path.write_text(html, encoding="utf-8")

print("Success! Real ROC and Calibration renderers were injected.")
print(f"Updated file: {html_path}")
print(f"Backup file: {backup_path}")

checks = [
    "REAL ROC CALIBRATION OVERRIDE START",
    "getEmbeddedCurveRows()",
    "filteredCurveRows(summary, ctx, 'Calibration')",
    "Extracted directly from the original Plotly calibration HTML files",
    "extracted predicted ↔ observed"
]

print("\nValidation:")
for c in checks:
    print(f"{'OK' if c in html else 'MISSING'}: {c}")