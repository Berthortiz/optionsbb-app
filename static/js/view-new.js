/* Inicio (perfil de inversor), Análisis de acción, Ranking de estrategias, 401(k) y Manual */
const MODS = {
  comando: ['▣', 'Centro de Comando', 'Señales de tus acciones y tu lista de seguimiento con % por periodo.'],
  analisis: ['◈', 'Análisis de acción', 'Elige una acción y ve su resumen y su comportamiento en 5 min, 15 min, 1 h y diario.'],
  covercall: ['◎', 'Cover Call', 'Calcula qué strike vender y simula mes a mes con recompra.'],
  k401: ['⛨', '401(k) y retiro', 'Mira cuánto pierde tu dinero quieto y cuánto puede crecer invertido, con cover call.'],
  flujo: ['↗', 'Flujo OI', 'Qué parte del volumen de opciones se convirtió en open interés.'],
  sectores: ['◍', 'Sectores', 'Acciones clave por sector con sus señales.'],
  ranking: ['★', 'Ranking', 'Las estrategias más efectivas por temporalidad y en qué acciones se dan.'],
  desempeno: ['▥', 'Desempeño', 'Resultados de tus backtests de Thinkorswim.'],
  senales: ['⚡', 'Señales', 'Catálogo de estrategias, tu selección y tus estrategias propias.'],
  videos: ['▶', 'Videos', 'Biblioteca del canal de YouTube.'],
  etf: ['◉', 'Mi ETF', 'Arma tu propio ETF y mira su rendimiento con y sin cover call.'],
  escenarios: ['⟲', '¿Qué hubiera pasado si…?', 'Ejemplos como BYND y MSFT: cuánto habría generado el cover call.'],
  opciones: ['∑', 'Calculadora de opciones', 'Ganancia, pérdida, equilibrio y griegas de tu estrategia.'],
  earnings: ['◷', 'Earnings', 'Movimiento del precio en reportes anteriores.'],
  dividendos: ['＄', 'Dividendos', 'Qué acciones pagan y cuánto.'],
  gex: ['▦', 'Gamma (GEX)', 'Paredes de calls y puts por strike.'],
  apalancados: ['⚡', 'Apalancados + Cover Call', 'NVDL, AMDL y otros con cover call (nivel Avanzado).'],
};
const TF_ES = { '5m': '5 min', '15m': '15 min', '30m': '30 min', '1h': '1 hora', '1d': 'Diario' };
const fld = (id, label, val, extra = '') => `<div><label for="${id}">${label}</label><input class="field" id="${id}" value="${esc(val ?? '')}" ${extra}></div>`;
const fmtPlain = n => (n == null ? '—' : nf0.format(Math.round(n)));

/* ------------------------------ Inicio ------------------------------ */
OBB.views.inicio = {
  async render(el) {
    const u = OBB.state.user; let d;
    try { d = await api('/api/prefs'); } catch (e) { return; }
    const heroH = await OBB.hero(u.plan);
    const draw = () => {
      const prof = d.profile && d.profiles[d.profile];
      const planNote = `<span class="status-pill ${u.reason === 'trial' ? 'warn' : 'ok'}">Plan ${esc(u.plan_name)}${u.reason === 'trial' ? ' · prueba ' + u.trial_days_left + ' día(s)' : u.reason === 'reward' ? ' · regalo ' + u.reward_days_left + ' día(s)' : ''}</span>`;
      if (!prof) {
        el.innerHTML = `<div class="view-title"><h1>Bienvenido a <span>Options BB</span></h1>${planNote}</div>${heroH}
        <section class="panel cyan"><h2>Cuéntanos cómo inviertes</h2><p class="muted">4 preguntas rápidas para mostrarte primero lo que más te sirve. Puedes repetirlo cuando quieras.</p>
        <form id="quiz">${d.quiz.map((q, i) => `<fieldset class="qz"><legend>${i + 1}. ${esc(q.q)}</legend>${q.opts.map((o, j) => `<label class="opt-r"><input type="radio" name="q${i}" value="${j}"> ${esc(o)}</label>`).join('')}</fieldset>`).join('')}
        <div class="stack"><button class="btn green" type="submit">Ver mi ruta</button></div><div class="err" id="qErr" style="color:#ff8b95"></div></form></section>`;
        $('#quiz').onsubmit = async ev => {
          ev.preventDefault();
          const a = d.quiz.map((_, i) => { const r = $(`input[name=q${i}]:checked`); return r ? +r.value : null; });
          if (a.includes(null)) { $('#qErr').textContent = 'Responde las 4 preguntas.'; return; }
          try { await api('/api/prefs', { method: 'POST', body: { answers: a } }); d = await api('/api/prefs'); draw(); } catch (er) { $('#qErr').textContent = er.message; }
        };
        return;
      }
      el.innerHTML = `<div class="view-title"><h1>Tu <span>ruta</span></h1>${planNote}<button class="btn ghost" id="retake" style="padding:4px 12px">Repetir cuestionario</button></div>${heroH}
      <section class="panel green"><h2>Perfil: ${esc(prof.name)}</h2><p>${esc(prof.desc)}</p></section>
      <div class="route">${prof.route.map((m, i) => `<button class="panel cyan rt" data-go="${m}"><span class="n">${i + 1}</span><b>${MODS[m][0]} ${MODS[m][1]}</b><small>${MODS[m][2]}</small></button>`).join('')}
        ${prof.locked.map(m => `<button class="panel yellow rt lk" data-go="planes"><span class="n">🔒</span><b>${MODS[m][1]}</b><small>${MODS[m][2]} <em>Disponible en un plan superior.</em></small></button>`).join('')}</div>
      <section class="panel red" style="margin-top:14px"><h2>Tu dinero no puede quedarse quieto</h2>
        <p>El efectivo parado pierde poder de compra cada año por la inflación. En el módulo <b>401(k) y retiro</b> comparas, con tus propios números, efectivo vs acciones vs acciones con cover call.</p>
        <div class="stack"><button class="btn green" data-go="k401">Calcular mi caso</button><button class="btn ghost" data-go="covercall">Probar el simulador de Cover Call</button></div></section>`;
      $('#retake').onclick = () => { d.profile = null; draw(); };
    };
    el.onclick = e => { const g = e.target.closest('[data-go]'); if (g) OBB.go(g.dataset.go); };
    draw();
  },
};

