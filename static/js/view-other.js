/* Vistas: Sectores, Desempeño (reporte de estrategias) y Cuenta/Administración */
const SECTOR_ES = { 'Technology': 'Tecnología', 'Communication Services': 'Comunicaciones', 'Consumer Discretionary': 'Consumo discrecional', 'Consumer Staples': 'Consumo básico', 'Health Care': 'Salud', 'Financials': 'Financiero', 'Industrials': 'Industriales', 'Energy': 'Energía', 'Materials': 'Materiales', 'Real Estate': 'Bienes raíces', 'Utilities': 'Servicios públicos' };

/* ------------------------------ Sectores ------------------------------ */
OBB.views.sectores = {
  async render(el) {
    el.innerHTML = `<div class="view-title"><h1>Sectores <span>acciones clave</span></h1><span class="muted">Clic en un símbolo para verlo en el gráfico</span></div><div class="sector-grid" id="secGrid"><div class="empty">Cargando…</div></div>`;
    const admin = OBB.state.user.role === 'admin';
    el.addEventListener('click', async e => {
      const s = e.target.closest('[data-sym]'); if (s) { OBB.state.symbol = s.dataset.sym; OBB.go('comando'); return; }
      try {
        const rm = e.target.closest('[data-rmsym]'); if (rm) { await api('/api/admin/sector', { method: 'DELETE', body: { sector: rm.dataset.sec, symbol: rm.dataset.rmsym } }); toast('Acción quitada'); load(); return; }
        const rs = e.target.closest('[data-rmsec]'); if (rs && confirm('¿Eliminar el sector completo?')) { await api('/api/admin/sector', { method: 'DELETE', body: { sector: rs.dataset.rmsec } }); toast('Sector eliminado'); load(); return; }
        const ad = e.target.closest('[data-addsym]');
        if (ad) { const inp = el.querySelector(`[data-addin="${CSS.escape(ad.dataset.addsym)}"]`); await api('/api/admin/sector', { method: 'POST', body: { sector: ad.dataset.addsym, symbol: inp.value } }); toast('Acción agregada'); load(); return; }
        if (e.target.id === 'secNew') { await api('/api/admin/sector', { method: 'POST', body: { sector: $('#secName').value, symbol: $('#secSym').value } }); toast('Sector creado'); load(); }
      } catch (er) { toast(er.message, true); }
    });
    const load = async () => {
      try {
        const d = await api('/api/sectors'); OBB.onStatus && OBB.onStatus(d.status);
        $('#secGrid').innerHTML = d.sectors.map(sec => {
          const ch = sec.stocks.map(s => s.change_pct).filter(v => v != null), avg = ch.length ? ch.reduce((a, b) => a + b, 0) / ch.length : null;
          return `<section class="panel cyan"><h2>${esc(SECTOR_ES[sec.sector] || sec.sector)} <small class="${cls(avg)}" style="font-size:13px">${fmtPct(avg)}</small></h2>
          <table class="t"><thead><tr><th>Símbolo</th><th class="r">Precio</th><th class="r">%</th><th class="r" title="Volumen puts ÷ calls">P/C</th><th>Señales</th></tr></thead><tbody>${sec.stocks.map(s => `<tr><td class="sym" data-sym="${esc(s.symbol)}">${esc(s.symbol)}${admin ? ` <button class="xbtn" data-sec="${esc(sec.sector)}" data-rmsym="${esc(s.symbol)}" title="Quitar" aria-label="Quitar ${esc(s.symbol)}">✕</button>` : ''}</td><td class="r">${fmtNum(s.price)}</td><td class="r ${cls(s.change_pct)}">${fmtPct(s.change_pct)}</td><td class="r">${s.pcr == null ? '—' : s.pcr.toFixed(2)}</td><td>${s.signals.map(g => `<span class="badge-sig ${g.side === 'BULL' ? 'b' : 's'}" title="${esc(g.label)}">${g.side === 'BULL' ? '▲' : '▼'} ${esc(g.label)}</span>`).join('') || '<span class="muted">—</span>'}</td></tr>`).join('')}</tbody></table>${admin ? `<div class="bar" style="margin-top:8px"><input class="field" data-addin="${esc(sec.sector)}" maxlength="8" placeholder="Símbolo" style="width:110px;text-transform:uppercase" aria-label="Agregar símbolo a ${esc(sec.sector)}"><button class="btn green" data-addsym="${esc(sec.sector)}">+ Agregar</button><button class="btn red" data-rmsec="${esc(sec.sector)}">Eliminar sector</button></div>` : ''}</section>`;
        }).join('') + (admin ? `<section class="panel yellow"><h2>Nuevo sector (administrador)</h2><div class="bar"><input class="field" id="secName" maxlength="40" placeholder="Nombre del sector" aria-label="Nombre del sector"><input class="field" id="secSym" maxlength="8" placeholder="Primera acción" style="width:140px;text-transform:uppercase" aria-label="Primera acción"><button class="btn green" id="secNew">Crear sector</button></div></section>` : '');
      } catch (e) { if (![401, 402].includes(e.status)) toast(e.message, true); }
    };
    load(); setInterval2(load, 60000);
  },
  destroy() { clearTimers(); },
};

