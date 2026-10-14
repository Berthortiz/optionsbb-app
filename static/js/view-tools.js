/* v3.0: Calculadora de opciones, Historial de earnings, Dividendos y Exposición gamma (GEX) */
(function () {
  const sgn = n => (n == null ? '—' : (n > 0 ? '+' : n < 0 ? '−' : '') + nf2.format(Math.abs(n)) + '%');
  const kpi = (label, val, c = '') => `<div class="kpi"><small>${label}</small><b class="${c}">${val}</b></div>`;
  const symBar = (id, val, go = 'Buscar') => `<div class="bar"><input class="field" id="${id}" maxlength="6" style="width:140px;text-transform:uppercase" value="${esc(val)}" aria-label="Símbolo"><button class="btn green" id="${id}Go">${go}</button></div>`;
  const errBox = (title, e) => `<div class="panel red"><h2>${title}</h2><p>${esc(e.message)}</p></div>`;
  const bigNum = n => { const a = Math.abs(n); const s = a >= 1e9 ? (a / 1e9).toFixed(2) + ' B' : a >= 1e6 ? (a / 1e6).toFixed(1) + ' M' : a >= 1e3 ? (a / 1e3).toFixed(0) + ' K' : a.toFixed(0); return (n < 0 ? '−$' : '$') + s; };

  /* ---------- gráfico de ganancia/pérdida ---------- */
  function pnlChart(r) {
    const W = 760, H = 300, L = 64, R = 14, T = 16, B = 30;
    const xs = r.x, all = r.expiry.concat(r.today);
    let lo = Math.min(...all, 0), hi = Math.max(...all, 0); const pad = (hi - lo) * .08 || 1; lo -= pad; hi += pad;
    const X = v => L + (v - xs[0]) / (xs[xs.length - 1] - xs[0]) * (W - L - R), Y = v => T + (hi - v) / (hi - lo) * (H - T - B);
    const path = a => a.map((v, i) => (i ? 'L' : 'M') + X(xs[i]).toFixed(1) + ' ' + Y(v).toFixed(1)).join('');
    const z = Y(0);
    const raw = (hi - lo) / 4, mag = Math.pow(10, Math.floor(Math.log10(raw))), st_ = [1, 2, 2.5, 5, 10].find(m => m * mag >= raw) * mag;
    const ticks = []; for (let v = Math.ceil(lo / st_) * st_; v <= hi; v += st_) ticks.push(v);
    return `<svg viewBox="0 0 ${W} ${H}" class="pnl" role="img" aria-label="Ganancia o pérdida según el precio">
      <defs><clipPath id="ca"><rect x="${L}" y="${T}" width="${W - L - R}" height="${Math.max(z - T, 0)}"/></clipPath><clipPath id="cb"><rect x="${L}" y="${z}" width="${W - L - R}" height="${Math.max(H - B - z, 0)}"/></clipPath></defs>
      ${ticks.map(v => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1f3558" stroke-width="1"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#9fb3d1">${bigNum(v)}</text>`).join('')}
      <line x1="${L}" x2="${W - R}" y1="${z}" y2="${z}" stroke="#7b8fb5" stroke-width="1.5"/>
      <path d="${path(r.expiry)}" fill="none" stroke="#35e08b" stroke-width="3" clip-path="url(#ca)"/><path d="${path(r.expiry)}" fill="none" stroke="#ff5a6a" stroke-width="3" clip-path="url(#cb)"/>
      <path d="${path(r.today)}" fill="none" stroke="#ffc933" stroke-width="2" stroke-dasharray="6 4"/>
      <line x1="${X(r.spot)}" x2="${X(r.spot)}" y1="${T}" y2="${H - B}" stroke="#38d6ff" stroke-dasharray="3 4"/><text x="${X(r.spot)}" y="${H - 10}" text-anchor="middle" font-size="11" fill="#38d6ff">precio ${nf2.format(r.spot)}</text>
      ${r.breakevens.map(b => `<circle cx="${X(b)}" cy="${z}" r="5" fill="#fff" stroke="#14325a" stroke-width="2"/><text x="${X(b)}" y="${z - 9}" text-anchor="middle" font-size="11" fill="#fff">${nf2.format(b)}</text>`).join('')}
      ${[0, 2, 4].map(i => { const v = xs[0] + (xs[xs.length - 1] - xs[0]) * i / 4; return `<text x="${X(v)}" y="${H - 10}" text-anchor="${i ? (i === 4 ? 'end' : 'middle') : 'start'}" font-size="11" fill="#9fb3d1" ${i === 2 ? 'opacity="0"' : ''}>${nf2.format(v)}</text>`; }).join('')}
    </svg><div class="legend"><span><i class="dot" style="background:#35e08b"></i>Al vencimiento (ganancia)</span><span><i class="dot" style="background:#ff5a6a"></i>Al vencimiento (pérdida)</span><span><i class="dot" style="background:#ffc933"></i>Hoy / en N días</span></div>`;
  }

  const TPL = [['long_call', 'Comprar call'], ['long_put', 'Comprar put'], ['covered_call', 'Cover call (100 acciones + call vendido)'], ['cash_secured_put', 'Put vendido con efectivo'],
    ['protective_put', 'Put protector (acciones + put)'], ['bull_call_spread', 'Spread alcista con calls'], ['bear_put_spread', 'Spread bajista con puts'], ['straddle', 'Straddle (call + put)'], ['iron_condor', 'Iron condor']];
  const TYPE = { C: 'Call', P: 'Put', S: 'Acción' };

  OBB.views.opciones = {
    async render(el) {
      const adv = OBB.state.user.plan === 'avanzado';
      const st = OBB.oc = OBB.oc || { symbol: 'AAPL', spot: '', iv: 35, dte: 30, template: 'covered_call', days: 0, mode: 'tpl', legs: [] };
      const draw = () => {
        el.innerHTML = `<div class="view-title"><h1>Calculadora de <span>opciones</span></h1><span class="muted">Ganancia y pérdida, equilibrio y griegas de tu estrategia</span></div>
        <section class="panel cyan"><div class="form-grid">
          ${fld('ocSym', 'Símbolo (opcional)', st.symbol, 'maxlength="6" style="text-transform:uppercase"')}${fld('ocSpot', 'Precio de la acción (vacío = actual)', st.spot, 'inputmode="decimal"')}
          ${fld('ocIv', 'Volatilidad implícita %', st.iv, 'inputmode="decimal"')}${fld('ocDte', 'Días al vencimiento', st.dte, 'inputmode="numeric"')}
          <div><label for="ocTpl">Estrategia</label><select class="field" id="ocTpl">${TPL.map(([k, n]) => `<option value="${k}" ${st.template === k ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
          ${adv ? `<div><label for="ocMode">Modo</label><select class="field" id="ocMode"><option value="tpl" ${st.mode === 'tpl' ? 'selected' : ''}>Plantilla</option><option value="free" ${st.mode === 'free' ? 'selected' : ''}>Patas libres (hasta 6)</option></select></div>` : ''}
        </div>
        ${st.mode === 'free' && adv ? legsEditor() : ''}
        <div class="stack"><button class="btn green" id="ocGo">Calcular</button></div><div class="err" id="ocErr" style="color:#ff8b95"></div></section><div id="ocOut"></div>
        <p class="muted">Las primas se estiman con Black-Scholes y la volatilidad que indiques (puedes escribir tu propia prima en el modo de patas libres). Es una simulación educativa, no una oferta ni asesoría.</p>`;
        $('#ocGo').onclick = run;
        $('#ocMode') && ($('#ocMode').onchange = e => { read(); st.mode = e.target.value; if (st.mode === 'free' && !st.legs.length && st.last) st.legs = st.last.legs.map(l => ({ ...l, premium: '' })); draw(); });
        $('#ocTpl').onchange = () => { st.template = $('#ocTpl').value; };
        $$('[data-rm]').forEach(b => b.onclick = () => { read(); st.legs.splice(+b.dataset.rm, 1); draw(); });
        $('#ocAdd') && ($('#ocAdd').onclick = () => { read(); if (st.legs.length >= 6) return toast('Máximo 6 patas', true); st.legs.push({ type: 'C', side: 1, strike: Math.round((+st.spot || 100)), qty: 1, dte: +st.dte || 30, premium: '' }); draw(); });
        if (st.last) paint(st.last);
      };
      const legsEditor = () => `<table class="tbl legs"><thead><tr><th>Tipo</th><th>Compra/Venta</th><th>Strike</th><th>Cantidad</th><th>Días</th><th>Prima (opc.)</th><th></th></tr></thead><tbody>
        ${st.legs.map((l, i) => `<tr data-i="${i}"><td><select class="field" data-k="type">${['C', 'P', 'S'].map(t => `<option value="${t}" ${l.type === t ? 'selected' : ''}>${TYPE[t]}</option>`).join('')}</select></td>
        <td><select class="field" data-k="side"><option value="1" ${l.side === 1 ? 'selected' : ''}>Compra</option><option value="-1" ${l.side === -1 ? 'selected' : ''}>Venta</option></select></td>
        <td><input class="field" data-k="strike" value="${esc(l.strike)}" size="7"></td><td><input class="field" data-k="qty" value="${esc(l.qty)}" size="5"></td><td><input class="field" data-k="dte" value="${esc(l.dte)}" size="4"></td>
        <td><input class="field" data-k="premium" value="${esc(l.premium ?? '')}" size="6" placeholder="auto"></td><td><button class="btn ghost" data-rm="${i}" style="padding:2px 9px">✕</button></td></tr>`).join('')}</tbody></table>
        <button class="btn ghost" id="ocAdd" style="margin:6px 0">+ Agregar pata</button><p class="muted">Para una acción, el «strike» es tu precio de compra y la cantidad son acciones (no contratos).</p>`;
      const read = () => {
        st.symbol = ($('#ocSym').value || '').trim().toUpperCase(); st.spot = $('#ocSpot').value.trim(); st.iv = $('#ocIv').value; st.dte = $('#ocDte').value; st.template = $('#ocTpl').value;
        if (st.mode === 'free') st.legs = $$('tr[data-i]').map(tr => { const o = {}; $$('[data-k]', tr).forEach(x => o[x.dataset.k] = x.value); return { type: o.type, side: +o.side, strike: +o.strike, qty: +o.qty, dte: +o.dte, premium: o.premium === '' ? null : +o.premium }; });
      };
      const run = async () => {
        read(); $('#ocErr').textContent = '';
        const body = { symbol: st.symbol, spot: st.spot, iv: (+st.iv || 35) / 100, dte: +st.dte || 30, days_ahead: +st.days || 0 };
        if (st.mode === 'free') body.legs = st.legs; else body.template = st.template;
        try { st.last = await api('/api/opcalc', { method: 'POST', body }); paint(st.last); } catch (e) { $('#ocErr').textContent = e.message; }
      };
      const paint = r => {
        const g = r.greeks, net = r.net;
        $('#ocOut').innerHTML = `<section class="panel green"><h2>Resultado${r.symbol ? ' · ' + esc(r.symbol) : ''}</h2>
          <div class="kpis">${kpi(net >= 0 ? 'Débito (pagas)' : 'Crédito (cobras)', fmtMoney(Math.abs(net)), net >= 0 ? 'down' : 'up')}${kpi('Ganancia máxima', r.max_profit == null ? 'Ilimitada' : fmtMoney(r.max_profit), 'up')}
          ${kpi('Pérdida máxima', r.max_loss == null ? 'Ilimitada' : fmtMoney(r.max_loss), 'down')}${kpi('Punto(s) de equilibrio', r.breakevens.length ? r.breakevens.map(b => nf2.format(b)).join(' / ') : '—')}
          ${kpi('Probabilidad de ganar', r.prob_profit == null ? '—' : (r.prob_profit * 100).toFixed(0) + '%')}</div>
          ${pnlChart(r)}
          <div class="bar"><label for="ocDays">Ver la curva de «hoy» dentro de</label><input type="range" id="ocDays" min="0" max="${Math.max(...r.legs.filter(l => l.type !== 'S').map(l => l.dte), 1)}" value="${st.days}" style="width:200px"><b id="ocDaysV">${st.days} día(s)</b></div>
          <h3>Griegas de la posición</h3><div class="kpis">${kpi('Delta', nf2.format(g.delta))}${kpi('Gamma', nf2.format(g.gamma))}${kpi('Theta por día', fmtMoney(g.theta))}${kpi('Vega por 1% vol.', fmtMoney(g.vega))}</div>
          <table class="tbl"><thead><tr><th>Pata</th><th>Strike</th><th>Cantidad</th><th>Días</th><th>Prima</th></tr></thead><tbody>${r.legs.map(l => `<tr><td>${l.side > 0 ? 'Compra' : 'Venta'} ${TYPE[l.type]}</td><td>${nf2.format(l.strike)}</td><td>${l.qty}</td><td>${l.dte || '—'}</td><td>${l.type === 'S' ? '—' : nf2.format(l.premium)}</td></tr>`).join('')}</tbody></table></section>`;
        $('#ocDays').oninput = e => { $('#ocDaysV').textContent = e.target.value + ' día(s)'; };
        $('#ocDays').onchange = e => { st.days = +e.target.value; run(); };
      };
      draw();
    },
  };

  /* ---------- Earnings (últimos 12 reportes, con tendencia) ---------- */
  const EMET = { day: ['Día del reporte', 'day_pct'], gap: ['Gap de apertura', 'gap_pct'], range: ['Rango del día', 'range_pct'], next: ['Día siguiente', 'next_pct'] };
  const mean = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0;
  const mmYY = d => d.slice(5, 7) + '/' + d.slice(2, 4);

  function earnChart(rows, key, hi) {
    const W = 760, H = 270, L = 44, R = 10, T = 16, B = 34, pw = W - L - R, ph = H - T - B, n = rows.length;
    const vals = rows.map(r => r[key] == null ? 0 : r[key]), signed = key !== 'range';
    const m = Math.max(...vals.map(Math.abs), 1) * 1.18, lo = signed ? -m : 0, hh = m;
    const X = i => L + (i + .5) * pw / n, Y = v => T + (hh - v) / (hh - lo) * ph, bw = Math.min(46, pw / n * .6);
    const avg = mean(vals.map(Math.abs));
    const ticks = signed ? [-m, -m / 2, 0, m / 2, m] : [0, m / 3, 2 * m / 3, m];
    const band = signed ? `<rect x="${L}" y="${Y(avg)}" width="${pw}" height="${Y(-avg) - Y(avg)}" fill="rgba(46,200,255,.09)"/><line x1="${L}" x2="${W - R}" y1="${Y(avg)}" y2="${Y(avg)}" stroke="#2ec8ff" stroke-dasharray="4 4" opacity=".7"/><line x1="${L}" x2="${W - R}" y1="${Y(-avg)}" y2="${Y(-avg)}" stroke="#2ec8ff" stroke-dasharray="4 4" opacity=".7"/><text x="${L + 4}" y="${Y(avg) - 4}" font-size="11" fill="#2ec8ff">±${nf2.format(avg)}% típico</text>`
      : `<line x1="${L}" x2="${W - R}" y1="${Y(avg)}" y2="${Y(avg)}" stroke="#2ec8ff" stroke-dasharray="4 4" opacity=".7"/><text x="${L + 4}" y="${Y(avg) - 4}" font-size="11" fill="#2ec8ff">promedio ${nf2.format(avg)}%</text>`;
    return `<svg viewBox="0 0 ${W} ${H}" class="pnl" role="img" aria-label="Movimiento en cada reporte">
      ${ticks.map(v => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1f3558"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#9fb3d1">${nf2.format(v)}%</text>`).join('')}
      ${band}<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#7b8fb5" stroke-width="1.4"/>
      ${rows.map((r, i) => { const v = vals[i], y0 = Y(0), y1 = Y(v), col = !signed ? '#38d6ff' : v >= 0 ? '#35e08b' : '#ff5a6a', top = Math.min(y0, y1), h = Math.max(Math.abs(y1 - y0), 2);
        return `<g class="ebar ${hi === i ? 'hi' : ''}" data-ei="${i}"><title>${fmtDate(r.date)} · ${sgn(v)}</title><rect x="${X(i) - pw / n / 2}" y="${T}" width="${pw / n}" height="${ph}" fill="transparent"/>
        <rect x="${X(i) - bw / 2}" y="${top}" width="${bw}" height="${h}" rx="3" fill="${col}" fill-opacity=".85" stroke="${col}"/>
        <text x="${X(i)}" y="${v >= 0 || !signed ? top - 4 : top + h + 11}" text-anchor="middle" font-size="10.5" fill="#dbe8ff">${sgn(v).replace('%', '')}</text>
        <text x="${X(i)}" y="${H - 14}" text-anchor="middle" font-size="10.5" fill="#9fb3d1">${mmYY(r.date)}</text>
        <text x="${X(i)}" y="${H - 3}" text-anchor="middle" font-size="9" fill="#6f86ab">${r.hour === 'bmo' ? 'antes' : r.hour === 'amc' ? 'después' : ''}</text></g>`; }).join('')}
    </svg>`;
  }

  function trendChart(rows, tr, key) {
    const W = 760, H = 190, L = 44, R = 10, T = 14, B = 26, pw = W - L - R, ph = H - T - B, n = rows.length;
    const ab = rows.map(r => Math.abs(r[key] == null ? 0 : r[key])), ma = ab.map((_, i) => mean(ab.slice(Math.max(0, i - 2), i + 1)));
    const mx = Math.max(...ab, 1) * 1.15, X = i => L + (i + .5) * pw / n, Y = v => T + (mx - v) / mx * ph;
    const my = mean(ab), sl = n > 2 ? (() => { const mxi = (n - 1) / 2; let num = 0, den = 0; ab.forEach((y, i) => { num += (i - mxi) * (y - my); den += (i - mxi) ** 2; }); return den ? num / den : 0; })() : 0;
    const reg = i => my + sl * (i - (n - 1) / 2), path = (f) => rows.map((_, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(f(i)).toFixed(1)).join('');
    const dir = sl > 0.03 ? ['sube', '#ff5a6a'] : sl < -0.03 ? ['baja', '#35e08b'] : ['se mantiene', '#ffc933'];
    return `<svg viewBox="0 0 ${W} ${H}" class="pnl" role="img" aria-label="Tendencia del tamaño del movimiento">
      ${[0, mx / 2, mx].map(v => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1f3558"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#9fb3d1">${nf2.format(v)}%</text>`).join('')}
      <path d="${path(reg)}" fill="none" stroke="#2ec8ff" stroke-width="2" stroke-dasharray="6 5"/>
      <path d="${path(i => ma[i])}" fill="none" stroke="#ffc933" stroke-width="2.6"/>
      ${ab.map((v, i) => `<circle cx="${X(i)}" cy="${Y(v)}" r="4.5" fill="#0a1d3d" stroke="#fff" stroke-width="1.6"><title>${fmtDate(rows[i].date)} · ±${nf2.format(v)}%</title></circle><text x="${X(i)}" y="${H - 8}" text-anchor="middle" font-size="10.5" fill="#9fb3d1">${mmYY(rows[i].date)}</text>`).join('')}
    </svg><div class="legend"><span><i class="dot" style="background:#fff"></i>Tamaño de cada reporte</span><span><i class="dot" style="background:#ffc933"></i>Promedio móvil (3)</span><span><i class="dot" style="background:#2ec8ff"></i>Tendencia: <b style="color:${dir[1]}">${dir[0]}</b></span></div>`;
  }

  function epsChart(rows) {
    const d = rows.filter(r => r.eps != null && r.eps_est != null); if (d.length < 3) return '';
    const W = 760, H = 210, L = 46, R = 10, T = 22, B = 26, pw = W - L - R, ph = H - T - B, n = d.length;
    const all = d.flatMap(r => [r.eps, r.eps_est]), lo0 = Math.min(...all), hi0 = Math.max(...all), pad = (hi0 - lo0) * .15 || .1, lo = lo0 - pad, hi = hi0 + pad;
    const X = i => L + (i + .5) * pw / n, Y = v => T + (hi - v) / (hi - lo) * ph;
    return `<svg viewBox="0 0 ${W} ${H}" class="pnl" role="img" aria-label="EPS real contra estimado">
      ${[lo, (lo + hi) / 2, hi].map(v => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1f3558"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#9fb3d1">$${nf2.format(v)}</text>`).join('')}
      ${d.map((r, i) => { const beat = r.eps >= r.eps_est, c = beat ? '#35e08b' : '#ff5a6a'; return `<g><title>${fmtDate(r.date)} · estimado $${nf2.format(r.eps_est)} · real $${nf2.format(r.eps)} (${sgn(r.surprise_pct)})</title>
        <line x1="${X(i)}" x2="${X(i)}" y1="${Y(r.eps_est)}" y2="${Y(r.eps)}" stroke="${c}" stroke-width="3"/>
        <circle cx="${X(i)}" cy="${Y(r.eps_est)}" r="5" fill="none" stroke="#9fb3d1" stroke-width="2"/><circle cx="${X(i)}" cy="${Y(r.eps)}" r="6" fill="${c}"/>
        <text x="${X(i)}" y="${Y(Math.max(r.eps, r.eps_est)) - 10}" text-anchor="middle" font-size="10.5" fill="${c}">${sgn(r.surprise_pct)}</text>
        <text x="${X(i)}" y="${H - 8}" text-anchor="middle" font-size="10.5" fill="#9fb3d1">${mmYY(r.date)}</text></g>`; }).join('')}
    </svg><div class="legend"><span><i class="dot" style="background:none;border:2px solid #9fb3d1"></i>EPS estimado</span><span><i class="dot" style="background:#35e08b"></i>Superó</span><span><i class="dot" style="background:#ff5a6a"></i>Quedó por debajo</span></div>`;
  }

  OBB.views.earnings = {
    metric: 'day',
    async render(el) {
      const st = OBB.state, self = this; let data = null, hi = -1;
      el.innerHTML = `<div class="view-title"><h1>Historial de <span>earnings</span></h1><span class="muted">Últimos 12 reportes: cómo se movió el precio y hacia dónde va la tendencia</span></div>${symBar('eSym', st.symbol)}<div id="eBody"><div class="empty">Elige una acción</div></div>`;
      const go = async () => {
        const sy = ($('#eSym').value || '').trim().toUpperCase(); if (!sy) return; st.symbol = sy; $('#eBody').innerHTML = '<div class="empty">Calculando…</div>';
        try { data = await api('/api/earnings?symbol=' + encodeURIComponent(sy)); paint(); } catch (e) { $('#eBody').innerHTML = errBox('No pude traer los earnings de ' + esc(sy), e); }
      };
      const paint = () => {
        const d = data, s = d.summary, tr = d.trend, rows = d.rows.slice().reverse(), key = EMET[self.metric][1];
        const when = h => ({ bmo: 'Antes de apertura', amc: 'Después del cierre', dmh: 'Durante el mercado' }[h] || '—');
        const mxAbs = Math.max(...rows.map(r => Math.abs(r.day_pct)), 1);
        const volTxt = !tr ? '' : tr.vol === 'up' ? `<b class="down">▲ Más movimiento:</b> los últimos 4 reportes movieron ±${tr.recent_avg}% en promedio, contra ±${tr.older_avg}% de los 8 anteriores.`
          : tr.vol === 'down' ? `<b class="up">▼ Más calma:</b> los últimos 4 reportes movieron ±${tr.recent_avg}% en promedio, contra ±${tr.older_avg}% de los 8 anteriores.`
            : `<b>● Movimiento estable:</b> los últimos 4 reportes movieron ±${tr.recent_avg}%, similar a los 8 anteriores (±${tr.older_avg}%).`;
        const ins = !tr ? '' : `<div class="insight">${volTxt}<br>Subió en el <b>${tr.up_rate}%</b> de los reportes · racha actual: <b class="${tr.streak_dir === 'up' ? 'up' : 'down'}">${tr.streak} ${tr.streak_dir === 'up' ? 'al alza' : 'a la baja'}</b>.
          ${tr.beat_rate != null ? `<br>Superó el estimado de ganancias en el <b>${tr.beat_rate}%</b> de los reportes${tr.after_beat_avg != null ? ` · reacción media si supera: <b class="${cls(tr.after_beat_avg)}">${sgn(tr.after_beat_avg)}</b>` : ''}${tr.after_miss_avg != null ? ` · si no supera: <b class="${cls(tr.after_miss_avg)}">${sgn(tr.after_miss_avg)}</b>` : ''}.` : ''}</div>`;
        const hs = d.hist, hmax = Math.max(...hs.counts, 1);
        $('#eBody').innerHTML = `${d.demo ? '<div class="banner">Datos simulados (modo DEMO): las fechas, los movimientos y el EPS no son reales.</div>' : ''}
        ${d.upcoming ? `<div class="callout"><b>Próximo reporte:</b> ${fmtDate(d.upcoming.date)} · ${when(d.upcoming.hour)}${s ? ` · el mercado suele moverla <b>±${s.avg_abs_day}%</b> ese día` : ''}</div>` : ''}
        ${s ? `<section class="panel cyan"><h2>Resumen · últimos ${s.count} reportes</h2><div class="kpis">${kpi('Movimiento medio (día)', '±' + s.avg_abs_day + '%')}${kpi('Gap medio de apertura', '±' + s.avg_abs_gap + '%')}${kpi('Mediana', '±' + s.median_abs_day + '%')}
        ${kpi('Subió / bajó', `<span class="up">${s.up}</span>&nbsp;/&nbsp;<span class="down">${s.down}</span>`)}${kpi('Mejor', sgn(s.best), 'up')}${kpi('Peor', sgn(s.worst), 'down')}${kpi('Rango medio del día', s.avg_range + '%')}</div>${ins}</section>` : ''}
        <section class="panel yellow"><h2>Movimiento en cada reporte</h2><div class="seg" id="eMet">${Object.entries(EMET).map(([k, v]) => `<button data-m="${k}" class="${k === self.metric ? 'on' : ''}">${v[0]}</button>`).join('')}</div>${earnChart(rows, key, hi)}
          <p class="muted">La franja azul marca el movimiento típico (promedio de los 12). Pasa el cursor por una barra para ver la fecha.</p></section>
        <section class="panel cyan"><h2>¿Se mueve más o menos con el tiempo?</h2>${trendChart(rows, tr, key)}</section>
        <section class="panel"><h2>Qué tan seguido ocurre cada movimiento</h2><div class="hist">${hs.labels.map((l, i) => `<div class="hb"><span class="hv">${hs.counts[i] || ''}</span><i class="${i < 4 ? 'ebd' : 'ebu'}" style="height:${hs.counts[i] / hmax * 100}%"></i><small>${l}</small></div>`).join('')}</div>
          <p class="muted">Cantidad de reportes en cada rango de movimiento del día.</p></section>
        ${epsChart(rows) ? `<section class="panel green"><h2>Ganancias por acción (EPS): real contra estimado</h2>${epsChart(rows)}</section>` : ''}
        <section class="panel"><h2>Detalle de los 12 reportes</h2><div class="tscroll"><table class="tbl"><thead><tr><th>Fecha</th><th>Hora</th><th>Gap</th><th>Día</th><th class="r">Movimiento</th><th>Rango</th><th>Día siguiente</th><th>EPS real / est.</th></tr></thead><tbody>
        ${d.rows.map(r => { const i = rows.length - 1 - d.rows.indexOf(r); return `<tr data-ei="${i}" class="${hi === i ? 'hirow' : ''}"><td>${fmtDate(r.date)}</td><td>${when(r.hour)}</td><td class="${cls(r.gap_pct)}">${sgn(r.gap_pct)}</td><td class="${cls(r.day_pct)}"><b>${sgn(r.day_pct)}</b></td>
          <td class="r"><span class="mbar"><i class="${r.day_pct >= 0 ? 'ebu' : 'ebd'}" style="width:${Math.abs(r.day_pct) / mxAbs * 100}%"></i></span></td><td>${r.range_pct}%</td><td class="${cls(r.next_pct)}">${sgn(r.next_pct)}</td>
          <td>${r.eps != null && r.eps_est != null ? `$${nf2.format(r.eps)} / $${nf2.format(r.eps_est)} <span class="chip neutral ${r.surprise_pct >= 0 ? 'st-up' : 'st-down'}">${r.surprise_pct >= 0 ? 'SUPERÓ' : 'POR DEBAJO'}</span>` : '<span class="muted">—</span>'}</td></tr>`; }).join('')}</tbody></table></div>
        <p class="muted">El movimiento se mide contra el cierre previo a la reacción (si reporta después del cierre, la reacción es el día siguiente). Las fechas vienen de Finnhub y los precios de Schwab; no hay captura manual. Es un historial: no predice el próximo reporte.</p></section>`;
      };
      el.addEventListener('click', e => { const b = e.target.closest('#eMet button'); if (b && data) { self.metric = b.dataset.m; paint(); } });
      el.addEventListener('mouseover', e => { const g = e.target.closest('[data-ei]'); if (!g || !data) return; const i = +g.dataset.ei; if (i !== hi) { hi = i; el.querySelectorAll('[data-ei]').forEach(x => x.classList.toggle(x.tagName === 'TR' ? 'hirow' : 'hi', +x.dataset.ei === i)); } });
      $('#eSymGo').onclick = go; $('#eSym').onkeydown = e => { if (e.key === 'Enter') go(); }; go();
    },
  };

  /* ---------- Dividendos: calculadora por acciones o monto, tabla ordenable, calendario y proyección ---------- */
  const DIV_FREQ = { 12: 'Mensual', 4: 'Trimestral', 2: 'Semestral', 1: 'Anual' };
  const MONTHS_ES = () => MON();

  function divProject(shares, price, annual, freq, years, gd, gp, drip) {
    let sh = shares, cum = 0; const out = [];
    for (let y = 1; y <= years; y++) {
      const dps = annual * Math.pow(1 + gd / 100, y - 1);
      let inc = 0;
      for (let k = 0; k < freq; k++) {
        const pay = sh * dps / freq; inc += pay;
        if (drip) sh += pay / (price * Math.pow(1 + gp / 100, (y - 1) + (k + .5) / freq));
      }
      cum += inc;
      out.push({ y, income: inc, cum, shares: sh, value: sh * price * Math.pow(1 + gp / 100, y) });
    }
    return out;
  }
  function divChart(a, b) {
    const W = 760, H = 240, L = 62, R = 12, T = 16, B = 28, n = a.length, pw = W - L - R, ph = H - T - B;
    const mx = Math.max(...a.map(p => p.value + p.cum), ...b.map(p => p.value + p.cum), 1) * 1.08;
    const X = i => L + (n === 1 ? pw / 2 : i * pw / (n - 1)), Y = v => T + (mx - v) / mx * ph;
    const line = (arr, f) => arr.map((p, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(f(p)).toFixed(1)).join('');
    const ticks = [0, mx / 3, 2 * mx / 3, mx];
    return `<svg viewBox="0 0 ${W} ${H}" class="pnl" role="img" aria-label="Proyección de dividendos">
      ${ticks.map(v => `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#1f3558"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#9fb3d1">${bigNum(v)}</text>`).join('')}
      <path d="${line(a, p => p.cum)}" fill="none" stroke="#35e08b" stroke-width="3"/>
      <path d="${line(b, p => p.value + p.cum)}" fill="none" stroke="#ffc933" stroke-width="2.6" stroke-dasharray="6 4"/>
      ${a.map((p, i) => (i === n - 1 || (n > 6 && i % Math.ceil(n / 6) === 0) || n <= 6) ? `<text x="${X(i)}" y="${H - 8}" text-anchor="${i === n - 1 && n > 1 ? 'end' : 'middle'}" font-size="11" fill="#9fb3d1">año ${p.y}</text>` : '').join('')}
      <circle cx="${X(n - 1)}" cy="${Y(a[n - 1].cum)}" r="5" fill="#35e08b"/><circle cx="${X(n - 1)}" cy="${Y(b[n - 1].value + b[n - 1].cum)}" r="5" fill="#ffc933"/>
    </svg><div class="legend"><span><i class="dot" style="background:#35e08b"></i>Dividendos cobrados acumulados</span><span><i class="dot" style="background:#ffc933"></i>Valor de las acciones + dividendos (reinvirtiendo)</span></div>`;
  }

  OBB.views.dividendos = {
    S: { mode: 'shares', val: 100, sort: 'income', desc: true, only: false, years: 10, gd: null, gp: 0, drip: true, rows: [], det: null },
    async render(el) {
      const self = this, S = this.S, adv = OBB.state.user.plan !== 'basico';
      el.innerHTML = `<div class="view-title"><h1><span>Dividendos</span></h1><span class="muted">Cuánto cobrarías según tus acciones o tu inversión</span></div>
      <section class="panel green"><h2>Dividendo + cover call = dos ingresos</h2><p>Con 100 acciones cobras el dividendo y además puedes vender un call cada mes. Aquí ves el primer ingreso; en <b>Cover Call</b>, el segundo.</p></section>
      <section class="panel yellow"><h2>Mi inversión</h2>
        <div class="bar"><div class="seg" id="dvMode"><button data-m="shares">Número de acciones</button><button data-m="amount">Monto a invertir ($)</button></div>
          <input class="field" id="dvVal" inputmode="decimal" style="width:140px" aria-label="Valor"><span class="muted" id="dvHint"></span>
          <label class="inl"><input type="checkbox" id="dvOnly"> Solo las que pagan</label></div>
        <div id="dvTot"></div></section>
      <section class="panel cyan"><h2>Acciones de tus listas</h2><div id="dTab"><div class="empty">Cargando…</div></div></section>
      <section class="panel"><h2>Detalle de una acción</h2>${symBar('dSym', S.det ? S.det.symbol : 'KO')}<div id="dBody"></div></section>`;
      const syncCtl = () => { $$('#dvMode button').forEach(b => b.classList.toggle('on', b.dataset.m === S.mode)); $('#dvVal').value = S.val; $('#dvHint').textContent = S.mode === 'shares' ? 'acciones de cada empresa' : 'dólares en cada empresa'; $('#dvOnly').checked = S.only; };
      const sharesOf = r => S.mode === 'shares' ? +S.val : (r.price ? +S.val / r.price : 0);
      const table = () => {
        let rows = S.rows.map(r => { const ann = (r.income_100 || 0) / 100, sh = sharesOf(r); return { ...r, annual: ann, sh, invest: sh * (r.price || 0), income: sh * ann }; });
        if (S.only) rows = rows.filter(r => r.pays);
        const k = S.sort, dir = S.desc ? -1 : 1;
        rows.sort((a, b) => ((a[k] ?? -1) > (b[k] ?? -1) ? 1 : -1) * dir);
        const tot = rows.reduce((a, r) => ({ inv: a.inv + r.invest, inc: a.inc + r.income }), { inv: 0, inc: 0 });
        $('#dvTot').innerHTML = `<div class="kpis">${kpi('Total invertido', fmtMoney(tot.inv))}${kpi('Ingreso anual por dividendos', fmtMoney(tot.inc), 'up')}${kpi('Ingreso mensual (promedio)', fmtMoney(tot.inc / 12), 'up')}${kpi('Rendimiento de tu inversión', tot.inv ? nf2.format(tot.inc / tot.inv * 100) + '%' : '—')}</div>`;
        const th = (key, l, cl = '') => `<th class="${cl}"><button class="sortb ${S.sort === key ? 'on' : ''}" data-sort="${key}">${l}${S.sort === key ? (S.desc ? ' ▼' : ' ▲') : ''}</button></th>`;
        $('#dTab').innerHTML = `<div class="tscroll"><table class="tbl"><thead><tr>${th('symbol', 'Acción')}${th('price', 'Precio')}${th('yield', 'Rendimiento')}${th('amount', 'Pago')}<th>Frecuencia</th>${th('sh', 'Acciones')}${th('invest', 'Inversión')}${th('income', 'Ingreso anual')}<th>Por mes</th></tr></thead><tbody>
        ${rows.map(r => `<tr class="rowlink" data-pick="${esc(r.symbol)}"><td><b>${esc(r.symbol)}</b></td><td>${fmtMoney(r.price)}</td><td>${r.pays ? (r.yield != null ? `<span class="yb"><i style="width:${Math.min(r.yield / 8 * 100, 100)}%"></i></span> ${r.yield}%` : '—') : '<span class="muted">No paga</span>'}</td><td>${r.amount ? fmtMoney(r.amount) : '—'}</td>
        <td>${r.pays ? (DIV_FREQ[r.freq] || r.freq + '/año') : '—'}</td><td>${nf2.format(r.sh)}${r.sh < 100 ? ' <small class="muted" title="Para vender un cover call necesitas 100 acciones">&lt;100</small>' : ''}</td><td>${fmtMoney(r.invest)}</td>
        <td class="up">${r.pays ? '<b>' + fmtMoney(r.income) + '</b>' : '—'}</td><td>${r.pays ? fmtMoney(r.income / 12) : '—'}</td></tr>`).join('')}</tbody></table></div>
        <p class="muted">Toca una fila para verla en detalle. Ingreso estimado con el último dividendo; las empresas pueden cambiarlo o suspenderlo.</p>`;
      };
      const detail = () => {
        const d = S.det; if (!d) return;
        const sh = S.mode === 'shares' ? +S.val : (d.price ? +S.val / d.price : 0), per = d.freq || 4, annual = d.annual || 0;
        if (!d.pays || !annual) { $('#dBody').innerHTML = `<p class="muted"><b>${esc(d.symbol)}</b> no paga dividendos.</p>`; return; }
        const gd = S.gd == null ? (d.growth != null ? Math.max(Math.min(d.growth, 25), -10) : 3) : S.gd;
        const a = divProject(sh, d.price, annual, per, S.years, gd, S.gp, false), b = divProject(sh, d.price, annual, per, S.years, gd, S.gp, S.drip), last = b[b.length - 1];
        const mo = MONTHS_ES(), hist = d.history || [];
        let months = hist.slice(0, per).map(h => +h.ex.slice(5, 7) - 1); if (months.length < per && d.next_date) months = Array.from({ length: per }, (_, i) => (+d.next_date.slice(5, 7) - 1 + i * (12 / per)) % 12);
        if (!months.length) months = Array.from({ length: per }, (_, i) => (i * 12 / per) % 12);
        const h = hist, mxh = Math.max(...h.map(x => x.amount), 0.01);
        $('#dBody').innerHTML = `<div class="kpis">${kpi('Rendimiento', d.yield != null ? d.yield + '%' : '—')}${kpi('Pago por acción', d.amount ? fmtMoney(d.amount) : '—')}${kpi('Acciones', nf2.format(sh))}${kpi('Inversión', fmtMoney(sh * d.price))}${kpi('Cobras por pago', fmtMoney(sh * annual / per), 'up')}${kpi('Ingreso anual', fmtMoney(sh * annual), 'up')}${kpi('Crecimiento anual', d.growth == null ? '—' : sgn(d.growth), cls(d.growth))}${kpi('Próxima fecha', d.next_date ? fmtDate(d.next_date) : '—')}</div>
        ${sh < 100 ? `<div class="cc-warn">⚠ Con menos de 100 acciones no puedes vender un cover call. ${S.mode === 'amount' ? `Con ${fmtMoney(d.price * 100)} llegas a 100.` : ''}</div>` : `<div class="insight">Con ${Math.floor(sh / 100)} contrato(s) de cover call podrías sumar un segundo ingreso mensual sobre estas mismas acciones. Míralo en <b>Cover Call</b>.</div>`}
        <h3 class="gh">Calendario de pagos estimado (12 meses)</h3><div class="cal">${mo.map((m, i) => `<div class="${months.includes(i) ? 'pay' : ''}"><small>${m}</small><b>${months.includes(i) ? fmtMoney(sh * annual / per) : ''}</b></div>`).join('')}</div>
        <h3 class="gh">Proyección</h3>
        <div class="g3"><div><label for="dvYears">Años: <b id="dvYn">${S.years}</b></label><input type="range" id="dvYears" min="1" max="30" value="${S.years}"></div>
          ${fld('dvGd', 'Crecimiento anual del dividendo %', gd, 'type="number" step="0.5" min="-10" max="25"')}${fld('dvGp', 'Crecimiento anual del precio %', S.gp, 'type="number" step="0.5" min="-20" max="30"')}</div>
        <label class="inl"><input type="checkbox" id="dvDrip" ${S.drip ? 'checked' : ''}> Reinvertir los dividendos (compro más acciones con cada pago)</label>
        <div class="kpis">${kpi(`Cobrado en ${S.years} año(s)`, fmtMoney(a[a.length - 1].cum), 'up')}${kpi('Ingreso anual al final (sin reinvertir)', fmtMoney(a[a.length - 1].income))}${S.drip ? kpi('Acciones al final (reinvirtiendo)', nf2.format(last.shares)) : ''}${S.drip ? kpi('Ingreso anual al final (reinvirtiendo)', fmtMoney(last.income), 'up') : ''}${kpi('Valor final (reinv.) + dividendos', fmtMoney(last.value + last.cum))}</div>
        ${divChart(a, b)}<p class="note">Proyección simple: usa el dividendo actual y los crecimientos que indiques. No es una promesa de rendimiento; las empresas pueden recortar o suspender el dividendo. Sin impuestos.</p>
        ${h.length ? `<h3 class="gh">Historial de pagos</h3><div class="ebars">${h.slice().reverse().map(x => `<div class="eb" title="${fmtDate(x.ex)} ${fmtMoney(x.amount)}"><span class="ebu" style="height:${x.amount / mxh * 100}%"></span><small>${x.ex.slice(2, 7)}</small></div>`).join('')}</div>` : `<p class="muted">${esc(d.history_note || 'El historial de pagos es del plan Intermedio o superior.')}</p>`}`;
      };
      const loadDetail = async () => {
        const sy = ($('#dSym').value || '').trim().toUpperCase(); if (!sy) return; $('#dBody').innerHTML = '<div class="empty">Cargando…</div>';
        try { S.det = await api('/api/dividends?symbol=' + encodeURIComponent(sy)); S.gd = null; detail(); } catch (e) { $('#dBody').innerHTML = errBox('No pude traer ' + esc(sy), e); }
      };
      el.addEventListener('click', e => {
        const m = e.target.closest('#dvMode button'); if (m) { S.mode = m.dataset.m; S.val = S.mode === 'shares' ? 100 : 5000; syncCtl(); table(); detail(); return; }
        const so = e.target.closest('[data-sort]'); if (so) { const k = so.dataset.sort; S.desc = S.sort === k ? !S.desc : k !== 'symbol'; S.sort = k; table(); return; }
        const pk = e.target.closest('[data-pick]'); if (pk) { $('#dSym').value = pk.dataset.pick; loadDetail(); $('#dSym').scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      });
      el.addEventListener('input', e => {
        if (e.target.id === 'dvVal') { S.val = Math.max(0, parseFloat(String(e.target.value).replace(',', '.')) || 0); table(); detail(); }
        if (e.target.id === 'dvYears') { S.years = +e.target.value; detail(); }
      });
      el.addEventListener('change', e => {
        const id = e.target.id;
        if (id === 'dvOnly') { S.only = e.target.checked; table(); }
        if (id === 'dvDrip') { S.drip = e.target.checked; detail(); }
        if (id === 'dvGd') { S.gd = parseFloat(String(e.target.value).replace(',', '.')) || 0; detail(); }
        if (id === 'dvGp') { S.gp = parseFloat(String(e.target.value).replace(',', '.')) || 0; detail(); }
      });
      syncCtl();
      try {
        const l = await api('/api/lists'); const syms = [...new Set([...l.optionsbb.low, ...l.optionsbb.mid, ...(l.mine.low || []), ...(l.mine.mid || []), ...(l.mine.high || [])])].slice(0, 20);
        S.rows = (await api('/api/dividends/table?symbols=' + syms.join(','))).rows; table();
      } catch (e) { $('#dTab').innerHTML = `<p class="muted">${esc(e.message)}</p>`; }
      $('#dSymGo').onclick = loadDetail; $('#dSym').onkeydown = e => { if (e.key === 'Enter') loadDetail(); };
      if (S.det) detail(); else loadDetail();
    },
  };

  /* ---------- Gamma exposure ---------- */
  OBB.views.gex = {
    async render(el) {
      const st = OBB.state; let expiry = 'all';
      el.innerHTML = `<div class="view-title"><h1>Exposición <span>gamma (GEX)</span></h1><span class="muted">Dónde están las paredes de calls y puts en la cadena de opciones</span></div>
      <div class="bar"><input class="field" id="gSym" maxlength="6" style="width:140px;text-transform:uppercase" value="${esc(st.symbol)}" aria-label="Símbolo"><select class="field" id="gExp" aria-label="Vencimiento"><option value="all">Todos los vencimientos</option></select><button class="btn green" id="gGo">Ver</button></div><div id="gBody"><div class="empty">Cargando…</div></div>`;
      const go = async () => {
        const sy = ($('#gSym').value || '').trim().toUpperCase(); if (!sy) return; st.symbol = sy; expiry = $('#gExp').value; $('#gBody').innerHTML = '<div class="empty">Calculando…</div>';
        try { const d = await api(`/api/gex?symbol=${encodeURIComponent(sy)}&expiry=${encodeURIComponent(expiry)}`); paint(d); } catch (e) { $('#gBody').innerHTML = errBox('No pude calcular el GEX de ' + esc(sy), e); }
      };
      const paint = d => {
        $('#gExp').innerHTML = '<option value="all">Todos los vencimientos</option>' + d.expiries.map(x => `<option value="${x}" ${x === expiry ? 'selected' : ''}>${fmtDate(x)}</option>`).join('');
        const rows = d.rows, mx = Math.max(...rows.map(r => Math.max(r.call, -r.put)), 1), W = 760, rh = 22, H = rows.length * rh + 24, mid = W / 2;
        const sc = v => v / mx * (mid - 130);
        const svg = `<svg viewBox="0 0 ${W} ${H}" class="gexc" role="img" aria-label="GEX por strike">${rows.slice().reverse().map((r, i) => { const y = 12 + i * rh; const isSpot = Math.abs(r.strike - d.spot) === Math.min(...rows.map(x => Math.abs(x.strike - d.spot)));
          return `<g><rect x="${mid}" y="${y}" width="${Math.max(sc(r.call), 0)}" height="${rh - 6}" fill="#35e08b" opacity=".85"/><rect x="${mid + sc(r.put)}" y="${y}" width="${Math.max(-sc(r.put), 0)}" height="${rh - 6}" fill="#ff5a6a" opacity=".85"/>
          <text x="8" y="${y + 13}" font-size="12" font-weight="${isSpot ? 800 : 500}" fill="${isSpot ? '#38d6ff' : '#fff'}">${r.strike}${isSpot ? ' ◂ precio' : ''}</text>
          ${r.strike === d.call_wall ? `<text x="${W - 6}" y="${y + 13}" text-anchor="end" font-size="11" fill="#35e08b">▲ pared de calls</text>` : ''}${r.strike === d.put_wall ? `<text x="${W - 6}" y="${y + ((r.strike === d.call_wall) ? 1 : 13)}" text-anchor="end" font-size="11" fill="#ff5a6a">▼ pared de puts</text>` : ''}</g>`; }).join('')}</svg>`;
        $('#gBody').innerHTML = `<section class="panel cyan"><h2>${esc(d.symbol)} · precio ${nf2.format(d.spot)} · ${d.expiry === 'all' ? 'todos los vencimientos' : fmtDate(d.expiry)}</h2>
        <div class="kpis">${kpi('Pared de calls (resistencia)', d.call_wall, 'up')}${kpi('Pared de puts (soporte)', d.put_wall, 'down')}${kpi('Gamma flip', d.flip ?? '—')}${kpi('GEX neto', bigNum(d.net_gex) + ' / 1%', d.net_gex > 0 ? 'up' : 'down')}${kpi('Régimen', d.regime === 'positive' ? 'Gamma positiva' : 'Gamma negativa')}</div>
        <p>${d.regime === 'positive' ? 'Con gamma positiva los dealers tienden a comprar en caídas y vender en subidas: el precio suele moverse menos y puede quedar «pegado» entre las paredes.' : 'Con gamma negativa los dealers acompañan el movimiento: pueden amplificar subidas y caídas.'}</p>
        <div class="tscroll">${svg}</div><div class="legend"><span><i class="dot" style="background:#35e08b"></i>Calls (GEX +)</span><span><i class="dot" style="background:#ff5a6a"></i>Puts (GEX −)</span></div>
        <p class="muted">Fuente: ${esc(d.source)}. Supuesto habitual: los dealers están largos las calls y cortos las puts de los clientes; es una estimación, no un dato oficial. Educativo, no es asesoría.</p></section>`;
      };
      $('#gGo').onclick = go; $('#gSym').onkeydown = e => { if (e.key === 'Enter') go(); }; go();
    },
  };
})();