/* ------------------------------ Análisis de acción ------------------------------ */
OBB.views.analisis = {
  async render(el) {
    const self = this;
    el.innerHTML = `<div class="view-title"><h1>Análisis de <span>acción</span></h1><span class="muted">Resumen y comportamiento por temporalidad</span></div>
    <div class="bar"><input class="field" id="anSym" maxlength="6" style="width:140px;text-transform:uppercase" value="${esc(OBB.state.symbol)}" aria-label="Símbolo"><button class="btn green" id="anGo">Analizar</button>
    <button class="btn ghost" id="anChart">Ver gráfico</button><button class="btn ghost" id="anCC">Cover Call con esta acción</button><button class="btn ghost" id="anWatch">+ Mi lista</button></div><div id="anBody"><div class="empty">Cargando…</div></div>`;
    const go = async () => {
      const sym = ($('#anSym').value || '').trim().toUpperCase(); if (!sym) return;
      OBB.state.symbol = sym; $('#anBody').innerHTML = '<div class="empty">Analizando…</div>';
      try { self.d = await api('/api/analysis?symbol=' + encodeURIComponent(sym)); self.paint(); } catch (e) { $('#anBody').innerHTML = `<div class="panel red"><h2>No pude analizar ${esc(sym)}</h2><p>${esc(e.message)}</p></div>`; }
    };
    $('#anGo').onclick = go; $('#anSym').onkeydown = e => { if (e.key === 'Enter') go(); };
    $('#anChart').onclick = () => { OBB.state.symbol = ($('#anSym').value || 'SPY').toUpperCase(); OBB.go('comando'); };
    $('#anWatch').onclick = () => addToMyList($('#anSym').value);
    $('#anCC').onclick = () => {
      const d = self.d; if (!d) return toast('Primero analiza la acción', true);
      OBB.cc = OBB.cc || {}; const px = d.quote.price || d.summary.price;
      OBB.cc.calc = Object.assign(OBB.cc.calc || {}, { symbol: d.symbol, spot: String(Math.round(px * 100) / 100), cost: '', mode: 'chain' }); OBB.cc.tab = 'calc'; OBB.go('covercall');
    };
    go();
  },
  paint() {
    const d = this.d, s = d.summary, body = $('#anBody'); if (!s || !s.price) { body.innerHTML = '<div class="empty">No hay suficiente historial para esta acción.</div>'; return; }
    const per = [['0', 'Hoy'], ['7', '7 días'], ['15', '15 días'], ['30', '30 días'], ['90', '90 días'], ['360', '360 días']];
    const trendChip = t => t ? `<span class="chip ${t === 'alcista' ? 'buy' : t === 'bajista' ? 'sell' : 'neutral'}">${t.toUpperCase()}</span>` : '—';
    const sp = s.spark, mn = Math.min(...sp), mx = Math.max(...sp), W = 320, H = 70;
    const pts = sp.map((v, i) => `${(i / (sp.length - 1) * W).toFixed(1)},${(H - 4 - (v - mn) / ((mx - mn) || 1) * (H - 8)).toFixed(1)}`).join(' ');
    const up = sp[sp.length - 1] >= sp[0];
    const rp = s.range_pos == null ? 50 : Math.max(0, Math.min(100, s.range_pos));
    body.innerHTML = `
<div class="kpis" style="grid-template-columns:repeat(auto-fit,minmax(130px,1fr))"><div><span>${esc(d.symbol)}</span><b>${fmtNum(s.price)}</b></div>${per.map(([k, l]) => `<div><span>${l}</span><b class="${cls(s.changes[k])}">${fmtPct(s.changes[k])}</b></div>`).join('')}</div>
<div class="an-grid">
 <section class="panel cyan"><h2>Resumen financiero</h2>
  <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto" role="img" aria-label="Últimos 90 cierres"><polyline points="${pts}" fill="none" stroke="${up ? C.green : C.red}" stroke-width="2.4"/></svg>
  <div class="rangebar" title="Posición dentro del rango de 52 semanas"><i style="left:${rp}%"></i></div>
  <div class="rangelbl"><span>Mín 52 sem ${fmtNum(s.lo52)}</span><span>Máx 52 sem ${fmtNum(s.hi52)}</span></div>
  <dl class="kv"><dt>Distancia al máximo</dt><dd class="${cls(s.from_hi_pct)}">${fmtPct(s.from_hi_pct)}</dd><dt>Distancia al mínimo</dt><dd class="${cls(s.from_lo_pct)}">${fmtPct(s.from_lo_pct)}</dd>
  <dt>Volatilidad anual</dt><dd>${s.vol_ann == null ? '—' : s.vol_ann.toFixed(1) + '%'}</dd><dt>Mayor caída (1 año)</dt><dd class="down">−${s.max_dd.toFixed(1)}%</dd>
  <dt>RSI (14 días)</dt><dd>${s.rsi14 == null ? '—' : s.rsi14.toFixed(0)} <small class="muted">${s.rsi14 > 70 ? 'sobrecomprada' : s.rsi14 < 30 ? 'sobrevendida' : 'neutral'}</small></dd>
  <dt>Tendencia (SMA 50/200)</dt><dd>${trendChip(s.trend_long)}</dd><dt>SMA 20 / 50 / 200</dt><dd>${[s.sma20, s.sma50, s.sma200].map(v => v == null ? '—' : fmtNum(v)).join(' / ')}</dd>
  <dt>Volumen hoy vs promedio 20 d</dt><dd>${s.vol_today && s.avg_vol20 ? (s.vol_today / s.avg_vol20).toFixed(2) + '×' : '—'}</dd>
  ${s.options ? `<dt>Opciones: calls / puts</dt><dd>${fmtInt(s.options.call_vol)} / ${fmtInt(s.options.put_vol)} <small class="muted">P/C ${s.options.pcr == null ? '—' : s.options.pcr.toFixed(2)}</small></dd>` : ''}</dl>
  <p class="note">P/E, ganancias (EPS), dividendos y capitalización se añadirán al enlazar tu cuenta de Schwab. Hoy el resumen sale de precio, volumen y opciones.</p></section>
 <section class="panel green"><h2>Por temporalidad</h2><div class="tbl-scroll" style="max-height:none;overflow-x:auto"><table class="t"><thead><tr><th>Temporalidad</th><th>Tendencia</th><th class="r">RSI</th><th>Estrategias con mejor historial en esta acción</th></tr></thead><tbody>
  ${d.tfs.map(t => `<tr><td><b>${esc(t.label)}</b></td><td>${trendChip(t.trend)}</td><td class="r">${t.rsi == null ? '—' : t.rsi.toFixed(0)}</td><td>${t.best.length ? t.best.map(b => `<span class="hit ${b.active ? 'new' : ''}" title="${b.n} señales · ${b.win_rate.toFixed(0)}% de aciertos · ${fmtPct(b.avg)} promedio${b.active ? ' · ACTIVA AHORA' : ''}">${b.side === 'BULL' ? '▲' : '▼'} ${esc(b.label)} <small>${b.win_rate.toFixed(0)}% · ${fmtPct(b.avg)}</small>${b.active ? ' <i>AHORA</i>' : ''}</span>`).join(' ') : '<span class="muted">Pocas señales en esta acción</span>'}</td></tr>`).join('')}</tbody></table></div>
  <p class="note">Resultado de cada señal = cambio del precio 5 velas después, a favor de la señal. Es historia reciente (≈10 días en velas intradía y 1 año en diario): sirve para comparar, no garantiza el futuro.</p></section>
</div>`;
  },
};

