// =====================================================================
//  Front-end: draws the maze and replays the steps recorded by the Python backend.
//  The algorithms themselves live in algorithms.py / local_search.py.
// =====================================================================
const CELL = 36;
const COLORS = { '.': '#cbd5e1', 'g': '#6fbf73', 'm': '#9a6b43', '#': '#0b1220' };
const BRUSH = { wall: '#', road: '.', grass: 'g', mud: 'm' };
const DELAYS = [900, 600, 380, 240, 150, 90, 50, 25, 10, 2];
const $ = id => document.getElementById(id);
const cv = $('cv'), ctx = cv.getContext('2d');

let META = null, grid = [], START = 0, GOAL = 0, ROWS = 0, COLS = 0, N = 0;
let routes = [], OPT = null;
let run = null, runPromise = null;            // result of /api/run for the current algorithm + maze
let view = newView();                         // what has been replayed so far
let playing = false, timer = null, runKey = null;
const results = {};

const rowOf = i => Math.floor(i / COLS);
const colOf = i => i % COLS;
const cost = i => META.terrain[grid[i]].cost;           // null for walls
function newView() {
  return { idx: 0, visited: new Set(), frontier: new Set(), current: -1, g: new Map(), trail: [], pher: null, expanded: 0, maxFrontier: 0 };
}
const finished = () => run && view.idx >= run.steps.length;