/* ------------------------------ Desempeño ------------------------------ */
OBB.views.desempeno = {
  id: null,

  async render(el) {
    const self = this, admin = OBB.state.user.role === 'admin';
    el.innerHTML = `
<div class="view-title"><h1>Desempeño <span>por estrategia</span></h1><span class="muted">Backtest exportado desde Thinkorswim (Strategy Report)</span></div>
<div class="bar" id="repBar"></div>
${admin ? `<div class="dropzone" id="drop"><b>Subir reporte de Thinkorswim</b> (.csv o .xlsx) — arrastra el archivo aquí o
  <label class="btn ghost" style="display:inline-block;margin:0 6px;cursor:pointer">Elegir archivo<input type="file" id="repFile" accept=".csv,.txt,.xlsx,.xlsm" hidden></label>
  Símbolo <input type="text" class="field" id="repSym" maxlength="6" placeholder="p. ej. MU" style="width:90px;text-transform:uppercase">
  <div class="note">En TOS: Charts → Strategies → Show Report → pestaña Trade List → clic derecho → Export to File.</div></div>` : ''}
<div id="repBody"><div class="empty">Cargando…</div></div>`;
    $('#repBar').onchange = e => { if (e.target.id === 'repSel') { self.id = +e.target.value; self.loadReport(); } };
    el.addEventListener('click', async e => {
      if (e.target.closest('#repDel')) {
        if (!confirm('¿Eliminar este reporte?')) return;
        try { await api('/api/reports/' + self.id, { method: 'DELETE' }); self.id = null; toast('Reporte eliminado'); self.loadList(); } catch (er) { toast(er.message, true); }
      }
    });
    if (admin) {
      const up = async f => {
        if (!f) return;
        try {
          const r = await api('/api/admin/report', { method: 'POST', body: await f.arrayBuffer(), headers: { 'X-Filename': encodeURIComponent(f.name), 'X-Symbol': ($('#repSym').value || '').trim().toUpperCase() } });
          toast(`Reporte cargado: ${r.trades} operaciones` + (r.warnings.length ? ' · ' + r.warnings[0] : '')); self.id = r.id; self.loadList();
        } catch (er) { toast(er.message, true); }
      };
      $('#repFile').onchange = e => up(e.target.files[0]);
      const dz = $('#drop');
      ['dragenter', 'dragover'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.add('drag'); }));
      ['dragleave', 'drop'].forEach(t => dz.addEventListener(t, e => { e.preventDefault(); dz.classList.remove('drag'); }));
      dz.addEventListener('drop', e => up(e.dataTransfer.files[0]));
    }
    this.loadList();
  },

  async loadList() {
    try {
      const { reports } = await api('/api/reports'), admin = OBB.state.user.role === 'admin';
      if (!reports.length) { $('#repBar').innerHTML = ''; $('#repBody').innerHTML = '<div class="empty">Todavía no hay reportes. ' + (admin ? 'Sube el primero arriba.' : 'El administrador publicará pronto el primero.') + '</div>'; return; }
      if (!reports.some(r => r.id === this.id)) this.id = reports[0].id;
      $('#repBar').innerHTML = `<select id="repSel" aria-label="Reporte">${reports.map(r => `<option value="${r.id}" ${r.id === this.id ? 'selected' : ''}>${esc(r.symbol || '—')} · ${esc((r.period_start || '').slice(0, 10))} → ${esc((r.period_end || '').slice(0, 10))}${r.is_demo ? ' · DEMO' : ''} · ${esc(r.filename)}</option>`).join('')}</select>
        <a class="btn green" id="repDl" href="/api/reports/${this.id}/xlsx">⬇ Descargar Excel</a>${admin ? '<button class="btn red" id="repDel">Eliminar</button>' : ''}`;
      this.loadReport();
    } catch (e) { if (![401, 402].includes(e.status)) toast(e.message, true); }
  },

  async loadReport() {
    $('#repDl') && ($('#repDl').href = `/api/reports/${this.id}/xlsx`);
    try { const r = await api('/api/reports/' + this.id); this.paint(r); } catch (e) { if (![401, 402].includes(e.status)) toast(e.message, true); }
  },

  paint(r) {
    const T = r.total, S = r.strategies, m = r.meta;
    const row = s => `<tr class="${s.absent ? 'absent' : ''}"><td>${esc(s.name)}</td><td>${s.ops}</td><td>${s.wins}</td><td>${s.losses}</td><td>${s.hit_rate == null ? '' : s.hit_rate.toFixed(1) + '%'}</td><td class="${cls(s.net)}">${fmtMoney(s.net)}</td><td>${s.avg_win == null ? '' : fmtMoney(s.avg_win)}</td><td>${s.avg_loss == null ? '' : fmtMoney(s.avg_loss)}</td><td>${s.ops ? fmtMoney(s.best) : fmtMoney(0)}</td><td>${s.ops ? fmtMoney(s.worst) : ''}</td><td>${s.profit_factor == null ? '' : s.profit_factor.toFixed(2)}</td></tr>`;
    $('#repBody').innerHTML = `
<div class="rep-head"><h2>OPTIONS BB &nbsp;|&nbsp; Reporte de Desempeño por Estrategia</h2>
  <p>Símbolo: <b>${esc(m.symbol || '—')}</b> &nbsp;|&nbsp; Periodo: ${esc(m.period_start || '—')} → ${esc(m.period_end || '—')} &nbsp;|&nbsp; Fuente: ${esc(m.source || 'Thinkorswim Strategy Report')}${m.is_demo ? ' &nbsp;<span class="status-pill warn">DEMO · cifras ilustrativas</span>' : ''}</p></div>
<div class="kpis" style="margin:0;border-radius:0;gap:0">
  <div class="kpi navy" style="border-radius:0"><small>Operaciones cerradas</small><b>${T.ops}</b></div>
  <div class="kpi gr" style="border-radius:0"><small>Ganadas</small><b>${T.wins}</b></div>
  <div class="kpi rd" style="border-radius:0"><small>Perdidas</small><b>${T.losses}</b></div>
  <div class="kpi teal" style="border-radius:0"><small>% Acierto global</small><b>${T.hit_rate == null ? '—' : T.hit_rate.toFixed(1) + '%'}</b></div>
  <div class="kpi navy" style="border-radius:0"><small>P/L neto total</small><b>${fmtMoney(T.net)}</b></div>
</div>
<div style="overflow-x:auto;margin-top:12px"><table class="t rep"><thead><tr><th>Estrategia</th><th>Operaciones</th><th>Ganadas</th><th>Perdidas</th><th>% Acierto</th><th>P/L Neto</th><th>Ganancia Prom.</th><th>Pérdida Prom.</th><th>Mejor Op.</th><th>Peor Op.</th><th>Factor Ben.</th></tr></thead><tbody>${S.map(row).join('')}
<tr class="tot"><td style="color:#fff">TOTAL</td><td>${T.ops}</td><td>${T.wins}</td><td>${T.losses}</td><td>${T.hit_rate == null ? '' : T.hit_rate.toFixed(1) + '%'}</td><td>${fmtMoney(T.net)}</td><td></td><td></td><td></td><td></td><td></td></tr></tbody></table></div>
${r.notes.map(n => `<p class="note" style="font-style:italic">Nota: ${esc(n)}</p>`).join('')}
<div class="note">Expectativa por operación ${fmtMoney(T.expectancy)} · Máx. retroceso (drawdown) ${fmtMoney(T.max_dd)}. Un backtest describe el pasado: no garantiza resultados futuros.</div>
<div class="charts">
  <div class="chart-card"><h3>% de Acierto por Estrategia</h3>${svgBars({ cats: S.map(s => s.name), series: [{ name: '% Acierto', color: '#1180a8', values: S.map(s => s.hit_rate == null ? null : s.hit_rate / 100) }], pct: true })}</div>
  <div class="chart-card"><h3>Ganadas vs Perdidas por Estrategia</h3>${svgBars({ cats: S.map(s => s.name), series: [{ name: 'Ganadas', color: '#1fa34a', values: S.map(s => s.wins) }, { name: 'Perdidas', color: '#dc2434', values: S.map(s => s.losses) }] })}</div>
</div>
<div class="eq-card"><b>Curva de P/L acumulado</b> <span class="muted">(cada punto es una operación cerrada; verde = ganada, rojo = perdida)</span>${svgEquity(r.equity)}</div>
<details class="help" style="margin-top:12px"><summary><b>Operaciones (${r.trades.length})</b></summary><div class="tbl-scroll" style="max-height:340px"><table class="t"><thead><tr><th>#</th><th>Estrategia</th><th>Entrada</th><th>Salida</th><th class="r">P/L</th><th class="r">Acumulado</th></tr></thead><tbody>${r.equity.map((q, i) => `<tr><td>${q.n}</td><td>${esc(q.strategy)}</td><td>${esc(r.trades[i]?.entry_ts || '')}</td><td>${esc(q.ts || '')}</td><td class="r ${cls(q.pnl)}">${fmtMoney(q.pnl)}</td><td class="r ${cls(q.cum)}">${fmtMoney(q.cum)}</td></tr>`).join('')}</tbody></table></div></details>`;
  },
  destroy() { clearTimers(); },
};

