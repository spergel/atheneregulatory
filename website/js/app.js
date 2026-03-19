// ============================================================
// NAIC Statutory Filings Dashboard — app.js
// ============================================================

// --- State ---
let COMPANIES = {};
let currentCo = null;
let currentEntity = null;
let currentPeriod = null;
let overviewData = null;   // overview.json for current company
let periodData = null;     // {entity}_{period}.json for current selection
let currentSection = 'sec-overview';

// --- Format helpers ---
const fmtB  = v => `$${(v / 1e9).toFixed(2)}B`;
const fmtM  = v => `$${(v / 1e6).toFixed(1)}M`;
const fmtK  = v => `$${(v / 1e3).toFixed(0)}K`;
const fmtN  = v => new Intl.NumberFormat('en-US').format(Math.round(v));
function fmtAuto(v) {
  const a = Math.abs(v);
  if (a >= 1e9) return fmtB(v);
  if (a >= 1e6) return fmtM(v);
  if (a >= 1e3) return fmtK(v);
  return `$${v.toFixed(0)}`;
}

// Generate clean $B/$M/$K axis tick labels for Plotly.
// Pass an array of raw values (in dollars). Returns {tickvals, ticktext} for the axis.
function yTicksAuto(values) {
  const max = Math.max(...values.filter(v => isFinite(v) && v > 0), 0);
  if (max === 0) return {};
  let scale, suffix;
  if (max >= 1e9)      { scale = 1e9; suffix = 'B'; }
  else if (max >= 1e6) { scale = 1e6; suffix = 'M'; }
  else if (max >= 1e3) { scale = 1e3; suffix = 'K'; }
  else                 { return {}; }
  const scaledMax = max / scale;
  const rawStep   = scaledMax / 5;
  const mag       = Math.pow(10, Math.floor(Math.log10(rawStep || 1)));
  const step      = Math.ceil(rawStep / mag) * mag;
  const ticks = [];
  for (let v = 0; v <= max * 1.1; v += step * scale) ticks.push(Math.round(v));
  return {
    tickvals: ticks,
    ticktext: ticks.map(v => {
      const s = v / scale;
      return `$${s % 1 === 0 ? s.toFixed(0) : s.toFixed(1)}${suffix}`;
    }),
  };
}

// Same but for a horizontal bar chart's x-axis.
const xTicksAuto = yTicksAuto;

// Truncate a string to n chars, appending '…' if longer.
const trunc = (s, n) => s && s.length > n ? s.slice(0, n - 1) + '…' : (s || '');

// Populate a <select> element with options. getText(value) → display label.
function populateSelect(sel, values, getText) {
  sel.innerHTML = '';
  values.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = getText ? getText(v) : v;
    sel.appendChild(opt);
  });
}

// --- Plotly shared ---
const CFG = { responsive: true, displayModeBar: false };
const LAY = {
  paper_bgcolor: 'transparent', plot_bgcolor: '#ffffff',
  font: { color: '#212121', family: 'Calibri,"Segoe UI",Arial,sans-serif', size: 12 },
  margin: { l: 55, r: 20, t: 30, b: 50 },
  xaxis: { gridcolor: '#e0e0e0', zerolinecolor: '#c0c0c0', tickfont: { color: '#666' }, linecolor: '#c0c0c0' },
  yaxis: { gridcolor: '#e0e0e0', zerolinecolor: '#c0c0c0', tickfont: { color: '#666' }, linecolor: '#c0c0c0' },
};

const COLORS = ['#4472c4','#ed7d31','#a9d18e','#ff0000','#ffc000','#5b9bd5','#70ad47','#264478'];
const CAT_COLORS = { Bonds: '#4472c4', Mortgages: '#ed7d31', Alternatives: '#a9d18e', Cash: '#70ad47', 'Real Estate': '#9e3ec8' };
const NAIC_COLORS = { '1':'#107c41','2':'#70ad47','3':'#ffc000','4':'#ed7d31','5':'#c55a11','6':'#c00000' };

// --- Data fetch ---
async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  // Nav section tabs
  document.querySelectorAll('.topnav a[data-section]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      showSection(a.dataset.section);
    });
  });

  // Selectors
  document.getElementById('sel-company').addEventListener('change', e => selectCompany(e.target.value));
  document.getElementById('sel-entity').addEventListener('change', e => selectEntity(e.target.value));
  document.getElementById('sel-period').addEventListener('change', e => selectPeriod(e.target.value));

  // Premium search
  document.getElementById('premiums-search').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('#premiums-tbody tr').forEach(tr => {
      tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });

  // Load company list
  try {
    COMPANIES = await fetchJSON('data/companies.json');
    populateCompanySelector();
    // Default to first company
    const firstCo = Object.keys(COMPANIES)[0];
    await selectCompany(firstCo);
  } catch (err) {
    console.error('Failed to load companies:', err);
  }
});

