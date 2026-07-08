'use strict';

// ─── Constants ────────────────────────────────────────────────────────────────

const DIMS = [
  'velocity',
  'contribution_margin',
  'shelf_space_cost',
  'production_complexity',
  'cannibalization_risk',
];
const DIM_LABELS = {
  velocity:             'Velocity',
  contribution_margin:  'Contribution Margin',
  shelf_space_cost:     'Shelf Space Cost',
  production_complexity:'Production Complexity',
  cannibalization_risk: 'Cannibalization Risk',
};
const DIM_RAW_UNITS = {
  uspw:                    'units/store/wk',
  loaded_margin_pct:       '% margin',
  annual_shelf_space_cost: 'USD/yr',
  complexity_ratio:        'landed/MSRP',
  cannibalization_risk:    'velocity Δ',
};
const DIM_RAW_KEYS = {
  velocity:             'uspw',
  contribution_margin:  'loaded_margin_pct',
  shelf_space_cost:     'annual_shelf_space_cost',
  production_complexity:'complexity_ratio',
  cannibalization_risk: 'cannibalization_risk',
};
const Q_COLORS = {
  double_down: '#158f75',
  maintain:    '#1f2e7a',
  fix_or_kill: '#ee8a2a',
  kill:        '#b82d4a', // Tokyo berry — red is never a FILL; #cc100a stays ink-only
};
const Q_LABELS = {
  double_down: 'Double Down',
  maintain:    'Maintain',
  fix_or_kill: 'Fix or Kill',
  kill:        'Kill',
};
const Q_ORDER = ['kill', 'fix_or_kill', 'maintain', 'double_down'];

// ─── Utilities ────────────────────────────────────────────────────────────────

/** Escape a value for safe insertion into innerHTML templates.
 *  Prevents XSS if the JSON data source is ever replaced with untrusted input.
 */
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── State ────────────────────────────────────────────────────────────────────

let allSkus = [];
let weights = Object.fromEntries(DIMS.map(d => [d, 0.2]));
let pinnedSku = null;
let sliderDebounceTimer = null;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function computeScore(sku) {
  return DIMS.reduce((s, d) => s + sku.scores[d] * weights[d], 0);
}

function getQuadrant(sku) {
  // Action bucket is determined by RED-FLAG COUNT (dimensions scoring <= 2),
  // computed once by the scoring engine and stored per-SKU in the JSON — see
  // src/scoring/quadrants.py assign_quadrant. It is weight-independent by
  // design: moving the dimension-weight sliders changes the composite score
  // and the ranking, but never the keep/cut bucket. That is what makes the
  // "can't be gamed" promise true — a fatal weakness on a single dimension
  // cannot be averaged away by re-weighting.
  return sku.quadrant;
}

function getFilteredSkus() {
  const lineVal = document.getElementById('line-filter').value;
  const qVal    = document.getElementById('q-filter').value;
  return allSkus.filter(s =>
    (!lineVal || s.product_line === lineVal) &&
    (!qVal    || getQuadrant(s) === qVal)
  );
}

function skuByCode(code) {
  return allSkus.find(s => s.sku === code);
}

// ─── Init ─────────────────────────────────────────────────────────────────────

