/* v2.0: nota de cover call, Mi ETF, ¿Qué hubiera pasado si…? y Apalancados + Cover Call */
const ccCallout = (extra = '') => `<div class="callout"><div class="co-ic">◎</div><div><b>Tus acciones nunca más permanecerán inactivas esperando que se revaloricen.</b>
  <span>En Optionsbb te damos las estrategias adecuadas para generar ingresos pasivos: el cover call es una estrategia silenciosa que va generando ingresos en el tiempo.</span>
  <small>Recuerda: para vender un call necesitas 100 acciones por cada contrato.</small>${extra}</div></div>`;
const signedMoney = n => (n == null ? '—' : (n > 0 ? '+' : '') + fmtMoney(n));

/* ------------------------------ resultado de un cover call de recubrimiento (¿Qué pasó si…? y Apalancados) ------------------------------ */
function wiResult(r, title, sym) {
  const lbl = i => 'M' + i;
  const series = [
    { name: 'Solo las acciones', color: C.cyan, dash: true, pts: [{ x: 'M0', y: 0 }].concat(r.cycles.map(c => ({ x: lbl(c.i), y: c.cum_stock }))) },
    { name: 'Acciones + cover call', color: C.green, pts: [{ x: 'M0', y: 0 }].concat(r.cycles.map(c => ({ x: lbl(c.i), y: c.cum_total }))) },
  ];
  const lossMsg = r.stock_pnl < 0
    ? (r.absorbed_pct != null ? `El cover call habría amortizado <b>${r.absorbed_pct.toFixed(0)}%</b> de la pérdida de las acciones (${signedMoney(r.overlay_pnl)} cobrados contra ${signedMoney(r.stock_pnl)} de caída).` : 'En este caso el cover call no alcanzó a compensar la caída.')
    : `La acción ${r.stock_pnl === 0 ? 'quedó igual' : 'subió'}; el cover call ${r.overlay_pnl >= 0 ? 'sumó' : 'restó'} ${signedMoney(r.overlay_pnl)}: cobras primas, pero limita las subidas fuertes.`;
  return `<section class="panel green"><h2>${esc(title)}</h2>
  <div class="kpis"><div><span>Solo las acciones</span><b class="${cls(r.stock_pnl)}">${signedMoney(r.stock_pnl)}</b><small class="sub">${fmtPct(r.stock_pct)}</small></div>
    <div><span>Primas cobradas (estimadas)</span><b class="up">${fmtMoney(r.premiums)}</b></div>
    <div><span>Resultado del cover call</span><b class="${cls(r.overlay_pnl)}">${signedMoney(r.overlay_pnl)}</b><small class="sub">${fmtPct(r.overlay_pct)}</small></div>
    <div><span>Acciones + cover call</span><b class="${cls(r.total_pnl)}">${signedMoney(r.total_pnl)}</b><small class="sub">${fmtPct(r.total_pct)}</small></div>
    <div><span>Calls ejercidos</span><b>${r.assigned} de ${r.n}</b></div><div><span>Contratos (100 acc.)</span><b>${r.lots}</b></div></div>
  <div class="insight">${lossMsg}</div>
  ${r.lots < 1 ? '<div class="cc-warn">⚠ Con menos de 100 acciones no se puede vender un call: aquí el cover call no suma nada.</div>' : ''}
  <div class="cc-chart">${ccLines(series)}<div class="legend"><span><i class="dot" style="background:${C.cyan}"></i>Solo las acciones (acumulado)</span><span><i class="dot" style="background:${C.green}"></i>Acciones + cover call (acumulado)</span></div></div>
  <div class="tbl-scroll" style="max-height:none;overflow-x:auto"><table class="t"><thead><tr><th>Mes</th><th class="r">Precio inicio</th><th class="r">Strike vendido</th><th class="r">Prima</th><th class="r">Precio al vencer</th><th>Resultado</th><th class="r">Call (mes)</th><th class="r">Acumulado acciones</th><th class="r">Acumulado total</th></tr></thead>
  <tbody>${r.cycles.map(c => `<tr><td>${c.i}</td><td class="r">${fmtNum(c.start)}</td><td class="r">${fmtNum(c.strike)}</td><td class="r">${fmtNum(c.premium)} <small class="muted">${fmtMoney(c.premium_total)}</small></td><td class="r">${fmtNum(c.end)}</td><td>${c.assigned ? '<span class="chip neutral">EJERCIDO</span>' : '<span class="chip neutral st-flat">PRIMA ✓</span>'}</td><td class="r ${cls(c.overlay)}">${signedMoney(c.overlay)}</td><td class="r ${cls(c.cum_stock)}">${signedMoney(c.cum_stock)}</td><td class="r ${cls(c.cum_total)}"><b>${signedMoney(c.cum_total)}</b></td></tr>`).join('')}</tbody></table></div>
  <p class="note">Primas estimadas con un modelo (Black-Scholes, volatilidad ${(r.vol * 100).toFixed(0)}%): úsalas para comparar, no como cotizaciones reales. Si te ejercen se asume que recompras al precio de vencimiento. Sin comisiones ni impuestos. Educativo, no es asesoría financiera.</p></section>`;
}