/* ------------------------------ Ranking ------------------------------ */
OBB.views.ranking = {
  tf: '15m',
  async render(el) {
    const self = this;
    el.innerHTML = `<div class="view-title"><h1>Ranking de <span>estrategias</span></h1><span class="muted">Las más efectivas por temporalidad y en qué acciones se dan</span></div>
    <div id="rkTop" class="rk-top"></div><div class="seg" id="rkTabs" style="margin:12px 0"></div><div id="rkBody"><div class="empty">Calculando…</div></div>`;
    el.onclick = e => { const t = e.target.closest('[data-tf]'); if (t) { self.tf = t.dataset.tf; self.load(); return; } const s = e.target.closest('[data-sym]'); if (s) { OBB.state.symbol = s.dataset.sym; OBB.go('analisis'); } };
    this.load(); this.topStrip();
  },
  async topStrip() {
    try {
      const all = await Promise.all(Object.keys(TF_ES).map(tf => api('/api/rank?tf=' + tf)));
      if (!$('#rkTop')) return;
      $('#rkTop').innerHTML = all.map(r => `<button class="panel ${r.tf === this.tf ? 'green' : 'cyan'} rkc" data-tf="${r.tf}"><b>${TF_ES[r.tf]}</b>${r.rows.slice(0, 3).map((x, i) => `<div><span class="${x.side === 'BULL' ? 'up' : 'down'}">${i + 1}. ${esc(x.label)}</span> <small>${fmtPct(x.avg)}</small></div>`).join('') || '<small class="muted">Sin datos suficientes</small>'}</button>`).join('');
    } catch (e) { /* se muestra abajo */ }
  },
  async load() {
    $$('#rkTop .rkc').forEach(b => b.className = 'panel ' + (b.dataset.tf === this.tf ? 'green' : 'cyan') + ' rkc');
    try {
      const d = await api('/api/rank?tf=' + this.tf); OBB.onStatus && OBB.onStatus(d.status);
      $('#rkTabs').innerHTML = d.tfs.map(t => `<button data-tf="${t.key}" class="${t.key === this.tf ? 'on' : ''}">${esc(t.label)}</button>`).join('');
      const chips = (arr, f) => arr.length ? arr.slice(0, 8).map(f).join(' ') + (arr.length > 8 ? ` <small class="muted">+${arr.length - 8}</small>` : '') : '<span class="muted">—</span>';
      const row = r => `<tr><td class="r"><b>${r.rank || '·'}</b></td><td><span class="${r.side === 'BULL' ? 'up' : 'down'}">${r.side === 'BULL' ? '▲' : '▼'}</span> <b>${esc(r.label)}</b>${r.kind === 'cat' ? ' <small class="muted">catálogo</small>' : ''}</td><td class="r">${fmtInt(r.n)}</td><td class="r">${r.win_rate == null ? '—' : r.win_rate.toFixed(0) + '%'}</td><td class="r ${cls(r.avg)}">${fmtPct(r.avg)}</td><td class="r">${r.profit_factor == null ? '—' : r.profit_factor.toFixed(2)}</td>
        <td>${chips(r.active, s => `<button class="hit new" data-sym="${esc(s)}">${esc(s)}</button>`)}</td><td>${chips(r.best, b => `<button class="hit" data-sym="${esc(b.symbol)}" title="${b.n} señales · ${b.win_rate.toFixed(0)}% aciertos">${esc(b.symbol)} <small>${fmtPct(b.avg)}</small></button>`)}</td></tr>`;
      const head = '<thead><tr><th class="r">#</th><th>Estrategia</th><th class="r">Señales</th><th class="r">% aciertos</th><th class="r">Rend. prom.</th><th class="r" title="Ganancias ÷ pérdidas">Factor</th><th>Activa ahora en</th><th>Mejor historial en</th></tr></thead>';
      $('#rkBody').innerHTML = `<section class="panel green"><h2>Temporalidad ${esc(TF_ES[d.tf])}</h2>${d.rows.length ? `<div class="tbl-scroll" style="max-height:none;overflow-x:auto"><table class="t">${head}<tbody>${d.rows.map(row).join('')}</tbody></table></div>` : '<div class="empty">' + (d.ready ? 'Ninguna estrategia tiene señales suficientes todavía.' : 'Calculando el ranking por primera vez; vuelve en un minuto.') + '</div>'}
        <p class="note">Cada señal se mide por el cambio del precio ${d.horizon} velas después (a favor de la señal). Solo entran estrategias con ${d.min_n}+ señales. Rend. prom. = promedio por señal. ${OBB.state.user.role === 'admin' ? '' : ''}En modo DEMO usa datos simulados. Es historia: no garantiza resultados futuros.</p></section>
        ${d.few.length ? `<details><summary>Con pocos datos (${d.few.length})</summary><div class="tbl-scroll" style="max-height:none;overflow-x:auto"><table class="t">${head}<tbody>${d.few.map(row).join('')}</tbody></table></div></details>` : ''}`;
    } catch (e) { if (![401, 402, 403].includes(e.status)) toast(e.message, true); }
  },
};