function showSection(id) {
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.getElementById(id)?.classList.add('active');
  document.querySelectorAll('.topnav a[data-section]').forEach(a => {
    a.classList.toggle('active', a.dataset.section === id);
  });
  currentSection = id;
  // Lazy-render section-specific content on first visit or data change
  if (id === 'sec-premiums'  && periodData) renderPremiums(periodData.sched_t, currentPeriod);
  if (id === 'sec-portfolio' && periodData) renderPortfolioDetail(periodData.sched_d_quality);
  if (id === 'sec-mortgages' && periodData) renderMortgages(periodData.sched_b);
  if (id === 'sec-compare')  renderCompare();
  if (id === 'sec-data')     renderDataRoom();
}

// ============================================================
// SELECTORS
// ============================================================
function populateCompanySelector() {
  populateSelect(
    document.getElementById('sel-company'),
    Object.keys(COMPANIES),
    k => `${COMPANIES[k].name} (${COMPANIES[k].ticker})`
  );
}

async function selectCompany(coKey) {
  if (coKey === currentCo && overviewData) { renderAll(); return; }
  currentCo = coKey;
  periodData = null;

  try {
    overviewData = await fetchJSON(`data/${coKey}/overview.json`);
  } catch (err) {
    console.error('Failed to load overview:', err);
    overviewData = null;
    showNoData(true);
    return;
  }

  // Populate entity selector
  const ep = overviewData.entity_periods || {};
  const entities = Object.keys(ep).filter(e => ep[e].length > 0);
  populateSelect(document.getElementById('sel-entity'), entities);

  // Select first entity with data
  const firstEntity = entities[0] || overviewData.meta?.entities?.[0] || '';
  await selectEntity(firstEntity);
}

async function selectEntity(entity) {
  currentEntity = entity;
  const ep = overviewData?.entity_periods || {};
  const periods = (ep[entity] || []).slice().reverse(); // newest first

  populateSelect(document.getElementById('sel-period'), periods);

  const latestPeriod = periods[0] || '';
  await selectPeriod(latestPeriod);
}

async function selectPeriod(period) {
  currentPeriod = period;
  periodData = null;

  if (currentCo && currentEntity && period) {
    try {
      periodData = await fetchJSON(`data/${currentCo}/${currentEntity}_${period}.json`);
    } catch (err) {
      // Period file may not exist (no schedule data for this period)
      periodData = null;
    }
  }

  renderAll();
}

// ============================================================
// RENDER ALL
// ============================================================
function renderAll() {
  if (!overviewData) { showNoData(true); return; }
  showNoData(false);

  const meta = overviewData.meta || {};
  const ts   = (overviewData.timeseries || []).filter(r => r.entity === currentEntity);
  const pd   = periodData;

  // Section titles
  document.getElementById('ov-title').textContent =
    `${meta.name || ''} — ${currentEntity} ${currentPeriod || ''}`;
  document.getElementById('ov-sub').textContent =
    `NAIC Statutory Filing · ${currentEntity}`;

  // --- Find latest KPIs from timeseries for this entity+period ---
  const kpiRow = ts.find(r => r.period === currentPeriod) ||
                 ts.slice().sort((a, b) => b.period.localeCompare(a.period))[0] || {};

  renderKpiGrid(kpiRow);
  renderDonut(kpiRow);
  renderNaicBar(pd?.sched_d_quality);
  renderHistTotal(ts);
  renderHistMix(ts);
  renderHistAnnuity(ts);

  // Section-specific renders — only when that section is active
  if (currentSection === 'sec-premiums')  renderPremiums(pd?.sched_t, currentPeriod);
  if (currentSection === 'sec-portfolio') renderPortfolioDetail(pd?.sched_d_quality);
  if (currentSection === 'sec-mortgages') renderMortgages(pd?.sched_b);
}

function showNoData(show) {
  const el = document.getElementById('no-data-notice');
  if (el) el.style.display = show ? '' : 'none';
}

// ============================================================
// KPI GRID
// ============================================================
function renderKpiGrid(row) {
  const grid = document.getElementById('kpi-grid');
  const cards = [
    { label: 'Total Invested',    val: row.total_invested,  sub: 'Bonds + Mortgages + Alts + Cash',  cls: 'accent' },
    { label: 'Bond Portfolio',    val: row.bonds,           sub: 'Schedule D ending book value',      cls: 'green' },
    { label: 'Mortgage Loans',    val: row.mortgages,       sub: 'Schedule B ending book value',      cls: '' },
    { label: 'Alternatives',      val: row.alts,            sub: 'Schedule BA ending book value',     cls: 'orange' },
    { label: 'Cash Equivalents',  val: row.cash,            sub: 'Schedule E Pt 2',                   cls: '' },
    { label: 'Annuity YTD',       val: row.annuity_ytd,     sub: 'Schedule T year to date',           cls: 'purple' },
  ];
  grid.innerHTML = cards.map(c => `
    <div class="kpi-card ${c.cls}">
      <div class="kpi-label">${c.label}</div>
      ${c.val
        ? `<div class="kpi-value">${fmtAuto(c.val)}</div><div class="kpi-sub">${c.sub}</div>`
        : `<div class="kpi-value na">N/A</div><div class="kpi-na-badge">not in filing</div>`}
    </div>`).join('');

  renderDataGaps(row);
}

