/* Cover Call: calculadora de una operación y simulador mensual con recompra */
const CC_EXAMPLE = `strike bid ask delta volume oi
70 4.20 4.30 .58 100 900
71 3.65 3.75 .53 200 1200
72 3.15 3.25 .48 150 800
73 2.70 2.90 .43 90 400
74 2.35 2.45 .40 80 500
75 2.08 2.15 .36 300 1500
76 1.70 1.95 .32 20 60`;
const iso = d => d.toISOString().slice(0, 10);
const addDays = (s, n) => { const d = new Date(s + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return iso(d); };
function thirdFriday(y, m) { const d = new Date(Date.UTC(y, m, 1, 12)); const off = (5 - d.getUTCDay() + 7) % 7; d.setUTCDate(1 + off + 14); return iso(d); }
function nextMonthly(after) { // primer 3.er viernes posterior a `after` y al menos 20 días después
  let d = new Date(after + 'T12:00:00Z'); let y = d.getUTCFullYear(), m = d.getUTCMonth();
  for (let i = 0; i < 4; i++) { const f = thirdFriday(y, m); if (f > addDays(after, 20)) return f; m++; if (m > 11) { m = 0; y++; } }
  return addDays(after, 28);
}
const ord = n => n + '.º';
const money = n => fmtMoney(n);

OBB.cc = OBB.cc || { tab: 'calc', calc: null, sim: null, simRes: null };

function ccPayoffSVG(pay, spot, strike, be) {
  const W = 620, H = 230, L = 62, R = 14, T = 14, B = 30, pw = W - L - R, ph = H - T - B;
  const xs = pay.map(p => p.price), ys = pay.map(p => p.pl), x0 = Math.min(...xs), x1 = Math.max(...xs), lo = Math.min(0, ...ys), hi = Math.max(0, ...ys), pad = (hi - lo) * .12 || 1;
  const X = v => L + (v - x0) / (x1 - x0) * pw, Y = v => T + (hi + pad - v) / (hi - lo + 2 * pad) * ph;
  let o = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Ganancia o pérdida al vencimiento">`;
  for (let k = 0; k <= 4; k++) { const v = lo - pad + (hi - lo + 2 * pad) * k / 4; o += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="rgba(120,160,220,.16)"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#8fa6c9">${(v < 0 ? '−$' : '$') + nf0.format(Math.abs(Math.round(v)))}</text>`; }
  o += `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#6c86b3" stroke-dasharray="4 3"/>`;
  const pts = pay.map(p => `${X(p.price)},${Y(p.pl)}`).join(' ');
  o += `<polyline points="${pts}" fill="none" stroke="${C.green}" stroke-width="3"/>`;
  [[spot, 'Precio hoy', C.cyan], [strike, 'Strike', C.yellow], [be, 'Equilibrio', '#ff8c96']].forEach(([v, lbl, col], i) => {
    if (v < x0 || v > x1) return;
    o += `<line x1="${X(v)}" x2="${X(v)}" y1="${T}" y2="${H - B}" stroke="${col}" stroke-dasharray="5 4" stroke-width="1.6"/><text x="${X(v)}" y="${H - B + 13 + i * 12}" text-anchor="middle" font-size="11" font-weight="700" fill="${col}">${lbl} ${nf2.format(v)}</text>`;
  });
  return o + '</svg>';
}

function ccLines(series, rows) { // series: [{name,color,pts:[{x:label,y}]}]
  const W = 620, H = 240, L = 62, R = 14, T = 14, B = 30, pw = W - L - R, ph = H - T - B;
  const all = series.flatMap(s => s.pts.map(p => p.y)).concat(0), lo = Math.min(...all), hi = Math.max(...all), pad = (hi - lo) * .12 || 1;
  const n = Math.max(...series.map(s => s.pts.length)); const X = i => L + (n === 1 ? pw / 2 : i * pw / (n - 1)), Y = v => T + (hi + pad - v) / (hi - lo + 2 * pad) * ph;
  let o = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Evolución de la ganancia por mes">`;
  for (let k = 0; k <= 4; k++) { const v = lo - pad + (hi - lo + 2 * pad) * k / 4; o += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="rgba(120,160,220,.16)"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#8fa6c9">${(v < 0 ? '−$' : '$') + nf0.format(Math.abs(Math.round(v)))}</text>`; }
  o += `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#6c86b3" stroke-dasharray="4 3"/>`;
  (series[0] ? series[0].pts : []).forEach((p, i) => { o += `<text x="${X(i)}" y="${H - 10}" text-anchor="middle" font-size="11" fill="#8fa6c9">${esc(p.x)}</text>`; });
  series.forEach(s => {
    o += `<polyline points="${s.pts.map((p, i) => X(i) + ',' + Y(p.y)).join(' ')}" fill="none" stroke="${s.color}" stroke-width="2.6" ${s.dash ? 'stroke-dasharray="6 4"' : ''}/>`;
    s.pts.forEach((p, i) => { o += `<circle cx="${X(i)}" cy="${Y(p.y)}" r="3.6" fill="${s.color}"><title>${esc(s.name)} · ${esc(p.x)}: ${money(p.y)}</title></circle>`; });
  });
  return o + '</svg>';
}

OBB.views.covercall = {
  render(el) {
    const st = OBB.cc;
    el.innerHTML = `<div class="view-title"><h1>Cover <span>Call</span></h1><span class="muted">Vende calls sobre las acciones que ya tienes (100 acciones = 1 contrato)</span></div>
${ccCallout()}<div class="bar" style="margin-top:12px"><div class="seg" id="ccTabs"><button data-t="calc">Calculadora</button><button data-t="sim">Simulador mensual</button><button data-t="saved">Guardadas</button></div></div>
<div id="ccBody"></div>`;
    $('#ccTabs').onclick = e => { const b = e.target.closest('button'); if (b) { st.tab = b.dataset.t; this.paint(); } };
    this.paint();
  },
  paint() {
    const st = OBB.cc; $('#ccBody').onclick = null; $$('#ccTabs button').forEach(b => b.classList.toggle('on', b.dataset.t === st.tab));
    ({ calc: () => ccCalc($('#ccBody')), sim: () => ccSim($('#ccBody')), saved: () => ccSaved($('#ccBody')) })[st.tab]();
  },
};

/* ------------------------------ Calculadora ------------------------------ */
function ccCalc(el) {
  const today = iso(new Date());
  const s = OBB.cc.calc = OBB.cc.calc || { symbol: '', spot: '', cost: '', shares: 100, sell: today, expiry: nextMonthly(today), basis: 'bid', comm: '0', k: 5, mode: 'chain', text: '', strike: '', premium: '', pick: '' };
  const f = (id, label, val, extra = '') => `<div><label for="${id}">${label}</label><input class="field" id="${id}" value="${esc(val)}" ${extra}></div>`;
  el.innerHTML = `<div class="cc-grid">
<section class="panel cyan"><h2>Datos de la operación</h2>
  <div class="cc-form">
    ${f('c_symbol', 'Acción', s.symbol, 'maxlength="6" placeholder="NFLX" style="text-transform:uppercase"')}
    ${f('c_spot', 'Precio actual', s.spot, 'inputmode="decimal" placeholder="70.98"')}
    ${f('c_cost', 'Tu costo por acción', s.cost, 'inputmode="decimal" placeholder="igual al precio"')}
    ${f('c_shares', 'Acciones (múltiplos de 100)', s.shares, 'inputmode="numeric"')}
    ${f('c_sell', 'Fecha de venta', s.sell, 'type="date"')}
    ${f('c_exp', 'Vencimiento', s.expiry, 'type="date"')}
    ${f('c_comm', 'Comisión por contrato ($)', s.comm, 'inputmode="decimal"')}
    <div><label>Prima a cobrar</label><div class="seg" id="c_basis"><button data-v="bid" class="${s.basis === 'bid' ? 'on' : ''}" title="Conservador: lo que realmente pagan al instante">Bid</button><button data-v="mid" class="${s.basis === 'mid' ? 'on' : ''}" title="Punto medio entre bid y ask: lo habitual al poner una orden límite">Punto medio</button></div></div>
  </div>
  <div class="seg" id="c_mode" style="margin:12px 0 8px"><button data-v="chain" class="${s.mode === 'chain' ? 'on' : ''}">Con cadena de opciones</button><button data-v="manual" class="${s.mode === 'manual' ? 'on' : ''}">Un strike a mano</button></div>
  <div id="c_chainBox" class="${s.mode === 'chain' ? '' : 'hidden'}">
    <label for="c_text">Pega la cadena (columnas: Strike, Bid, Ask, y opcional Delta, Volumen, OI) — solo la parte de CALLS del vencimiento elegido</label>
    <textarea class="field mono" id="c_text" rows="9" placeholder="strike bid ask delta volume oi&#10;71 3.65 3.75 .53 200 1200">${esc(s.text)}</textarea>
    <div class="stack"><button class="btn ghost" id="c_ex">Cargar ejemplo (NFLX)</button></div>
    <label style="margin-top:10px">¿Qué strike vender? <span class="muted">(contando desde el primero sobre el precio)</span></label>
    <div class="stack" id="c_k">${[1, 2, 3, 5].map(k => `<button class="btn ghost ${s.k === k && !s.pick ? 'on' : ''}" data-k="${k}">${k === 1 ? '1.º (el inmediato)' : ord(k)}</button>`).join('')}<input class="field" id="c_kn" style="width:70px" inputmode="numeric" value="${s.k}" title="Número de strike por encima del precio"></div>
  </div>
  <div id="c_manualBox" class="cc-form ${s.mode === 'manual' ? '' : 'hidden'}" style="margin-top:6px">
    ${f('c_strike', 'Strike', s.strike, 'inputmode="decimal"')}${f('c_prem', 'Prima por acción', s.premium, 'inputmode="decimal"')}
  </div>
  <div class="stack"><button class="btn green" id="c_go">Calcular</button></div>
  <p class="note">Tip: en Thinkorswim abre Trade → cadena del vencimiento, selecciona las filas de Calls (Bid, Ask, Strike), cópialas y pégalas aquí. También puedes enviarme la captura y te transcribo la cadena.</p>
</section>
<section id="c_out"><div class="panel green"><h2>Resultado</h2><div class="empty">Completa los datos y pulsa <b>Calcular</b>.</div></div></section></div>`;
  const read = () => {
    s.symbol = $('#c_symbol').value.trim().toUpperCase(); s.spot = $('#c_spot').value; s.cost = $('#c_cost').value; s.shares = $('#c_shares').value;
    s.sell = $('#c_sell').value; s.expiry = $('#c_exp').value; s.comm = $('#c_comm').value; s.text = $('#c_text').value;
    s.strike = $('#c_strike').value; s.premium = $('#c_prem').value; s.k = Math.max(1, parseInt($('#c_kn').value) || 1);
  };
  $('#c_basis').onclick = e => { const b = e.target.closest('button'); if (b) { read(); s.basis = b.dataset.v; ccCalc(el); } };
  $('#c_mode').onclick = e => { const b = e.target.closest('button'); if (b) { read(); s.mode = b.dataset.v; s.pick = ''; ccCalc(el); } };
  $('#c_k').onclick = e => { const b = e.target.closest('[data-k]'); if (b) { read(); s.k = +b.dataset.k; s.pick = ''; ccCalc(el); if (s.spot && s.text) run(); } };
  $('#c_ex').onclick = () => { read(); Object.assign(s, { symbol: 'NFLX', spot: '70.98', cost: '70.98', text: CC_EXAMPLE, expiry: '2026-11-06', sell: '2026-10-09', mode: 'chain' }); ccCalc(el); toast('Ejemplo: los strikes 71 y 75 vienen de tu captura; completa o corrige los demás.'); };
  const run = async () => {
    read();
    const body = { spot: s.spot, cost: s.cost || undefined, shares: s.shares, sell_date: s.sell, expiry: s.expiry, basis: s.basis, commission: s.comm || 0, k: s.k };
    if (s.mode === 'chain') { body.chain_text = s.text; if (s.pick) body.strike = s.pick; } else { body.strike = s.strike; body.premium = s.premium; }
    try { paintCalc(await api('/api/cc/analyze', { method: 'POST', body })); } catch (e) { $('#c_out').innerHTML = `<div class="panel red"><h2>Revisa los datos</h2><p>${esc(e.message)}</p></div>`; }
  };
  $('#c_go').onclick = () => { s.pick = ''; run(); };
  el.onclick = e => { const r = e.target.closest('[data-pick]'); if (r) { s.pick = +r.dataset.pick; run(); } };
  const paintCalc = d => {
    const c = d.chosen, I = d.inputs, sym = s.symbol || 'la acción', ch = d.chain || [];
    const sh = I.shares, dteTxt = c.dte ? ` en ${c.dte} días` : '';
    const strikeName = c.ordinal_above ? ` (${ord(c.ordinal_above)} strike sobre el precio)` : '';
    let compare = '';
    const r1 = ch.find(r => r.ordinal_above === 1), r5 = ch.find(r => r.ordinal_above === 5);
    if (r1 && r5) {
      const cross = r1.strike + r1.premium - r5.premium;
      compare = `<section class="panel yellow"><h2>Comparación: ${ord(1)} vs ${ord(5)} strike</h2>
      <table class="t"><thead><tr><th></th><th class="r">Strike ${r1.strike}</th><th class="r">Strike ${r5.strike}</th></tr></thead><tbody>
      <tr><td>Prima</td><td class="r">${fmtNum(r1.premium)}</td><td class="r">${fmtNum(r5.premium)}</td></tr>
      <tr><td>Ganancia si te ejercen</td><td class="r up">${money(r1.max_profit)} <small>(${fmtPct(r1.max_profit_pct, false)})</small></td><td class="r up">${money(r5.max_profit)} <small>(${fmtPct(r5.max_profit_pct, false)})</small></td></tr>
      <tr><td>Ganancia si la acción no se mueve</td><td class="r">${money(r1.flat_profit)}</td><td class="r">${money(r5.flat_profit)}</td></tr>
      <tr><td>Debe subir para ejercerte</td><td class="r">${fmtPct(r1.distance_pct)}</td><td class="r">${fmtPct(r5.distance_pct)}</td></tr>
      <tr><td>Equilibrio</td><td class="r">${fmtNum(r1.breakeven)}</td><td class="r">${fmtNum(r5.breakeven)}</td></tr>
      <tr><td>Delta ≈ prob. de ejercicio</td><td class="r">${r1.delta == null ? '—' : r1.delta}</td><td class="r">${r5.delta == null ? '—' : r5.delta}</td></tr></tbody></table>
      <p class="note">Si al vencimiento ${esc(sym)} termina <b>sobre ${fmtNum(cross)}</b>, el ${ord(5)} strike deja más ganancia; si termina por debajo, gana el ${ord(1)}.</p></section>`;
    }
    $('#c_out').innerHTML = `
<section class="panel green"><h2>Resumen</h2>
  <ul class="cc-sum">
    <li>Vendes <b>${I.shares / 100} contrato(s) call ${c.strike}</b>${strikeName} y cobras <b>${fmtNum(c.premium)}</b> por acción = <b class="up">${money(c.credit)}</b> hoy${dteTxt}.</li>
    <li><b>Te ejercen</b> si ${esc(sym)} termina <b>por encima de ${fmtNum(c.assign_above)}</b> al vencimiento: debe subir ${fmtPct(c.distance_pct)} desde ${fmtNum(I.spot)}.</li>
    <li>Si te ejercen vendes a ${fmtNum(c.strike)} y tu ganancia máxima es <b class="${cls(c.max_profit)}">${money(c.max_profit)} (${fmtPct(c.max_profit_pct, false)})</b>${c.annualized_if_called_pct != null ? ` ≈ ${fmtPct(c.annualized_if_called_pct, false)} anualizado` : ''}.</li>
    <li>Si <b>no</b> te ejercen y la acción queda igual, ganas <b>${money(c.flat_profit)}</b> (${fmtPct(c.flat_profit_pct, false)}) y conservas las ${sh} acciones.</li>
    <li>Punto de equilibrio: <b>${fmtNum(c.breakeven)}</b> (la prima te protege ${fmtPct(c.downside_protection_pct, false)}). Bajo ese precio empiezas a perder.</li>
  </ul>
  ${d.warnings.map(w => `<div class="cc-warn">⚠ ${esc(w)}</div>`).join('')}
  <div class="cc-chart">${ccPayoffSVG(d.payoff, I.spot, c.strike, c.breakeven)}</div>
  <p class="note">Al vencimiento: tu ganancia sube con la acción hasta el strike y ahí se queda plana (ese es el costo de cobrar la prima). Se evalúa solo al vencimiento; el ejercicio anticipado es posible, sobre todo antes de dividendos.</p>
</section>${compare}
${ch.length ? `<section class="panel blue"><h2>Todos los strikes <small class="muted">(toca uno para calcularlo)</small></h2><div class="tbl-scroll" style="max-height:340px;overflow-x:auto"><table class="t"><thead><tr><th class="r">#</th><th class="r">Strike</th><th class="r">Bid</th><th class="r">Ask</th><th class="r">Delta</th><th class="r">Spread</th><th class="r">Prima %</th><th class="r">Gan. máx.</th><th class="r">%</th><th class="r">Equilibrio</th><th class="r">Sube</th></tr></thead><tbody>${ch.map(r => `<tr class="${r.recommended ? 'cc-sel' : ''} ${r.itm ? 'muted' : ''}" data-pick="${r.strike}" style="cursor:pointer"><td class="r">${r.ordinal_above || 'ITM'}</td><td class="r"><b>${r.strike}</b></td><td class="r">${fmtNum(r.bid)}</td><td class="r">${fmtNum(r.ask)}</td><td class="r">${r.delta == null ? '—' : r.delta}</td><td class="r ${r.liquid ? '' : 'down'}" title="${r.liquid ? 'Líquido' : 'Spread amplio o poco open interest'}">${r.spread_pct == null ? '—' : r.spread_pct.toFixed(0) + '%'}</td><td class="r">${fmtPct(r.premium_yield_pct, false)}</td><td class="r ${cls(r.max_profit)}">${money(r.max_profit)}</td><td class="r">${fmtPct(r.max_profit_pct, false)}</td><td class="r">${fmtNum(r.breakeven)}</td><td class="r">${fmtPct(r.distance_pct)}</td></tr>`).join('')}</tbody></table></div><p class="note">Spread en rojo = bid/ask muy separados o poco open interest: la prima real puede ser menor al bid mostrado.</p></section>` : ''}`;
  };
  if (s.spot && (s.text || s.strike)) run();
}

/* ------------------------------ Simulador ------------------------------ */
function ccSim(el) {
  const today = iso(new Date());
  const S = OBB.cc.sim = OBB.cc.sim || { symbol: '', shares: 100, cost: '', k: 5, basis: 'bid', comm: '0', rebuy: true, months: 6, start: today, cycles: null };
  const f = (id, label, val, extra = '') => `<div><label for="${id}">${label}</label><input class="field" id="${id}" value="${esc(val)}" ${extra}></div>`;
  el.innerHTML = `<section class="panel cyan"><h2>1 · Parámetros de la simulación</h2>
  <div class="cc-form">
    ${f('s_symbol', 'Acción', S.symbol, 'maxlength="6" placeholder="NFLX" style="text-transform:uppercase"')}
    ${f('s_shares', 'Acciones', S.shares, 'inputmode="numeric"')}
    ${f('s_cost', 'Costo inicial por acción', S.cost, 'inputmode="decimal" placeholder="= precio del mes 1"')}
    ${f('s_months', '¿Por cuántos meses simular? (1–36)', S.months, 'inputmode="numeric"')}
    ${f('s_start', 'Primera venta', S.start, 'type="date"')}
    ${f('s_comm', 'Comisión por contrato ($)', S.comm, 'inputmode="decimal"')}
    <div><label>Prima</label><div class="seg" id="s_basis"><button data-v="bid" class="${S.basis === 'bid' ? 'on' : ''}">Bid</button><button data-v="mid" class="${S.basis === 'mid' ? 'on' : ''}">Punto medio</button></div></div>
    <div><label>Strike a vender (regla por defecto)</label><div class="stack" style="margin:0"><select class="field" id="s_k">${[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(k => `<option value="${k}" ${S.k === k ? 'selected' : ''}>${k === 1 ? '1.º (inmediato superior)' : ord(k) + ' sobre el precio'}</option>`).join('')}</select></div></div>
    <div><label>Si te ejercen</label><label class="chk"><input type="checkbox" id="s_rebuy" ${S.rebuy ? 'checked' : ''}> Recomprar las ${esc(S.shares)} acciones al precio del mes siguiente y seguir vendiendo</label></div>
  </div>
  <div class="stack"><button class="btn green" id="s_make">${S.cycles ? 'Actualizar meses' : 'Crear los meses'}</button></div>
  <p class="note">Después te pido, mes a mes, la cadena de opciones del vencimiento y (si quieres) el strike que vendiste. Con el precio al vencimiento sabremos si te ejercieron.</p></section>
<div id="s_months_box"></div><div id="s_res"></div>`;
  const read = () => {
    S.symbol = $('#s_symbol').value.trim().toUpperCase(); S.shares = $('#s_shares').value; S.cost = $('#s_cost').value; S.months = $('#s_months').value;
    S.start = $('#s_start').value; S.comm = $('#s_comm').value; S.k = +$('#s_k').value; S.rebuy = $('#s_rebuy').checked;
  };
  $('#s_basis').onclick = e => { const b = e.target.closest('button'); if (b) { read(); S.basis = b.dataset.v; $$('#s_basis button').forEach(x => x.classList.toggle('on', x === b)); } };
  $('#s_make').onclick = () => {
    read(); const n = parseInt(S.months);
    if (!(n >= 1 && n <= 36)) return toast('Indica entre 1 y 36 meses', true);
    if (!S.start) return toast('Indica la fecha de la primera venta', true);
    const old = S.cycles || [], cy = [];
    for (let i = 0; i < n; i++) {
      const prev = cy[i - 1], sell = prev ? prev.expiry : S.start;
      cy.push(old[i] || { sell_date: sell, expiry: nextMonthly(sell), spot: '', text: '', strike: '', spot_at_expiry: '' });
    }
    S.cycles = cy; S.res = null; paintMonths();
  };
  const paintMonths = () => {
    const box = $('#s_months_box'); if (!S.cycles) { box.innerHTML = ''; $('#s_res').innerHTML = ''; return; }
    box.innerHTML = `<div class="view-title" style="margin-top:16px"><h1 style="font-size:20px">2 · Datos de cada <span>mes</span></h1><span class="muted">${S.cycles.length} mes(es) · pega la cadena de CALLS de cada vencimiento</span></div>` +
      S.cycles.map((c, i) => `<section class="panel ${i % 2 ? 'blue' : 'cyan'} cc-month" data-i="${i}"><h2>Mes ${i + 1}</h2>
      <div class="cc-form">
        <div><label>Fecha de venta</label><input class="field" data-f="sell_date" type="date" value="${esc(c.sell_date)}"></div>
        <div><label>Vencimiento</label><input class="field" data-f="expiry" type="date" value="${esc(c.expiry)}"></div>
        <div><label>Precio de la acción al vender</label><input class="field" data-f="spot" inputmode="decimal" value="${esc(c.spot)}" placeholder="70.98"></div>
        <div><label>Strike que vendiste <span class="muted">(vacío = regla por defecto)</span></label><input class="field" data-f="strike" inputmode="decimal" value="${esc(c.strike)}" placeholder="auto"></div>
        <div><label>Precio al vencimiento <span class="muted">(vacío = aún abierto)</span></label><input class="field" data-f="spot_at_expiry" inputmode="decimal" value="${esc(c.spot_at_expiry)}" placeholder="p. ej. 76.50"></div>
      </div>
      <label>Cadena de CALLS (strike, bid, ask, delta, volumen, OI)</label>
      <textarea class="field mono" data-f="text" rows="5" placeholder="strike bid ask delta volume oi">${esc(c.text)}</textarea>
      ${i === 0 ? '<div class="stack"><button class="btn ghost" data-ex="1">Cargar ejemplo en este mes</button></div>' : ''}</section>`).join('') +
      `<div class="stack" style="margin:14px 0"><button class="btn green" id="s_run">Simular</button><button class="btn" id="s_cmp">Comparar 1.º vs 5.º strike</button><button class="btn ghost" id="s_save">Guardar simulación</button></div>`;
    box.oninput = e => {
      const m = e.target.closest('.cc-month'), fld = e.target.dataset.f; if (!m || !fld) return;
      const i = +m.dataset.i; S.cycles[i][fld] = e.target.value;
      if (fld === 'expiry' && S.cycles[i + 1]) { /* la siguiente venta arranca en este vencimiento si no la tocaste */ }
      if (fld === 'spot_at_expiry') { const nx = S.cycles[i + 1]; if (nx && e.target.value) { const inp = $(`.cc-month[data-i="${i + 1}"] [data-f="spot"]`); if (!nx.spot && inp) { nx.spot = e.target.value; inp.value = e.target.value; } } }
    };
    box.onclick = e => {
      if (e.target.dataset.ex) { Object.assign(S.cycles[0], { text: CC_EXAMPLE, spot: '70.98', sell_date: '2026-10-09', expiry: '2026-11-06' }); if (!S.symbol) S.symbol = 'NFLX'; paintMonths(); return; }
      if (e.target.id === 's_run') run(false); if (e.target.id === 's_cmp') run(true); if (e.target.id === 's_save') save();
    };
  };
  const payload = (k, stripStrikes) => {
    read();
    return { params: { shares: S.shares, initial_cost: S.cost || undefined, k, basis: S.basis, commission: S.comm || 0, rebuy: S.rebuy },
      cycles: S.cycles.map(c => ({ sell_date: c.sell_date, expiry: c.expiry, spot: c.spot, chain_text: c.text, strike: stripStrikes ? '' : c.strike, spot_at_expiry: c.spot_at_expiry })) };
  };
  const run = async cmp => {
    const out = $('#s_res'); out.innerHTML = '<div class="empty">Calculando…</div>';
    try {
      if (!cmp) { const r = await api('/api/cc/simulate', { method: 'POST', body: payload(S.k, false) }); S.res = { one: r, k: S.k }; }
      else { const [a, b] = await Promise.all([1, 5].map(k => api('/api/cc/simulate', { method: 'POST', body: payload(k, true) }))); S.res = { cmp: { 1: a, 5: b } }; }
      paintRes();
    } catch (e) { out.innerHTML = `<div class="panel red"><h2>Revisa los datos</h2><p>${esc(e.message)}</p></div>`; out.scrollIntoView({ behavior: 'smooth' }); }
  };
  const chip = r => `<span class="chip ${r.status === 'ejercida' ? 'sell' : r.status === 'abierta' ? 'neutral' : 'buy'}">${r.status === 'ejercida' ? 'EJERCIDA' : r.status === 'abierta' ? 'ABIERTA' : 'NO EJERCIDA'}</span>`;
  const kpis = su => `<div class="kpis">
    <div><span>Ganancia total</span><b class="${cls(su.total_pl)}">${money(su.total_pl)}</b></div><div><span>Rendimiento</span><b class="${cls(su.return_pct)}">${fmtPct(su.return_pct)}</b></div>
    <div><span>Anualizado</span><b class="${cls(su.annualized_pct)}">${fmtPct(su.annualized_pct)}</b></div><div><span>Primas cobradas</span><b class="up">${money(su.total_premium)}</b></div>
    <div><span>Ejercidas</span><b>${su.assigned} de ${su.closed}</b></div><div><span>Solo mantener la acción</span><b class="${cls(su.buy_hold_pl)}">${money(su.buy_hold_pl)}</b></div>
    <div><span>Cover call vs mantener</span><b class="${cls(su.vs_buy_hold)}">${fmtMoney(su.vs_buy_hold)}</b></div><div><span>Mayor caída</span><b class="down">${money(-su.max_drawdown)}</b></div></div>`;
  const table = r => `<div class="tbl-scroll" style="max-height:none;overflow-x:auto"><table class="t"><thead><tr><th>Mes</th><th>Venta → Vence</th><th class="r">Acción</th><th class="r">Strike</th><th class="r">Prima</th><th>Resultado</th><th class="r">Al vencer</th><th class="r">Gan./pérd. del mes</th><th class="r">Acumulado</th></tr></thead><tbody>${r.rows.map(x => `<tr><td>${x.n}${x.rebought ? ' <span class="chip neutral" title="Recompraste las acciones a ' + fmtNum(x.spot) + '">RECOMPRA</span>' : ''}</td><td>${fmtDate(x.sell_date)} → ${fmtDate(x.expiry)}</td><td class="r">${fmtNum(x.spot)}</td><td class="r"><b>${x.strike}</b> <small class="muted">(${ord(x.ordinal_above)})</small></td><td class="r">${fmtNum(x.premium)} <small class="muted">${money(x.credit)}</small></td><td>${chip(x)}</td><td class="r">${x.spot_at_expiry == null ? '—' : fmtNum(x.spot_at_expiry)}</td><td class="r ${cls(x.cycle_pl)}">${money(x.cycle_pl)}</td><td class="r ${cls(x.equity)}">${money(x.equity)}</td></tr>`).join('')}</tbody></table></div>${r.warnings.map(w => `<div class="cc-warn">⚠ ${esc(w)}</div>`).join('')}`;
  const bhSeries = r => { const sh = +S.shares, init = +(S.cost || r.rows[0].spot); return { name: 'Solo mantener la acción', color: C.cyan, dash: true, pts: r.rows.map(x => ({ x: 'M' + x.n, y: ((x.spot_at_expiry == null ? x.spot : x.spot_at_expiry) - init) * sh })) }; };
  const paintRes = () => {
    const R = S.res, out = $('#s_res'); if (!R) { out.innerHTML = ''; return; }
    if (R.one) {
      const r = R.one;
      out.innerHTML = `<section class="panel green"><h2>Resultado · ${esc(S.symbol || 'acción')} · strike ${S.k === 1 ? 'inmediato superior' : ord(S.k) + ' sobre el precio'}</h2>${kpis(r.summary)}
        <div class="cc-chart">${ccLines([{ name: 'Cover call', color: C.green, pts: r.rows.map(x => ({ x: 'M' + x.n, y: x.equity })) }, bhSeries(r)], r.rows)}</div>
        <p class="note"><span style="color:${C.green}">━</span> Cover call · <span style="color:${C.cyan}">┅</span> solo mantener la acción</p>${table(r)}</section>`;
    } else {
      const a = R.cmp[1], b = R.cmp[5], best = a.summary.total_pl >= b.summary.total_pl ? 1 : 5;
      out.innerHTML = `<section class="panel yellow"><h2>Comparación · ${esc(S.symbol || 'acción')} · ${a.rows.length} mes(es)</h2>
        <table class="t"><thead><tr><th></th><th class="r">1.º strike (inmediato)</th><th class="r">5.º strike sobre el precio</th></tr></thead><tbody>
        ${[['Ganancia total', x => money(x.total_pl), x => cls(x.total_pl)], ['Rendimiento', x => fmtPct(x.return_pct), x => cls(x.return_pct)], ['Anualizado', x => fmtPct(x.annualized_pct), x => ''], ['Primas cobradas', x => money(x.total_premium), x => ''], ['Veces ejercida', x => `${x.assigned} de ${x.closed}`, x => ''], ['Subida que dejaste de ganar', x => money(x.missed_upside), x => ''], ['Mayor caída', x => money(-x.max_drawdown), x => 'down']].map(([l, fn, c]) => `<tr><td>${l}</td><td class="r ${c(a.summary)}">${fn(a.summary)}</td><td class="r ${c(b.summary)}">${fn(b.summary)}</td></tr>`).join('')}</tbody></table>
        <p class="note">En estos datos, el <b>${best === 1 ? '1.º strike' : '5.º strike'}</b> terminó mejor. Es solo este escenario: con otra trayectoria del precio puede cambiar. Se ignoran los strikes que fijaste a mano.</p>
        <div class="cc-chart">${ccLines([{ name: '1.º strike', color: C.yellow, pts: a.rows.map(x => ({ x: 'M' + x.n, y: x.equity })) }, { name: '5.º strike', color: C.green, pts: b.rows.map(x => ({ x: 'M' + x.n, y: x.equity })) }, bhSeries(a)], a.rows)}</div>
        <p class="note"><span style="color:${C.yellow}">━</span> 1.º · <span style="color:${C.green}">━</span> 5.º · <span style="color:${C.cyan}">┅</span> solo mantener la acción</p>
        <details><summary>Detalle mes a mes — 1.º strike</summary>${table(a)}</details><details><summary>Detalle mes a mes — 5.º strike</summary>${table(b)}</details></section>`;
    }
    out.scrollIntoView({ behavior: 'smooth' });
  };
  const save = async () => {
    const name = prompt('Nombre de la simulación', `${S.symbol || 'Cover call'} · ${S.cycles.length} meses`); if (!name) return;
    const p = payload(S.k, false); p.params.symbol = S.symbol; p.params.months = S.months; p.params.start = S.start; p.params.k = S.k; p.params.cost = S.cost;
    try { await api('/api/cc/sims', { method: 'POST', body: { name, ...p } }); toast('Simulación guardada'); } catch (e) { toast(e.message, true); }
  };
  paintMonths(); if (S.res) paintRes();
}

/* ------------------------------ Guardadas ------------------------------ */
async function ccSaved(el) {
  el.innerHTML = '<div class="empty">Cargando…</div>';
  const draw = async () => {
    const { sims } = await api('/api/cc/sims');
    el.innerHTML = `<section class="panel cyan"><h2>Simulaciones guardadas</h2>${sims.length ? `<table class="t"><thead><tr><th>Nombre</th><th>Guardada</th><th></th></tr></thead><tbody>${sims.map(s => `<tr><td>${esc(s.name)}</td><td>${fmtTs(s.created_at)}</td><td class="r"><button class="btn ghost" data-open="${s.id}" style="padding:3px 10px">Abrir</button> <button class="btn red" data-del="${s.id}" style="padding:3px 10px">Borrar</button></td></tr>`).join('')}</tbody></table>` : '<div class="empty">Aún no guardas ninguna. Crea una en “Simulador mensual”.</div>'}</section>`;
  };
  try { await draw(); } catch (e) { return toast(e.message, true); }
  el.onclick = async e => {
    const o = e.target.closest('[data-open]'), d = e.target.closest('[data-del]');
    try {
      if (o) {
        const s = await api('/api/cc/sims/' + o.dataset.open), p = s.params || {};
        OBB.cc.sim = { symbol: p.symbol || '', shares: p.shares || 100, cost: p.cost || '', k: p.k || 5, basis: p.basis || 'bid', comm: String(p.commission ?? '0'), rebuy: p.rebuy !== false, months: p.months || s.cycles.length, start: p.start || (s.cycles[0] || {}).sell_date,
          cycles: s.cycles.map(c => ({ sell_date: c.sell_date, expiry: c.expiry, spot: c.spot, text: c.chain_text || '', strike: c.strike || '', spot_at_expiry: c.spot_at_expiry ?? '' })) };
        OBB.cc.tab = 'sim'; OBB.views.covercall.render($('#main'));
      }
      if (d && confirm('¿Borrar esta simulación?')) { await api('/api/cc/sims/' + d.dataset.del, { method: 'DELETE' }); await draw(); }
    } catch (er) { toast(er.message, true); }
  };
}
