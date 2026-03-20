// ============================================================
// NAIC Statutory Filings Dashboard — app.js
// ============================================================

// --- State ---
let COMPANIES = {};
let currentCo = null;
let currentEntity = null;
let currentPeriod = null;
let overviewData = null;
let periodData = null;
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
const xTicksAuto = yTicksAuto;
const trunc = (s, n) => s && s.length > n ? s.slice(0, n - 1) + '…' : (s || '');
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
const CAT_COLORS = { Bonds: '#4472c4', Mortgages: '#ed7d31', Alternatives: '#a9d18e', Cash: '#70ad47', 'Real Estate': '#9e3ec8' };
const NAIC_COLORS = { '1':'#107c41','2':'#70ad47','3':'#ffc000','4':'#ed7d31','5':'#c55a11','6':'#c00000' };

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

// ============================================================
// FULL-DATA CSV LOADING + PAGINATION
// ============================================================

const PAGE_SIZE = 500;
const csvCache = {};   // url → { headers, rows }
const pgViews = {};    // viewId → { allRows, filteredRows, page, headerDefs }

function parseCSV(text) {
  const lines = text.split('\n');
  const nonEmpty = lines.filter(l => l.trim() !== '');
  if (!nonEmpty.length) return { headers: [], rows: [] };
  const headers = splitCSVLine(nonEmpty[0]);
  const rows = nonEmpty.slice(1).map(line => {
    const vals = splitCSVLine(line);
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']));
  });
  return { headers, rows };
}

function splitCSVLine(line) {
  const result = [];
  let cur = '', inQ = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') { inQ = !inQ; }
    else if (c === ',' && !inQ) { result.push(cur.trim()); cur = ''; }
    else { cur += c; }
  }
  result.push(cur.trim());
  return result;
}

async function fetchCSV(url) {
  if (csvCache[url]) return csvCache[url];
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  const text = await r.text();
  csvCache[url] = parseCSV(text);
  return csvCache[url];
}

// Create/update a paginated view.
// headerDefs: [{ key, label, num, fmt }]
function pgCreate(viewId, headerDefs, allRows) {
  pgViews[viewId] = { headerDefs, allRows, filteredRows: allRows, page: 0 };
  pgRender(viewId);
}

function pgSearch(viewId, query) {
  const v = pgViews[viewId];
  if (!v) return;
  const q = query.toLowerCase();
  v.filteredRows = q
    ? v.allRows.filter(r => v.headerDefs.some(h => String(r[h.key] ?? '').toLowerCase().includes(q)))
    : v.allRows;
  v.page = 0;
  pgRender(viewId);
}

function pgGoPage(viewId, page) {
  const v = pgViews[viewId];
  if (!v) return;
  const maxPage = Math.max(0, Math.ceil(v.filteredRows.length / PAGE_SIZE) - 1);
  v.page = Math.max(0, Math.min(page, maxPage));
  pgRender(viewId);
}