async function init() {
  try {
    const res = await fetch('data/cinderhaven_scored.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    allSkus = json.skus;

    populateLineFilter();
    initSliders();
    renderSummaryCards();
    renderBarChart();
    renderDimensionCharts();
    renderTable();
    wireEvents();
    syncBucketButtons('');

  } catch (e) {
    const el = document.getElementById('load-error');
    el.textContent = `Could not load data: ${e.message}. Serve this page over HTTP — run: python -m http.server 8000 (from repo root), then open http://localhost:8000/app/`;
    el.hidden = false;
  }
}

function populateLineFilter() {
  const lines = [...new Set(allSkus.map(s => s.product_line))].sort();
  const sel = document.getElementById('line-filter');
  lines.forEach(l => {
    const opt = document.createElement('option');
    opt.value = l;
    opt.textContent = l;
    sel.appendChild(opt);
  });
}

function wireEvents() {
  document.getElementById('reset-weights').addEventListener('click', resetWeights);
  document.getElementById('dc-close').addEventListener('click', hideDetailCard);
  document.getElementById('line-filter').addEventListener('change', onFiltersChange);
  document.getElementById('q-filter').addEventListener('change', onFiltersChange);

  // Bucket filter buttons
  document.querySelectorAll('.bucket-btn[data-q]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('q-filter').value = btn.dataset.q;
      onFiltersChange();
    });
  });

  // Quadrant summary cards — click to set q-filter
  document.querySelectorAll('.quadrant-card[data-q]').forEach(card => {
    const q = card.dataset.q;
    card.addEventListener('click', () => {
      const sel = document.getElementById('q-filter');
      sel.value = sel.value === q ? '' : q;
      onFiltersChange();
    });
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') card.click();
    });
  });

  // Dismiss detail card on outside click
  document.addEventListener('click', e => {
    const card = document.getElementById('detail-card');
    if (!card.hidden && !card.contains(e.target)) {
      // only dismiss if click wasn't on a chart (Plotly owns those clicks)
      if (!e.target.closest('#chart-bar') && !e.target.closest('.dim-charts-stack') &&
          !e.target.closest('.sku-table') && !e.target.closest('.bucket-filter') &&
          !e.target.closest('.weight-controls') && !e.target.closest('.quadrant-summary')) {
        hideDetailCard();
      }
    }
  });
}

function onFiltersChange() {
  const activeQ = document.getElementById('q-filter').value;
  renderBarChart();
  renderDimensionCharts();
  renderTable();
  updateQuadrantCardHighlights();
  syncBucketButtons(activeQ);
}

function syncBucketButtons(activeQ) {
  document.querySelectorAll('.bucket-btn[data-q]').forEach(btn => {
    const isActive = btn.dataset.q === activeQ;
    btn.classList.toggle('is-active', isActive);
    btn.setAttribute('aria-pressed', String(isActive));
  });
}

// ─── Sliders ──────────────────────────────────────────────────────────────────

function initSliders() {
  const container = document.getElementById('sliders');
  DIMS.forEach(dim => {
    const row = document.createElement('div');
    row.className = 'slider-row';
    const pct = Math.round(weights[dim] * 100);
    row.innerHTML = `
      <label class="slider-label" for="sl-${dim}">${DIM_LABELS[dim]}</label>
      <input class="slider-input" type="range" id="sl-${dim}" min="0" max="100" step="1" value="${pct}">
      <span class="slider-value" id="sv-${dim}">${pct}%</span>
    `;
    container.appendChild(row);
    document.getElementById(`sl-${dim}`).addEventListener('input', () => onSliderChange(dim));
  });
}

function onSliderChange(changedDim) {
  const raw = Object.fromEntries(DIMS.map(d => [d, parseInt(document.getElementById(`sl-${d}`).value) || 0]));
  const total = DIMS.reduce((s, d) => s + raw[d], 0);
  if (total === 0) {
    DIMS.forEach(d => { weights[d] = 0.2; });
  } else {
    DIMS.forEach(d => { weights[d] = raw[d] / total; });
  }

  DIMS.forEach(d => {
    document.getElementById(`sl-${d}`).value = Math.round(weights[d] * 100);
    document.getElementById(`sv-${d}`).textContent = `${Math.round(weights[d] * 100)}%`;
  });

  clearTimeout(sliderDebounceTimer);
  sliderDebounceTimer = setTimeout(() => {
    renderSummaryCards();
    renderBarChart();
    renderDimensionCharts();
    renderTable();
    if (pinnedSku) refreshDetailScore(pinnedSku);
  }, 80);
}

function resetWeights() {
  const eq = 1 / DIMS.length;
  DIMS.forEach(d => { weights[d] = eq; });
  DIMS.forEach(d => {
    document.getElementById(`sl-${d}`).value = 20;
    document.getElementById(`sv-${d}`).textContent = '20%';
  });
  renderSummaryCards();
  renderBarChart();
  renderDimensionCharts();
  renderTable();
  if (pinnedSku) refreshDetailScore(pinnedSku);
}

// ─── Summary cards ────────────────────────────────────────────────────────────