/* ------------------------------ ¿Qué hubiera pasado si…? ------------------------------ */
const caseSpark = (prices, up) => { const W = 120, H = 34, mn = Math.min(...prices), mx = Math.max(...prices), r = mx - mn || 1;
  const pts = prices.map((v, i) => `${(i / (prices.length - 1) * (W - 4) + 2).toFixed(1)},${(H - 3 - (v - mn) / r * (H - 6)).toFixed(1)}`).join(' ');
  return `<svg viewBox="0 0 ${W} ${H}" class="spark" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${up ? '#35e08b' : '#ff5a6a'}" stroke-width="2"/></svg>`; };

OBB.views.escenarios = {
  S: { ex: [], mine: [], sel: null, cat: 'Todos', mode: 'prices', p: { symbol: '', shares: 100, otm: 5, iv: 30, prices: '' }, res: null },
  all() { return this.S.ex.concat(this.S.mine); },
  async render(el) {
    const S = this.S, self = this, admin = OBB.state.user.role === 'admin';
    el.innerHTML = `<div class="view-title"><h1>¿Qué hubiera <span>pasado si…?</span></h1><span class="muted">Elige un caso de la lista o arma el tuyo, y mira cuánto habría generado el cover call</span></div>
    ${ccCallout()}
    <section class="panel cyan" style="margin-top:12px"><h2>Casos de estudio</h2>
      <div class="bar"><label for="exSel" style="margin:0">Elige de la lista</label><select class="field" id="exSel" style="min-width:280px;max-width:100%"></select></div>
      <div class="seg wrap" id="exCats" style="margin:8px 0"></div><div class="cases" id="exCases"></div></section>
    <div class="grid2"><section class="panel cyan"><h2>Tu escenario</h2><div id="exStory" class="muted" style="margin-bottom:8px"></div>
      <div class="seg" id="exMode"><button data-m="prices">Mis precios</button><button data-m="hist">Historial de un símbolo</button></div>
      <div id="exForm" style="margin-top:10px"></div><div class="stack"><button class="btn green" id="exRun">Calcular</button></div><div class="err" id="exErr" style="color:#ff8b95"></div>
      <div class="savebox"><h3 class="gh">Guardar este caso</h3><div class="bar"><input class="field" id="exName" maxlength="60" placeholder="Nombre del caso" aria-label="Nombre del caso" style="min-width:180px"><button class="btn ghost" id="exSave">Guardar en mis casos</button>
        ${admin ? '<button class="btn yellow" id="exSaveA">Guardar como caso de Optionsbb</button>' : ''}<button class="btn red hidden" id="exDel">Eliminar este caso</button></div></div></section>
      <div id="exOut"><section class="panel blue"><h2>Resultado</h2><div class="empty">Elige un caso o escribe tus datos y pulsa <b>Calcular</b>.</div></section></div></div>`;
    try { const r = await api('/api/whatif/examples'); S.ex = r.examples; S.mine = r.mine || []; } catch (e) { return; }
    this.cases();
    el.addEventListener('click', async e => {
      const b = e.target.closest('[data-ex]'); if (b) { self.pick(b.dataset.ex); return; }
      const c = e.target.closest('#exCats button'); if (c) { S.cat = c.dataset.c; self.cases(); return; }
      const m = e.target.closest('#exMode button'); if (m) { self.read(); S.mode = m.dataset.m; self.form(); return; }
      if (e.target.id === 'exRun') self.run();
      if (e.target.id === 'exSave' || e.target.id === 'exSaveA') await self.save(e.target.id === 'exSaveA');
      if (e.target.id === 'exDel') await self.del();
    });
    el.addEventListener('change', e => { if (e.target.id === 'exSel' && e.target.value) self.pick(e.target.value); });
    if (S.res) this.paintRes(); this.form();
    if (!S.sel && S.ex[0]) this.pick(S.ex[0].id); else this.mark();
  },
  cases() {
    const S = this.S, all = this.all(), cats = ['Todos', ...new Set(all.map(x => x.category || 'Casos de estudio'))];
    if (!cats.includes(S.cat)) S.cat = 'Todos';
    $('#exCats').innerHTML = cats.map(c => `<button data-c="${esc(c)}" class="${c === S.cat ? 'on' : ''}">${esc(c)}</button>`).join('');
    const list = all.filter(x => S.cat === 'Todos' || (x.category || 'Casos de estudio') === S.cat);
    $('#exCases').innerHTML = list.map(x => `<button class="case" data-ex="${esc(x.id)}" title="${esc(x.story || '')}"><b>${esc(x.title)}</b>${caseSpark(x.prices, x.prices[x.prices.length - 1] >= x.prices[0])}
      <small>${x.prices.length - 1} meses · ${esc(x.symbol)} · ${x.shares} acc. · call +${x.otm}% · vol ${x.iv}%${x.kind === 'mine' ? ' · <i>mío</i>' : x.kind === 'admin' ? ' · <i>Optionsbb</i>' : ''}</small></button>`).join('') || '<div class="muted">Aún no tienes casos guardados. Arma un escenario y pulsa «Guardar en mis casos».</div>';
    const groups = {}; all.forEach(x => { (groups[x.category || 'Casos de estudio'] = groups[x.category || 'Casos de estudio'] || []).push(x); });
    $('#exSel').innerHTML = '<option value="">— Elige un caso —</option>' + Object.entries(groups).map(([g, xs]) => `<optgroup label="${esc(g)}">${xs.map(x => `<option value="${esc(x.id)}">${esc(x.title)}</option>`).join('')}</optgroup>`).join('');
    this.mark();
  },
  mark() {
    const S = this.S, x = this.all().find(v => v.id === S.sel);
    if ($('#exSel')) $('#exSel').value = S.sel || '';
    $$('#exCases [data-ex]').forEach(b => b.classList.toggle('on', b.dataset.ex === S.sel));
    const admin = OBB.state.user.role === 'admin';
    if ($('#exDel')) $('#exDel').classList.toggle('hidden', !(x && (x.kind === 'mine' || (x.kind === 'admin' && admin))));
    if ($('#exStory')) $('#exStory').textContent = x ? (x.story || '') : '';
  },
  pick(id) {
    const S = this.S, x = this.all().find(v => v.id === id); if (!x) return;
    S.sel = id; S.mode = 'prices'; S.p = { symbol: x.symbol, shares: x.shares, otm: x.otm, iv: x.iv, prices: x.prices.join(', ') };
    this.mark(); this.form(); this.run();
  },
  async save(asAdmin) {
    const S = this.S; this.read(); const p = S.p; $('#exErr').textContent = '';
    const name = ($('#exName').value || '').trim(); if (!name) { $('#exErr').textContent = 'Escribe un nombre para el caso.'; return; }
    if (S.mode !== 'prices') { $('#exErr').textContent = 'Para guardar un caso usa «Mis precios» (puedes copiar los precios del historial).'; return; }
    try {
      const body = { title: name, symbol: p.symbol || 'EJEMPLO', shares: +p.shares, otm: +p.otm, iv: +p.iv || 30, prices: String(p.prices).split(/[,\s;]+/).filter(Boolean).map(Number), story: (this.all().find(v => v.id === S.sel) || {}).story || '' };
      const r = await api(asAdmin ? '/api/admin/whatif/cases' : '/api/whatif/cases', { method: 'POST', body });
      (asAdmin ? S.ex : S.mine).push(asAdmin ? r.case : r.case); S.sel = r.case.id; S.cat = 'Todos'; $('#exName').value = ''; this.cases(); toast(asAdmin ? 'Caso agregado para todos los usuarios' : 'Caso guardado en «Mis casos»');
    } catch (e) { $('#exErr').textContent = e.message; }
  },
  async del() {
    const S = this.S, x = this.all().find(v => v.id === S.sel); if (!x || !confirm('¿Eliminar este caso?')) return;
    try {
      await api(x.kind === 'admin' ? '/api/admin/whatif/cases/' + x.id : '/api/whatif/cases/' + x.id, { method: 'DELETE' });
      S.ex = S.ex.filter(v => v.id !== x.id); S.mine = S.mine.filter(v => v.id !== x.id); S.sel = null; this.cases(); toast('Caso eliminado');
    } catch (e) { toast(e.message, true); }
  },
  form() {
    const S = this.S, p = S.p; $$('#exMode button').forEach(b => b.classList.toggle('on', b.dataset.m === S.mode));
    $('#exForm').innerHTML = `<div class="g3">${fld('exSym', 'Símbolo', p.symbol, 'maxlength="8" style="text-transform:uppercase"')}${fld('exSh', 'Acciones', p.shares, 'type="number" min="1" step="any"')}${fld('exOtm', 'Call a % fuera del dinero', p.otm, 'type="number" min="0" max="50" step="0.5"')}</div>
      ${S.mode === 'prices' ? `<div class="g3">${fld('exIv', 'Volatilidad anual %', p.iv, 'type="number" min="5" max="300"')}</div>
        <label for="exPr">Precio al inicio de cada mes, separados por coma (el último es el precio final)</label><textarea class="field" id="exPr" rows="3">${esc(p.prices)}</textarea>
        <p class="note">Los casos son ilustrativos, con precios redondeados (no son históricos exactos): reemplázalos por los precios reales que quieras estudiar.</p>`
        : `<div class="g3">${fld('exDays', 'Últimos días (20–360)', p.days || 360, 'type="number" min="20" max="360"')}${fld('exIv', 'Volatilidad % (vacío = histórica)', p.iv === 30 ? '' : p.iv, 'type="number" min="0" max="300"')}</div><p class="note">Usa el historial del símbolo en tu fuente de datos (con Schwab conectado, los precios reales; en DEMO son simulados).</p>`}`;
  },
  read() {
    const S = this.S, g = id => ($('#' + id) || {}).value;
    if (!$('#exSym')) return;
    S.p = { ...S.p, symbol: (g('exSym') || '').toUpperCase(), shares: g('exSh'), otm: g('exOtm'), iv: g('exIv') ?? S.p.iv, prices: g('exPr') ?? S.p.prices, days: g('exDays') || S.p.days };
  },
  async run() {
    const S = this.S; this.read(); const p = S.p; $('#exErr').textContent = '';
    const body = { shares: +p.shares, otm: +p.otm, iv: +p.iv || 0 };
    if (S.mode === 'prices') { body.prices = String(p.prices).split(/[,\s;]+/).filter(Boolean).map(Number); if (body.prices.some(n => !(n > 0))) { $('#exErr').textContent = 'Revisa los precios: deben ser números positivos.'; return; } }
    else { body.symbol = p.symbol; body.days = +p.days || 360; }
    try { S.res = { r: await api('/api/whatif', { method: 'POST', body }), sym: p.symbol }; this.paintRes(); } catch (e) { $('#exErr').textContent = e.message; }
  },
  paintRes() { const R = this.S.res; if (R && $('#exOut')) $('#exOut').innerHTML = wiResult(R.r, `Resultado · ${R.sym || 'acción'} · ${R.r.n} mes(es)`, R.sym); },
  destroy() { clearTimers(); },
};