function renderDataGaps(row) {
  const bar   = document.getElementById('data-gaps-bar');
  const chips = document.getElementById('data-gaps-chips');
  if (!bar || !chips) return;

  const missing = [];
  if (!row.bonds)       missing.push({ label: 'Bonds',         hint: 'Schedule D not parsed' });
  if (!row.mortgages)   missing.push({ label: 'Mortgages',     hint: 'Schedule B not in filing' });
  if (!row.alts)        missing.push({ label: 'Alternatives',  hint: 'Schedule BA not parsed' });
  if (!row.cash)        missing.push({ label: 'Cash',          hint: 'Schedule E not parsed' });
  if (!row.annuity_ytd) missing.push({ label: 'Annuity YTD',  hint: 'Schedule T not parsed' });

  if (missing.length === 0) {
    bar.style.display = 'none';
    return;
  }
  bar.style.display = '';
  chips.innerHTML = missing.map(m =>
    `<span class="gap-chip" title="${m.hint}">${m.label}</span>`
  ).join('');
}

// ============================================================
// DONUT — Asset Allocation
// ============================================================
function renderDonut(row) {
  const labels = ['Bonds', 'Mortgages', 'Alternatives', 'Cash', 'Real Estate'];
  const values = [row.bonds, row.mortgages, row.alts, row.cash, row.real_estate].map(v => v || 0);
  if (values.every(v => v === 0)) { Plotly.purge('chart-donut'); return; }

  Plotly.react('chart-donut', [{
    type: 'pie', hole: 0.5, labels, values,
    marker: { colors: Object.values(CAT_COLORS) },
    textinfo: 'percent', hovertemplate: '<b>%{label}</b><br>%{value:$,.0f}<extra></extra>',
    sort: false,
  }], { ...LAY, margin: { l: 10, r: 10, t: 10, b: 10 }, showlegend: true,
    legend: { orientation: 'v', x: 1, y: 0.5, font: { size: 11 } } }, CFG);
}

// ============================================================
// NAIC QUALITY BAR (Overview panel)
// ============================================================
function renderNaicBar(dq) {
  if (!dq || dq.length === 0) { Plotly.purge('chart-naic-bar'); return; }

  // Group by NAIC number extracted from designation string
  const byNaic = {};
  dq.forEach(r => {
    const m = r.naic?.match(/(\d)/);
    if (!m) return;
    const n = m[1];
    byNaic[n] = (byNaic[n] || 0) + (r.current || 0);
  });

  const keys = ['1','2','3','4','5','6'].filter(k => byNaic[k]);
  const yVals = keys.map(k => byNaic[k]);
  Plotly.react('chart-naic-bar', [{
    type: 'bar', x: keys.map(k => `NAIC ${k}`), y: yVals,
    marker: { color: keys.map(k => NAIC_COLORS[k] || '#aaa') },
    hovertemplate: '<b>%{x}</b><br>%{y:$,.0f}<extra></extra>',
  }], { ...LAY, yaxis: { ...LAY.yaxis, ...yTicksAuto(yVals) } }, CFG);
}

// ============================================================
// HISTORICAL CHARTS
// ============================================================
function renderHistTotal(ts) {
  if (!ts.length) { Plotly.purge('chart-hist-total'); return; }
  const sorted = ts.slice().sort((a, b) => a.period.localeCompare(b.period));
  document.getElementById('hist-hint').textContent =
    `${sorted.length} data points · ${sorted[0]?.period} – ${sorted.at(-1)?.period}`;

  const histY = sorted.map(r => r.total_invested || null);
  const histYDefined = histY.filter(Boolean);
  Plotly.react('chart-hist-total', [{
    type: 'scatter', mode: 'lines+markers',
    x: sorted.map(r => r.period), y: histY,
    line: { color: '#4472c4', width: 2 }, marker: { size: 6 },
    connectgaps: false,
    hovertemplate: '<b>%{x}</b><br>%{y:$,.0f}<extra></extra>',
  }], { ...LAY, yaxis: { ...LAY.yaxis, ...yTicksAuto(histYDefined) } }, CFG);
}

function renderHistMix(ts) {
  if (!ts.length) { Plotly.purge('chart-hist-mix'); return; }
  const sorted = ts.slice().sort((a, b) => a.period.localeCompare(b.period));
  const x = sorted.map(r => r.period);
  const series = [
    { name: 'Bonds',        key: 'bonds',     color: '#4472c4' },
    { name: 'Mortgages',    key: 'mortgages', color: '#ed7d31' },
    { name: 'Alternatives', key: 'alts',      color: '#a9d18e' },
    { name: 'Cash',         key: 'cash',      color: '#70ad47' },
  ];
  const mixTraces = series.map(s => ({
    type: 'bar', name: s.name, x, y: sorted.map(r => r[s.key] || null),
    marker: { color: s.color },
    hovertemplate: `<b>${s.name}</b><br>%{y:$,.0f}<extra></extra>`,
  }));
  // Stack totals for tick scale
  const mixTotals = sorted.map((r, i) => series.reduce((sum, s) => sum + (r[s.key] || 0), 0));
  Plotly.react('chart-hist-mix', mixTraces,
    { ...LAY, barmode: 'stack', yaxis: { ...LAY.yaxis, ...yTicksAuto(mixTotals) } }, CFG);
}