/* ------------------------------ Cuenta / Admin ------------------------------ */
OBB.views.cuenta = {
  async render(el) {
    const u = OBB.state.user, admin = u.role === 'admin', self = this;
    const pill = u.reason === 'admin' ? '<span class="status-pill ok">ADMINISTRADOR</span>' : u.reason === 'active' ? '<span class="status-pill ok">SUSCRIPCIÓN ACTIVA</span>'
      : u.reason === 'reward' ? `<span class="status-pill ok">REGALO POR REFERIDOS · ${u.reward_days_left} día(s)</span>` : u.reason === 'trial' ? `<span class="status-pill warn">PRUEBA GRATIS · ${u.trial_days_left} día(s)</span>` : '<span class="status-pill bad">SIN ACCESO</span>';
    const msg = { expired: 'Tu prueba gratis terminó. Suscríbete para volver a entrar.', canceled: 'Tu suscripción fue cancelada. Reactívala para volver a entrar.', past_due: 'Tu último pago falló. Actualiza tu método de pago para recuperar el acceso.' }[u.reason];
    el.innerHTML = `
<div class="view-title"><h1>Mi <span>cuenta</span></h1></div>
${!u.access ? `<div class="panel red paywall"><h2>Acceso suspendido</h2><p>${esc(msg || 'Tu acceso no está activo.')}</p></div><br>` : ''}
<div class="acct">
  <section class="panel cyan"><h2>Plan</h2><p>${pill}</p>
    <dl class="kv"><dt>Plan</dt><dd>${esc(u.plan_name)}</dd><dt>Correo</dt><dd>${esc(u.email)}</dd><dt>Nombre</dt><dd>${esc(u.name || '—')}</dd>
    ${u.reason === 'active' && u.sub_ends ? `<dt>Próxima renovación</dt><dd>${fmtTs(u.sub_ends)}</dd>` : ''}
    ${u.reason === 'trial' ? `<dt>La prueba termina</dt><dd>${fmtTs(u.trial_ends)}</dd>` : ''}</dl>
    <div class="stack">
      ${u.reason !== 'admin' ? `<button class="btn green" id="btnSub">${u.reason === 'active' ? 'Cambiar plan' : 'Suscribirme'}</button>` : ''}
      ${['active', 'past_due'].includes(u.reason) || u.sub_status === 'active' ? '<button class="btn ghost" id="btnPortal">Administrar suscripción / facturas</button>' : ''}
      <button class="btn ghost" id="btnOut">Cerrar sesión</button></div>
    <p class="note" id="billNote"></p></section>
  ${admin ? `
  <section class="panel yellow"><h2>Estado del sistema</h2><div id="sysBox" class="muted">Cargando…</div></section>
  <section class="panel green"><h2>Conexión con Schwab</h2><div id="schwabBox"></div></section>
  <section class="panel blue"><h2>Datos y listas</h2>
    <p class="note">Fotos de open interest (se toman solas a las 9:00 am y 4:15 pm ET; aquí puedes forzarlas):</p>
    <div class="stack"><button class="btn" data-snap="CLOSE">Foto de CIERRE (volumen) ahora</button><button class="btn" data-snap="MORNING">Foto de MAÑANA (OI) ahora</button></div>
    <p class="note" style="margin-top:14px">Acciones por sector (Excel con columnas “Sector” y lista separada por comas):</p>
    <label class="btn ghost" style="display:inline-block;cursor:pointer">Subir Excel<input type="file" id="wlFile" accept=".xlsx" hidden></label></section>` : ''}
</div>
${admin ? `<section class="panel cyan" style="margin-top:14px"><h2>Usuarios</h2><div class="tbl-scroll" style="max-height:420px;overflow-x:auto" id="usersBox"><div class="empty">Cargando…</div></div></section>` : ''}`;

    $('#btnOut').onclick = async () => { await api('/api/auth/logout', { method: 'POST', body: {} }).catch(() => { }); OBB.state.user = null; OBB.showAuth(); };
    const pay = async (path, btn) => { btn.disabled = true; try { location.href = (await api(path, { method: 'POST', body: {} })).url; } catch (e) { $('#billNote').textContent = e.message; } btn.disabled = false; };
    $('#btnSub') && ($('#btnSub').onclick = () => OBB.go('planes'));
    $('#btnPortal') && ($('#btnPortal').onclick = e => pay('/api/billing/portal', e.target));
    if (!admin) return;
    this.loadSys(); this.loadUsers();
    el.addEventListener('change', async e => { const sp = e.target.closest('[data-setplan]'); if (sp) { try { await api('/api/admin/users/' + sp.dataset.setplan, { method: 'POST', body: { action: 'set_plan', value: sp.value } }); toast('Plan actualizado'); } catch (er) { toast(er.message, true); } } });
    el.addEventListener('click', async e => {
      const snap = e.target.closest('[data-snap]');
      if (snap) { snap.disabled = true; toast('Tomando foto… puede tardar un minuto'); try { const r = await api('/api/admin/snapshot', { method: 'POST', body: { kind: snap.dataset.snap } }); toast(`Foto guardada: ${fmtInt(r.rows)} contratos`); } catch (er) { toast(er.message, true); } snap.disabled = false; return; }
      const ua = e.target.closest('[data-uid]');
      if (ua) { try { await api('/api/admin/users/' + ua.dataset.uid, { method: 'POST', body: { action: ua.dataset.act, value: ua.dataset.val } }); toast('Usuario actualizado'); self.loadUsers(); } catch (er) { toast(er.message, true); } return; }
      if (e.target.id === 'schwabGo') {
        try { const d = await api('/api/admin/schwab/login'); $('#schwabLink').innerHTML = `<p>1) <a href="${esc(d.url)}" target="_blank" rel="noopener">Abre el login de Schwab</a> y autoriza la app.</p><p>2) Tu navegador terminará en una página que no carga (<code>${esc(d.callback)}</code>…). Copia la URL <b>completa</b> de esa página:</p><textarea class="field" id="schwabUrl" placeholder="https://127.0.0.1:8182/?code=…"></textarea><div class="stack"><button class="btn green" id="schwabSend">Conectar</button></div>`; } catch (er) { toast(er.message, true); }
      }
      if (e.target.id === 'schwabSend') {
        try { await api('/api/admin/schwab/exchange', { method: 'POST', body: { url: $('#schwabUrl').value } }); toast('Schwab conectado'); self.loadSys(); $('#schwabLink').innerHTML = ''; } catch (er) { toast(er.message, true); }
      }
    });
    $('#wlFile').onchange = async e => { const f = e.target.files[0]; if (!f) return; try { const r = await api('/api/admin/watchlist', { method: 'POST', body: await f.arrayBuffer() }); toast(`Lista cargada: ${r.sectors} sectores, ${r.symbols} acciones`); } catch (er) { toast(er.message, true); } };
  },

  async loadSys() {
    try {
      const d = await api('/api/command'), s = d.status, ago = t => (t ? Math.round((s.now - t) / 60) + ' min' : '—');
      $('#sysBox').innerHTML = `<dl class="kv"><dt>Datos</dt><dd>${s.mode === 'demo' ? '<span class="status-pill warn">DEMO (simulados)</span>' : '<span class="status-pill ok">SCHWAB (reales)</span>'}</dd><dt>Mercado</dt><dd>${{ open: 'Abierto', pre: 'Pre-mercado', closed: 'Cerrado' }[s.market]}</dd><dt>Cotizaciones</dt><dd>hace ${ago(s.updated.quotes)}</dd><dt>Señales</dt><dd>hace ${ago(s.updated.scan)}</dd><dt>Opciones</dt><dd>hace ${ago(s.updated.chains)}</dd><dt>Errores</dt><dd class="${s.error ? 'down' : 'up'}">${esc(s.error || 'ninguno')}</dd></dl>`;
      const sc = s.schwab;
      $('#schwabBox').innerHTML = `<p>${sc.connected ? `<span class="status-pill ok">CONECTADO</span> el permiso vence en ${sc.refresh_days_left} día(s)` : sc.configured ? '<span class="status-pill warn">NO CONECTADO</span>' : '<span class="status-pill bad">SIN CREDENCIALES</span>'}</p>
        <p class="note">${sc.configured ? 'El permiso de Schwab dura 7 días: renuévalo cada semana (botón de abajo).' : 'Define SCHWAB_APP_KEY y SCHWAB_APP_SECRET (developer.schwab.com) y reinicia el servidor.'}</p>
        ${sc.configured ? '<div class="stack"><button class="btn green" id="schwabGo">Conectar / renovar Schwab</button></div><div id="schwabLink" style="margin-top:10px"></div>' : ''}`;
    } catch (e) { /* ya notificado */ }
  },

  async loadUsers() {
    try {
      const { users } = await api('/api/admin/users');
      const st = u => ({ admin: 'Admin', active: 'Activo', trial: `Prueba (${u.trial_days_left} d)`, reward: `Regalo (${u.reward_days_left} d)`, expired: 'Vencido', canceled: 'Cancelado', past_due: 'Pago fallido' }[u.reason] || u.reason);
      const b = (u, act, val, label, c = 'ghost') => `<button class="btn ${c}" style="padding:3px 9px;font-size:12px" data-uid="${u.id}" data-act="${act}" data-val="${val}">${label}</button>`;
      $('#usersBox').innerHTML = `<table class="t"><thead><tr><th>Correo</th><th>Nombre</th><th>Estado</th><th>Plan</th><th>Registro</th><th>Acciones</th></tr></thead><tbody>${users.map(u => `<tr><td>${esc(u.email)}</td><td>${esc(u.name)}</td><td><span class="status-pill ${u.access ? (u.reason === 'trial' ? 'warn' : 'ok') : 'bad'}">${st(u)}</span></td><td><select class="field" data-setplan="${u.id}" style="padding:3px 6px">${['basico', 'intermedio', 'avanzado'].map(p => `<option value="${p}" ${u.plan_set === p ? 'selected' : ''}>${PLAN_NAME[p]}</option>`).join('')}</select></td><td>${fmtTs(u.created_at)}</td><td>${b(u, 'grant_days', 30, '+30 días pago', 'green')} ${b(u, 'extend_trial', 7, '+7 prueba')} ${u.reason === 'admin' ? '' : b(u, 'revoke', 0, 'Revocar', 'red')} ${b(u, 'set_role', u.role === 'admin' ? 'user' : 'admin', u.role === 'admin' ? 'Quitar admin' : 'Hacer admin')}</td></tr>`).join('')}</tbody></table>`;
    } catch (e) { /* ya notificado */ }
  },
  destroy() { clearTimers(); },
};