/* ------------------------------ Apalancados + Cover Call (nivel Avanzado) ------------------------------ */
OBB.views.apalancados = {
  S: { items: [], sym: 'NVDL', shares: 100, days: 180, otm: 10, iv: '', res: null },
  async render(el) {
    const S = this.S, self = this;
    el.innerHTML = `<div class="view-title"><h1>Apalancados <span>+ Cover Call</span></h1><span class="muted">NVDL, AMDL y otros instrumentos con cover call · nivel Avanzado</span></div>
    <section class="panel red"><h2>⚠ Alto riesgo: léelo antes de usarlos</h2><ul class="riskl">
      <li>Los ETF apalancados <b>se reinician cada día</b>: si la acción base sube y baja, el apalancado pierde valor aunque la base quede igual (decadencia por volatilidad).</li>
      <li>Pueden perder más de la mitad de su valor en pocas semanas. No son para dinero que necesites.</li>
      <li>El cover call limita justo la subida que buscabas con un apalancado: cobras prima, pero renuncias a los movimientos fuertes.</li>
      <li>Sus opciones pueden tener spreads amplios y poca liquidez: revisa open interest y bid/ask. Necesitas 100 acciones por contrato.</li></ul></section>
    ${ccCallout()}
    <section class="panel cyan" style="margin-top:14px"><h2>Instrumentos</h2><div id="lvTable"><div class="empty">Cargando…</div></div></section>
    <div class="grid2" style="margin-top:14px"><section class="panel yellow"><h2>Simula el cover call</h2><div class="g3">${fld('lvSym', 'Símbolo', S.sym, 'maxlength="6" style="text-transform:uppercase"')}${fld('lvSh', 'Acciones', S.shares, 'type="number" min="1" step="any"')}
      <div><label for="lvDays">Periodo</label><select class="field" id="lvDays">${[[90, '90 días'], [180, '180 días'], [360, '360 días']].map(([v, l]) => `<option value="${v}" ${S.days === v ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
      ${fld('lvOtm', 'Call a % fuera del dinero', S.otm, 'type="number" min="0" max="50" step="0.5"')}${fld('lvIv', 'Volatilidad % (vacío = histórica)', S.iv, 'type="number" min="0" max="300"')}</div>
      <div class="stack"><button class="btn green" id="lvRun">Simular</button></div><div class="err" id="lvErr" style="color:#ff8b95"></div>
      <p class="note">Como son más volátiles, las primas son más altas… y también la probabilidad de que te ejerzan. Prueba strikes más lejanos (10–15 %).</p></section>
    <section class="panel green"><h2>La decadencia de un apalancado</h2><div class="g3">${fld('dcL', 'Apalancamiento (x)', 2, 'type="number" min="1" max="5" step="1"')}${fld('dcV', 'Volatilidad anual de la acción base %', 60, 'type="number" min="5" max="300"')}${fld('dcT', 'Años', 1, 'type="number" min="0.25" max="5" step="0.25"')}</div>
      <div id="dcOut" class="insight"></div><p class="note">Fórmula teórica: pérdida por volatilidad ≈ 1 − e<sup>−L(L−1)/2·σ²·T</sup> si la acción base termina sin cambio. Es una referencia, no una predicción.</p></section></div>
    <div id="lvOut" style="margin-top:14px"></div>`;
    el.addEventListener('click', e => {
      const b = e.target.closest('[data-lv]'); if (b) { $('#lvSym').value = b.dataset.lv; self.sim(); return; }
      if (e.target.id === 'lvRun') self.sim();
    });
    el.addEventListener('input', e => { if (['dcL', 'dcV', 'dcT'].includes(e.target.id)) self.decay(); });
    this.decay();
    try { S.items = (await api('/api/lev')).items; } catch (er) { if (![401, 402, 403].includes(er.status)) toast(er.message, true); return; }
    $('#lvTable').innerHTML = `<div class="tbl-scroll" style="max-height:none"><table class="t"><thead><tr><th>Símbolo</th><th>Instrumento</th><th>Base</th><th class="r">Apalanc.</th><th class="r">Precio</th><th class="r">Hoy</th><th></th></tr></thead><tbody>${S.items.map(x => `<tr><td class="sym" data-sym="${esc(x.symbol)}">${esc(x.symbol)}</td><td>${esc(x.name)}</td><td>${esc(x.base)}</td><td class="r"><b>${x.leverage}x</b></td><td class="r">${fmtNum(x.price)}</td><td class="r ${cls(x.change_pct)}">${fmtPct(x.change_pct)}</td><td class="r"><button class="btn ghost" style="padding:2px 8px;font-size:12px" data-lv="${esc(x.symbol)}">Simular cover call</button></td></tr>`).join('')}</tbody></table></div><p class="note">Lista de ejemplo editable en <code>obb/scenarios.py</code>. Verifica en tu broker que el instrumento exista y tenga opciones.</p>`;
    el.addEventListener('click', e => { const s = e.target.closest('.sym[data-sym]'); if (s) { OBB.state.symbol = s.dataset.sym; OBB.go('analisis'); } });
  },
  decay() {
    const L = +$('#dcL').value, v = +$('#dcV').value / 100, T = +$('#dcT').value; if (!(L >= 1 && v > 0 && T > 0)) return;
    const loss = (1 - Math.exp(-L * (L - 1) / 2 * v * v * T)) * 100;
    $('#dcOut').innerHTML = L === 1 ? 'Sin apalancamiento no hay decadencia por reinicio diario.' : `Con ${L}x y ${(v * 100).toFixed(0)}% de volatilidad, en ${T} año(s) un apalancado perdería en teoría <b class="down">${loss.toFixed(0)}%</b> de su valor <i>solo por la volatilidad</i> si la acción base termina igual que empezó.`;
  },
  async sim() {
    const S = this.S, g = id => $('#' + id).value; $('#lvErr').textContent = '';
    S.sym = g('lvSym').toUpperCase(); S.shares = g('lvSh'); S.days = +g('lvDays'); S.otm = g('lvOtm'); S.iv = g('lvIv');
    try { const r = await api('/api/whatif', { method: 'POST', body: { symbol: S.sym, shares: +S.shares, days: S.days, otm: +S.otm, iv: +S.iv || 0 } }); $('#lvOut').innerHTML = wiResult(r, `Cover call sobre ${S.sym} · ${S.days} días`, S.sym); $('#lvOut').scrollIntoView({ behavior: 'smooth' }); }
    catch (e) { $('#lvErr').textContent = e.message; }
  },
  destroy() { clearTimers(); },
};
