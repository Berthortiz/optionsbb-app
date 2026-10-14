/* Mis listas: tres listas de Optionsbb (poco / moderado / alto riesgo) + «Mi lista» propia por nivel */
const RISK_NAME = { low: 'Poco riesgo', mid: 'Riesgo moderado', high: 'Alto riesgo' };

/* Pregunta en qué nivel de riesgo guardar una acción y la agrega a «Mi lista»; luego te lleva a Mis listas */
async function addToMyList(symbol) {
  const sym = (symbol || '').trim().toUpperCase(); if (!sym) return toast('Escribe un símbolo', true);
  const risk = await new Promise(res => {
    const o = document.createElement('div'); o.className = 'modal';
    o.innerHTML = `<div class="mbox pick"><h2>Guardar ${esc(sym)} en…</h2><p class="muted">Elige el nivel de riesgo de tu lista</p>
      <div class="stack">${['low', 'mid', 'high'].map(r => `<button class="btn ${r === 'low' ? 'green' : r === 'mid' ? 'ghost' : 'red'}" data-r="${r}">${RISK_NAME[r]}</button>`).join('')}<button class="btn ghost" data-r="">Cancelar</button></div></div>`;
    o.onclick = e => { const b = e.target.closest('[data-r]'); if (b || e.target === o) { o.remove(); res(b ? b.dataset.r : ''); } };
    document.body.appendChild(o);
  });
  if (!risk) return;
  try {
    const info = await api('/api/lists');
    if (info.mine[risk].includes(sym)) toast(`${sym} ya está en tu lista`);
    else await api('/api/lists/' + risk, { method: 'POST', body: { symbols: info.mine[risk].concat(sym) } });
    OBB.state.flash = { risk, symbol: sym }; OBB.go('listas');
  } catch (e) { toast(e.message, true); }
}