/* ------------------------------ 401(k) ------------------------------ */
OBB.views.k401 = {
  tab: 'proj', real: false, last: null,
  async render(el) {
    const self = this;
    const pr = await api('/api/prefs').catch(() => ({ k401: {} }));
    this.p = Object.assign({ balance: '20000', monthly: '500', salary: '', match_rate: '50', match_cap: '6', years: '25', inflation: '3', cash_rate: '0.5', stock_return: '7', fee: '0.1', cc_premium_month: '0.6', cc_giveup: '6', cc_share: '100', income: '3000', withdraw_rate: '4', fee_low: '0.1', fee_high: '1' }, pr.k401 || {});
    el.innerHTML = `<div class="view-title"><h1>401(k) y <span>retiro</span></h1><span class="muted">Que tu dinero trabaje, no que se deprecie</span></div>
    <div class="bar"><div class="seg" id="kTabs"><button data-t="proj">Proyección</button><button data-t="goal">Meta de retiro</button><button data-t="fees">Comisiones</button><button data-t="hold">Mi cartera</button></div></div><div id="kBody"></div>
    <div class="legal" style="text-align:left;padding:10px 0">Educativo, no es asesoría financiera ni fiscal. Los rendimientos son supuestos que tú editas, no promesas. Un 401(k) normal ofrece un menú fijo de fondos: las opciones (como el cover call) solo se pueden usar si tu plan tiene una ventana de corretaje y tu broker aprueba opciones; en una IRA es más común. Verifica con tu plan.</div>`;
    $('#kTabs').onclick = e => { const b = e.target.closest('button'); if (b) { self.tab = b.dataset.t; self.paint(); } };
    this.paint();
  },
  paint() {
    $$('#kTabs button').forEach(b => b.classList.toggle('on', b.dataset.t === this.tab));
    ({ proj: () => this.proj(), goal: () => this.goal(), fees: () => this.fees(), hold: () => this.hold() })[this.tab]();
  },
  read(ids) { ids.forEach(i => { const e = $('#k_' + i); if (e) this.p[i] = e.value; }); return Object.fromEntries(ids.map(i => [i, this.p[i]])); },
  proj() {
    const p = this.p, self = this;
    $('#kBody').innerHTML = `<div class="cc-grid"><section class="panel cyan"><h2>Tus datos</h2><div class="cc-form">
      ${fld('k_balance', 'Saldo actual ($)', p.balance, 'inputmode="decimal"')}${fld('k_monthly', 'Tu aporte mensual ($)', p.monthly, 'inputmode="decimal"')}${fld('k_years', 'Años hasta el retiro', p.years, 'inputmode="numeric"')}
      ${fld('k_salary', 'Salario anual ($) — opcional', p.salary, 'inputmode="decimal" placeholder="para calcular el aporte de la empresa"')}${fld('k_match_rate', 'La empresa aporta (% de lo que pones)', p.match_rate, 'inputmode="decimal"')}${fld('k_match_cap', 'hasta (% del salario)', p.match_cap, 'inputmode="decimal"')}</div>
      <details open><summary>Supuestos (editables)</summary><div class="cc-form">
      ${fld('k_inflation', 'Inflación anual %', p.inflation, 'inputmode="decimal"')}${fld('k_cash_rate', 'Interés del efectivo %', p.cash_rate, 'inputmode="decimal"')}${fld('k_stock_return', 'Rendimiento de las acciones %', p.stock_return, 'inputmode="decimal"')}${fld('k_fee', 'Comisión anual %', p.fee, 'inputmode="decimal"')}
      ${fld('k_cc_premium_month', 'Cover call: prima mensual %', p.cc_premium_month, 'inputmode="decimal"')}${fld('k_cc_giveup', 'Cover call: subida que cedes (puntos %/año)', p.cc_giveup, 'inputmode="decimal"')}${fld('k_cc_share', '% de la cartera con cover call', p.cc_share, 'inputmode="decimal"')}</div>
      <p class="note">Los valores de cover call son ilustrativos: usa los de tu simulación en el módulo Cover Call. Si la prima no compensa lo que cedes, no suma.</p></details>
      <div class="stack"><button class="btn green" id="kGo">Calcular</button></div></section><section id="kOut"><div class="panel green"><h2>Resultado</h2><div class="empty">Pulsa <b>Calcular</b>.</div></div></section></div>`;
    const ids = ['balance', 'monthly', 'years', 'salary', 'match_rate', 'match_cap', 'inflation', 'cash_rate', 'stock_return', 'fee', 'cc_premium_month', 'cc_giveup', 'cc_share'];
    const run = async () => {
      const body = this.read(ids); Object.keys(body).forEach(k => { if (body[k] === '') delete body[k]; });
      try { this.last = await api('/api/k401/project', { method: 'POST', body }); this.paintProj(); api('/api/prefs', { method: 'POST', body: { key: 'k401', value: this.p } }).catch(() => { }); }
      catch (e) { $('#kOut').innerHTML = `<div class="panel red"><h2>Revisa los datos</h2><p>${esc(e.message)}</p></div>`; }
    };
    $('#kGo').onclick = run; run();
  },
  paintProj() {
    const r = this.last, S = r.scenarios, real = this.real, key = real ? 'final_real' : 'final', y = r.inputs.years;
    const col = { cash: C.red, stocks: C.cyan, cc: C.green }, step = Math.max(1, Math.ceil(r.rows.length / 8));
    const series = Object.keys(S).map(k => ({ name: S[k].label, color: col[k], pts: r.rows.filter((_, i) => (i + 1) % step === 0 || i === r.rows.length - 1).map(x => ({ x: 'A' + x.year, y: x[k + (real ? '_real' : '')] })) }));
    const lost = r.cash_power_lost * 100;
    $('#kOut').innerHTML = `
    <section class="panel red"><h2>El efectivo quieto se deprecia</h2><p>Con ${r.inputs.inflation}% de inflación, en <b>${y} años</b> tu efectivo pierde <b class="down">${lost.toFixed(0)}%</b> de poder de compra. De los ${money(r.contributed)} que habrás puesto, el efectivo equivale a <b>${money(S.cash.final_real)}</b> de hoy${r.inputs.employer_monthly ? ` (incluye ${money(r.inputs.employer_monthly)}/mes de la empresa: dinero gratis que no debes dejar pasar)` : ''}.</p></section>
    <section class="panel green" style="margin-top:14px"><h2>Resultado a ${y} años</h2>
      <div class="seg" id="kReal" style="margin-bottom:8px"><button data-r="0" class="${real ? '' : 'on'}">Dólares futuros</button><button data-r="1" class="${real ? 'on' : ''}">Dólares de hoy (sin inflación)</button></div>
      <div class="kpis">${['cash', 'stocks', 'cc'].map(k => `<div style="border-color:${col[k]}"><span>${esc(S[k].label)} · ${S[k].rate}%/año</span><b style="color:${col[k]}">${money(S[k][key])}</b></div>`).join('')}</div>
      <div class="cc-chart">${ccLines(series)}</div>
      <p class="note"><span style="color:${col.cash}">━</span> Efectivo · <span style="color:${col.stocks}">━</span> Acciones · <span style="color:${col.cc}">━</span> Acciones + Cover Call (retorno neto del cover call: ${r.cc_net_return}%/año con tus supuestos)</p>
      ${r.warnings.map(w => `<div class="cc-warn">⚠ ${esc(w)}</div>`).join('')}
      <div class="stack"><button class="btn ghost" data-go="covercall">Simular un cover call real</button><button class="btn ghost" data-go="analisis">Analizar una acción</button></div></section>`;
    $('#kReal').onclick = e => { const b = e.target.closest('button'); if (b) { this.real = b.dataset.r === '1'; this.paintProj(); } };
    $('#kOut').onclick = e => { const g = e.target.closest('[data-go]'); if (g) OBB.go(g.dataset.go); };
  },
  goal() {
    const p = this.p;
    $('#kBody').innerHTML = `<div class="cc-grid"><section class="panel cyan"><h2>¿Cuánto necesito ahorrar?</h2><div class="cc-form">
      ${fld('k_income', 'Ingreso mensual deseado (dólares de hoy)', p.income, 'inputmode="decimal"')}${fld('k_years', 'Años para retirarte', p.years, 'inputmode="numeric"')}${fld('k_balance', 'Saldo actual ($)', p.balance, 'inputmode="decimal"')}
      ${fld('k_withdraw_rate', 'Retiro anual sostenible %', p.withdraw_rate, 'inputmode="decimal"')}${fld('k_inflation', 'Inflación %', p.inflation, 'inputmode="decimal"')}${fld('k_stock_return', 'Rendimiento acciones %', p.stock_return, 'inputmode="decimal"')}${fld('k_cash_rate', 'Interés efectivo %', p.cash_rate, 'inputmode="decimal"')}${fld('k_fee', 'Comisión %', p.fee, 'inputmode="decimal"')}</div>
      <div class="stack"><button class="btn green" id="gGo">Calcular</button></div></section><section id="gOut"></section></div>`;
    const run = async () => {
      const body = this.read(['income', 'years', 'balance', 'withdraw_rate', 'inflation', 'stock_return', 'cash_rate', 'fee']);
      try {
        const r = await api('/api/k401/goal', { method: 'POST', body }), c = r.scenarios.cash.monthly, s = r.scenarios.stocks.monthly;
        $('#gOut').innerHTML = `<section class="panel green"><h2>Resultado</h2><p>${esc(r.note)} Con inflación, en ${r.years} años serán <b>${money(r.need_future)}</b> futuros.</p>
        <div class="kpis"><div style="border-color:${C.red}"><span>Aporte mensual si lo dejas en efectivo (${r.scenarios.cash.rate}%)</span><b class="down">${money(c)}</b></div><div style="border-color:${C.green}"><span>Aporte mensual invirtiendo en acciones (${r.scenarios.stocks.rate}%)</span><b class="up">${money(s)}</b></div></div>
        <p>Invertir en vez de dejar el dinero quieto reduce lo que tienes que ahorrar cada mes en <b class="up">${money(c - s)}</b>.</p></section>`;
      } catch (e) { $('#gOut').innerHTML = `<div class="panel red"><h2>Revisa los datos</h2><p>${esc(e.message)}</p></div>`; }
    };
    $('#gGo').onclick = run; run();
  },
  fees() {
    const p = this.p;
    $('#kBody').innerHTML = `<div class="cc-grid"><section class="panel cyan"><h2>El costo de las comisiones</h2><div class="cc-form">
      ${fld('k_balance', 'Saldo actual ($)', p.balance, 'inputmode="decimal"')}${fld('k_monthly', 'Aporte mensual ($)', p.monthly, 'inputmode="decimal"')}${fld('k_years', 'Años', p.years, 'inputmode="numeric"')}${fld('k_stock_return', 'Rendimiento bruto %', p.stock_return, 'inputmode="decimal"')}${fld('k_fee_low', 'Comisión baja %', p.fee_low, 'inputmode="decimal"')}${fld('k_fee_high', 'Comisión alta %', p.fee_high, 'inputmode="decimal"')}</div>
      <div class="stack"><button class="btn green" id="fGo">Calcular</button></div><p class="note">Muchos fondos de 401(k) cobran 0.1 % o menos; otros cobran 1 % o más. Revisa el “expense ratio” de tus fondos.</p></section><section id="fOut"></section></div>`;
    const run = async () => {
      try {
        const r = await api('/api/k401/fees', { method: 'POST', body: this.read(['balance', 'monthly', 'years', 'stock_return', 'fee_low', 'fee_high']) });
        $('#fOut').innerHTML = `<section class="panel green"><h2>Resultado</h2><div class="kpis"><div style="border-color:${C.green}"><span>Con ${r.low.fee}% de comisión</span><b class="up">${money(r.low.final)}</b></div><div style="border-color:${C.red}"><span>Con ${r.high.fee}% de comisión</span><b class="down">${money(r.high.final)}</b></div></div>
        <p>La diferencia es <b class="down">${money(r.lost)}</b> (${r.lost_pct}% de tu resultado final) por pagar más comisión.</p></section>`;
      } catch (e) { $('#fOut').innerHTML = `<div class="panel red"><h2>Revisa los datos</h2><p>${esc(e.message)}</p></div>`; }
    };
    $('#fGo').onclick = run; run();
  },
  async hold() {
    const self = this, body = $('#kBody'); body.innerHTML = '<div class="empty">Cargando…</div>';
    let d; try { d = await api('/api/k401/holdings'); } catch (e) { return; }
    const tot = d.rows.reduce((a, r) => a + (r.price || 0) * r.shares, 0), cost = d.rows.reduce((a, r) => a + r.cost * r.shares, 0);
    const prem = +(this.p.cc_premium_month || 0.6), est = tot * prem / 100;
    body.innerHTML = `<section class="panel cyan"><h2>Mi cartera <small class="muted" style="font-size:12px;text-transform:none">${d.rows.length}/${d.max} posiciones</small></h2>
      <div class="bar"><input class="field" id="hSym" maxlength="6" placeholder="Símbolo" style="width:110px;text-transform:uppercase"><input class="field" id="hSh" inputmode="decimal" placeholder="Acciones" style="width:110px"><input class="field" id="hCost" inputmode="decimal" placeholder="Costo por acción" style="width:150px"><button class="btn green" id="hAdd">Guardar posición</button></div>
      ${d.rows.length ? `<div class="tbl-scroll" style="max-height:none;overflow-x:auto"><table class="t"><thead><tr><th>Símbolo</th><th class="r">Acciones</th><th class="r">Costo</th><th class="r">Precio</th><th class="r">Valor</th><th class="r">Ganancia</th><th class="r">%</th><th></th></tr></thead><tbody>${d.rows.map(r => { const v = (r.price || 0) * r.shares, g = v - r.cost * r.shares; return `<tr><td class="sym" data-an="${esc(r.symbol)}">${esc(r.symbol)}</td><td class="r">${fmtNum(r.shares)}</td><td class="r">${fmtNum(r.cost)}</td><td class="r">${fmtNum(r.price)}</td><td class="r">${money(v)}</td><td class="r ${cls(g)}">${money(g)}</td><td class="r">${tot ? (v / tot * 100).toFixed(0) + '%' : '—'}</td><td class="r"><button class="btn ghost" style="padding:2px 8px;font-size:12px" data-cc="${esc(r.symbol)}" data-px="${r.price || ''}" data-cost="${r.cost}" data-sh="${r.shares}" ${r.shares < 100 ? 'disabled title="Un contrato necesita 100 acciones"' : ''}>Cover Call</button> <button class="btn ghost" style="padding:2px 8px;font-size:12px" data-hdel="${esc(r.symbol)}" aria-label="Quitar">✕</button></td></tr>`; }).join('')}</tbody></table></div>
      <div class="kpis"><div><span>Valor total</span><b>${money(tot)}</b></div><div><span>Ganancia total</span><b class="${cls(tot - cost)}">${money(tot - cost)}</b></div><div><span>Ingreso mensual estimado con cover call (${prem}% de prima)</span><b class="up">${money(est)}</b></div></div>
      <div class="stack"><button class="btn" id="hUse">Usar ${money(tot)} como saldo inicial de la proyección</button></div><p class="note">El ingreso estimado es una aproximación con la prima mensual de tus supuestos; el real depende del strike y del mercado. Usa el módulo Cover Call para cifras reales. Un contrato = 100 acciones.</p>`
        : '<div class="empty">Agrega las acciones que tienes (o que quieres tener) para ver su valor y simular cover calls sobre ellas.</div>'}</section>`;
    body.onclick = async e => {
      try {
        if (e.target.id === 'hAdd') { await api('/api/k401/holdings', { method: 'POST', body: { symbol: $('#hSym').value, shares: $('#hSh').value, cost: $('#hCost').value } }); self.hold(); return; }
        const del = e.target.closest('[data-hdel]'); if (del) { await api('/api/k401/holdings/' + del.dataset.hdel, { method: 'DELETE' }); self.hold(); return; }
        const an = e.target.closest('[data-an]'); if (an) { OBB.state.symbol = an.dataset.an; OBB.go('analisis'); return; }
        const cc = e.target.closest('[data-cc]');
        if (cc) { OBB.cc = OBB.cc || {}; OBB.cc.calc = Object.assign(OBB.cc.calc || {}, { symbol: cc.dataset.cc, spot: String(Math.round(+cc.dataset.px * 100) / 100 || ''), cost: cc.dataset.cost, shares: String(Math.floor(+cc.dataset.sh / 100) * 100), mode: 'chain' }); OBB.cc.tab = 'calc'; OBB.go('covercall'); return; }
        if (e.target.id === 'hUse') { self.p.balance = String(Math.round(tot)); self.tab = 'proj'; self.paint(); }
      } catch (er) { toast(er.message, true); }
    };
  },
};

