/* Vista: Flujo OI — volumen del día D → open interest de D+1 */
OBB.views.flujo = {
  data: null, tab: 'stock', type: 'ALL', minVol: 1000, label: 'ALL', q: '', sort: { k: 'volume', dir: -1 }, pair: '',

  render(el) {
    const self = this;
    el.innerHTML = `
<div class="view-title"><h1>Flujo <span>volumen → open interest</span></h1></div>
<details class="help"><summary><b>Cómo leer esta tabla</b></summary>
  <p>El volumen del día <b>D</b> no “se convierte” en open interest por sí solo: la OCC publica el OI cada noche. La app guarda el volumen y el OI al cierre de D y el OI de la mañana de <b>D+1</b>; la diferencia dice cuánto cambió de verdad.</p>
  <p><b>ΔOI</b> = OI después − OI antes · <b>% OI</b> = ΔOI ÷ OI antes · <b>Conversión</b> = ΔOI ÷ volumen: cerca de +100 % casi todo fueron posiciones nuevas (<i>apertura probable</i>), cerca de −100 % fueron cierres, cerca de 0 % day trading o traspasos.</p>
  <p>Limitación: con volumen y OI no se sabe si el flujo fue <u>compra o venta</u> (un call con mucho volumen puede ser alcista o bajista). Los contratos que vencen en D aparecen como “Vencido” y no cuentan.</p></details>
<div class="bar" id="flowBar"></div>
<div class="kpis" id="flowKpis"></div>
<div class="panel cyan"><div class="tbl-scroll" style="max-height:none;overflow-x:auto" id="flowTable"><div class="empty">Cargando…</div></div></div>`;
    el.addEventListener('click', e => {
      const th = e.target.closest('th.sortable');
      if (th) { const k = th.dataset.k; self.sort = { k, dir: self.sort.k === k ? -self.sort.dir : -1 }; self.paintTable(); return; }
      const seg = e.target.closest('[data-seg]');
      if (seg) { self[seg.dataset.seg] = seg.dataset.v; self.paintBar(); self.paint(); return; }
      const sym = e.target.closest('[data-sym]');
      if (sym) { OBB.state.symbol = sym.dataset.sym; OBB.go('comando'); }
    });
    this.load();
  },

  async load() {
    try {
      const [c, m] = (this.pair || '|').split('|');
      this.data = await api('/api/oi-flow' + (c ? `?close=${c}&morning=${m}` : ''));
      OBB.onStatus && OBB.onStatus(this.data.status);
      if (this.data.result && !this.pair) this.pair = `${this.data.result.close_date}|${this.data.result.morning_date}`;
      this.paintBar(); this.paint();
    } catch (e) { if (![401, 402].includes(e.status)) $('#flowTable').innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  },

  paintBar() {
    const d = this.data, self = this; if (!d) return;
    const seg = (name, opts) => `<div class="seg">${opts.map(([v, l]) => `<button data-seg="${name}" data-v="${v}" class="${self[name] === v ? 'on' : ''}">${l}</button>`).join('')}</div>`;
    $('#flowBar').innerHTML = `
      <select id="flowPair" aria-label="Día analizado">${d.pairs.map(p => `<option value="${p.close_date}|${p.morning_date}" ${this.pair === p.close_date + '|' + p.morning_date ? 'selected' : ''}>Volumen ${fmtDate(p.close_date)} → OI ${fmtDate(p.morning_date)}</option>`).join('')}</select>
      ${seg('tab', [['stock', 'Por acción'], ['contract', 'Por contrato']])}
      ${seg('type', [['ALL', 'Calls + Puts'], ['C', 'Calls'], ['P', 'Puts']])}
      <label class="muted">Vol. mín. <input type="number" class="field" id="flowMin" min="0" step="100" value="${this.minVol}" style="width:90px"></label>
      <select id="flowLbl" aria-label="Lectura"><option value="ALL">Toda lectura</option><option>Apertura probable</option><option>Cierre probable</option><option>Mixto</option></select>
      <input type="text" id="flowQ" placeholder="Buscar símbolo" value="${esc(this.q)}" style="width:130px">`;
    $('#flowLbl').value = this.label;
    $('#flowPair').onchange = e => { this.pair = e.target.value; this.load(); };
    $('#flowMin').oninput = e => { this.minVol = Math.max(0, +e.target.value || 0); this.paint(); };
    $('#flowLbl').onchange = e => { this.label = e.target.value; this.paint(); };
    $('#flowQ').oninput = e => { this.q = e.target.value.toUpperCase(); this.paint(); };
  },

  filtered() {
    const r = this.data.result; if (!r) return [];
    return r.contracts.filter(c => c.label !== 'Vencido' && c.volume >= this.minVol && (this.type === 'ALL' || c.cp === this.type) &&
      (this.label === 'ALL' || c.label === this.label) && (!this.q || c.symbol.includes(this.q)));
  },

  paint() { this.paintKpis(); this.paintTable(); },

  paintKpis() {
    const d = this.data, box = $('#flowKpis');
    if (!d.result) { box.innerHTML = ''; return; }
    const rows = this.filtered(), vol = rows.reduce((a, c) => a + c.volume, 0), dOi = rows.reduce((a, c) => a + c.d_oi, 0), oi0 = rows.reduce((a, c) => a + c.oi0, 0);
    const n = l => rows.filter(c => c.label === l).length;
    box.innerHTML = `
      <div class="kpi navy"><small>Contratos analizados</small><b>${fmtInt(rows.length)}</b></div>
      <div class="kpi navy"><small>Volumen del día</small><b>${fmtInt(vol)}</b></div>
      <div class="kpi ${dOi >= 0 ? 'gr' : 'rd'}"><small>ΔOI neto</small><b>${fmtSigned(dOi)}</b></div>
      <div class="kpi teal"><small>% OI</small><b>${oi0 ? fmtPct(dOi / oi0 * 100) : '—'}</b></div>
      <div class="kpi gr"><small>Apertura probable</small><b>${n('Apertura probable')}</b></div>
      <div class="kpi rd"><small>Cierre probable</small><b>${n('Cierre probable')}</b></div>
      <div class="kpi navy"><small>Mixto</small><b>${n('Mixto')}</b></div>`;
  },

  th(k, label, c = 'r') { const a = this.sort.k === k ? (this.sort.dir < 0 ? ' ▼' : ' ▲') : ''; return `<th class="sortable ${c}" data-k="${k}">${label}${a}</th>`; },
  lblHtml(l) { const c = l === 'Apertura probable' ? 'o' : l === 'Cierre probable' ? 'c' : l === 'Vencido' ? 'x' : 'm'; return `<span class="lbl ${c}">${esc(l)}</span>`; },

  paintTable() {
    const box = $('#flowTable'), d = this.data;
    if (!d.result) { box.innerHTML = `<div class="empty">Aún no hay datos de OI.<br><span class="note">La app toma una foto del volumen a las 4:15 pm ET y otra del OI a las 9:00 am ET del día siguiente. El administrador puede forzarlas desde la pestaña Cuenta.</span></div>`; return; }
    const { k, dir } = this.sort, cmp = (a, b) => { const x = a[k] ?? -Infinity, y = b[k] ?? -Infinity; return (typeof x === 'string' ? x.localeCompare(y) : x - y) * dir; };
    if (this.tab === 'stock') return this.paintStocks(box, cmp);
    const rows = this.filtered().sort(cmp), shown = rows.slice(0, 150);
    box.innerHTML = rows.length ? `<table class="t"><thead><tr>${this.th('symbol', 'Contrato', '')}${this.th('volume', 'Volumen (D)')}${this.th('oi0', 'OI antes')}${this.th('oi1', 'OI después')}${this.th('d_oi', 'ΔOI')}${this.th('pct', '% OI')}${this.th('conv', 'Conversión', '')}${this.th('label', 'Lectura', '')}</tr></thead><tbody>${shown.map(c => {
      const cv = c.conv == null ? 0 : Math.max(-1, Math.min(1, c.conv)), w = Math.abs(cv) * 50;
      return `<tr><td><span class="sym" data-sym="${esc(c.symbol)}">${esc(c.symbol)}</span> ${fmtExp(c.expiry)} ${c.strike}<span class="cp ${c.cp}">${c.cp === 'C' ? 'CALL' : 'PUT'}</span></td><td class="r">${fmtInt(c.volume)}</td><td class="r">${fmtInt(c.oi0)}</td><td class="r">${fmtInt(c.oi1)}</td><td class="r ${cls(c.d_oi)}">${fmtSigned(c.d_oi)}</td><td class="r ${cls(c.pct)}">${fmtPct(c.pct)}</td><td><div class="bars"><div class="convbar"><i style="${cv >= 0 ? 'left:50%' : `right:50%`};width:${w}%;background:${cv >= 0 ? C.green : C.red}"></i></div><span class="${cls(c.conv)}">${c.conv == null ? '—' : fmtPct(c.conv * 100, true).replace(/\.\d+/, '')}</span></div></td><td>${this.lblHtml(c.label)}</td></tr>`;
    }).join('')}</tbody></table>${rows.length > shown.length ? `<div class="note" style="padding:8px">Mostrando ${shown.length} de ${fmtInt(rows.length)}. Sube el volumen mínimo para afinar.</div>` : ''}` : '<div class="empty">Ningún contrato cumple los filtros.</div>';
  },

  paintStocks(box, cmp) {
    const m = {};
    this.filtered().forEach(c => {
      const s = m[c.symbol] = m[c.symbol] || { symbol: c.symbol, call_vol: 0, put_vol: 0, call_d: 0, put_d: 0, oi0: 0, top: null };
      s[c.cp === 'C' ? 'call_vol' : 'put_vol'] += c.volume; s[c.cp === 'C' ? 'call_d' : 'put_d'] += c.d_oi; s.oi0 += c.oi0;
      if (!s.top || c.volume > s.top.volume) s.top = c;
    });
    const rows = Object.values(m).map(s => ({ ...s, volume: s.call_vol + s.put_vol, d_oi: s.call_d + s.put_d, pcr: s.call_vol ? s.put_vol / s.call_vol : null }));
    rows.forEach(s => { s.pct = s.oi0 ? s.d_oi / s.oi0 * 100 : null; });
    rows.sort(cmp);
    box.innerHTML = rows.length ? `<table class="t"><thead><tr>${this.th('symbol', 'Acción', '')}${this.th('call_vol', 'Vol. Calls')}${this.th('put_vol', 'Vol. Puts')}${this.th('pcr', 'Put/Call')}${this.th('call_d', 'ΔOI Calls')}${this.th('put_d', 'ΔOI Puts')}${this.th('d_oi', 'ΔOI total')}${this.th('pct', '% OI')}<th>Contrato líder</th></tr></thead><tbody>${rows.map(s =>
      `<tr><td><span class="sym" data-sym="${esc(s.symbol)}">${esc(s.symbol)}</span></td><td class="r">${fmtInt(s.call_vol)}</td><td class="r">${fmtInt(s.put_vol)}</td><td class="r">${s.pcr == null ? '—' : s.pcr.toFixed(2)}</td><td class="r ${cls(s.call_d)}">${fmtSigned(s.call_d)}</td><td class="r ${cls(s.put_d)}">${fmtSigned(s.put_d)}</td><td class="r ${cls(s.d_oi)}">${fmtSigned(s.d_oi)}</td><td class="r ${cls(s.pct)}">${fmtPct(s.pct)}</td><td>${fmtExp(s.top.expiry)} ${s.top.strike}<span class="cp ${s.top.cp}">${s.top.cp === 'C' ? 'CALL' : 'PUT'}</span> <small class="muted">${fmtInt(s.top.volume)}</small></td></tr>`).join('')}</tbody></table>` : '<div class="empty">Ninguna acción cumple los filtros.</div>';
  },

  destroy() { clearTimers(); },
};