function renderSummaryCards() {
  const counts = { double_down: 0, maintain: 0, fix_or_kill: 0, kill: 0 };
  allSkus.forEach(s => { counts[getQuadrant(s)]++; });
  Object.keys(counts).forEach(q => {
    document.getElementById(`count-${q}`).textContent = counts[q];
  });
}

function updateQuadrantCardHighlights() {
  const activeQ = document.getElementById('q-filter').value;
  document.querySelectorAll('.quadrant-card[data-q]').forEach(card => {
    const q = card.dataset.q;
    card.classList.toggle('is-active', !!activeQ && q === activeQ);
    card.classList.toggle('is-dimmed', !!activeQ && q !== activeQ);
    card.setAttribute('aria-pressed', String(!!activeQ && q === activeQ));
  });
}

// ─── Bar chart ────────────────────────────────────────────────────────────────

function renderBarChart() {
  const visible = getFilteredSkus();
  if (visible.length === 0) {
    Plotly.react('chart-bar', [], {
      paper_bgcolor: '#f5f3ee', plot_bgcolor: '#f5f3ee',
      height: 160, margin: { l: 20, r: 20, t: 20, b: 20 },
      xaxis: { visible: false }, yaxis: { visible: false },
      annotations: [{ text: 'No SKUs match this filter', showarrow: false,
        font: { family: "'Source Sans 3', sans-serif", size: 14, color: '#595959' },
        xref: 'paper', yref: 'paper', x: 0.5, y: 0.5 }],
    }, { displayModeBar: false, responsive: true });
    return;
  }
  // Sort globally by score ascending (lowest at bottom = worst to best top-to-bottom)
  const sorted = [...visible].sort((a, b) => computeScore(a) - computeScore(b));

  const y      = sorted.map(s => s.sku);
  const x      = sorted.map(s => computeScore(s));
  const colors = sorted.map(s => Q_COLORS[getQuadrant(s)]);
  const custom = sorted.map(s => [Q_LABELS[getQuadrant(s)], s.product_line, computeScore(s).toFixed(2)]);

  // Main data trace (single trace with per-bar colors; legend built separately)
  const dataTrace = {
    type: 'bar',
    orientation: 'h',
    y, x,
    marker: { color: colors },
    customdata: custom,
    text: x.map(v => v.toFixed(2)),
    texttemplate: '%{text}',
    textposition: 'outside',
    textfont: { family: "'Source Sans 3', sans-serif", size: 9, color: '#595959' },
    cliponaxis: false,
    hovertemplate: '<b>%{y}</b><br>%{customdata[1]}<br>Score: %{customdata[2]} — %{customdata[0]}<extra></extra>',
    showlegend: false,
  };

  // Invisible traces for the legend
  const legendTraces = Q_ORDER.map(q => ({
    type: 'bar', orientation: 'h',
    x: [null], y: [null],
    name: Q_LABELS[q],
    marker: { color: Q_COLORS[q] },
    showlegend: true,
    hoverinfo: 'none',
  }));

  const barH = 18;
  const height = Math.max(420, sorted.length * barH + 130);

  const layout = {
    paper_bgcolor: '#f5f3ee',
    plot_bgcolor: '#f5f3ee',
    margin: { l: 100, r: 40, t: 10, b: 64 },
    xaxis: {
      range: [0, 5.3],
      tickfont: { family: "'Source Sans 3', sans-serif", size: 11, color: '#595959' },
      gridcolor: '#d9d9d9',
      gridwidth: 1,
      zeroline: false,
      title: {
        text: 'Weighted Composite Score (1–5)',
        font: { family: "'Source Sans 3', sans-serif", size: 12, color: '#595959' },
        standoff: 10,
      },
    },
    yaxis: {
      automargin: true,
      tickfont: { family: 'monospace', size: 10, color: '#333333' },
      gridcolor: 'rgba(0,0,0,0)',
      fixedrange: true,
    },
    height,
    showlegend: true,
    legend: {
      font: { family: "'Source Sans 3', sans-serif", size: 11 },
      bgcolor: 'rgba(0,0,0,0)',
      orientation: 'h',
      y: -0.07,
      x: 0,
      traceorder: 'normal',
    },
    shapes: [{
      type: 'line',
      x0: 3, x1: 3,
      y0: -0.5, y1: sorted.length - 0.5,
      line: { color: '#666666', width: 1, dash: 'dot' },
    }],
    bargap: 0.28,
  };

  const config = { displayModeBar: false, responsive: true };

  Plotly.react('chart-bar', [dataTrace, ...legendTraces], layout, config);

  const barDiv = document.getElementById('chart-bar');
  barDiv.removeAllListeners && barDiv.removeAllListeners('plotly_click');
  barDiv.on('plotly_click', evt => {
    const pt = evt.points[0];
    if (pt && pt.y) showDetailCard(pt.y);
  });
}