/* ------------------------------ Manual ------------------------------ */
function mdToHtml(md) {
  const inline = t => esc(t).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/\*([^*]+)\*/g, '<i>$1</i>');
  const lines = md.replace(/\r/g, '').split('\n'); let out = '', i = 0, list = null; const toc = [];
  const closeList = () => { if (list) { out += `</${list}>`; list = null; } };
  while (i < lines.length) {
    const l = lines[i];
    let m;
    if ((m = l.match(/^(#{1,3})\s+(.*)$/))) { closeList(); const n = m[1].length, id = 'h' + toc.length; if (n > 1) toc.push([n, id, m[2]]); out += `<h${n} id="${id}">${inline(m[2])}</h${n}>`; i++; continue; }
    if (/^\s*[-*]\s+/.test(l)) { if (list !== 'ul') { closeList(); out += '<ul>'; list = 'ul'; } out += `<li>${inline(l.replace(/^\s*[-*]\s+/, ''))}</li>`; i++; continue; }
    if (/^\s*\d+\.\s+/.test(l)) { if (list !== 'ol') { closeList(); out += '<ol>'; list = 'ol'; } out += `<li>${inline(l.replace(/^\s*\d+\.\s+/, ''))}</li>`; i++; continue; }
    if (/^\|/.test(l) && /^\|[\s:|-]+\|?\s*$/.test(lines[i + 1] || '')) {
      closeList(); const row = r => r.replace(/^\||\|\s*$/g, '').split('|').map(c => c.trim());
      const head = row(l); i += 2; let body = '';
      while (i < lines.length && /^\|/.test(lines[i])) { body += '<tr>' + row(lines[i]).map(c => `<td>${inline(c)}</td>`).join('') + '</tr>'; i++; }
      out += `<table class="t"><thead><tr>${head.map(c => `<th>${inline(c)}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table>`; continue;
    }
    if (/^>\s?/.test(l)) { closeList(); out += `<blockquote>${inline(l.replace(/^>\s?/, ''))}</blockquote>`; i++; continue; }
    if (/^---+\s*$/.test(l)) { closeList(); out += '<hr>'; i++; continue; }
    if (!l.trim()) { closeList(); i++; continue; }
    closeList(); out += `<p>${inline(l)}</p>`; i++;
  }
  closeList();
  return { html: out, toc };
}

OBB.views.manual = {
  async render(el) {
    el.innerHTML = `<div class="view-title"><h1>Manual de <span>usuario</span></h1><button class="btn ghost" id="mPrint" style="padding:4px 12px">Imprimir / guardar PDF</button></div><div class="manual panel cyan"><div class="empty">Cargando…</div></div>`;
    $('#mPrint').onclick = () => window.print();
    try {
      let r = OBB.lang === 'es' ? null : await fetch(`/manual.${OBB.lang}.md`, { credentials: 'same-origin' }).catch(() => null);   // manual traducido; si falta, el español
      if (!r || !r.ok) r = await fetch('/manual.md', { credentials: 'same-origin' });
      if (!r.ok) throw new Error('No se encontró el manual');
      const { html, toc } = mdToHtml(await r.text());
      $('.manual', el).innerHTML = `<nav class="mtoc"><b>Contenido</b>${toc.filter(t => t[0] === 2).map(t => `<a href="#manual" data-h="${t[1]}">${esc(t[2])}</a>`).join('')}</nav><article>${html}</article>`;
      el.onclick = e => { const a = e.target.closest('[data-h]'); if (a) { e.preventDefault(); const h = document.getElementById(a.dataset.h); if (h) h.scrollIntoView({ behavior: 'smooth' }); } };
    } catch (e) { $('.manual', el).innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  },
};
