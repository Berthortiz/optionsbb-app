/* Mi ETF: 3 ETF de Optionsbb (fijos; el usuario solo cambia el monto) + ETF propios del usuario */
const PAL = ['#8ecae6', '#a8e6cf', '#ffd6a5', '#f7b7c4', '#cdb4f6', '#ffe99a', '#9ee0d6', '#b5c7f2', '#f9c6e7', '#d4e79e', '#9fd8f5', '#ffc9a8', '#c3e8b5', '#e6c9f0', '#a5d6c8', '#f3d1a1', '#b9d3ee', '#f5b8b8', '#d1e3b0', '#c7c0f0'];
const LOGO_DOMAINS = { MSFT: 'microsoft.com', AAPL: 'apple.com', GOOGL: 'google.com', GOOG: 'google.com', AMZN: 'amazon.com', META: 'meta.com', NVDA: 'nvidia.com', TSLA: 'tesla.com', AMD: 'amd.com', NFLX: 'netflix.com',
  JNJ: 'jnj.com', PG: 'pg.com', KO: 'coca-cola.com', PEP: 'pepsico.com', WMT: 'walmart.com', MCD: 'mcdonalds.com', COST: 'costco.com', VZ: 'verizon.com', DUK: 'duke-energy.com', SO: 'southerncompany.com',
  V: 'visa.com', JPM: 'jpmorganchase.com', HD: 'homedepot.com', UNH: 'unitedhealthgroup.com', LLY: 'lilly.com', AVGO: 'broadcom.com', COIN: 'coinbase.com', PLTR: 'palantir.com', HOOD: 'robinhood.com',
  AFRM: 'affirm.com', SOFI: 'sofi.com', MSTR: 'strategy.com', RIVN: 'rivian.com', BYND: 'beyondmeat.com', INTC: 'intel.com', ORCL: 'oracle.com', CRM: 'salesforce.com', ADBE: 'adobe.com', DIS: 'disney.com',
  BA: 'boeing.com', XOM: 'exxonmobil.com', CVX: 'chevron.com', PFE: 'pfizer.com', MRK: 'merck.com', ABBV: 'abbvie.com', T: 'att.com', IBM: 'ibm.com', CSCO: 'cisco.com', NKE: 'nike.com', SBUX: 'starbucks.com',
  BAC: 'bankofamerica.com', WFC: 'wellsfargo.com', GS: 'goldmansachs.com', MA: 'mastercard.com', PYPL: 'paypal.com', UBER: 'uber.com', ABNB: 'airbnb.com', SHOP: 'shopify.com', SNOW: 'snowflake.com', QCOM: 'qualcomm.com',
  MU: 'micron.com', TXN: 'ti.com', TGT: 'target.com', LOW: 'lowes.com', CAT: 'caterpillar.com', DE: 'deere.com', GE: 'ge.com', HON: 'honeywell.com', MMM: '3m.com', LMT: 'lockheedmartin.com', F: 'ford.com', GM: 'gm.com' };
const logoSources = sym => [`/logos/${encodeURIComponent(sym)}.png`, OBB.logo ? OBB.logo.replace('{SYM}', encodeURIComponent(sym)) : '', LOGO_DOMAINS[sym] ? `https://www.google.com/s2/favicons?domain=${LOGO_DOMAINS[sym]}&sz=128` : ''].filter(Boolean);