// ─── Dimension charts ─────────────────────────────────────────────────────────

function renderDimensionCharts() {
  DIMS.forEach(dim => renderOneDimChart(dim));
}

function renderOneDimChart(dim) {
  const visible = getFilteredSkus();
  const id = `chart-dim-${dim}`;
  if (visible.length === 0) {
    Plotly.react(id, [], {
      paper_bgcolor: '#f5f3ee', plot_bgcolor: '#f5f3ee',
      height: 160, margin: { l: 20, r: 20, t: 20, b: 20 },
      xaxis: { visible: false }, yaxis: { visible: false },
      annotations: [{ text: 'No SKUs match this filter', showarrow: false,
        font: { family: "'Source Sans 3', sans-serif", size: 14, color: '#595959' },
        xref: 'paper', yref: 'paper', x: 0.5, y: 0.5 }],
    }, { displayModeBar: false, responsive: true });
    return;
  }
  const sorted = [...visible].sort((a, b) => a.scores[dim] - b.scores[dim]);

  const y      = sorted.map(s => s.sku);
  const x      = sorted.map(s => s.scores[dim]);
  const colors = sorted.map(s => dimScoreColor(s.scores[dim]));
  const custom = sorted.map(s => [Q_LABELS[getQuadrant(s)], s.product_line]);

  const trace = {
    type: 'bar',
    orientation: 'h',
    y, x,
    marker: { color: colors },
    customdata: custom,
    hovertemplate: '<b>%{y}</b><br>%{customdata[1]}<br>Score: %{x} — %{customdata[0]}<extra></extra>',
    showlegend: false,
  };

  const barH = 18;
  const height = Math.max(420, sorted.length * barH + 130);

  const layout = {
    paper_bgcolor: '#f5f3ee',
    plot_bgcolor: '#f5f3ee',
    margin: { l: 100, r: 40, t: 10, b: 40 },
    xaxis: {
      range: [0, 5.3],
      tickvals: [1, 2, 3, 4, 5],
      tickfont: { family: "'Source Sans 3', sans-serif", size: 11, color: '#595959' },
      gridcolor: '#d9d9d9',
      gridwidth: 1,
      zeroline: false,
    },
    yaxis: {
      automargin: true,
      tickfont: { family: 'monospace', size: 10, color: '#333333' },
      gridcolor: 'rgba(0,0,0,0)',
      fixedrange: true,
    },
    height,
    showlegend: false,
    shapes: [{
      type: 'line',
      x0: 3, x1: 3,
      y0: -0.5, y1: sorted.length - 0.5,
      line: { color: '#666666', width: 1, dash: 'dot' },
    }],
    bargap: 0.28,
  };

  const config = { displayModeBar: false, responsive: true };
  Plotly.react(id, [trace], layout, config);

  const el = document.getElementById(id);
  el.removeAllListeners && el.removeAllListeners('plotly_click');
  el.on('plotly_click', evt => {
    const pt = evt.points[0];
    if (pt && pt.y) showDetailCard(pt.y);
  });
}

// ─── Table ────────────────────────────────────────────────────────────────────