function renderHistAnnuity(ts) {
  if (!ts.length) { Plotly.purge('chart-hist-annuity'); return; }
  const sorted = ts.slice().sort((a, b) => a.period.localeCompare(b.period));
  const annY = sorted.map(r => r.annuity_ytd || null);
  Plotly.react('chart-hist-annuity', [{
    type: 'bar', x: sorted.map(r => r.period), y: annY,
    marker: { color: '#7030a0' },
    hovertemplate: '<b>%{x}</b><br>%{y:$,.0f}<extra></extra>',
  }], { ...LAY, yaxis: { ...LAY.yaxis, ...yTicksAuto(annY) } }, CFG);
}

// ============================================================
// PREMIUMS (Schedule T)
// ============================================================
function renderPremiums(sched_t, period) {
  document.getElementById('prem-sub').textContent =
    `Schedule T — Direct Business, Year to Date ${period || ''}`;

  if (!sched_t || sched_t.length === 0) {
    Plotly.purge('chart-premiums-map');
    Plotly.purge('chart-top-states');
    document.getElementById('premiums-tbody').innerHTML =
      '<tr><td colspan="5" style="text-align:center;color:#999;padding:20px">No Schedule T data for this period</td></tr>';
    return;
  }

  const sorted = sched_t.slice().sort((a, b) => b.total - a.total);
  const total = sorted.reduce((s, r) => s + r.total, 0);

  // Map
  Plotly.react('chart-premiums-map', [{
    type: 'choropleth', locationmode: 'USA-states',
    locations: sorted.map(r => r.state), z: sorted.map(r => r.annuity),
    colorscale: 'Blues', reversescale: false,
    hovertemplate: '<b>%{location}</b><br>Annuity: %{z:$,.0f}<extra></extra>',
    colorbar: { title: 'Annuity ($)', thickness: 14, len: 0.8 },
  }], {
    geo: { scope: 'usa', projection: { type: 'albers usa' }, showlakes: true, lakecolor: '#f0f6ff', bgcolor: 'transparent' },
    paper_bgcolor: 'transparent', margin: { l: 0, r: 0, t: 0, b: 0 },
  }, CFG);

  // Top 20 bar
  const top20 = sorted.slice(0, 20).reverse();
  const stateXvals = top20.map(r => r.life + r.annuity);
  Plotly.react('chart-top-states', [
    { type: 'bar', orientation: 'h', name: 'Life',    x: top20.map(r => r.life),    y: top20.map(r => r.state), marker: { color: '#4472c4' } },
    { type: 'bar', orientation: 'h', name: 'Annuity', x: top20.map(r => r.annuity), y: top20.map(r => r.state), marker: { color: '#ed7d31' } },
  ], { ...LAY, barmode: 'stack', margin: { ...LAY.margin, l: 45 },
    xaxis: { ...LAY.xaxis, ...xTicksAuto(stateXvals) }, height: 420 }, CFG);

  // Table
  const tbody = document.getElementById('premiums-tbody');
  tbody.innerHTML = sorted.map((r, i) => `
    <tr>
      <td class="rank">${i + 1}</td>
      <td>${r.name || r.state} <span style="color:#999">(${r.state})</span></td>
      <td class="num">${fmtAuto(r.life)}</td>
      <td class="num">${fmtAuto(r.annuity)}</td>
      <td class="num">${fmtAuto(r.total)}</td>
    </tr>`).join('');
}

// ============================================================
// PORTFOLIO DETAIL (Schedule D Quality)
// ============================================================
function renderPortfolioDetail(dq) {
  if (!dq || dq.length === 0) {
    Plotly.purge('chart-naic-detail');
    document.getElementById('naic-tbody').innerHTML =
      '<tr><td colspan="4" style="text-align:center;color:#999;padding:20px">No bond quality data for this period (annual filings only)</td></tr>';
    return;
  }

  // Group by category and NAIC
  const cats = [...new Set(dq.map(r => r.category))].filter(Boolean);
  const naics = ['NAIC 1','NAIC 2','NAIC 3','NAIC 4','NAIC 5','NAIC 6'];

  const catTotals = {};
  dq.forEach(r => {
    const n = r.naic?.match(/(\d)/)?.[1];
    if (!n) return;
    const cat = r.category || 'Other';
    if (!catTotals[cat]) catTotals[cat] = {};
    catTotals[cat][`NAIC ${n}`] = (catTotals[cat][`NAIC ${n}`] || 0) + (r.current || 0);
  });

  const catKeys = Object.keys(catTotals);
  // Truncate long category labels for the x-axis; full name shows in hover
  const catLabels = catKeys.map(c => trunc(c, 28));
  const portYvals = catKeys.map(c => naics.reduce((s, n) => s + (catTotals[c][n] || 0), 0));
  Plotly.react('chart-naic-detail',
    naics.map(n => ({
      type: 'bar', name: n, x: catLabels, y: catKeys.map(c => catTotals[c][n] || 0),
      marker: { color: NAIC_COLORS[n.slice(-1)] },
      hovertemplate: `<b>${n}</b><br>%{x}<br>%{y:$,.0f}<extra></extra>`,
    })),
    { ...LAY, barmode: 'stack', height: 400,
      margin: { ...LAY.margin, b: 130 },
      yaxis: { ...LAY.yaxis, ...yTicksAuto(portYvals) },
      xaxis: { ...LAY.xaxis, tickangle: -40, automargin: true } }, CFG);

  // Table
  const tbody = document.getElementById('naic-tbody');
  tbody.innerHTML = dq.map(r => `
    <tr>
      <td>${r.category || ''}</td>
      <td><span style="font-weight:600">${r.naic || ''}</span></td>
      <td class="num">${fmtAuto(r.current || 0)}</td>
      <td class="num" style="color:#888">${fmtAuto(r.prior || 0)}</td>
    </tr>`).join('');
}