// ---------- maze <-> server ----------
function loadMap(rows) {
  ROWS = rows.length; COLS = rows[0].length; N = ROWS * COLS; grid = [];
  rows.forEach((row, r) => [...row].forEach((ch, c) => {
    const i = r * COLS + c;
    if (ch === 'S') { START = i; ch = '.'; }
    if (ch === 'E') { GOAL = i; ch = '.'; }
    grid.push(ch);
  }));
  cv.width = COLS * CELL; cv.height = ROWS * CELL;
}
function mapRows() {
  const rows = [];
  for (let r = 0; r < ROWS; r++) {
    let s = '';
    for (let c = 0; c < COLS; c++) { const i = r * COLS + c; s += i === START ? 'S' : i === GOAL ? 'E' : grid[i]; }
    rows.push(s);
  }
  return rows;
}
async function post(url, body) {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

// ---------- reference routes ----------
function expandWaypoints(wps) {
  const cells = [wps[0][0] * COLS + wps[0][1]];
  for (let k = 1; k < wps.length; k++) {
    let [r, c] = wps[k - 1]; const [tr, tc] = wps[k];
    while (r !== tr || c !== tc) { r += Math.sign(tr - r); c += Math.sign(tc - c); cells.push(r * COLS + c); }
  }
  return cells;
}
function computeRoutes() {
  routes = META.routes.map(d => {
    const cells = expandWaypoints(d.wps);
    const valid = cells.every(i => grid[i] !== '#') && cells[0] === START && cells[cells.length - 1] === GOAL;
    return { ...d, cells, valid, steps: cells.length - 1, cost: valid ? cells.slice(1).reduce((s, n) => s + cost(n), 0) : null };
  });
}

// ---------- drawing ----------
function draw() {
  ctx.clearRect(0, 0, cv.width, cv.height);
  for (let i = 0; i < N; i++) {
    const x = colOf(i) * CELL, y = rowOf(i) * CELL;
    ctx.fillStyle = COLORS[grid[i]]; ctx.fillRect(x, y, CELL, CELL);
    if (grid[i] !== '#') { ctx.strokeStyle = 'rgba(0,0,0,.14)'; ctx.strokeRect(x + .5, y + .5, CELL - 1, CELL - 1); }
  }
  if (view.pher) {
    let mx = 1; for (let i = 0; i < N; i++) if (grid[i] !== '#' && view.pher[i] > mx) mx = view.pher[i];
    for (let i = 0; i < N; i++) if (grid[i] !== '#') {
      const a = Math.min(.85, (view.pher[i] - 1) / (mx - 1 + 1e-9));
      if (a > 0.02) { ctx.fillStyle = `rgba(168,85,247,${a})`; ctx.fillRect(colOf(i) * CELL, rowOf(i) * CELL, CELL, CELL); }
    }
  }
  const fill = (set, color) => { ctx.fillStyle = color; for (const i of set) ctx.fillRect(colOf(i) * CELL, rowOf(i) * CELL, CELL, CELL); };
  fill(view.visited, 'rgba(56,189,248,.50)');
  fill(view.frontier, 'rgba(249,115,22,.78)');
  if (view.current >= 0) { ctx.fillStyle = 'rgba(239,68,68,.92)'; ctx.fillRect(colOf(view.current) * CELL, rowOf(view.current) * CELL, CELL, CELL); }

  if ($('showCosts').checked) {
    ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#04121f';
    for (const [i, g] of view.g) ctx.fillText(g, colOf(i) * CELL + CELL / 2, rowOf(i) * CELL + CELL / 2);
  }
  if ($('showRoutes').checked) for (const r of routes) if (r.valid) line(r.cells, r.color, 3, [7, 6]);
  const done = finished() && run.found;
  if (view.trail.length > 1 && !done) line(view.trail, '#c084fc', 3, []);
  if (done && run.path.length > 1) { line(run.path, '#0b1220', 10, []); line(run.path, '#facc15', 6, []); }

  badge(START, '#22c55e', 'S'); badge(GOAL, '#ef4444', 'E');
}
function line(cells, color, w, dash) {
  ctx.save(); ctx.beginPath();
  cells.forEach((i, k) => { const x = colOf(i) * CELL + CELL / 2, y = rowOf(i) * CELL + CELL / 2; k ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.strokeStyle = color; ctx.lineWidth = w; ctx.setLineDash(dash); ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.stroke(); ctx.restore();
}
function badge(i, color, text) {
  const x = colOf(i) * CELL + CELL / 2, y = rowOf(i) * CELL + CELL / 2;
  ctx.beginPath(); ctx.arc(x, y, CELL * .38, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
  ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke();
  ctx.fillStyle = '#fff'; ctx.font = 'bold 15px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, x, y + 1);
}

// ---------- legend, info, stats ----------
function renderLegend() {
  const sw = (c, t) => `<span><i class="sw" style="background:${c}"></i>${t}</span>`;
  const t = META.terrain;
  let html = sw(COLORS['.'], `Road (${t['.'].cost})`) + sw(COLORS.g, `Grass (${t.g.cost})`) + sw(COLORS.m, `Mud (${t.m.cost})`) +
             sw(COLORS['#'], 'Wall') + sw('#22c55e', 'Start') + sw('#ef4444', 'Exit') +
             sw('rgba(249,115,22,.9)', 'Frontier') + sw('rgba(56,189,248,.7)', 'Explored') + sw('#facc15', 'Final path');
  routes.filter(r => r.valid).forEach(r => {
    html += `<span><i class="ln" style="border-color:${r.color}"></i>Route ${r.name} (${r.label}): ${r.steps} steps, cost ${r.cost}</span>`;
  });
  $('legend').innerHTML = html;
}
function algoMeta() { return META.algorithms.find(a => a.key === $('algo').value); }
function renderInfo() {
  const a = algoMeta(), i = a.info;
  $('info').innerHTML = `<h2>${a.name}</h2><p class="idea">${i.idea}</p><dl>
    <dt>Data structure</dt><dd>${i.structure}</dd>
    <dt>Time complexity</dt><dd>${i.time}</dd>
    <dt>Space complexity</dt><dd>${i.space}</dd>
    <dt>Complete?</dt><dd>${i.complete}</dd>
    <dt>Optimal?</dt><dd>${i.optimal}</dd></dl>
    <div class="note">${i.note}</div>`;
  $('limitWrap').hidden = a.key !== 'dls';
}
function renderStats() {
  const done = finished();
  $('sStatus').textContent = !run ? 'ready' : done ? run.status : 'running';
  $('sExp').textContent = view.expanded;
  $('sFront').textContent = view.frontier.size;
  $('sMax').textContent = view.maxFrontier;
  $('sSteps').textContent = done && run.found ? run.pathSteps : '-';
  $('sCost').textContent = done && run.found ? run.pathCost : '-';
  $('sBest').textContent = OPT ? `${OPT.cost} / ${OPT.steps}` : '-';
}
function renderResults() {
  const mark = ok => ok ? '<span class="ok">yes</span>' : '<span class="bad">no</span>';
  const rows = META.algorithms.filter(a => results[a.key]).map(a => {
    const r = results[a.key];
    return `<tr><td>${a.name}</td><td>${r.expanded}</td><td>${r.found ? r.pathSteps : '-'}</td><td>${r.found ? r.pathCost : '-'}</td>
            <td>${r.found && OPT ? mark(r.pathSteps === OPT.steps) : '-'}</td><td>${r.found && OPT ? mark(r.pathCost === OPT.cost) : '-'}</td></tr>`;
  });
  $('resBody').innerHTML = rows.length ? rows.join('') : '<tr><td colspan="6" class="hint">Run an algorithm to compare it here.</td></tr>';
}
function addLog(msg, cls) {
  const d = document.createElement('div');
  d.innerHTML = `<span class="n">${cls === 'end' ? '*' : view.idx}</span>` + msg.replace(/</g, '&lt;');
  if (cls) d.className = cls;
  const box = $('log'); box.appendChild(d);
  while (box.childElementCount > 500) box.removeChild(box.firstChild);
  box.scrollTop = box.scrollHeight;
}

// ---------- replaying a run ----------
function resetSearch() {
  stopPlay(); run = null; runPromise = null; view = newView();
  $('log').innerHTML = ''; $('result').textContent = '';
  draw(); renderStats();
}
function ensureRun() {                         // ask the Python backend to run the algorithm (once)
  if (run) return Promise.resolve();
  if (!runPromise) {
    runKey = $('algo').value;
    runPromise = post('/api/run', { algorithm: runKey, map: mapRows(), limit: parseInt($('limit').value, 10) || 20 })
      .then(data => { run = data; OPT = data.best; })
      .catch(err => { runPromise = null; $('result').innerHTML = `<span class="bad">Server error: ${err.message}</span>`; throw err; });
  }
  return runPromise;
}
function applyStep(s) {
  view.idx++;
  if (s.current !== null && s.current !== undefined) view.current = s.current;
  (s.visit || []).forEach(i => view.visited.add(i));
  view.frontier = new Set(s.frontier);
  (s.g || []).forEach(([i, v]) => view.g.set(i, v));
  if (s.trail) view.trail = s.trail;
  if (s.pher) view.pher = s.pher;
  view.expanded = s.expanded;
  view.maxFrontier = Math.max(view.maxFrontier, view.frontier.size);
  addLog(s.msg);
}
function endRun() {
  stopPlay();
  results[runKey] = { expanded: run.expanded, found: run.found, pathSteps: run.pathSteps, pathCost: run.pathCost };
  let msg;
  if (run.found) {
    const extra = run.pathCost - OPT.cost;
    msg = `<b>Route found:</b> ${run.pathSteps} steps, cost ${run.pathCost}. ` +
      (run.pathCost === OPT.cost ? '<span class="ok">This is the cheapest possible route.</span>'
        : `<span class="bad">Not the cheapest - ${extra} more than the best cost ${OPT.cost}.</span>`) +
      (run.pathSteps === OPT.steps ? ' <span class="ok">It also has the fewest steps.</span>' : ` Fewest possible steps: ${OPT.steps}.`);
  } else {
    msg = `<b>No route found</b> (${run.status}).`;
  }
  $('result').innerHTML = msg;
  addLog(run.found ? `Finished: ${run.expanded} nodes expanded, ${run.pathSteps} steps, cost ${run.pathCost}.` : `Finished without a route (${run.status}).`, 'end');
  renderResults();
}
async function stepOnce() {                    // returns true while there are more steps
  try { await ensureRun(); } catch (e) { return false; }
  if (view.idx >= run.steps.length) return false;
  applyStep(run.steps[view.idx]);
  if (view.idx >= run.steps.length) endRun();
  draw(); renderStats();
  return view.idx < run.steps.length;
}
async function tick() {
  if (!playing) return;
  const speed = +$('speed').value, burst = speed >= 9 ? 4 : 1;
  let more = true;
  for (let k = 0; k < burst && more && playing; k++) more = await stepOnce();
  if (more && playing) timer = setTimeout(tick, DELAYS[speed - 1]); else stopPlay();
}
function startPlay() { if (finished()) resetSearch(); playing = true; $('play').innerHTML = '&#9208; Pause'; tick(); }
function stopPlay() { playing = false; clearTimeout(timer); $('play').innerHTML = '&#9654; Play'; }

// ---------- maze editing ----------
async function mazeChanged() {
  resetSearch(); computeRoutes(); renderLegend();
  for (const k in results) delete results[k];
  renderResults();
  try { OPT = (await post('/api/best', { map: mapRows() })).best; } catch (e) { OPT = null; }
  renderStats();
}
let painting = false;
function cellAt(e) {
  const rc = cv.getBoundingClientRect();
  const c = Math.floor((e.clientX - rc.left) * cv.width / rc.width / CELL);
  const r = Math.floor((e.clientY - rc.top) * cv.height / rc.height / CELL);
  return (r < 0 || c < 0 || r >= ROWS || c >= COLS) ? -1 : r * COLS + c;
}
function paint(e) {
  const i = cellAt(e); if (i < 0 || i === START || i === GOAL) return;
  const ch = BRUSH[$('brush').value]; if (grid[i] === ch) return;
  grid[i] = ch; mazeChanged();
}
cv.addEventListener('mousedown', e => { painting = true; paint(e); });
cv.addEventListener('mousemove', e => { if (painting) paint(e); });
window.addEventListener('mouseup', () => painting = false);

// ---------- wiring ----------
function buildDropdown() {
  const sel = $('algo'), groups = {};
  META.algorithms.forEach(a => {
    if (!groups[a.group]) { groups[a.group] = document.createElement('optgroup'); groups[a.group].label = a.group; sel.appendChild(groups[a.group]); }
    const o = document.createElement('option'); o.value = a.key; o.textContent = a.name; groups[a.group].appendChild(o);
  });
}
$('algo').addEventListener('change', () => { resetSearch(); renderInfo(); });
$('play').addEventListener('click', () => playing ? stopPlay() : startPlay());
$('step').addEventListener('click', async () => { stopPlay(); if (finished()) resetSearch(); await stepOnce(); });
$('finish').addEventListener('click', async () => {
  stopPlay(); if (finished()) resetSearch();
  try { await ensureRun(); } catch (e) { return; }
  while (view.idx < run.steps.length) { applyStep(run.steps[view.idx]); }
  endRun(); draw(); renderStats();
});
$('reset').addEventListener('click', resetSearch);
$('resetMaze').addEventListener('click', () => { loadMap(META.map); mazeChanged(); });
$('showCosts').addEventListener('change', draw);
$('showRoutes').addEventListener('change', draw);
$('limit').addEventListener('change', resetSearch);

fetch('/api/meta').then(r => r.json()).then(meta => {
  META = meta; OPT = meta.best;
  loadMap(META.map); buildDropdown(); computeRoutes(); renderLegend(); renderInfo(); renderStats(); draw();
}).catch(err => { $('result').innerHTML = `<span class="bad">Cannot reach the server: ${err.message}</span>`; });