OBB.views.listas = {
  L: null,
  RISK_CLS: { low: 'green', mid: 'yellow', high: 'red' },
  render(el) {
    const self = this; this.L = null;
    el.innerHTML = `<div class="view-title"><h1>Mis <span>listas</span></h1><span class="muted">Optionsbb te propone 3 listas de 10 acciones; tú armas las tuyas por nivel de riesgo</span></div><div id="watchPanel"><div class="empty">Cargando…</div></div>`;
    el.addEventListener('click', e => self.click(e));
    el.addEventListener('change', e => self.change(e));
    el.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.classList && e.target.classList.contains('lAdd')) self.click({ target: e.target.closest('.lbox').querySelector('[data-ladd]') }); });
    this.load(); setInterval2(() => self.loadBoxes(), 60000);
  },
  async load() {
    try {
      const info = await api('/api/lists'); const f = OBB.state.flash;
      this.L = { info, src: { low: 'optionsbb', mid: 'optionsbb', high: 'optionsbb' }, rows: {} };
      if (f) this.L.src[f.risk] = 'mine';
      this.paint(); await this.loadBoxes();
      if (f) { OBB.state.flash = null; const row = $(`.lbox[data-risk="${f.risk}"] tr[data-row="${f.symbol}"]`); if (row) { row.classList.add('flash'); row.scrollIntoView({ behavior: 'smooth', block: 'center' }); } toast(`${f.symbol} agregada a Mi lista · ${RISK_NAME[f.risk]}`); }
    } catch (e) { if (![0, 401, 402, 403].includes(e.status)) toast(e.message, true); }
  },
  async loadBoxes(only) {
    const L = this.L; if (!L) return;
    await Promise.all((only ? [only] : ['low', 'mid', 'high']).map(async r => { const v = await api(`/api/lists/view?risk=${r}&src=${L.src[r]}`); L.rows[r] = v.rows; L.info.periods = v.periods; }));
    this.paint();
  },
  paint() {
    const L = this.L, p = $('#watchPanel'); if (!L || !p) return;
    const info = L.info, ps = info.all_periods.filter(x => info.periods.includes(x.key));
    const keep = {}; $$('.lAdd', p).forEach(i => { keep[i.closest('.lbox').dataset.risk] = i.value; });
    const focus = document.activeElement && document.activeElement.classList.contains('lAdd') ? document.activeElement.closest('.lbox').dataset.risk : null;
    const box = rk => {
      const r = rk.risk, src = L.src[r], mine = info.mine[r], rows = L.rows[r];
      const table = !rows ? '<div class="empty">Cargando…</div>' : rows.length ? `<div class="tbl-scroll" style="max-height:420px;overflow-x:auto"><table class="t"><thead><tr><th>Símbolo</th><th class="r">Precio</th>${ps.map(x => `<th class="r">${esc(x.label)}</th>`).join('')}<th></th></tr></thead><tbody>${rows.map(w => `<tr data-row="${esc(w.symbol)}"><td class="sym" data-sym="${esc(w.symbol)}">${esc(w.symbol)}</td><td class="r">${fmtNum(w.price)}</td>${ps.map(x => `<td class="r ${cls(w.changes[x.key])}">${fmtPct(w.changes[x.key])}</td>`).join('')}<td class="r"><button class="btn ghost" style="padding:2px 8px;font-size:12px" data-analyze="${esc(w.symbol)}">Analizar</button>${src === 'mine' ? ` <button class="btn ghost" style="padding:2px 8px;font-size:12px" data-ldel="${esc(w.symbol)}" aria-label="Quitar ${esc(w.symbol)}">✕</button>` : ''}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="empty">Tu lista está vacía. Agrega acciones o copia la lista de Optionsbb para editarla.</div>';
      return `<section class="panel ${this.RISK_CLS[r]} lbox" data-risk="${r}"><h2>${esc(rk.title)}</h2>
        <div class="seg lsrc"><button data-lsrc="optionsbb" class="${src === 'optionsbb' ? 'on' : ''}">Lista Optionsbb</button><button data-lsrc="mine" class="${src === 'mine' ? 'on' : ''}">Mi lista (${mine.length}/${info.max})</button></div>
        ${src === 'mine' ? `<div class="bar" style="margin:8px 0"><input class="field lAdd" maxlength="6" placeholder="Símbolo (ej. NVDA)" style="width:140px;text-transform:uppercase" value="${esc(keep[r] || '')}"><button class="btn green" data-ladd>Agregar</button><button class="btn ghost" data-lcopy title="Copia las ${info.optionsbb[r].length} acciones de Optionsbb a tu lista">Copiar lista Optionsbb</button></div>` : ''}
        ${table}</section>`;
    };
    p.innerHTML = `<div class="bar" style="margin-bottom:10px"><span class="muted" style="font-size:12.5px">Mostrar:</span>
      <span class="chips">${info.all_periods.map(x => `<label class="pchip ${info.periods.includes(x.key) ? 'on' : ''}"><input type="checkbox" data-period="${x.key}" ${info.periods.includes(x.key) ? 'checked' : ''}>${esc(x.label)}</label>`).join('')}</span></div>
      <div class="lgrid">${info.risks.map(box).join('')}</div>${ccCallout()}`;
    if (focus) { const i = $(`.lbox[data-risk="${focus}"] .lAdd`, p); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }
  },
  async save(r, syms) {
    try { const d = await api('/api/lists/' + r, { method: 'POST', body: { symbols: syms } }); this.L.info.mine[r] = d.symbols; await this.loadBoxes(r); } catch (er) { toast(er.message, true); }
  },
  click(e) {
    const t = e.target, L = this.L; if (!t.closest || !L) return;
    const bx = t.closest('.lbox'), r = bx && bx.dataset.risk;
    const src = t.closest('[data-lsrc]');
    if (src) { L.src[r] = src.dataset.lsrc; L.rows[r] = null; this.paint(); this.loadBoxes(r).catch(er => toast(er.message, true)); return; }
    if (t.closest('[data-ladd]')) { const i = $('.lAdd', bx), v = (i.value || '').trim().toUpperCase(); if (v) { i.value = ''; this.save(r, L.info.mine[r].concat(v)); } return; }
    if (t.closest('[data-lcopy]')) { this.save(r, L.info.optionsbb[r]); return; }
    const del = t.closest('[data-ldel]');
    if (del) { this.save(r, L.info.mine[r].filter(s => s !== del.dataset.ldel)); return; }
    const an = t.closest('[data-analyze]');
    if (an) { OBB.state.symbol = an.dataset.analyze; OBB.go('analisis'); return; }
    const sy = t.closest('.sym[data-sym]');
    if (sy) { OBB.state.symbol = sy.dataset.sym; OBB.go('analisis'); }
  },
  change(e) {
    const t = e.target, self = this;
    if (t.dataset && t.dataset.period) {
      const sel = $$('[data-period]:checked').map(x => x.dataset.period); if (!sel.length) { t.checked = true; return toast('Deja al menos un periodo', true); }
      api('/api/prefs', { method: 'POST', body: { key: 'watch_periods', value: sel } }).then(() => self.loadBoxes()).catch(er => toast(er.message, true));
    }
  },
  destroy() { clearTimers(); },
};