// ============================================================
// MORTGAGES (Schedule B)
// ============================================================
function renderMortgages(sched_b) {
  document.getElementById('mort-sub').textContent =
    'Schedule B — Individual Loan Details (annual filings only)';

  const kpis = document.getElementById('mort-kpis');
  if (!sched_b) {
    kpis.innerHTML = `<div class="kpi-card" style="grid-column:span 3;text-align:center;color:#999">
      No Schedule B data for this period. Select an annual (Q4) filing.
    </div>`;
    Plotly.purge('chart-mortgage-map');
    Plotly.purge('chart-rate-hist');
    document.getElementById('mortgage-tbody').innerHTML = '';
    return;
  }

  // KPIs
  kpis.innerHTML = `
    <div class="kpi-card accent">
      <div class="kpi-label">Total Loans</div>
      <div class="kpi-value">${fmtN(sched_b.count)}</div>
      <div class="kpi-sub">Individual loans on Schedule B</div>
    </div>
    <div class="kpi-card green">
      <div class="kpi-label">Total Book Value</div>
      <div class="kpi-value">${fmtAuto(sched_b.total_bv)}</div>
      <div class="kpi-sub">Ending carrying value</div>
    </div>
    <div class="kpi-card orange">
      <div class="kpi-label">States Active</div>
      <div class="kpi-value">${sched_b.by_state?.length || 0}</div>
      <div class="kpi-sub">States with loan activity</div>
    </div>`;

  // Map
  const byState = sched_b.by_state || [];
  Plotly.react('chart-mortgage-map', [{
    type: 'choropleth', locationmode: 'USA-states',
    locations: byState.map(r => r.state), z: byState.map(r => r.bv),
    colorscale: 'Oranges',
    customdata: byState.map(r => r.count),
    hovertemplate: '<b>%{location}</b><br>Book Value: %{z:$,.0f}<br>Loans: %{customdata:,}<extra></extra>',
    colorbar: { title: 'Book Value ($)', thickness: 14, len: 0.8 },
  }], {
    geo: { scope: 'usa', projection: { type: 'albers usa' }, showlakes: true, lakecolor: '#f0f6ff', bgcolor: 'transparent' },
    paper_bgcolor: 'transparent', margin: { l: 0, r: 0, t: 0, b: 0 },
  }, CFG);

  // Rate histogram
  const hist = sched_b.rate_histogram || [];
  Plotly.react('chart-rate-hist', [{
    type: 'bar', x: hist.map(r => `${r.rate}%`), y: hist.map(r => r.count),
    marker: { color: '#4472c4' },
    hovertemplate: '<b>%{x}</b><br>%{y:,} loans<extra></extra>',
  }], { ...LAY, yaxis: { ...LAY.yaxis, title: 'Loan Count' },
    xaxis: { ...LAY.xaxis, title: 'Interest Rate' } }, CFG);

  // Table
  const top20 = byState.slice(0, 20);
  document.getElementById('mortgage-tbody').innerHTML = top20.map((r, i) => `
    <tr>
      <td class="rank">${i + 1}</td>
      <td>${r.state}</td>
      <td class="num">${fmtN(r.count)}</td>
      <td class="num">${fmtAuto(r.bv)}</td>
      <td class="num">${r.avg_rate ? r.avg_rate.toFixed(2) + '%' : '—'}</td>
    </tr>`).join('');
}

// ============================================================
// COMPARE — Cross-firm
// ============================================================
let crossfirmData = null;

async function loadCrossfirm() {
  if (crossfirmData) return crossfirmData;
  crossfirmData = await fetchJSON('data/crossfirm.json');
  return crossfirmData;
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('compare-metric')?.addEventListener('change', () => renderCompare());
});