/* Gráfico circular (dona) con logo y % de cada acción */
function donutSVG(rows) {
  const R = 150, r = 84, cx = 180, cy = 180, mid = (R + r) / 2, tot = rows.reduce((a, x) => a + (x.value || 0), 0);
  if (!tot) return '<div class="empty">Agrega acciones para ver tu ETF.</div>';
  let a0 = -Math.PI / 2, o = `<svg viewBox="0 0 360 360" class="donut" role="img" aria-label="Composición del ETF">`;
  const pt = (rad, a) => [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
  const logos = [];
  rows.forEach((x, i) => {
    const w = (x.value || 0) / tot, a1 = a0 + w * Math.PI * 2, col = PAL[i % PAL.length], big = w > .5 ? 1 : 0;
    if (w >= .9999) o += `<circle cx="${cx}" cy="${cy}" r="${mid}" fill="none" stroke="${col}" stroke-width="${R - r}"><title>${esc(x.symbol)} ${(w * 100).toFixed(1)}%</title></circle>`;
    else if (w > 0) {
      const [x0, y0] = pt(R, a0), [x1, y1] = pt(R, a1), [x2, y2] = pt(r, a1), [x3, y3] = pt(r, a0);
      o += `<path d="M${x0},${y0} A${R},${R} 0 ${big} 1 ${x1},${y1} L${x2},${y2} A${r},${r} 0 ${big} 0 ${x3},${y3} Z" fill="${col}" stroke="#06122a" stroke-width="2"><title>${esc(x.symbol)} · ${(w * 100).toFixed(1)}% · ${fmtMoney(x.value)}</title></path>`;
    }
    if (w >= .035) logos.push({ x, w, col, am: (a0 + a1) / 2 });
    a0 = a1;
  });
  logos.forEach(({ x, w, col, am }) => {
    const [px, py] = pt(mid, am), src = logoSources(x.symbol);
    o += `<g class="lg" transform="translate(${px.toFixed(1)},${(py - 7).toFixed(1)})"><circle r="18" fill="#fff" stroke="#06122a" stroke-width="2"/><text class="lgt" y="3.5" text-anchor="middle" font-size="${x.symbol.length > 4 ? 7.5 : 9.5}" font-weight="900" fill="#13213f">${esc(x.symbol)}</text>
      ${src.length ? `<image class="lgi" data-sym="${esc(x.symbol)}" data-n="0" href="${esc(src[0])}" x="-13" y="-13" width="26" height="26" opacity="0" preserveAspectRatio="xMidYMid meet"/>` : ''}
      <text y="33" text-anchor="middle" font-size="12.5" font-weight="900" fill="#13213f" stroke="rgba(255,255,255,.85)" stroke-width="3" paint-order="stroke">${(w * 100).toFixed(w >= .1 ? 0 : 1)}%</text></g>`;
  });
  o += `<text x="${cx}" y="${cy - 6}" text-anchor="middle" font-size="13" fill="#9fb4d6">ETF</text><text x="${cx}" y="${cy + 18}" text-anchor="middle" font-size="22" font-weight="900" fill="#fff">${fmtMoney(tot).replace(/\.\d+$/, '')}</text></svg>`;
  return o;
}
/* Cadena de logos: carpeta local → LOGO_URL → favicon por dominio → siglas */
document.addEventListener('load', e => {
  const im = e.target; if (!im || !im.classList || !im.classList.contains('lgi')) return;
  im.setAttribute('opacity', 1); const tx = im.parentNode.querySelector('.lgt'); if (tx) tx.setAttribute('opacity', 0);
}, true);
document.addEventListener('error', e => {
  const im = e.target; if (!im || !im.classList || !im.classList.contains('lgi')) return;
  const src = logoSources(im.dataset.sym), n = +im.dataset.n + 1;
  if (n < src.length) { im.dataset.n = n; im.setAttribute('href', src[n]); }
}, true);

const stateChip = s => s === 'flat' ? '<span class="chip neutral st-flat" title="Se movió poco: el cover call rinde más cuando la acción se queda quieta">Sin movimiento</span>'
  : s === 'up' ? '<span class="chip neutral st-up">En movimiento ▲</span>' : s === 'down' ? '<span class="chip neutral st-down">En movimiento ▼</span>' : '<span class="muted">—</span>';

function etfPerfHtml(v) {
  const rows = v.rows || [];
  if (!rows.length) return '<div class="empty">Agrega acciones para ver cuánto habría rendido tu ETF con cover call.</div>';
  const tr = x => {
    if (x.state == null) return `<tr><td class="sym" data-sym="${esc(x.symbol)}">${esc(x.symbol)}</td><td colspan="8" class="muted">Sin historial suficiente</td></tr>`;
    const lots = x.lots >= 1 ? `${x.lots} contrato${x.lots > 1 ? 's' : ''}` : `<span class="down" title="Un contrato necesita 100 acciones">Faltan ${fmtNum(100 - x.shares)}</span>`;
    return `<tr><td class="sym" data-sym="${esc(x.symbol)}">${esc(x.symbol)}</td><td class="r">${x.weight == null ? '—' : x.weight.toFixed(1) + '%'}</td><td class="r">${fmtNum(x.shares)}</td><td class="r">${fmtMoney(x.value)}</td><td>${stateChip(x.state)}</td>
      <td class="r ${cls(x.stock_pnl)}">${signedMoney(x.stock_pnl)}<small class="sub">${fmtPct(x.stock_pct)}</small></td>
      <td class="r ${cls(x.overlay_pnl)}">${x.lots >= 1 ? signedMoney(x.overlay_pnl) : '—'}<small class="sub">${x.lots >= 1 ? fmtPct(x.overlay_pct) : ''}</small></td>
      <td class="r ${cls(x.total_pnl)}"><b>${signedMoney(x.total_pnl)}</b><small class="sub">${fmtPct(x.total_pct)}</small></td><td class="r">${lots}</td></tr>`;
  };
  const sum = (lbl, g, cl) => `<tr class="${cl}"><td colspan="5"><b>${lbl}</b> <small class="muted">(${g.n})</small></td><td class="r ${cls(g.stock_pnl)}">${signedMoney(g.stock_pnl)}<small class="sub">${fmtPct(g.stock_pct)}</small></td><td class="r ${cls(g.overlay_pnl)}">${signedMoney(g.overlay_pnl)}</td><td class="r ${cls(g.total_pnl)}"><b>${signedMoney(g.total_pnl)}</b><small class="sub">${fmtPct(g.total_pct)}</small></td><td></td></tr>`;
  return `<div class="tbl-scroll" style="max-height:none;overflow-x:auto"><table class="t etf-t"><thead><tr><th>Acción</th><th class="r">Peso</th><th class="r">Acciones</th><th class="r">Valor</th><th>Estado</th><th class="r">Sin cover call</th><th class="r">Cover call (ingreso)</th><th class="r">Suma de las 2</th><th class="r">Contratos</th></tr></thead>
    <tbody>${rows.map(tr).join('')}</tbody><tfoot>${sum('Sin movimiento', v.flat, 'tf')}${sum('En movimiento', v.moving, 'tf')}${sum('Total del ETF', v.total, 'tf tot')}</tfoot></table></div>
    <div class="insight">En ${v.days} días, el cover call habría aportado <b class="${cls(v.total.overlay_pnl)}">${signedMoney(v.total.overlay_pnl)}</b> a tu ETF
      (${signedMoney(v.flat.overlay_pnl)} en las acciones sin movimiento). Resultado total con cover call: <b class="${cls(v.total.total_pnl)}">${signedMoney(v.total.total_pnl)}</b> frente a <b class="${cls(v.total.stock_pnl)}">${signedMoney(v.total.stock_pnl)}</b> solo con las acciones.</div>
    <p class="note">Las primas son <b>estimadas</b> con un modelo (Black-Scholes con la volatilidad histórica de cada acción), vendiendo un call cada mes. Solo se cubren lotes de 100 acciones; si te ejercen, se asume que recompras al precio de vencimiento. Es historia/simulación: no garantiza resultados futuros. En modo DEMO los precios son simulados.</p>`;
}

const RISK_ETF = { low: ['Poco riesgo', 'green'], mid: ['Riesgo moderado', 'yellow'], high: ['Alto riesgo', 'red'] };

OBB.views.etf = {
  S: { off: [], list: [], cur: 'low', days: 90, otm: 5, iv: '', amount: {}, view: null, src: '', admin: false },
  async render(el) {
    const S = this.S, self = this; S.admin = OBB.state.user.role === 'admin';
    el.innerHTML = `<div class="view-title"><h1>Mi <span>ETF</span> Optionsbb</h1><span class="muted">Elige uno de los 3 ETF de Optionsbb o arma el tuyo: pesos, cantidad de acciones y rendimiento con y sin cover call</span></div>
    <div id="etfTabs" class="etf-pick"></div><div id="etfBody"><div class="empty">Cargando…</div></div>`;
    el.addEventListener('click', e => self.click(e));
    el.addEventListener('change', e => self.change(e));
    el.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.id === 'eSym') self.add(); });
    try { await this.reload(); } catch (e) { if (![401, 402, 403].includes(e.status)) toast(e.message, true); }
  },
  isOff() { return typeof this.S.cur === 'string'; },
  cur() { return this.S.list.find(x => x.id === this.S.cur); },
  curOff() { return this.S.off.find(x => x.key === this.S.cur); },
  async reload() {
    const S = this.S; S.off = (await api('/api/etfs/official')).etfs; S.list = (await api('/api/etfs')).etfs;
    S.off.forEach(e => { if (S.amount[e.key] == null) S.amount[e.key] = Math.max(100, Math.round(e.ref_value / 100) * 100); });
    if (!this.isOff() && !S.list.some(x => x.id === S.cur)) S.cur = 'low';
    this.paint(); await this.loadView();
  },
  async loadView() {
    const S = this.S; S.view = null;
    if (this.isOff()) {
      $('#etfPerf') && ($('#etfPerf').innerHTML = '<div class="empty">Calculando…</div>');
      try { S.view = await api(`/api/etfs/official/${S.cur}/view?amount=${S.amount[S.cur] || 0}&days=${S.days}&otm=${S.otm}&iv=${S.iv || 0}`); this.paintView(); } catch (e) { toast(e.message, true); }
      return;
    }
    const c = this.cur(); if (!c) return;
    if (!c.positions.length) { S.view = { rows: [], empty: true }; this.paintView(); return; }
    $('#etfPerf') && ($('#etfPerf').innerHTML = '<div class="empty">Calculando…</div>');
    try { S.view = await api(`/api/etfs/${c.id}/view?days=${S.days}&otm=${S.otm}&iv=${S.iv || 0}`); this.paintView(); } catch (e) { toast(e.message, true); }
  },
  perfPanel() {
    const S = this.S;
    return `${ccCallout()}<section class="panel yellow" style="margin-top:14px"><h2>Rendimiento por acción: sola vs con cover call</h2>
      <div class="bar"><label class="muted">Periodo</label><select class="field" id="ePer">${[[30, '30 días'], [90, '90 días'], [180, '180 días'], [360, '360 días']].map(([v, l]) => `<option value="${v}" ${S.days === v ? 'selected' : ''}>${l}</option>`).join('')}</select>
        <label class="muted">Call vendido a</label><input class="field" id="eOtm" type="number" min="0" max="50" step="0.5" value="${S.otm}" style="width:70px"><span class="muted">% fuera del dinero, cada mes</span>
        <label class="muted">Volatilidad (opcional)</label><input class="field" id="eIv" type="number" min="0" max="300" step="1" value="${S.iv}" placeholder="auto" style="width:80px"><span class="muted">%</span></div>
      <div id="etfPerf"><div class="empty">Cargando…</div></div></section>`;
  },
  paint() {
    const S = this.S, off = this.isOff();
    $('#etfTabs').innerHTML = `<div class="pk"><b>ETF Optionsbb</b><div class="seg">${S.off.map(e => `<button data-tab="${e.key}" class="${S.cur === e.key ? 'on' : ''}">${RISK_ETF[e.key][0]}</button>`).join('')}</div></div>
      <div class="pk"><b>Mis ETF</b><div class="seg">${S.list.map(x => `<button data-tab="${x.id}" class="${S.cur === x.id ? 'on' : ''}">${esc(x.name)}</button>`).join('') || '<span class="muted" style="padding:6px 10px">Aún no tienes</span>'}</div><button class="btn ghost" data-new>+ Nuevo ETF</button></div>`;
    if (off) {
      const e = this.curOff(), cl = RISK_ETF[e.key][1];
      $('#etfBody').innerHTML = `<div class="etf-grid"><section class="panel ${cl}"><h2>${esc(e.name)}</h2>
          <div class="bar"><label for="eAmt" class="muted">Monto a invertir ($)</label><input class="field" id="eAmt" type="number" min="100" step="100" value="${S.amount[e.key]}" style="width:130px"><button class="btn green" data-amt>Calcular</button></div>
          <div id="ePos"><div class="empty">Calculando…</div></div>
          <p class="note">Este ETF lo arma Optionsbb y no se modifica. Tú eliges cuánto invertir; las acciones se ajustan en la misma proporción. Para otra mezcla, crea tu propio ETF y agrégale acciones de este.</p>
          <div class="stack"><button class="btn ghost" data-clone>Crear mi ETF a partir de este</button>${S.admin ? '<button class="btn ghost" data-adm>Editar (administrador)</button>' : ''}</div><div id="eAdm"></div></section>
        <section class="panel cyan"><h2>Composición</h2><div id="eDonut"><div class="empty">Cargando…</div></div><div id="eLegend"></div></section></div>${this.perfPanel()}`;
    } else {
      const c = this.cur();
      $('#etfBody').innerHTML = `<div class="bar"><input class="field" id="eName" maxlength="60" value="${esc(c.name)}" style="width:230px" aria-label="Nombre del ETF"><button class="btn red" data-del style="padding:5px 12px" title="Borrar este ETF">Borrar</button></div>
        <div class="etf-grid"><section class="panel cyan"><h2>Construye tu ETF</h2>
          <div class="bar"><input class="field" id="eSym" maxlength="6" placeholder="Símbolo (ej. MSFT)" style="width:140px;text-transform:uppercase">
            <select class="field" id="eMode" aria-label="Cómo indicas la cantidad"><option value="shares">Acciones</option><option value="amount">Dólares ($)</option></select>
            <input class="field" id="eQty" type="number" min="0" step="any" placeholder="Cantidad" style="width:110px"><button class="btn green" data-add>Agregar</button></div>
          <div id="ePos">${this.posHtml(c)}</div>
          <details class="imp"><summary>Agregar acciones desde otro ETF</summary>${this.importHtml()}</details>
          <p class="note">Si indicas dólares, se convierten a acciones al precio actual. Máx. 20 acciones por ETF.</p></section>
        <section class="panel green"><h2>Composición</h2><div id="eDonut"><div class="empty">Cargando…</div></div><div id="eLegend"></div></section></div>${this.perfPanel()}`;
    }
  },
  posHtml(c) {
    if (!c.positions.length) return '<div class="empty">Tu ETF está vacío. Agrega la primera acción.</div>';
    return `<div class="tbl-scroll" style="max-height:320px"><table class="t"><thead><tr><th></th><th>Símbolo</th><th class="r">Acciones</th><th class="r">Costo ref.</th><th></th></tr></thead><tbody>${c.positions.map((p, i) => `<tr><td><i class="dot" style="background:${PAL[i % PAL.length]}"></i></td><td class="sym" data-sym="${esc(p.symbol)}">${esc(p.symbol)}</td><td class="r"><input class="field ePs" data-sym="${esc(p.symbol)}" type="number" min="0" step="any" value="${p.shares}" style="width:100px;text-align:right"></td><td class="r">${fmtNum(p.buy_price)}</td><td class="r"><button class="btn ghost" style="padding:2px 8px;font-size:12px" data-rm="${esc(p.symbol)}" aria-label="Quitar ${esc(p.symbol)}">✕</button></td></tr>`).join('')}</tbody></table></div>`;
  },
  importHtml() {
    const S = this.S, cur = this.cur();
    const opts = S.off.map(e => `<option value="o:${e.key}" ${S.src === 'o:' + e.key ? 'selected' : ''}>${esc(e.name)}</option>`).join('') + S.list.filter(x => cur && x.id !== cur.id).map(x => `<option value="c:${x.id}" ${S.src === 'c:' + x.id ? 'selected' : ''}>${esc(x.name)}</option>`).join('');
    const sel = this.srcPositions();
    return `<div class="bar" style="margin-top:8px"><select class="field" id="iSrc"><option value="">Elige un ETF…</option>${opts}</select>
      ${S.src.startsWith('o:') ? `<label class="muted" for="iAmt">Monto $</label><input class="field" id="iAmt" type="number" min="100" step="100" value="${S.amount[S.src.slice(2)] || 1000}" style="width:110px">` : ''}</div>
      ${sel.length ? `<div class="tbl-scroll" style="max-height:220px"><table class="t"><tbody>${sel.map(p => `<tr><td><input type="checkbox" class="iCk" data-sym="${esc(p.symbol)}" checked></td><td class="sym">${esc(p.symbol)}</td><td class="r">${fmtNum(p.shares)} acc.</td></tr>`).join('')}</tbody></table></div><div class="stack"><button class="btn green" data-iadd>Agregar seleccionadas</button></div>` : ''}`;
  },
  srcPositions() {
    const S = this.S; if (!S.src) return [];
    if (S.src.startsWith('c:')) { const x = S.list.find(v => v.id === +S.src.slice(2)); return x ? x.positions.map(p => ({ symbol: p.symbol, shares: p.shares })) : []; }
    const e = S.off.find(v => v.key === S.src.slice(2)); if (!e || !e.ref_value) return [];
    const k = (S.amount[e.key] || e.ref_value) / e.ref_value;
    return e.positions.map(p => ({ symbol: p.symbol, shares: Math.round(p.shares * k * 10000) / 10000 }));
  },
  paintView() {
    const v = this.S.view; if (!v) return;
    const rows = v.rows || [];
    if ($('#ePos')) $('#ePos').innerHTML = this.isOff() ? this.offPosHtml(v) : this.posHtml(this.cur());
    $('#eDonut') && ($('#eDonut').innerHTML = donutSVG(rows));
    $('#eLegend') && ($('#eLegend').innerHTML = rows.length ? `<div class="legend">${rows.map((x, i) => `<span><i class="dot" style="background:${PAL[i % PAL.length]}"></i><b>${esc(x.symbol)}</b> ${x.weight == null ? '' : x.weight.toFixed(1) + '%'} <small class="muted">${fmtMoney(x.value)}</small></span>`).join('')}</div>` : '');
    $('#etfPerf') && ($('#etfPerf').innerHTML = etfPerfHtml(v));
  },
  offPosHtml(v) {
    return `<div class="tbl-scroll" style="max-height:340px"><table class="t"><thead><tr><th></th><th>Símbolo</th><th class="r">Acciones</th><th class="r">Precio</th><th class="r">Valor</th><th class="r">Peso</th></tr></thead><tbody>${v.rows.map((x, i) => `<tr><td><i class="dot" style="background:${PAL[i % PAL.length]}"></i></td><td class="sym" data-sym="${esc(x.symbol)}">${esc(x.symbol)}</td><td class="r">${fmtNum(x.shares)}</td><td class="r">${fmtNum(x.price)}</td><td class="r">${fmtMoney(x.value)}</td><td class="r">${x.weight == null ? '—' : x.weight.toFixed(1) + '%'}</td></tr>`).join('')}</tbody></table></div>`;
  },
  async save(pos) {
    const c = this.cur();
    try { const d = await api('/api/etfs/' + c.id, { method: 'PUT', body: { name: c.name, positions: pos } }); c.positions = d.positions; this.paint(); await this.loadView(); }
    catch (e) { toast(e.message, true); this.paint(); this.paintView(); }
  },
  async add() {
    const sym = ($('#eSym').value || '').trim().toUpperCase(), q = parseFloat($('#eQty').value), mode = $('#eMode').value, c = this.cur();
    if (!sym) return toast('Escribe un símbolo', true);
    if (!(q > 0)) return toast('Indica una cantidad mayor que 0', true);
    const keep = c.positions.filter(p => p.symbol !== sym).map(p => ({ symbol: p.symbol, shares: p.shares, buy_price: p.buy_price }));
    keep.push(mode === 'amount' ? { symbol: sym, amount: q } : { symbol: sym, shares: q });
    await this.save(keep);
  },
  async click(e) {
    const S = this.S, t = e.target;
    const tab = t.closest('[data-tab]');
    if (tab) { const v = tab.dataset.tab; S.cur = ['low', 'mid', 'high'].includes(v) ? v : +v; S.view = null; this.paint(); return this.loadView(); }
    if (t.closest('[data-new]')) { try { const d = await api('/api/etfs', { method: 'POST', body: { name: 'Mi ETF ' + (S.list.length + 1) } }); S.cur = d.id; S.list = (await api('/api/etfs')).etfs; this.paint(); return this.loadView(); } catch (er) { return toast(er.message, true); } }
    if (t.closest('[data-amt]')) { const a = parseFloat($('#eAmt').value); if (!(a >= 100)) return toast('El monto mínimo es $100', true); S.amount[S.cur] = a; return this.loadView(); }
    if (t.closest('[data-clone]')) return this.clone();
    if (t.closest('[data-adm]')) return this.adminEditor();
    if (t.closest('[data-admsave]')) return this.adminSave();
    const c = this.cur();
    if (t.closest('[data-del]')) { if (!confirm(`¿Borrar “${c.name}”?`)) return; await api('/api/etfs/' + c.id, { method: 'DELETE' }); S.cur = 'low'; return this.reload(); }
    if (t.closest('[data-add]')) return this.add();
    const rm = t.closest('[data-rm]');
    if (rm) return this.save(c.positions.filter(p => p.symbol !== rm.dataset.rm));
    if (t.closest('[data-iadd]')) {
      const chosen = new Set($$('.iCk:checked').map(x => x.dataset.sym)), add = this.srcPositions().filter(p => chosen.has(p.symbol));
      if (!add.length) return toast('Marca al menos una acción', true);
      const map = new Map(c.positions.map(p => [p.symbol, { symbol: p.symbol, shares: p.shares, buy_price: p.buy_price }]));
      add.forEach(p => { const x = map.get(p.symbol); if (x) x.shares = Math.round((x.shares + p.shares) * 10000) / 10000; else map.set(p.symbol, { symbol: p.symbol, shares: p.shares }); });
      return this.save([...map.values()]);
    }
    const sym = t.closest('.sym[data-sym]');
    if (sym) { OBB.state.symbol = sym.dataset.sym; OBB.go('analisis'); }
  },
  async clone() {
    const S = this.S, e = this.curOff(), v = S.view; if (!v || !v.rows) return;
    try {
      const d = await api('/api/etfs', { method: 'POST', body: { name: `${e.name} (mío)`.slice(0, 60) } });
      await api('/api/etfs/' + d.id, { method: 'PUT', body: { name: `${e.name} (mío)`.slice(0, 60), positions: v.rows.map(r => ({ symbol: r.symbol, shares: r.shares })) } });
      S.list = (await api('/api/etfs')).etfs; S.cur = d.id; toast('Listo: ya puedes modificar tu copia'); this.paint(); await this.loadView();
    } catch (er) { toast(er.message, true); }
  },
  adminEditor() {
    const e = this.curOff(), box = $('#eAdm');
    box.innerHTML = `<div class="insight" style="margin-top:10px"><b>Editar ETF Optionsbb</b> <small class="muted">(solo administrador)</small>
      <label for="aName">Nombre</label><input class="field" id="aName" maxlength="60" value="${esc(e.name)}">
      <label for="aPos">Acciones (una por línea: SÍMBOLO acciones)</label><textarea class="field" id="aPos" rows="9">${e.positions.map(p => `${p.symbol} ${p.shares}`).join('\n')}</textarea>
      <div class="stack"><button class="btn green" data-admsave>Guardar</button></div></div>`;
  },
  async adminSave() {
    const S = this.S, pos = $('#aPos').value.split(/\n+/).map(l => l.trim()).filter(Boolean).map(l => { const [s, n] = l.split(/[\s,;:]+/); return { symbol: s, shares: +n }; });
    try { await api('/api/admin/official-etfs', { method: 'POST', body: { [S.cur]: { name: $('#aName').value, positions: pos } } }); toast('ETF actualizado'); await this.reload(); } catch (er) { toast(er.message, true); }
  },
  async change(e) {
    const S = this.S, t = e.target;
    if (t.id === 'ePer') { S.days = +t.value; return this.loadView(); }
    if (t.id === 'eOtm') { S.otm = Math.min(50, Math.max(0, parseFloat(t.value) || 0)); return this.loadView(); }
    if (t.id === 'eIv') { S.iv = t.value; return this.loadView(); }
    if (t.id === 'eAmt') { const a = parseFloat(t.value); if (a >= 100) { S.amount[S.cur] = a; return this.loadView(); } return; }
    if (t.id === 'iSrc') { S.src = t.value; const d = t.closest('details'); $('#etfBody details.imp').innerHTML = `<summary>Agregar acciones desde otro ETF</summary>${this.importHtml()}`; $('#etfBody details.imp').open = true; return; }
    if (t.id === 'iAmt') { const k = S.src.slice(2), a = parseFloat(t.value); if (a >= 100) { S.amount[k] = a; $('#etfBody details.imp').innerHTML = `<summary>Agregar acciones desde otro ETF</summary>${this.importHtml()}`; $('#etfBody details.imp').open = true; } return; }
    const c = this.cur(); if (!c) return;
    if (t.id === 'eName') { c.name = t.value.trim() || 'Mi ETF Optionsbb'; try { await api('/api/etfs/' + c.id, { method: 'PUT', body: { name: c.name, positions: c.positions } }); this.paint(); this.paintView(); } catch (er) { toast(er.message, true); } return; }
    if (t.classList.contains('ePs')) { const v = parseFloat(t.value); if (!(v > 0)) { toast('Cantidad no válida', true); return this.paint(); } return this.save(c.positions.map(p => p.symbol === t.dataset.sym ? { ...p, shares: v } : p)); }
  },
  destroy() { clearTimers(); },
};