function renderTable() {
  const visible = getFilteredSkus();
  const sorted = [...visible].sort((a, b) => computeScore(b) - computeScore(a));

  document.getElementById('table-count').textContent =
    `${sorted.length} of ${allSkus.length} SKUs`;

  const tbody = document.getElementById('sku-tbody');
  tbody.innerHTML = '';

  if (sorted.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="9" style="text-align:center;color:var(--text-secondary);padding:24px;">No SKUs match this filter.</td>`;
    tbody.appendChild(tr);
    return;
  }

  sorted.forEach(sku => {
    const tr = document.createElement('tr');
    tr.dataset.sku = sku.sku;

    const dimCells = DIMS.map(d => {
      const s = sku.scores[d];
      return `<td class="dim-col" style="color:${dimScoreColor(s)};font-weight:600;">${s}</td>`;
    }).join('');

    const score = computeScore(sku).toFixed(2);
    const q = getQuadrant(sku);
    const qClass = q.replace('_', '-');

    tr.innerHTML = `
      <td class="sku-code">${esc(sku.sku)}</td>
      <td class="product-line">${esc(sku.product_line)}</td>
      ${dimCells}
      <td class="score-cell" style="color:${compositeScoreColor(parseFloat(score))}">${score}</td>
      <td><span class="badge badge--${esc(qClass)}">${Q_LABELS[q]}</span></td>
    `;
    tr.addEventListener('click', () => showDetailCard(sku.sku));
    tbody.appendChild(tr);
  });
}

function dimScoreColor(score) {
  if (score >= 4) return '#158f75';
  if (score === 3) return '#595959';
  return '#cc100a';
}

function compositeScoreColor(score) {
  if (score >= 4) return '#158f75';
  if (score >= 3) return '#333333';
  return '#cc100a';
}

// ─── Detail card ──────────────────────────────────────────────────────────────

function showDetailCard(skuCode) {
  const sku = skuByCode(skuCode);
  if (!sku) return;
  pinnedSku = skuCode;

  document.getElementById('dc-sku').textContent = sku.sku;
  document.getElementById('dc-line').textContent = sku.product_line;

  const badgeWrap = document.getElementById('dc-badge-wrap');
  const q = getQuadrant(sku);
  const qClass = q.replace('_', '-');
  badgeWrap.innerHTML = `<span class="badge badge--${esc(qClass)}" style="font-size:11px;padding:3px 9px;">${Q_LABELS[q]}</span>`;

  refreshDetailScore(skuCode);

  const dimsEl = document.getElementById('dc-dims');
  dimsEl.innerHTML = '';
  DIMS.forEach(dim => {
    const score  = sku.scores[dim];
    const rawKey = DIM_RAW_KEYS[dim];
    const rawVal = sku.raw[rawKey];
    const units  = DIM_RAW_UNITS[rawKey];
    const pct    = (score / 5) * 100;

    let fillClass = 'dim-row__bar-fill--high';
    if (score <= 2) fillClass = 'dim-row__bar-fill--low';
    else if (score === 3) fillClass = 'dim-row__bar-fill--mid';

    const row = document.createElement('div');
    row.className = 'dim-row';
    row.innerHTML = `
      <span class="dim-row__name" title="${DIM_LABELS[dim]}">${DIM_LABELS[dim]}</span>
      <div class="dim-row__bar-track">
        <div class="dim-row__bar-fill ${fillClass}" style="width:${pct}%"></div>
      </div>
      <span class="dim-row__score" title="${formatRaw(rawVal, rawKey)} ${units}">${score}/5</span>
    `;
    dimsEl.appendChild(row);
  });

  document.getElementById('detail-card').hidden = false;
}

function refreshDetailScore(skuCode) {
  const sku = skuByCode(skuCode);
  if (!sku) return;
  const score = computeScore(sku).toFixed(2);
  document.getElementById('dc-score').textContent = score;
  document.getElementById('dc-score').style.color = compositeScoreColor(parseFloat(score));
  const q = getQuadrant(sku);
  const qClass = q.replace('_', '-');
  const badgeWrap = document.getElementById('dc-badge-wrap');
  if (badgeWrap) {
    badgeWrap.innerHTML = `<span class="badge badge--${esc(qClass)}" style="font-size:11px;padding:3px 9px;">${Q_LABELS[q]}</span>`;
  }
}

function hideDetailCard() {
  document.getElementById('detail-card').hidden = true;
  pinnedSku = null;
}

function formatRaw(val, key) {
  if (val == null) return '—';
  if (key === 'annual_shelf_space_cost') return `$${val.toLocaleString('en-US', {maximumFractionDigits: 0})}`;
  if (key === 'loaded_margin_pct') return `${val.toFixed(2)}%`;
  if (key === 'uspw') return val.toFixed(2);
  return val.toFixed(4);
}

// ─── Boot ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