async function renderCompare() {
  const cf = await loadCrossfirm();
  const metric = document.getElementById('compare-metric')?.value || 'total_invested';
  const metricLabels = {
    total_invested: 'Total Invested Assets',
    bonds: 'Bond Portfolio',
    mortgages: 'Mortgage Loans',
    alts: 'Alternatives (BA)',
    annuity_ytd: 'Annuity Premiums YTD',
  };
  const label = metricLabels[metric] || metric;

  document.getElementById('compare-chart-title').textContent = `${label} — All Companies`;
  document.getElementById('compare-bar-title').textContent = `Latest Period — ${label} by Firm`;

  const coKeys = Object.keys(cf);
  const palette = ['#4472c4','#ed7d31','#a9d18e','#c00000','#ffc000','#5b9bd5','#70ad47','#7030a0','#264478','#9e3ec8','#107c41'];

  // Pre-filter annual (Q4) rows once per company — reused across line + annuity charts
  const annualsByco = Object.fromEntries(coKeys.map(co =>
    [co, cf[co].timeseries.filter(r => r.period.endsWith('Q4'))]
  ));

  // Line chart — annual (Q4) only for cleanliness
  const lineTraces = coKeys.map((co, i) => {
    const d = cf[co];
    const annuals = annualsByco[co];
    return {
      type: 'scatter', mode: 'lines+markers', name: d.ticker || co,
      x: annuals.map(r => r.period), y: annuals.map(r => r[metric] || null),
      line: { color: palette[i % palette.length], width: 2 },
      marker: { size: 5 },
      connectgaps: false,
      hovertemplate: `<b>${d.name}</b><br>%{x}<br>%{y:$,.0f}<extra></extra>`,
    };
  });
  const lineAllY = lineTraces.flatMap(t => t.y);
  Plotly.react('chart-compare-lines', lineTraces,
    { ...LAY, margin: { ...LAY.margin, b: 60 }, height: 380,
      yaxis: { ...LAY.yaxis, ...yTicksAuto(lineAllY) },
      xaxis: { ...LAY.xaxis, categoryorder: 'category ascending' },
      legend: { orientation: 'h', y: -0.18, font: { size: 11 } } }, CFG);

  // Bar chart — latest value per company
  const barItems = coKeys.map(co => {
    const d = cf[co];
    const latest = d.timeseries.slice().sort((a, b) => b.period.localeCompare(a.period))[0] || {};
    return { co, name: d.name, ticker: d.ticker || co, period: latest.period || '—', val: latest[metric] || 0, latest };
  }).sort((a, b) => b.val - a.val);

  Plotly.react('chart-compare-bar', [{
    type: 'bar', orientation: 'h',
    x: barItems.map(r => r.val).reverse(),
    y: barItems.map(r => r.ticker).reverse(),
    marker: { color: barItems.map((_, i) => palette[(barItems.length - 1 - i) % palette.length]).reverse() },
    text: barItems.map(r => r.period).reverse(),
    textposition: 'outside',
    hovertemplate: '<b>%{y}</b><br>%{x:$,.0f}<extra></extra>',
  }], { ...LAY, margin: { ...LAY.margin, l: 60, r: 80 }, height: 320,
    xaxis: { ...LAY.xaxis, ...xTicksAuto(barItems.map(r => r.val)) } }, CFG);

  // Annuity comparison — annual Q4 only, grouped bar
  const annualPeriods = [...new Set(coKeys.flatMap(co =>
    annualsByco[co].map(r => r.period)
  ))].sort();
  const recentPeriods = annualPeriods.slice(-5); // last 5 annual periods

  const annuityTraces = coKeys.map((co, i) => {
    const d = cf[co];
    const byPeriod = Object.fromEntries(d.timeseries.map(r => [r.period, r.annuity_ytd || 0]));
    return {
      type: 'bar', name: d.ticker || co,
      x: recentPeriods, y: recentPeriods.map(p => byPeriod[p] || 0),
      marker: { color: palette[i % palette.length] },
      hovertemplate: `<b>${d.name}</b><br>%{x}<br>%{y:$,.0f}<extra></extra>`,
    };
  });
  const annY2 = annuityTraces.flatMap(t => t.y);
  Plotly.react('chart-compare-annuity', annuityTraces,
    { ...LAY, barmode: 'group', height: 340,
      yaxis: { ...LAY.yaxis, ...yTicksAuto(annY2) },
      legend: { orientation: 'h', y: -0.2, font: { size: 11 } } }, CFG);

  // Summary table
  document.getElementById('compare-tbody').innerHTML = barItems.map(r => {
    const d = cf[r.co];
    const latest = r.latest;
    return `<tr>
      <td>${d.name}</td>
      <td><strong>${d.ticker || r.co}</strong></td>
      <td>${latest.period || '—'}</td>
      <td class="num">${latest.total_invested ? fmtAuto(latest.total_invested) : '—'}</td>
      <td class="num">${latest.bonds ? fmtAuto(latest.bonds) : '—'}</td>
      <td class="num">${latest.mortgages ? fmtAuto(latest.mortgages) : '—'}</td>
      <td class="num">${latest.annuity_ytd ? fmtAuto(latest.annuity_ytd) : '—'}</td>
    </tr>`;
  }).join('');
}