function pgRender(viewId) {
  const v = pgViews[viewId];
  if (!v) return;
  const { headerDefs, filteredRows, page } = v;
  const total = filteredRows.length;
  const maxPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);
  const start = page * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, total);
  const pageRows = filteredRows.slice(start, end);

  // thead
  const thead = document.getElementById(`${viewId}-thead`);
  const tbody = document.getElementById(`${viewId}-tbody`);
  if (!thead || !tbody) return;

  thead.innerHTML = '<tr>' + headerDefs.map(h => `<th${h.num ? ' class="num"' : ''}>${h.label}</th>`).join('') + '</tr>';

  if (!total) {
    tbody.innerHTML = `<tr><td colspan="${headerDefs.length}" style="text-align:center;color:#999;padding:20px">No rows match filter</td></tr>`;
  } else {
    tbody.innerHTML = pageRows.map((r, i) =>
      '<tr>' + headerDefs.map(h => {
        const raw = r[h.key] ?? '';
        const v = h.num ? (parseFloat(raw) || 0) : raw;
        const display = h.fmt ? h.fmt(v, r) : (h.num ? fmtAuto(v) : raw);
        return `<td${h.num ? ' class="num"' : ''}>${display}</td>`;
      }).join('') + '</tr>'
    ).join('');
  }

  // Pagination bar
  const pgBar = document.getElementById(`${viewId}-pagination`);
  if (!pgBar) return;
  if (total <= PAGE_SIZE) {
    pgBar.style.display = 'none';
    return;
  }
  pgBar.style.display = 'flex';
  const rowStart = total ? start + 1 : 0;
  const rowEnd   = end;
  pgBar.innerHTML = `
    <button class="pg-btn" onclick="pgGoPage('${viewId}',0)" ${page===0?'disabled':''}>«</button>
    <button class="pg-btn" onclick="pgGoPage('${viewId}',${page-1})" ${page===0?'disabled':''}>‹</button>
    <span class="pg-info">${fmtN(rowStart)}–${fmtN(rowEnd)} of ${fmtN(total)} rows &nbsp;·&nbsp; page ${page+1} of ${maxPage+1}</span>
    <button class="pg-btn" onclick="pgGoPage('${viewId}',${page+1})" ${page>=maxPage?'disabled':''}>›</button>
    <button class="pg-btn" onclick="pgGoPage('${viewId}',${maxPage})" ${page>=maxPage?'disabled':''}>»</button>`;
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  document.querySelectorAll('.topnav a[data-section]').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); showSection(a.dataset.section); });
  });
  document.getElementById('sel-company').addEventListener('change', e => selectCompany(e.target.value));
  document.getElementById('sel-entity').addEventListener('change',  e => selectEntity(e.target.value));
  document.getElementById('sel-period').addEventListener('change',  e => selectPeriod(e.target.value));

  document.getElementById('premiums-search').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('#premiums-tbody tr').forEach(tr => {
      tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
  document.getElementById('mortgage-state-search').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('#mortgage-tbody tr').forEach(tr => {
      tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
  document.getElementById('full-loans-search').addEventListener('input', e => pgSearch('full-loans', e.target.value));
  document.getElementById('full-ba-search').addEventListener('input',    e => pgSearch('full-ba',    e.target.value));

  try {
    COMPANIES = await fetchJSON('data/companies.json');
    populateCompanySelector();
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
  if (id === 'sec-premiums'  && periodData) renderPremiums(periodData.sched_t, currentPeriod);
  if (id === 'sec-portfolio' && periodData) renderPortfolioDetail(periodData.sched_d_quality);
  if (id === 'sec-mortgages' && periodData) renderMortgages(periodData.sched_b);
  if (id === 'sec-alts'      && periodData) renderAlternatives(periodData.sched_ba);
  if (id === 'sec-compare')  renderCompare();
  if (id === 'sec-data')     renderDataRoom();
}

// ============================================================
// SELECTORS
// ============================================================
function populateCompanySelector() {
  populateSelect(document.getElementById('sel-company'), Object.keys(COMPANIES),
    k => `${COMPANIES[k].name} (${COMPANIES[k].ticker})`);
}
async function selectCompany(coKey) {
  if (coKey === currentCo && overviewData) { renderAll(); return; }
  currentCo = coKey;
  periodData = null;
  try {
    overviewData = await fetchJSON(`data/${coKey}/overview.json`);
  } catch (err) {
    overviewData = null; showNoData(true); return;
  }
  const ep = overviewData.entity_periods || {};
  const entities = Object.keys(ep).filter(e => ep[e].length > 0);
  populateSelect(document.getElementById('sel-entity'), entities);
  await selectEntity(entities[0] || overviewData.meta?.entities?.[0] || '');
}
async function selectEntity(entity) {
  currentEntity = entity;
  const periods = ((overviewData?.entity_periods || {})[entity] || []).slice().reverse();
  populateSelect(document.getElementById('sel-period'), periods);
  await selectPeriod(periods[0] || '');
}
async function selectPeriod(period) {
  currentPeriod = period;
  periodData = null;
  if (currentCo && currentEntity && period) {
    try { periodData = await fetchJSON(`data/${currentCo}/${currentEntity}_${period}.json`); }
    catch { periodData = null; }
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

  document.getElementById('ov-title').textContent = `${meta.name || ''} — ${currentEntity} ${currentPeriod || ''}`;
  document.getElementById('ov-sub').textContent   = `NAIC Statutory Filing · ${currentEntity}`;

  const kpiRow = ts.find(r => r.period === currentPeriod) ||
                 ts.slice().sort((a,b) => b.period.localeCompare(a.period))[0] || {};
  if (pd?.sched_b?.count)  kpiRow._loan_count  = pd.sched_b.count;
  if (pd?.sched_ba?.count) kpiRow._ba_count    = pd.sched_ba.count;
  if (pd?.sched_t?.length) kpiRow._state_count = pd.sched_t.length;

  renderKpiGrid(kpiRow);
  renderDonut(kpiRow);
  renderNaicBar(pd?.sched_d_quality);
  renderHistTotal(ts);
  renderHistMix(ts);
  renderHistAnnuity(ts);
  renderOvTopStates(pd?.sched_t);
  renderOvTopLoans(pd?.sched_b);
  renderOvTopBA(pd?.sched_ba);

  if (currentSection === 'sec-premiums')  renderPremiums(pd?.sched_t, currentPeriod);
  if (currentSection === 'sec-portfolio') renderPortfolioDetail(pd?.sched_d_quality);
  if (currentSection === 'sec-mortgages') renderMortgages(pd?.sched_b);
  if (currentSection === 'sec-alts')      renderAlternatives(pd?.sched_ba);
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
    { label: 'Indiv. Loans',      val: row._loan_count,     sub: 'Loan count on Schedule B',          cls: 'teal', fmt: fmtN },
    { label: 'Alt Holdings',      val: row._ba_count,       sub: 'Holdings count on Schedule BA',     cls: '',     fmt: fmtN },
    { label: 'States w/ Premium', val: row._state_count,    sub: 'States reporting on Schedule T',    cls: '',     fmt: v => String(v) },
  ];
  grid.innerHTML = cards.map(c => {
    const display = c.val
      ? `<div class="kpi-value">${(c.fmt || fmtAuto)(c.val)}</div><div class="kpi-sub">${c.sub}</div>`
      : `<div class="kpi-value na">N/A</div><div class="kpi-na-badge">not in filing</div>`;
    return `<div class="kpi-card ${c.cls}"><div class="kpi-label">${c.label}</div>${display}</div>`;
  }).join('');
  renderDataGaps(row);
}
function renderDataGaps(row) {
  const bar = document.getElementById('data-gaps-bar');
  const chips = document.getElementById('data-gaps-chips');
  if (!bar || !chips) return;
  const missing = [];
  if (!row.bonds)       missing.push({ label: 'Bonds',        hint: 'Schedule D not parsed' });
  if (!row.mortgages)   missing.push({ label: 'Mortgages',    hint: 'Schedule B not in filing' });
  if (!row.alts)        missing.push({ label: 'Alternatives', hint: 'Schedule BA not parsed' });
  if (!row.cash)        missing.push({ label: 'Cash',         hint: 'Schedule E not parsed' });
  if (!row.annuity_ytd) missing.push({ label: 'Annuity YTD', hint: 'Schedule T not parsed' });
  if (!missing.length) { bar.style.display = 'none'; return; }
  bar.style.display = '';
  chips.innerHTML = missing.map(m => `<span class="gap-chip" title="${m.hint}">${m.label}</span>`).join('');
}

// ============================================================
// OVERVIEW QUICK-LOOK TABLES
// ============================================================
function renderOvTopStates(sched_t) {
  const tbody = document.getElementById('ov-top-states-tbody');
  if (!sched_t?.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999;padding:12px">No Schedule T data</td></tr>'; return;
  }
  const sorted = sched_t.slice().sort((a,b) => b.total - a.total).slice(0,10);
  tbody.innerHTML = sorted.map((r,i) => `<tr>
    <td class="rank">${i+1}</td>
    <td>${r.name||r.state} <span style="color:#999">(${r.state})</span></td>
    <td class="num">${fmtAuto(r.life||0)}</td>
    <td class="num">${fmtAuto(r.annuity||0)}</td>
    <td class="num">${fmtAuto(r.total||0)}</td>
  </tr>`).join('');
}
function renderOvTopLoans(sched_b) {
  const tbody = document.getElementById('ov-top-loans-tbody');
  if (!sched_b?.top_loans?.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999;padding:12px">No loan data (annual filings only)</td></tr>'; return;
  }
  tbody.innerHTML = sched_b.top_loans.slice(0,10).map((r,i) => `<tr>
    <td class="rank">${i+1}</td>
    <td>${r.city||'—'}</td>
    <td>${r.state||'—'}</td>
    <td class="num">${fmtAuto(r.bv)}</td>
    <td class="num">${r.rate ? r.rate.toFixed(3)+'%' : '—'}</td>
  </tr>`).join('');
}
function renderOvTopBA(sched_ba) {
  const tbody = document.getElementById('ov-top-ba-tbody');
  if (!sched_ba?.top?.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#999;padding:12px">No Schedule BA data (annual filings only)</td></tr>'; return;
  }
  tbody.innerHTML = sched_ba.top.slice(0,10).map((r,i) => {
    const yld = r.income && r.bv ? ((r.income/r.bv)*100).toFixed(2)+'%' : '—';
    return `<tr>
      <td class="rank">${i+1}</td>
      <td>${r.name||'—'}</td>
      <td>${r.state||'—'}</td>
      <td class="num">${fmtAuto(r.bv)}</td>
      <td class="num">${r.income ? fmtAuto(r.income) : '—'}</td>
      <td class="num">${yld}</td>
    </tr>`;
  }).join('');
}

// ============================================================
// DONUT
// ============================================================
function renderDonut(row) {
  const labels = ['Bonds','Mortgages','Alternatives','Cash','Real Estate'];
  const values = [row.bonds,row.mortgages,row.alts,row.cash,row.real_estate].map(v=>v||0);
  if (values.every(v=>v===0)) { Plotly.purge('chart-donut'); return; }
  Plotly.react('chart-donut',[{
    type:'pie', hole:0.5, labels, values,
    marker:{colors:Object.values(CAT_COLORS)},
    textinfo:'percent', hovertemplate:'<b>%{label}</b><br>%{value:$,.0f}<extra></extra>', sort:false,
  }],{...LAY,margin:{l:10,r:10,t:10,b:10},showlegend:true,
    legend:{orientation:'v',x:1,y:0.5,font:{size:11}}},CFG);
}

// ============================================================
// NAIC QUALITY BAR
// ============================================================
function renderNaicBar(dq) {
  if (!dq?.length) { Plotly.purge('chart-naic-bar'); return; }
  const byNaic = {};
  dq.forEach(r => {
    const m = r.naic?.match(/(\d)/);
    if (!m) return;
    const n = m[1];
    byNaic[n] = (byNaic[n]||0) + (r.current||0);
  });
  const keys = ['1','2','3','4','5','6'].filter(k => byNaic[k]);
  const yVals = keys.map(k => byNaic[k]);
  Plotly.react('chart-naic-bar',[{
    type:'bar', x:keys.map(k=>`NAIC ${k}`), y:yVals,
    marker:{color:keys.map(k=>NAIC_COLORS[k]||'#aaa')},
    hovertemplate:'<b>%{x}</b><br>%{y:$,.0f}<extra></extra>',
  }],{...LAY,yaxis:{...LAY.yaxis,...yTicksAuto(yVals)}},CFG);
}

// ============================================================
// HISTORICAL CHARTS
// ============================================================
function renderHistTotal(ts) {
  if (!ts.length) { Plotly.purge('chart-hist-total'); return; }
  const sorted = ts.slice().sort((a,b)=>a.period.localeCompare(b.period));
  document.getElementById('hist-hint').textContent =
    `${sorted.length} data points · ${sorted[0]?.period} – ${sorted.at(-1)?.period}`;
  const histY = sorted.map(r=>r.total_invested||null);
  Plotly.react('chart-hist-total',[{
    type:'scatter',mode:'lines+markers',x:sorted.map(r=>r.period),y:histY,
    line:{color:'#4472c4',width:2},marker:{size:6},connectgaps:false,
    hovertemplate:'<b>%{x}</b><br>%{y:$,.0f}<extra></extra>',
  }],{...LAY,yaxis:{...LAY.yaxis,...yTicksAuto(histY.filter(Boolean))}},CFG);
}
function renderHistMix(ts) {
  if (!ts.length) { Plotly.purge('chart-hist-mix'); return; }
  const sorted = ts.slice().sort((a,b)=>a.period.localeCompare(b.period));
  const x = sorted.map(r=>r.period);
  const series = [
    {name:'Bonds',key:'bonds',color:'#4472c4'},
    {name:'Mortgages',key:'mortgages',color:'#ed7d31'},
    {name:'Alternatives',key:'alts',color:'#a9d18e'},
    {name:'Cash',key:'cash',color:'#70ad47'},
  ];
  const mixTotals = sorted.map(r=>series.reduce((s,s2)=>s+(r[s2.key]||0),0));
  Plotly.react('chart-hist-mix',
    series.map(s=>({type:'bar',name:s.name,x,y:sorted.map(r=>r[s.key]||null),marker:{color:s.color},
      hovertemplate:`<b>${s.name}</b><br>%{y:$,.0f}<extra></extra>`})),
    {...LAY,barmode:'stack',yaxis:{...LAY.yaxis,...yTicksAuto(mixTotals)}},CFG);
}
function renderHistAnnuity(ts) {
  if (!ts.length) { Plotly.purge('chart-hist-annuity'); return; }
  const sorted = ts.slice().sort((a,b)=>a.period.localeCompare(b.period));
  const annY = sorted.map(r=>r.annuity_ytd||null);
  Plotly.react('chart-hist-annuity',[{
    type:'bar',x:sorted.map(r=>r.period),y:annY,marker:{color:'#7030a0'},
    hovertemplate:'<b>%{x}</b><br>%{y:$,.0f}<extra></extra>',
  }],{...LAY,yaxis:{...LAY.yaxis,...yTicksAuto(annY.filter(Boolean))}},CFG);
}

// ============================================================
// PREMIUMS (Schedule T) — ALL STATES
// ============================================================
function renderPremiums(sched_t, period) {
  document.getElementById('prem-sub').textContent =
    `Schedule T — Direct Business, Year to Date ${period||''}`;
  if (!sched_t?.length) {
    Plotly.purge('chart-premiums-map'); Plotly.purge('chart-top-states');
    document.getElementById('premiums-tbody').innerHTML =
      '<tr><td colspan="6" style="text-align:center;color:#999;padding:20px">No Schedule T data for this period</td></tr>';
    return;
  }
  const sorted = sched_t.slice().sort((a,b)=>b.total-a.total);
  const grandTotal = sorted.reduce((s,r)=>s+(r.total||0),0);

  Plotly.react('chart-premiums-map',[{
    type:'choropleth',locationmode:'USA-states',
    locations:sorted.map(r=>r.state),z:sorted.map(r=>r.annuity),
    colorscale:'Blues',reversescale:false,
    hovertemplate:'<b>%{location}</b><br>Annuity: %{z:$,.0f}<extra></extra>',
    colorbar:{title:'Annuity ($)',thickness:14,len:0.8},
  }],{geo:{scope:'usa',projection:{type:'albers usa'},showlakes:true,lakecolor:'#f0f6ff',bgcolor:'transparent'},
    paper_bgcolor:'transparent',margin:{l:0,r:0,t:0,b:0}},CFG);

  const top20 = sorted.slice(0,20).reverse();
  Plotly.react('chart-top-states',[
    {type:'bar',orientation:'h',name:'Life',   x:top20.map(r=>r.life||0),   y:top20.map(r=>r.state),marker:{color:'#4472c4'}},
    {type:'bar',orientation:'h',name:'Annuity',x:top20.map(r=>r.annuity||0),y:top20.map(r=>r.state),marker:{color:'#ed7d31'}},
  ],{...LAY,barmode:'stack',margin:{...LAY.margin,l:45},
    xaxis:{...LAY.xaxis,...xTicksAuto(top20.map(r=>(r.life||0)+(r.annuity||0)))},height:420},CFG);

  document.getElementById('premiums-tbody').innerHTML = sorted.map((r,i) => {
    const pct = grandTotal ? ((r.total/grandTotal)*100).toFixed(2)+'%' : '—';
    return `<tr>
      <td class="rank">${i+1}</td>
      <td>${r.name||r.state} <span style="color:#999">(${r.state})</span></td>
      <td class="num">${fmtAuto(r.life||0)}</td>
      <td class="num">${fmtAuto(r.annuity||0)}</td>
      <td class="num">${fmtAuto(r.total||0)}</td>
      <td class="num">${pct}</td>
    </tr>`;
  }).join('');
}

// ============================================================
// PORTFOLIO DETAIL (Schedule D Quality) — ALL ROWS
// ============================================================
function renderPortfolioDetail(dq) {
  if (!dq?.length) {
    Plotly.purge('chart-naic-detail');
    document.getElementById('naic-tbody').innerHTML =
      '<tr><td colspan="6" style="text-align:center;color:#999;padding:20px">No bond quality data for this period (annual filings only)</td></tr>';
    return;
  }
  const naics = ['NAIC 1','NAIC 2','NAIC 3','NAIC 4','NAIC 5','NAIC 6'];
  const catTotals = {};
  dq.forEach(r => {
    const n = r.naic?.match(/(\d)/)?.[1]; if (!n) return;
    const cat = r.category||'Other';
    if (!catTotals[cat]) catTotals[cat] = {};
    catTotals[cat][`NAIC ${n}`] = (catTotals[cat][`NAIC ${n}`]||0) + (r.current||0);
  });
  const catKeys = Object.keys(catTotals);
  const portYvals = catKeys.map(c => naics.reduce((s,n)=>s+(catTotals[c][n]||0),0));
  Plotly.react('chart-naic-detail',
    naics.map(n=>({type:'bar',name:n,x:catKeys.map(c=>trunc(c,28)),y:catKeys.map(c=>catTotals[c][n]||0),
      marker:{color:NAIC_COLORS[n.slice(-1)]},hovertemplate:`<b>${n}</b><br>%{x}<br>%{y:$,.0f}<extra></extra>`})),
    {...LAY,barmode:'stack',height:400,margin:{...LAY.margin,b:130},
      yaxis:{...LAY.yaxis,...yTicksAuto(portYvals)},xaxis:{...LAY.xaxis,tickangle:-40,automargin:true}},CFG);

  document.getElementById('naic-tbody').innerHTML = dq.map(r => {
    const change = (r.current||0) - (r.prior||0);
    const pctStr = r.prior ? (change>=0?'+':'') + ((change/r.prior)*100).toFixed(1)+'%' : '—';
    const col = change>0?'var(--green)':change<0?'var(--red)':'var(--muted)';
    return `<tr>
      <td>${r.category||''}</td>
      <td><strong>${r.naic||''}</strong></td>
      <td class="num">${fmtAuto(r.current||0)}</td>
      <td class="num" style="color:#888">${fmtAuto(r.prior||0)}</td>
      <td class="num" style="color:${col}">${r.prior ? (change>=0?'+':'')+fmtAuto(change) : '—'}</td>
      <td class="num" style="color:${col}">${pctStr}</td>
    </tr>`;
  }).join('');
}

// ============================================================
// MORTGAGES (Schedule B)
// ============================================================

// Track what's loaded for the full-loans view
let _fullLoansContext = null; // { co, entity, period }

function triggerLoadFullLoans() {
  if (_fullLoansContext) {
    loadFullLoans(_fullLoansContext.co, _fullLoansContext.entity, _fullLoansContext.period);
  }
}

function renderMortgages(sched_b) {
  document.getElementById('mort-sub').textContent = 'Schedule B — Individual Loan Details (annual filings only)';
  const kpis = document.getElementById('mort-kpis');

  if (!sched_b) {
    kpis.innerHTML = `<div class="kpi-card" style="grid-column:span 4;text-align:center;color:#999">
      No Schedule B data for this period. Select an annual (Q4) filing.</div>`;
    Plotly.purge('chart-mortgage-map'); Plotly.purge('chart-rate-hist');
    document.getElementById('mortgage-tbody').innerHTML = '';
    document.getElementById('full-loans-count-info').textContent = '';
    document.getElementById('full-loans-load-btn').disabled = true;
    document.getElementById('full-loans-search-bar').style.display = 'none';
    document.getElementById('full-loans-thead').innerHTML = '';
    document.getElementById('full-loans-tbody').innerHTML =
      '<tr><td colspan="6" style="text-align:center;color:#999;padding:20px">No Schedule B data for this period</td></tr>';
    document.getElementById('full-loans-pagination').style.display = 'none';
    _fullLoansContext = null;
    return;
  }

  // Store context for lazy load
  _fullLoansContext = { co: currentCo, entity: currentEntity, period: currentPeriod };

  // Weighted avg rate
  const byState = sched_b.by_state || [];
  let totalBv = 0, weightedRate = 0;
  byState.forEach(r => { totalBv += r.bv||0; weightedRate += (r.avg_rate||0)*(r.bv||0); });
  const avgRate = totalBv > 0 ? weightedRate/totalBv : null;

  kpis.innerHTML = `
    <div class="kpi-card accent"><div class="kpi-label">Total Loans</div>
      <div class="kpi-value">${fmtN(sched_b.count)}</div><div class="kpi-sub">Individual loans on Schedule B</div></div>
    <div class="kpi-card green"><div class="kpi-label">Total Book Value</div>
      <div class="kpi-value">${fmtAuto(sched_b.total_bv)}</div><div class="kpi-sub">Ending carrying value</div></div>
    <div class="kpi-card orange"><div class="kpi-label">States Active</div>
      <div class="kpi-value">${byState.length}</div><div class="kpi-sub">States with loan activity</div></div>
    <div class="kpi-card teal"><div class="kpi-label">Wt. Avg Rate</div>
      <div class="kpi-value">${avgRate ? avgRate.toFixed(2)+'%' : 'N/A'}</div><div class="kpi-sub">Book value weighted avg coupon</div></div>`;

  // Map
  Plotly.react('chart-mortgage-map',[{
    type:'choropleth',locationmode:'USA-states',
    locations:byState.map(r=>r.state),z:byState.map(r=>r.bv),colorscale:'Oranges',
    customdata:byState.map(r=>r.count),
    hovertemplate:'<b>%{location}</b><br>Book Value: %{z:$,.0f}<br>Loans: %{customdata:,}<extra></extra>',
    colorbar:{title:'Book Value ($)',thickness:14,len:0.8},
  }],{geo:{scope:'usa',projection:{type:'albers usa'},showlakes:true,lakecolor:'#f0f6ff',bgcolor:'transparent'},
    paper_bgcolor:'transparent',margin:{l:0,r:0,t:0,b:0}},CFG);

  // Rate histogram
  const hist = sched_b.rate_histogram || [];
  Plotly.react('chart-rate-hist',[{
    type:'bar',x:hist.map(r=>`${r.rate}%`),y:hist.map(r=>r.count),marker:{color:'#4472c4'},
    hovertemplate:'<b>%{x}</b><br>%{y:,} loans<extra></extra>',
  }],{...LAY,yaxis:{...LAY.yaxis,title:'Loan Count'},xaxis:{...LAY.xaxis,title:'Interest Rate'}},CFG);

  // All states table
  const sortedStates = byState.slice().sort((a,b)=>(b.bv||0)-(a.bv||0));
  document.getElementById('mortgage-tbody').innerHTML = sortedStates.map((r,i) => {
    const pct = sched_b.total_bv ? ((r.bv/sched_b.total_bv)*100).toFixed(2)+'%' : '—';
    return `<tr>
      <td class="rank">${i+1}</td>
      <td>${r.state}</td>
      <td class="num">${fmtN(r.count)}</td>
      <td class="num">${fmtAuto(r.bv)}</td>
      <td class="num">${r.avg_rate ? r.avg_rate.toFixed(3)+'%' : '—'}</td>
      <td class="num">${pct}</td>
    </tr>`;
  }).join('');

  // Set up full-data load bar
  document.getElementById('full-loans-count-info').textContent =
    `${fmtN(sched_b.count)} loans · ${fmtAuto(sched_b.total_bv)} total`;
  document.getElementById('full-loans-load-btn').disabled = false;
  document.getElementById('full-loans-load-btn').textContent = `↓ Load All ${fmtN(sched_b.count)} Loans`;

  // Check if already cached
  const url = `data/${currentCo}/${currentEntity}_${currentPeriod}_sched_b.csv`;
  if (csvCache[url]) {
    loadFullLoans(currentCo, currentEntity, currentPeriod);
  } else {
    document.getElementById('full-loans-search-bar').style.display = 'none';
    document.getElementById('full-loans-thead').innerHTML = '';
    document.getElementById('full-loans-tbody').innerHTML =
      '<tr><td colspan="6" style="text-align:center;color:#999;padding:20px">Click "Load All Loans" to fetch the full dataset</td></tr>';
    document.getElementById('full-loans-pagination').style.display = 'none';
  }
}

async function loadFullLoans(co, entity, period) {
  const url = `data/${co}/${entity}_${period}_sched_b.csv`;
  const btn = document.getElementById('full-loans-load-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Loading…'; }
  try {
    const { rows } = await fetchCSV(url);
    const totalBv = rows.reduce((s,r) => s + parseFloat(r.book_value||0), 0);
    const headers = [
      { key: 'loan_number',  label: 'Loan #' },
      { key: 'city',         label: 'City' },
      { key: 'state',        label: 'State' },
      { key: 'date_acquired',label: 'Date Acquired' },
      { key: 'interest_rate',label: 'Rate', num: true, fmt: v => v ? parseFloat(v).toFixed(3)+'%' : '—' },
      { key: 'book_value',   label: 'Book Value', num: true, fmt: v => fmtAuto(parseFloat(v)||0) },
    ];
    pgCreate('full-loans', headers, rows);
    document.getElementById('full-loans-search-bar').style.display = '';
    if (btn) { btn.textContent = `✓ ${fmtN(rows.length)} loans loaded`; }
  } catch (err) {
    document.getElementById('full-loans-tbody').innerHTML =
      `<tr><td colspan="6" style="text-align:center;color:#c00;padding:20px">Failed to load: ${err.message}</td></tr>`;
    if (btn) { btn.disabled = false; btn.textContent = 'Retry'; }
  }
}

// ============================================================
// ALTERNATIVES (Schedule BA)
// ============================================================

let _fullBAContext = null;

function triggerLoadFullBA() {
  if (_fullBAContext) {
    loadFullBA(_fullBAContext.co, _fullBAContext.entity, _fullBAContext.period);
  }
}

function renderAlternatives(sched_ba) {
  const sub = document.getElementById('alts-sub');
  if (sub) sub.textContent = 'Schedule BA — Other Long-Term Assets (annual filings only)';
  const kpis = document.getElementById('alts-kpis');

  if (!sched_ba) {
    kpis.innerHTML = `<div class="kpi-card" style="grid-column:span 3;text-align:center;color:#999">
      No Schedule BA data for this period. Select an annual (Q4) filing.</div>`;
    Plotly.purge('chart-ba-bar');
    document.getElementById('full-ba-count-info').textContent = '';
    document.getElementById('full-ba-load-btn').disabled = true;
    document.getElementById('full-ba-search-bar').style.display = 'none';
    document.getElementById('full-ba-thead').innerHTML = '';
    document.getElementById('full-ba-tbody').innerHTML =
      '<tr><td colspan="6" style="text-align:center;color:#999;padding:20px">No Schedule BA data for this period</td></tr>';
    document.getElementById('full-ba-pagination').style.display = 'none';
    _fullBAContext = null;
    return;
  }

  _fullBAContext = { co: currentCo, entity: currentEntity, period: currentPeriod };
  const top = sched_ba.top || [];
  const topIncome = top.reduce((s,r) => s+(r.income||0), 0);

  kpis.innerHTML = `
    <div class="kpi-card accent"><div class="kpi-label">Total Holdings</div>
      <div class="kpi-value">${fmtN(sched_ba.count)}</div><div class="kpi-sub">Individual positions on Schedule BA</div></div>
    <div class="kpi-card green"><div class="kpi-label">Total Book Value</div>
      <div class="kpi-value">${fmtAuto(sched_ba.total_bv)}</div><div class="kpi-sub">Ending carrying value</div></div>
    <div class="kpi-card orange"><div class="kpi-label">Top 100 Income</div>
      <div class="kpi-value">${fmtAuto(topIncome)}</div><div class="kpi-sub">Investment income from top 100 holdings</div></div>`;

  const top20rev = top.slice(0,20).slice().reverse();
  Plotly.react('chart-ba-bar',[{
    type:'bar',orientation:'h',
    x:top20rev.map(r=>r.bv),
    y:top20rev.map((r,i)=>`${top20rev.length-i}. ${trunc(r.name||'—',38)}`),
    marker:{color:'#107c41'},
    hovertemplate:'<b>%{y}</b><br>BV: %{x:$,.0f}<extra></extra>',
  }],{...LAY,margin:{l:280,r:20,t:20,b:50},height:520,
    xaxis:{...LAY.xaxis,...xTicksAuto(top20rev.map(r=>r.bv))}},CFG);

  // Set up full-data load bar
  document.getElementById('full-ba-count-info').textContent =
    `${fmtN(sched_ba.count)} holdings · ${fmtAuto(sched_ba.total_bv)} AUM`;
  document.getElementById('full-ba-load-btn').disabled = false;
  document.getElementById('full-ba-load-btn').textContent = `↓ Load All ${fmtN(sched_ba.count)} Holdings`;

  const url = `data/${currentCo}/${currentEntity}_${currentPeriod}_sched_ba.csv`;
  if (csvCache[url]) {
    loadFullBA(currentCo, currentEntity, currentPeriod);
  } else {
    document.getElementById('full-ba-search-bar').style.display = 'none';
    document.getElementById('full-ba-thead').innerHTML = '';
    document.getElementById('full-ba-tbody').innerHTML =
      '<tr><td colspan="6" style="text-align:center;color:#999;padding:20px">Click "Load All Holdings" to fetch the full dataset</td></tr>';
    document.getElementById('full-ba-pagination').style.display = 'none';
  }
}

async function loadFullBA(co, entity, period) {
  const url = `data/${co}/${entity}_${period}_sched_ba.csv`;
  const btn = document.getElementById('full-ba-load-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Loading…'; }
  try {
    const { rows } = await fetchCSV(url);
    const headers = [
      { key: 'name',               label: 'Name / Identifier' },
      { key: 'state',              label: 'State' },
      { key: 'date_acquired',      label: 'Date Acquired' },
      { key: 'book_value',         label: 'Book Value',    num: true, fmt: v => fmtAuto(parseFloat(v)||0) },
      { key: 'investment_income',  label: 'Inv. Income',   num: true,
        fmt: v => parseFloat(v) ? fmtAuto(parseFloat(v)) : '—' },
      { key: 'ownership_pct',      label: 'Ownership %',   num: true,
        fmt: (v, r) => {
          const bv = parseFloat(r.book_value||0), inc = parseFloat(r.investment_income||0);
          const yld = bv ? ((inc/bv)*100).toFixed(2)+'%' : (v ? v+'%' : '—');
          return yld;
        }},
    ];
    pgCreate('full-ba', headers, rows);
    document.getElementById('full-ba-search-bar').style.display = '';
    if (btn) { btn.textContent = `✓ ${fmtN(rows.length)} holdings loaded`; }
  } catch (err) {
    document.getElementById('full-ba-tbody').innerHTML =
      `<tr><td colspan="6" style="text-align:center;color:#c00;padding:20px">Failed to load: ${err.message}</td></tr>`;
    if (btn) { btn.disabled = false; btn.textContent = 'Retry'; }
  }
}

// ============================================================
// COMPARE
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
    total_invested:'Total Invested Assets', bonds:'Bond Portfolio',
    mortgages:'Mortgage Loans', alts:'Alternatives (BA)', annuity_ytd:'Annuity Premiums YTD',
  };
  const label = metricLabels[metric] || metric;
  document.getElementById('compare-chart-title').textContent = `${label} — All Companies`;
  document.getElementById('compare-bar-title').textContent   = `Latest Period — ${label} by Firm`;

  const coKeys  = Object.keys(cf);
  const palette = ['#4472c4','#ed7d31','#a9d18e','#c00000','#ffc000','#5b9bd5','#70ad47','#7030a0','#264478','#9e3ec8','#107c41'];
  const annualsByco = Object.fromEntries(coKeys.map(co=>[co, cf[co].timeseries.filter(r=>r.period.endsWith('Q4'))]));

  const lineTraces = coKeys.map((co,i) => {
    const d = cf[co]; const annuals = annualsByco[co];
    return {type:'scatter',mode:'lines+markers',name:d.ticker||co,
      x:annuals.map(r=>r.period),y:annuals.map(r=>r[metric]||null),
      line:{color:palette[i%palette.length],width:2},marker:{size:5},connectgaps:false,
      hovertemplate:`<b>${d.name}</b><br>%{x}<br>%{y:$,.0f}<extra></extra>`};
  });
  Plotly.react('chart-compare-lines',lineTraces,
    {...LAY,margin:{...LAY.margin,b:60},height:380,
      yaxis:{...LAY.yaxis,...yTicksAuto(lineTraces.flatMap(t=>t.y))},
      xaxis:{...LAY.xaxis,categoryorder:'category ascending'},
      legend:{orientation:'h',y:-0.18,font:{size:11}}},CFG);

  const barItems = coKeys.map(co => {
    const d = cf[co];
    const latest = d.timeseries.slice().sort((a,b)=>b.period.localeCompare(a.period))[0]||{};
    return {co,name:d.name,ticker:d.ticker||co,period:latest.period||'—',val:latest[metric]||0,latest};
  }).sort((a,b)=>b.val-a.val);
  Plotly.react('chart-compare-bar',[{
    type:'bar',orientation:'h',
    x:barItems.map(r=>r.val).reverse(),y:barItems.map(r=>r.ticker).reverse(),
    marker:{color:barItems.map((_,i)=>palette[(barItems.length-1-i)%palette.length]).reverse()},
    text:barItems.map(r=>r.period).reverse(),textposition:'outside',
    hovertemplate:'<b>%{y}</b><br>%{x:$,.0f}<extra></extra>',
  }],{...LAY,margin:{...LAY.margin,l:60,r:80},height:320,
    xaxis:{...LAY.xaxis,...xTicksAuto(barItems.map(r=>r.val))}},CFG);

  const annualPeriods = [...new Set(coKeys.flatMap(co=>annualsByco[co].map(r=>r.period)))].sort();
  const recentPeriods = annualPeriods.slice(-5);
  const annuityTraces = coKeys.map((co,i) => {
    const d = cf[co];
    const byPeriod = Object.fromEntries(d.timeseries.map(r=>[r.period,r.annuity_ytd||0]));
    return {type:'bar',name:d.ticker||co,x:recentPeriods,y:recentPeriods.map(p=>byPeriod[p]||0),
      marker:{color:palette[i%palette.length]},hovertemplate:`<b>${d.name}</b><br>%{x}<br>%{y:$,.0f}<extra></extra>`};
  });
  Plotly.react('chart-compare-annuity',annuityTraces,
    {...LAY,barmode:'group',height:340,
      yaxis:{...LAY.yaxis,...yTicksAuto(annuityTraces.flatMap(t=>t.y))},
      legend:{orientation:'h',y:-0.2,font:{size:11}}},CFG);

  document.getElementById('compare-tbody').innerHTML = barItems.map(r => {
    const d = cf[r.co]; const l = r.latest;
    return `<tr>
      <td>${d.name}</td><td><strong>${d.ticker||r.co}</strong></td><td>${l.period||'—'}</td>
      <td class="num">${l.total_invested?fmtAuto(l.total_invested):'—'}</td>
      <td class="num">${l.bonds?fmtAuto(l.bonds):'—'}</td>
      <td class="num">${l.mortgages?fmtAuto(l.mortgages):'—'}</td>
      <td class="num">${l.annuity_ytd?fmtAuto(l.annuity_ytd):'—'}</td>
    </tr>`;
  }).join('');
}

// ============================================================
// DATA ROOM
// ============================================================
let drCatalog = null;
let drCurrentSched = 't';
let drTableRows = [];
let drTableHeaders = [];

async function renderDataRoom() {
  if (!drCatalog) {
    drCatalog = await fetchJSON('data/catalog.json');
    drInitSelectors();
    drInitTabs();
    document.getElementById('dr-search')?.addEventListener('input', e => {
      pgSearch('dr', e.target.value);
    });
  }
  await drLoadView();
}

function drInitSelectors() {
  const coSel = document.getElementById('dr-company');
  const cos = [...new Set(drCatalog.map(r => r.company))].sort();
  populateSelect(coSel, cos, co => (COMPANIES[co]?.name||co)+' ('+(COMPANIES[co]?.ticker||'')+')');
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
  const entities = [...new Set(drCatalog.filter(r=>r.company===co).map(r=>r.entity))].sort();
  populateSelect(document.getElementById('dr-entity'), entities);
  drOnEntityChange();
}
function drOnEntityChange() {
  const co = document.getElementById('dr-company')?.value;
  const entity = document.getElementById('dr-entity')?.value;
  const periods = drCatalog.filter(r=>r.company===co&&r.entity===entity).map(r=>r.period).sort().reverse();
  populateSelect(document.getElementById('dr-period'), periods);
  drLoadView();
}

const drPeriodCache = {};
const drOverviewCache = {};
async function drGetOverview(co) {
  if (!drOverviewCache[co]) drOverviewCache[co] = await fetchJSON(`data/${co}/overview.json`);
  return drOverviewCache[co];
}

async function drLoadView() {
  const co     = document.getElementById('dr-company')?.value;
  const entity = document.getElementById('dr-entity')?.value;
  const period = document.getElementById('dr-period')?.value;
  if (!co || !entity || !period) return;

  const allLinks = {
    t:       `data/${co}/sched_t_all.csv`,
    dq:      `data/${co}/sched_dq_all.csv`,
    b:       `data/${co}/sched_b_states.csv`,
    b_loans: `data/${co}/${entity}_${period}_sched_b.csv`,
    ba:      `data/${co}/${entity}_${period}_sched_ba.csv`,
    kpi:     `data/download_all_timeseries.csv`,
  };
  const allLinkEl = document.getElementById('dr-all-link');
  if (allLinkEl) {
    allLinkEl.href     = allLinks[drCurrentSched] || '#';
    allLinkEl.download = (allLinks[drCurrentSched]||'').split('/').pop();
  }

  if (drCurrentSched === 'kpi') {
    const ov = await drGetOverview(co);
    drRenderKpiTable((ov?.timeseries||[]).filter(r=>r.entity===entity));
    return;
  }

  // Full CSV tabs — load directly
  if (drCurrentSched === 'b_loans' || drCurrentSched === 'ba') {
    const url = allLinks[drCurrentSched];
    await drLoadFullCSV(url, drCurrentSched);
    return;
  }

  // Period JSON tabs
  const key = `${entity}_${period}`;
  if (!drPeriodCache[key]) {
    try { drPeriodCache[key] = await fetchJSON(`data/${co}/${entity}_${period}.json`); }
    catch { drPeriodCache[key] = {}; }
  }
  const pd = drPeriodCache[key];
  ({ t:()=>drRenderSchedT(pd.sched_t), dq:()=>drRenderSchedDQ(pd.sched_d_quality), b:()=>drRenderSchedB(pd.sched_b) }[drCurrentSched]||(() => {}))();
}

async function drLoadFullCSV(url, sched) {
  document.getElementById('dr-row-count').textContent = 'Loading…';
  document.getElementById('dr-tbody').innerHTML =
    `<tr><td colspan="6" style="text-align:center;color:#999;padding:20px">Loading full dataset…</td></tr>`;
  document.getElementById('dr-pagination').style.display = 'none';
  try {
    const { rows } = await fetchCSV(url);
    const headers = sched === 'b_loans' ? [
      { key:'loan_number',  label:'Loan #' },
      { key:'city',         label:'City' },
      { key:'state',        label:'State' },
      { key:'date_acquired',label:'Date Acquired' },
      { key:'interest_rate',label:'Rate',       num:true, fmt:v=>v?parseFloat(v).toFixed(3)+'%':'—' },
      { key:'book_value',   label:'Book Value', num:true, fmt:v=>fmtAuto(parseFloat(v)||0) },
    ] : [
      { key:'name',              label:'Name / Identifier' },
      { key:'state',             label:'State' },
      { key:'date_acquired',     label:'Date Acquired' },
      { key:'book_value',        label:'Book Value',   num:true, fmt:v=>fmtAuto(parseFloat(v)||0) },
      { key:'investment_income', label:'Inv. Income',  num:true, fmt:v=>parseFloat(v)?fmtAuto(parseFloat(v)):'—' },
      { key:'ownership_pct',     label:'Ownership %',  num:true, fmt:v=>v?parseFloat(v).toFixed(2)+'%':'—' },
    ];

    // Wire search to this view via dr-search
    pgCreate('dr', headers, rows);
    document.getElementById('dr-row-count').textContent = `${fmtN(rows.length)} rows`;
  } catch(err) {
    document.getElementById('dr-row-count').textContent = '';
    document.getElementById('dr-tbody').innerHTML =
      `<tr><td colspan="6" style="text-align:center;color:#c00;padding:20px">Failed to load: ${err.message}</td></tr>`;
  }
}

// Override pgRender for 'dr' to use dr-thead/dr-tbody/dr-pagination
const _pgRender = pgRender;
function pgRenderDR(viewId) {
  if (viewId !== 'dr') { _pgRender(viewId); return; }
  const v = pgViews[viewId];
  if (!v) return;
  const { headerDefs, filteredRows, page } = v;
  const total = filteredRows.length;
  const maxPage = Math.max(0, Math.ceil(total/PAGE_SIZE)-1);
  const start = page * PAGE_SIZE;
  const end = Math.min(start+PAGE_SIZE, total);

  const thead = document.getElementById('dr-thead');
  const tbody = document.getElementById('dr-tbody');
  if (thead) thead.innerHTML = '<tr>'+headerDefs.map(h=>`<th${h.num?' class="num"':''}>${h.label}</th>`).join('')+'</tr>';
  if (tbody) {
    if (!total) {
      tbody.innerHTML = `<tr><td colspan="${headerDefs.length}" style="text-align:center;color:#999;padding:20px">No rows match filter</td></tr>`;
    } else {
      tbody.innerHTML = filteredRows.slice(start,end).map(r=>
        '<tr>'+headerDefs.map(h=>{
          const raw = r[h.key]??'';
          const val = h.num?(parseFloat(raw)||0):raw;
          const display = h.fmt?h.fmt(val,r):(h.num?fmtAuto(val):raw);
          return `<td${h.num?' class="num"':''}>${display}</td>`;
        }).join('')+'</tr>'
      ).join('');
    }
  }

  const pgBar = document.getElementById('dr-pagination');
  if (!pgBar) return;
  if (total <= PAGE_SIZE) { pgBar.style.display='none'; return; }
  pgBar.style.display = 'flex';
  pgBar.innerHTML = `
    <button class="pg-btn" onclick="pgGoPage('dr',0)" ${page===0?'disabled':''}>«</button>
    <button class="pg-btn" onclick="pgGoPage('dr',${page-1})" ${page===0?'disabled':''}>‹</button>
    <span class="pg-info">${fmtN(start+1)}–${fmtN(end)} of ${fmtN(total)} rows &nbsp;·&nbsp; page ${page+1} of ${maxPage+1}</span>
    <button class="pg-btn" onclick="pgGoPage('dr',${page+1})" ${page>=maxPage?'disabled':''}>›</button>
    <button class="pg-btn" onclick="pgGoPage('dr',${maxPage})" ${page>=maxPage?'disabled':''}>»</button>`;
  document.getElementById('dr-row-count').textContent = `${fmtN(total)} rows`;
}

// Patch pgCreate/pgSearch/pgGoPage to route dr through pgRenderDR
const _pgCreate   = pgCreate;
const _pgSearch   = pgSearch;
const _pgGoPage   = pgGoPage;

function pgCreate(viewId, headerDefs, allRows) {
  pgViews[viewId] = { headerDefs, allRows, filteredRows: allRows, page: 0 };
  pgRenderDR(viewId);
}
function pgSearch(viewId, query) {
  const v = pgViews[viewId]; if (!v) return;
  const q = query.toLowerCase();
  v.filteredRows = q ? v.allRows.filter(r=>v.headerDefs.some(h=>String(r[h.key]??'').toLowerCase().includes(q))) : v.allRows;
  v.page = 0;
  pgRenderDR(viewId);
}
function pgGoPage(viewId, page) {
  const v = pgViews[viewId]; if (!v) return;
  const maxPage = Math.max(0, Math.ceil(v.filteredRows.length/PAGE_SIZE)-1);
  v.page = Math.max(0, Math.min(page, maxPage));
  pgRenderDR(viewId);
}

function drSetTable(headers, rows, emptyMsg) {
  drTableHeaders = headers;
  drTableRows = rows;
  document.getElementById('dr-row-count').textContent = rows.length ? `${rows.length.toLocaleString()} rows` : '';
  const thead = document.getElementById('dr-thead');
  const tbody = document.getElementById('dr-tbody');
  if (!thead || !tbody) return;
  thead.innerHTML = '<tr>'+headers.map(h=>`<th>${h.label}</th>`).join('')+'</tr>';
  if (!rows.length) {
    tbody.innerHTML=`<tr><td colspan="${headers.length}" style="text-align:center;color:#999;padding:24px">${emptyMsg}</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(r =>
    '<tr>'+headers.map(h=>{
      const v = r[h.key];
      const cls = h.num?' class="num"':'';
      return `<td${cls}>${h.fmt?h.fmt(v):(v??'')}</td>`;
    }).join('')+'</tr>'
  ).join('');
  document.getElementById('dr-pagination').style.display = 'none';
}

function drRenderSchedT(data) {
  if (!data?.length) { drSetTable([],[],'No Schedule T data for this period.'); return; }
  const grandTotal = data.reduce((s,r)=>s+(r.total||0),0);
  const sorted = data.slice().sort((a,b)=>(b.total||0)-(a.total||0))
    .map(r=>({...r,_pct:grandTotal?((r.total/grandTotal)*100).toFixed(2)+'%':'—'}));
  drSetTable([
    {key:'state',   label:'Code'},
    {key:'name',    label:'State'},
    {key:'life',    label:'Life Premiums', num:true, fmt:v=>fmtAuto(v||0)},
    {key:'annuity', label:'Annuity',       num:true, fmt:v=>fmtAuto(v||0)},
    {key:'total',   label:'Total',         num:true, fmt:v=>fmtAuto(v||0)},
    {key:'_pct',    label:'% of Total',    num:true},
  ], sorted, '');
}
function drRenderSchedDQ(data) {
  if (!data?.length) { drSetTable([],[],'No bond quality data for this period (annual filings only).'); return; }
  const enriched = data.map(r => {
    const change = (r.current||0)-(r.prior||0);
    return {...r,
      _change:    r.prior?(change>=0?'+':'')+fmtAuto(change):'—',
      _changePct: r.prior?(change>=0?'+':'')+((change/r.prior)*100).toFixed(1)+'%':'—'};
  });
  drSetTable([
    {key:'category',   label:'Category'},
    {key:'naic',       label:'NAIC Rating'},
    {key:'current',    label:'Current Year BV', num:true, fmt:v=>fmtAuto(v||0)},
    {key:'prior',      label:'Prior Year BV',   num:true, fmt:v=>fmtAuto(v||0)},
    {key:'_change',    label:'Change',          num:true},
    {key:'_changePct', label:'Change %',        num:true},
  ], enriched, '');
}
function drRenderSchedB(data) {
  if (!data) { drSetTable([],[],'No Schedule B data for this period (annual filings only).'); return; }
  const sorted = (data.by_state||[]).slice().sort((a,b)=>(b.bv||0)-(a.bv||0))
    .map(r=>({...r,_pct:data.total_bv?((r.bv/data.total_bv)*100).toFixed(2)+'%':'—'}));
  drSetTable([
    {key:'state',    label:'State'},
    {key:'count',    label:'Loan Count', num:true, fmt:v=>fmtN(v||0)},
    {key:'bv',       label:'Book Value', num:true, fmt:v=>fmtAuto(v||0)},
    {key:'avg_rate', label:'Avg Rate',   num:true, fmt:v=>v?v.toFixed(3)+'%':'—'},
    {key:'_pct',     label:'% of Total', num:true},
  ], sorted, 'No mortgage data.');
  document.getElementById('dr-row-count').textContent +=
    ` · ${fmtN(data.count)} individual loans · ${fmtAuto(data.total_bv)} total`;
}
function drRenderKpiTable(ts) {
  drSetTable([
    {key:'period',         label:'Period'},
    {key:'total_invested', label:'Total Invested', num:true, fmt:v=>fmtAuto(v||0)},
    {key:'bonds',          label:'Bonds',          num:true, fmt:v=>fmtAuto(v||0)},
    {key:'mortgages',      label:'Mortgages',      num:true, fmt:v=>fmtAuto(v||0)},
    {key:'alts',           label:'Alts (BA)',       num:true, fmt:v=>fmtAuto(v||0)},
    {key:'cash',           label:'Cash',            num:true, fmt:v=>fmtAuto(v||0)},
    {key:'annuity_ytd',    label:'Annuity YTD',     num:true, fmt:v=>fmtAuto(v||0)},
  ], ts.slice().sort((a,b)=>a.period.localeCompare(b.period)), 'No timeseries data for this entity.');
}

function drExportCSV() {
  if (!drTableRows.length && !pgViews['dr']?.filteredRows?.length) return;
  const rows = pgViews['dr']?.filteredRows ?? drTableRows;
  const hdrs = pgViews['dr']?.headerDefs   ?? drTableHeaders;
  const keys = hdrs.map(h=>h.key);
  const lines = [
    keys.join(','),
    ...rows.map(r=>keys.map(k=>{
      const s = String(r[k]??'');
      return s.includes(',')||s.includes('"') ? `"${s.replace(/"/g,'""')}"` : s;
    }).join(','))
  ];
  const blob = new Blob([lines.join('\n')],{type:'text/csv'});
  const co=document.getElementById('dr-company')?.value||'data';
  const entity=document.getElementById('dr-entity')?.value||'';
  const period=document.getElementById('dr-period')?.value||'';
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=`${co}_${entity}_${period}_sched_${drCurrentSched}.csv`;
  a.click(); URL.revokeObjectURL(a.href);
}
