/* Vista: Centro de Comando */
OBB.views.comando = {
  cmd: null, chart: null, range: '1D', open: { BULL: true, BEAR: true },

  render(el) {
    const self = this;
    el.innerHTML = `
<div class="cmd">
  <div class="row1">
    <section class="chero">
      <div class="t1"><span>CENTRO DE COMANDO</span></div>
      <div class="t2"><span>OPTIONS <b>BB</b></span></div>
      <div class="pill">ANALIZA · CREA · AUTOMATIZA · EJECUTA</div>
    </section>
    <section class="panel cyan chart-panel">
      <div class="chart-head">
        <input id="chSym" list="symList" maxlength="6" value="${esc(OBB.state.symbol)}" aria-label="Símbolo del gráfico" spellcheck="false">
        <datalist id="symList"></datalist>
        <span class="px" id="chPx">—</span><span class="ch" id="chCh"></span>
        <div class="ranges" id="ranges">${['1D', '5D', '1M', '3M', '1Y'].map(r => `<button data-r="${r}" class="${r === self.range ? 'on' : ''}">${r}</button>`).join('')}</div>
      </div>
      <div class="chart-wrap"><canvas id="chCanvas"></canvas><div class="chart-tip hidden" id="chTip"></div></div>
    </section>
    <aside class="panel cyan info">
      <h3>Mejores estrategias<br>más oportunidades<b>un solo lugar</b></h3>
      <ul>
        <li><i class="r">▶</i>@optionsbb</li>
        <li><i>✉</i>info@optionsbb.com</li>
        <li><i>✉</i>jroa@optionsbb.com</li>
        <li><i>◍</i>www.optionsbb.com</li>
      </ul>
    </aside>
  </div>
  <div class="row2">
    <section class="panel green sel" id="selBull"></section>
    <section class="panel green pat" id="patPanel"></section>
    <section class="panel red sel" id="selBear"></section>
  </div>
  <div class="row3">
    <section class="panel green"><h2><span class="g">▲</span> Estrategia <span class="g">alcista</span> - lista dinámica</h2><div class="tbl-scroll" id="listBull"></div></section>
    <section class="panel red"><h2><span class="r">▼</span> Estrategia <span class="r">bajista</span> - lista dinámica</h2><div class="tbl-scroll" id="listBear"></div></section>
    <section class="panel yellow"><h2><span class="y">▮▮</span> Contratos con más volumen</h2><div class="tbl-scroll" id="listTop"></div><div class="idea" id="idea"></div></section>
  </div>
  <div class="row4"><section class="panel cyan lnk"><h2>Mis listas de seguimiento</h2><p class="muted">Tres listas de Optionsbb (poco riesgo, riesgo moderado y alto riesgo) y tus propias listas, con el % de cambio de hoy, 7, 15, 30, 90 y 360 días.</p><button class="btn green" data-go-lists>Abrir Mis listas →</button></section></div>
</div>`;

    el.addEventListener('click', e => { if (e.target.closest('[data-go-lists]')) { OBB.go('listas'); return; }
      const r = e.target.closest('#ranges button');
      if (r) { self.range = r.dataset.r; $$('#ranges button').forEach(b => b.classList.toggle('on', b === r)); self.loadChart(); return; }
      const opt = e.target.closest('.opt');
      if (opt) {
        const side = opt.dataset.side;
        OBB.state[side === 'BULL' ? 'bull' : 'bear'] = opt.dataset.id; OBB.state.patternSide = side;
        self.paintAll(); self.loadChart(); return;
      }
      const box = e.target.closest('.sel .box');
      if (box) { const side = box.dataset.side; self.open[side] = !self.open[side]; self.paintSelectors(); return; }
      const sym = e.target.closest('[data-sym]');
      if (sym) { self.setSymbol(sym.dataset.sym); window.scrollTo({ top: 0, behavior: 'smooth' }); }
    });
    const inp = $('#chSym', el);
    inp.addEventListener('keydown', e => { if (e.key === 'Enter') self.setSymbol(inp.value); });
    inp.addEventListener('change', () => self.setSymbol(inp.value));
    this.paintPattern();
    this.loadCmd(); this.loadChart();
    setInterval2(() => { self.loadCmd(); self.loadChart(); }, 30000);
  },

  setSymbol(s) {
    s = (s || '').trim().toUpperCase();
    if (!/^[A-Z][A-Z.\-]{0,5}$/.test(s)) return toast('Símbolo no válido', true);
    OBB.state.symbol = s; $('#chSym').value = s; this.loadChart();
  },

  async loadCmd() {
    try {
      this.cmd = await api('/api/command');
      OBB.onStatus && OBB.onStatus(this.cmd.status);
      const dl = $('#symList'); if (dl && !dl.children.length) dl.innerHTML = (this.cmd.symbols || []).map(s => `<option value="${esc(s)}">`).join('');
      this.paintAll();
    } catch (e) { if (e.status !== 401 && e.status !== 402) toast(e.message, true); }
  },

  async loadChart() {
    const st = OBB.state, canvas = $('#chCanvas'); if (!canvas) return;
    const q = new URLSearchParams({ symbol: st.symbol, range: this.range, bull: st.bull, bear: st.bear });
    try {
      const d = await api('/api/chart?' + q);
      if (d.symbol !== OBB.state.symbol || d.range !== this.range) return;
      const last = d.candles[d.candles.length - 1];
      const px = d.quote.price ?? (last && last.c), pc = d.quote.change_pct;
      $('#chPx').textContent = px != null ? fmtNum(px) : '—';
      const ch = $('#chCh'); ch.className = 'ch ' + cls(pc);
      ch.textContent = d.quote.change != null ? `${d.quote.change >= 0 ? '+' : '−'}${fmtNum(Math.abs(d.quote.change))} (${fmtPct(pc)})` : '';
      drawCandles(canvas, $('#chTip'), d);
    } catch (e) { if (e.status === 400) toast(e.message + ' — usa un símbolo de tu lista', true); else if (![0, 401, 402].includes(e.status)) toast(e.message, true); }
  },

  paintAll() { this.paintSelectors(); this.paintPattern(); this.paintLists(); },

  paintSelectors() {
    if (!this.cmd) return;
    [['BULL', '#selBull', 'bull', 'alcista', '▲', 'g'], ['BEAR', '#selBear', 'bear', 'bajista', '▼', 'r']].forEach(([side, sel, key, word, ico, c]) => {
      const list = this.cmd.strategies.filter(s => s.side === side), cur = OBB.state[key], counts = this.cmd.signals[side];
      const curLbl = (list.find(s => s.id === cur) || list[0]).label;
      $(sel).innerHTML = `<h2><span class="${c}">${ico}</span> Estrategia <span class="${c}">${word}</span></h2>
        <button class="box" data-side="${side}" aria-expanded="${this.open[side]}"><span>${esc(curLbl)}</span><span>${this.open[side] ? '⌃' : '⌄'}</span></button>
        <div class="opts ${this.open[side] ? '' : 'hidden'}">${list.map(s => `<button class="opt ${s.id === cur ? 'on' : ''}" data-side="${side}" data-id="${s.id}"><span class="dot"></span>${esc(s.label)}<span class="n" title="Señales ahora">${(counts[s.id] || []).length}</span></button>`).join('')}</div>`;
    });
  },

  paintPattern() {
    const side = OBB.state.patternSide, id = OBB.state[side === 'BULL' ? 'bull' : 'bear'], P = PATTERNS[id], panel = $('#patPanel');
    if (!panel || !P) return;
    const c = P.side === 'BULL' ? 'g' : 'r';
    panel.className = 'panel pat ' + (P.side === 'BULL' ? 'green' : 'red');
    panel.innerHTML = `<div class="pat-title"><h2><span class="${c}">${esc(P.title)}</span> · ${esc(P.sub)}</h2><small>⏱ TEMPORALIDAD: 5 MINUTOS</small></div>${patternSVG(id)}<div class="pat-rule">${esc(P.rule)}</div>`;
  },

  paintLists() {
    if (!this.cmd) return;
    const mk = (rows, side) => {
      if (!rows.length) return `<div class="empty">Sin señales con esta estrategia por ahora.<br><span class="note">Se evalúan velas de 5 min; se actualiza cada 3 min en horario de mercado.</span></div>`;
      return `<table class="t"><thead><tr><th>Símbolo</th><th>Estrategia</th><th class="c">Señal</th><th class="r">Precio</th><th class="r">% Cambio</th></tr></thead><tbody>${rows.map(r =>
        `<tr title="${esc(r.sector || '')} · señal ${etTime(r.t)} ET"><td class="sym" data-sym="${esc(r.symbol)}">${esc(r.symbol)}</td><td>${esc(r.strategy)}</td><td class="c"><span class="chip ${side === 'BULL' ? 'buy' : 'sell'}">${r.signal}</span></td><td class="r">${fmtNum(r.price)}</td><td class="r ${cls(r.change_pct)}">${fmtPct(r.change_pct)}</td></tr>`).join('')}</tbody></table>`;
    };
    $('#listBull').innerHTML = mk(this.cmd.signals.BULL[OBB.state.bull] || [], 'BULL');
    $('#listBear').innerHTML = mk(this.cmd.signals.BEAR[OBB.state.bear] || [], 'BEAR');
    const top = this.cmd.top;
    $('#listTop').innerHTML = top.length ? `<table class="t"><thead><tr><th>Símbolo</th><th>Tipo</th><th class="r">Strike</th><th class="r">Volumen</th></tr></thead><tbody>${top.map(t =>
      `<tr title="Vence ${fmtExp(t.expiry)} · OI ${fmtInt(t.oi)} · Vol/OI ${t.vol_oi == null ? '—' : t.vol_oi.toFixed(2)}"><td class="sym" data-sym="${esc(t.symbol)}">${esc(t.symbol)} <small class="muted">${fmtExp(t.expiry)}</small></td><td class="${t.cp === 'C' ? 'up' : 'down'}">${t.cp === 'C' ? 'Call' : 'Put'}</td><td class="r">${t.strike}</td><td class="r">${fmtInt(t.volume)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">Cargando contratos…</div>';
    $('#idea').innerHTML = this.cmd.idea ? `<b>IDEA DEL DÍA</b> ${esc(this.cmd.idea)}` : '';
  },

  destroy() { clearTimers(); },
};