// ============================================================
// DATA ROOM — company-first, full schedule viewer
// ============================================================

let drCatalog = null;          // catalog.json
let drPeriodCache = {};        // entity_period -> period JSON
let drCurrentSched = 't';      // active schedule tab
let drTableRows = [];          // current rendered rows (for CSV export)
let drTableHeaders = [];       // current column headers

async function renderDataRoom() {
  if (!drCatalog) {
    drCatalog = await fetchJSON('data/catalog.json');
    drInitSelectors();
    drInitTabs();
    document.getElementById('dr-search')?.addEventListener('input', drApplyFilter);
  }
  await drLoadView();
}

function drInitSelectors() {
  const coSel = document.getElementById('dr-company');
  const cos = [...new Set(drCatalog.map(r => r.company))].sort();
  populateSelect(coSel, cos, co => (COMPANIES[co]?.name || co) + ' (' + (COMPANIES[co]?.ticker || '') + ')');
  coSel.addEventListener('change', drOnCompanyChange);
  document.getElementById('dr-entity')?.addEventListener('change', drOnEntityChange);
  document.getElementById('dr-period')?.addEventListener('change', () => drLoadView());
  drOnCompanyChange();
}

function drInitTabs() {
  document.querySelectorAll('.sched-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sched-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      drCurrentSched = btn.dataset.sched;
      drLoadView();
    });
  });
}

function drOnCompanyChange() {
  const co = document.getElementById('dr-company')?.value;
  const entries = drCatalog.filter(r => r.company === co);
  const entities = [...new Set(entries.map(r => r.entity))].sort();

  populateSelect(document.getElementById('dr-entity'), entities);
  drOnEntityChange();
}

function drOnEntityChange() {
  const co     = document.getElementById('dr-company')?.value;
  const entity = document.getElementById('dr-entity')?.value;
  const entries = drCatalog.filter(r => r.company === co && r.entity === entity);
  const periods = entries.map(r => r.period).sort().reverse();

  populateSelect(document.getElementById('dr-period'), periods);
  drLoadView();
}

async function drLoadView() {
  const co     = document.getElementById('dr-company')?.value;
  const entity = document.getElementById('dr-entity')?.value;
  const period = document.getElementById('dr-period')?.value;
  if (!co || !entity || !period) return;

  // Update bulk download link
  const allLinks = {
    t: `data/${co}/sched_t_all.csv`,
    dq: `data/${co}/sched_dq_all.csv`,
    b: `data/${co}/sched_b_states.csv`,
    ba: `data/${co}/sched_ba_all.csv`,
    kpi: `data/download_all_timeseries.csv`,
  };
  const allLinkEl = document.getElementById('dr-all-link');
  if (allLinkEl) {
    allLinkEl.href = allLinks[drCurrentSched] || '#';
    allLinkEl.download = (allLinks[drCurrentSched] || '').split('/').pop();
  }

  if (drCurrentSched === 'kpi') {
    // KPI timeseries — load from overview
    const overview = await drGetOverview(co);
    const ts = (overview?.timeseries || []).filter(r => r.entity === entity);
    drRenderKpiTable(ts);
    return;
  }

  // All other schedules come from the period detail JSON
  const key = `${entity}_${period}`;
  if (!drPeriodCache[key]) {
    try {
      drPeriodCache[key] = await fetchJSON(`data/${co}/${entity}_${period}.json`);
    } catch {
      drPeriodCache[key] = {};
    }
  }
  const pd = drPeriodCache[key];

  const schedDisp = {
    t:  () => drRenderSchedT(pd.sched_t),
    dq: () => drRenderSchedDQ(pd.sched_d_quality),
    b:  () => drRenderSchedB(pd.sched_b),
    ba: () => drRenderSchedBA(pd.sched_ba),
  };
  schedDisp[drCurrentSched]?.();
}

const drOverviewCache = {};
async function drGetOverview(co) {
  if (!drOverviewCache[co]) drOverviewCache[co] = await fetchJSON(`data/${co}/overview.json`);
  return drOverviewCache[co];
}

