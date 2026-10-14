/* v3.1: Referidos — enlace propio, progreso hacia los premios, historial y panel del administrador */
(function () {
  const fmtD = ts => ts ? new Date(ts * 1000).toLocaleDateString(LOC(), { day: 'numeric', month: 'short', year: 'numeric' }) : '—';
  const copy = async (txt, btn) => { try { await navigator.clipboard.writeText(txt); toast('Copiado'); } catch (e) { const i = btn.previousElementSibling; if (i && i.select) { i.select(); } toast('Selecciona el texto y cópialo', true); } };

  function ladder(d) {
    const ms = d.rules.milestones, top = Math.max(...ms.map(m => m.n), 1), pct = Math.min(d.qualified / top * 100, 100);
    const stops = [{ n: 1, label: `${d.rules.disc_pct}% de descuento por cada referido`, kind: 'disc' }, ...ms.map(m => ({ n: m.n, label: `${m.months} meses gratis · plan Avanzado`, kind: 'free' }))];
    return `<div class="rladder"><div class="rtrack"><i style="width:${pct}%"></i>
      ${stops.map(s => `<span class="rstop ${d.qualified >= s.n ? 'done' : ''}" style="left:${Math.min(s.n / top * 100, 100)}%" title="${esc(s.label)}"><b>${s.n}</b></span>`).join('')}</div>
      <div class="rlegend">${stops.map(s => `<div class="${d.qualified >= s.n ? 'done' : ''}"><b>${s.n} referido${s.n > 1 ? 's' : ''}</b><span>${esc(s.label)}</span></div>`).join('')}</div></div>`;
  }

  OBB.views.referidos = {
    async render(el) {
      const admin = OBB.state.user.role === 'admin';
      el.innerHTML = '<div class="view-title"><h1>Programa de <span>referidos</span></h1><span class="muted">Invita a otros traders y gana descuentos y meses gratis</span></div><div id="rfBody"><div class="empty">Cargando…</div></div>';
      let d; try { d = await api('/api/referrals'); } catch (e) { $('#rfBody').innerHTML = errBoxR(e); return; }
      const until = d.reward_until && d.reward_until * 1000 > Date.now() ? d.reward_until : null;
      const next = d.next;
      $('#rfBody').innerHTML = `
      ${until ? `<div class="promo">🎁 Tienes <b>plan Avanzado gratis</b> hasta el <b>${fmtD(until)}</b>, ganado con tus referidos.</div>` : ''}
      <section class="panel green"><h2>Tu enlace para invitar</h2>
        <p>Cuando alguien se registre con tu enlace y <b>pague su suscripción</b>, cuenta como referido tuyo. Tomar la prueba gratis no cuenta todavía.</p>
        <div class="bar"><input class="field" id="rfLink" readonly value="${esc(d.link)}" style="flex:1;min-width:240px" aria-label="Tu enlace de referido"><button class="btn green" id="rfCopy">Copiar enlace</button></div>
        <div class="bar"><span class="muted">O dale tu código:</span><b class="rfcode" id="rfCode">${esc(d.code)}</b><button class="btn ghost" id="rfCopyCode">Copiar código</button></div></section>
      <section class="panel yellow"><h2>Tu progreso</h2>
        <div class="kpis">${kpi('Se registraron', d.registered)}${kpi('Ya se suscribieron', d.qualified, 'up')}${kpi('Descuentos por usar', d.discounts_waiting)}${kpi(next ? `Faltan para ${next.months} meses gratis` : 'Metas', next ? d.missing : '¡Todas logradas!')}</div>
        ${ladder(d)}
        <ul class="rrules"><li>Por <b>cada</b> referido que se suscribe: <b>${d.rules.disc_pct}% de descuento</b> en tu siguiente mes. Si ganas varios, se aplican uno por mes.</li>
        ${d.rules.milestones.map(m => `<li>Al llegar a <b>${m.n} referidos</b>: <b>${m.months} meses completamente gratis</b> de la suscripción nivel Avanzado.</li>`).join('')}
        <li>Los premios por metas se suman: llegar a la siguiente no borra el anterior.</li></ul></section>
      <div class="grid2"><section class="panel cyan"><h2>Tus referidos</h2>${d.referred.length ? `<table class="t"><thead><tr><th>Persona</th><th>Estado</th><th>Desde</th></tr></thead><tbody>${d.referred.map(r => `<tr><td>${esc(r.who)}</td><td>${r.status === 'qualified' ? '<span class="status-pill ok">SE SUSCRIBIÓ</span>' : '<span class="status-pill warn">EN PRUEBA</span>'}</td><td>${fmtD(r.date)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">Aún nadie se registró con tu enlace. Compártelo en tu canal de YouTube, tus redes o por mensaje.</div>'}</section>
      <section class="panel"><h2>Tus premios</h2>${d.rewards.length ? `<table class="t"><thead><tr><th>Premio</th><th>Estado</th><th>Fecha</th></tr></thead><tbody>${d.rewards.map(w => `<tr><td>${w.kind === 'free' ? `🎁 ${w.months} meses gratis (${w.milestone} referidos)` : `${w.pct}% de descuento`}</td><td>${({ pending: 'En cola', active: 'Se aplicará en tu próximo cobro', used: 'Usado', applied: 'Activo' })[w.status] || w.status}</td><td>${fmtD(w.date)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">Tus premios aparecerán aquí.</div>'}</section></div>
      ${d.has_referrer ? '' : `<section class="panel"><h2>¿Alguien te invitó?</h2><div class="bar"><input class="field" id="rfClaim" maxlength="12" placeholder="Código de quien te invitó" style="text-transform:uppercase;width:220px" aria-label="Código de referido"><button class="btn ghost" id="rfClaimGo">Agregar código</button></div><p class="muted">Solo puedes agregarlo antes de suscribirte.</p></section>`}
      ${admin ? '<div id="rfAdmin"></div>' : ''}`;
      $('#rfCopy').onclick = e => copy(d.link, e.target); $('#rfCopyCode').onclick = e => copy(d.code, e.target);
      const cg = $('#rfClaimGo'); if (cg) cg.onclick = async () => { try { await api('/api/referrals/claim', { method: 'POST', body: { code: $('#rfClaim').value } }); toast('Código agregado'); OBB.views.referidos.render(el); } catch (e) { toast(e.message, true); } };
      if (admin) this.admin();
    },
    async admin() {
      const host = $('#rfAdmin'); if (!host) return;
      const load = async () => {
        const a = await api('/api/admin/referrals'), r = a.rules;
        host.innerHTML = `<section class="panel yellow"><h2>Administrador · reglas del programa</h2><div class="g3">${fld('rfPct', 'Descuento por referido (%)', r.disc_pct, 'type="number" min="0" max="100"')}${r.milestones.map((m, i) => fld('rfN' + i, `Meta ${i + 1}: referidos`, m.n, 'type="number" min="1"') + fld('rfM' + i, `Meta ${i + 1}: meses gratis`, m.months, 'type="number" min="1" max="60"')).join('')}</div>
          <div class="bar"><button class="btn green" id="rfSaveRules">Guardar reglas</button><span class="muted">Los cambios aplican a referidos futuros.</span></div></section>
        <section class="panel"><h2>Administrador · referidos en prueba (aún no pagan)</h2>${a.pending.length ? `<table class="t"><thead><tr><th>Invitado</th><th>Lo invitó</th><th>Desde</th><th></th></tr></thead><tbody>${a.pending.map(p => `<tr><td>${esc(p.referred)}</td><td>${esc(p.referrer)}</td><td>${fmtD(p.created_at)}</td><td><button class="btn ghost" data-q="${p.referred_id}" style="padding:3px 10px">Marcar como pagado</button></td></tr>`).join('')}</tbody></table><p class="muted">Con Stripe activo esto es automático al primer pago. «Marcar como pagado» sirve para cobros fuera de Stripe o para pruebas.</p>` : '<div class="empty">No hay referidos pendientes.</div>'}</section>
        <section class="panel"><h2>Administrador · premios por aplicar a mano</h2>${a.manual.length ? `<table class="t"><thead><tr><th>Usuario</th><th>Premio</th><th>Nota</th><th></th></tr></thead><tbody>${a.manual.map(w => `<tr><td>${esc(w.email)}</td><td>${w.kind === 'free' ? w.months + ' meses gratis' : w.pct + '% de descuento'}</td><td>${esc(w.note)}</td><td><button class="btn ghost" data-done="${w.id}" style="padding:3px 10px">Ya lo apliqué</button></td></tr>`).join('')}</tbody></table>` : '<div class="empty">Nada pendiente.</div>'}</section>
        <section class="panel"><h2>Administrador · quienes más refieren</h2>${a.top.length ? `<table class="t"><thead><tr><th>Usuario</th><th>Registrados</th><th>Suscritos</th></tr></thead><tbody>${a.top.map(t => `<tr><td>${esc(t.email)}</td><td>${t.total}</td><td><b>${t.q}</b></td></tr>`).join('')}</tbody></table>` : '<div class="empty">Todavía no hay referidos.</div>'}</section>`;
        $('#rfSaveRules').onclick = async () => {
          try { await api('/api/admin/referrals/rules', { method: 'POST', body: { disc_pct: +$('#rfPct').value, milestones: r.milestones.map((_, i) => ({ n: +$('#rfN' + i).value, months: +$('#rfM' + i).value })) } }); toast('Reglas guardadas'); load(); } catch (e) { toast(e.message, true); }
        };
        host.querySelectorAll('[data-q]').forEach(b => b.onclick = async () => { try { await api('/api/admin/referrals/qualify', { method: 'POST', body: { user_id: +b.dataset.q } }); toast('Referido confirmado'); OBB.views.referidos.render($('#main')); } catch (e) { toast(e.message, true); } });
        host.querySelectorAll('[data-done]').forEach(b => b.onclick = async () => { try { await api('/api/admin/referrals/reward/' + b.dataset.done + '/done', { method: 'POST', body: {} }); load(); } catch (e) { toast(e.message, true); } });
      };
      try { await load(); } catch (e) { host.innerHTML = ''; }
    },
    destroy() { clearTimers(); },
  };
  const errBoxR = e => `<div class="panel red"><h2>No pude cargar tus referidos</h2><p>${esc(e.message)}</p></div>`;
  const kpi = (l, v, c = '') => `<div class="kpi"><small>${l}</small><b class="${c}">${v}</b></div>`;
})();