// --- Shared table renderer ---
function drSetTable(headers, rows, emptyMsg) {
  drTableHeaders = headers;
  drTableRows = rows;
  document.getElementById('dr-row-count').textContent =
    rows.length ? `${rows.length.toLocaleString()} rows` : '';
  const thead = document.getElementById('dr-thead');
  const tbody = document.getElementById('dr-tbody');
  if (!thead || !tbody) return;
  thead.innerHTML = '<tr>' + headers.map(h => `<th>${h.label}</th>`).join('') + '</tr>';

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="${headers.length}" style="text-align:center;color:#999;padding:24px">${emptyMsg}</td></tr>`;
    return;
  }
  drRenderTableBody(rows);
}

function drRenderTableBody(rows) {
  const tbody = document.getElementById('dr-tbody');
  tbody.innerHTML = rows.map(r =>
    '<tr>' + drTableHeaders.map(h => {
      const v = r[h.key];
      const cls = h.num ? ' class="num"' : '';
      const display = h.fmt ? h.fmt(v) : (v ?? '');
      return `<td${cls}>${display}</td>`;
    }).join('') + '</tr>'
  ).join('');
}

function drFilteredRows() {
  const q = (document.getElementById('dr-search')?.value || '').toLowerCase();
  if (!q) return drTableRows;
  return drTableRows.filter(r =>
    drTableHeaders.some(h => String(r[h.key] ?? '').toLowerCase().includes(q))
  );
}

function drApplyFilter() {
  drRenderTableBody(drFilteredRows());
}

// --- Schedule renderers ---
function drRenderSchedT(data) {
  if (!data?.length) {
    drSetTable([], [], 'No Schedule T data for this period.');
    return;
  }
  const headers = [
    { key: 'state', label: 'Code' },
    { key: 'name',  label: 'State' },
    { key: 'life',    label: 'Life Premiums',    num: true, fmt: v => fmtAuto(v||0) },
    { key: 'annuity', label: 'Annuity',          num: true, fmt: v => fmtAuto(v||0) },
    { key: 'total',   label: 'Total',            num: true, fmt: v => fmtAuto(v||0) },
  ];
  const sorted = data.slice().sort((a, b) => (b.total||0) - (a.total||0));
  drSetTable(headers, sorted, '');
}

function drRenderSchedDQ(data) {
  if (!data?.length) {
    drSetTable([], [], 'No bond quality data for this period (annual filings only).');
    return;
  }
  const headers = [
    { key: 'category', label: 'Category' },
    { key: 'naic',     label: 'NAIC Rating' },
    { key: 'current',  label: 'Current Year BV', num: true, fmt: v => fmtAuto(v||0) },
    { key: 'prior',    label: 'Prior Year BV',   num: true, fmt: v => fmtAuto(v||0) },
  ];
  drSetTable(headers, data, '');
}

function drRenderSchedB(data) {
  if (!data) {
    drSetTable([], [], 'No Schedule B data for this period (annual filings only).');
    return;
  }
  const byState = (data.by_state || []).slice().sort((a, b) => (b.bv||0) - (a.bv||0));
  const headers = [
    { key: 'state',    label: 'State' },
    { key: 'count',    label: 'Loan Count', num: true, fmt: v => fmtN(v||0) },
    { key: 'bv',       label: 'Book Value', num: true, fmt: v => fmtAuto(v||0) },
    { key: 'avg_rate', label: 'Avg Rate',   num: true, fmt: v => v ? v.toFixed(3)+'%' : '—' },
  ];
  drSetTable(headers, byState,
    'No mortgage data. Note: state-level summary shown; individual loans in raw CSVs.');
  document.getElementById('dr-row-count').textContent +=
    ` · ${fmtN(data.count)} individual loans · ${fmtAuto(data.total_bv)} total`;
}

function drRenderSchedBA(data) {
  if (!data) {
    drSetTable([], [], 'No Schedule BA data for this period (annual filings only).');
    return;
  }
  const headers = [
    { key: 'name',   label: 'Investment Name' },
    { key: 'state',  label: 'State' },
    { key: 'bv',     label: 'Book Value', num: true, fmt: v => fmtAuto(v||0) },
    { key: 'income', label: 'Inv. Income', num: true, fmt: v => v ? fmtAuto(v) : '—' },
  ];
  drSetTable(headers, data.top || [], '');
  document.getElementById('dr-row-count').textContent +=
    ` of ${fmtN(data.count)} total · ${fmtAuto(data.total_bv)} AUM`;
}

function drRenderKpiTable(ts) {
  const sorted = ts.slice().sort((a, b) => a.period.localeCompare(b.period));
  const headers = [
    { key: 'period',      label: 'Period' },
    { key: 'total_invested', label: 'Total Invested', num: true, fmt: v => fmtAuto(v||0) },
    { key: 'bonds',       label: 'Bonds',    num: true, fmt: v => fmtAuto(v||0) },
    { key: 'mortgages',   label: 'Mortgages',num: true, fmt: v => fmtAuto(v||0) },
    { key: 'alts',        label: 'Alts (BA)',num: true, fmt: v => fmtAuto(v||0) },
    { key: 'cash',        label: 'Cash',     num: true, fmt: v => fmtAuto(v||0) },
    { key: 'annuity_ytd', label: 'Annuity YTD', num: true, fmt: v => fmtAuto(v||0) },
  ];
  drSetTable(headers, sorted, 'No timeseries data for this entity.');
}

// --- CSV export (current view) ---
function drExportCSV() {
  if (!drTableRows.length) return;
  const rows = drFilteredRows();

  const keys = drTableHeaders.map(h => h.key);
  const lines = [
    keys.join(','),
    ...rows.map(r => keys.map(k => {
      const v = r[k] ?? '';
      const s = String(v);
      return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g,'""')}"` : s;
    }).join(','))
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const co = document.getElementById('dr-company')?.value || 'data';
  const entity = document.getElementById('dr-entity')?.value || '';
  const period = document.getElementById('dr-period')?.value || '';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${co}_${entity}_${period}_sched_${drCurrentSched}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}
