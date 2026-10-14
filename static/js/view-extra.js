/* Planes, Biblioteca de videos y Señales (estrategias de mentores + personalizadas) */
const safeUrl = u => (typeof u === 'string' && /^https:\/\//.test(u) ? u : '#');
const PLAN_NAME = { basico: 'Básico', intermedio: 'Intermedio', avanzado: 'Avanzado' };

/* ------------------------------ Planes ------------------------------ */
OBB.views.planes = {
  async render(el) {
    const u = OBB.state.user, admin = u.role === 'admin';
    let d; try { d = await refreshMe(); } catch (e) { return; }
    const plans = d.plans, billing = d.billing;
    const trial = u.reason === 'trial' ? `<div class="promo">Estás en prueba gratis del plan <b>${esc(u.plan_name)}</b> · te quedan <b>${u.trial_days_left}</b> día(s). Elige el plan con el que quieres continuar.</div>` : '';
    el.innerHTML = `<div class="view-title"><h1>Planes de <span>suscripción</span></h1><span class="muted">Mensual · cancela cuando quieras</span></div>${trial}
<div class="plans">${plans.map(p => `<section class="panel ${p.id === 'basico' ? 'cyan' : p.id === 'intermedio' ? 'yellow' : 'green'} plan ${p.current ? 'cur' : ''}">
  <h2>${esc(p.name)}</h2><p class="muted" style="margin:-4px 0 8px">${esc(p.tagline)}</p>
  <div class="price">${p.price_label ? esc(p.price_label) : '<small>Consulta el precio</small>'}</div>
  <ul>${p.features.map(f => `<li>${esc(f)}</li>`).join('')}</ul>
  <div class="mini"><b>${p.bull}</b> ${p.bull === 1 ? 'alcista' : 'alcistas'} · <b>${p.bear}</b> ${p.bear === 1 ? 'bajista' : 'bajistas'}${p.custom ? ` · <b>${p.custom}</b> personalizadas` : ''}</div>
  ${p.current && u.reason === 'active' ? '<div class="status-pill ok">TU PLAN ACTUAL</div>' : admin ? '' : `<button class="btn ${p.id === 'avanzado' ? 'green' : ''}" data-plan="${p.id}" ${p.checkout ? '' : 'data-nocheckout="1"'}>${u.reason === 'active' ? 'Cambiar a ' + esc(p.name) : 'Suscribirme a ' + esc(p.name)}</button>`}
  ${p.current && u.reason !== 'active' ? `<div class="note">${u.reason === 'trial' ? 'Plan de tu prueba' : ''}</div>` : ''}
  ${admin ? `<div class="stack"><input class="field" style="width:150px" data-price="${p.id}" value="${esc(p.price_label)}" placeholder="Ej. $29/mes" maxlength="40"><button class="btn ghost" data-saveprice="${p.id}">Guardar precio</button></div>` : ''}
</section>`).join('')}</div>
<p class="note" id="planNote">${billing ? '' : 'El cobro automático aún no está activado: escribe a jroa@optionsbb.com para activar tu plan.'}</p>
<div class="matrix panel blue"><h2>Comparación</h2><table class="t"><thead><tr><th></th>${plans.map(p => `<th class="c">${esc(p.name)}</th>`).join('')}</tr></thead><tbody>
${[['Centro de Comando (acciones)', 'comando'], ['Cover Call', 'covercall'], ['Biblioteca de videos', 'videos'], ['Flujo OI', 'flujo'], ['Sectores', 'sectores'], ['Desempeño', 'desempeno'], ['Señales de mentores', 'senales']].map(([l, m]) => `<tr><td>${l}</td>${plans.map(p => `<td class="c">${p.modules.includes(m) ? '<span class="up">✔</span>' : '<span class="muted">—</span>'}</td>`).join('')}</tr>`).join('')}
<tr><td>Estrategias alcistas</td>${plans.map(p => `<td class="c">${p.bull}</td>`).join('')}</tr><tr><td>Estrategias bajistas</td>${plans.map(p => `<td class="c">${p.bear}</td>`).join('')}</tr>
<tr><td>Estrategias personalizadas</td>${plans.map(p => `<td class="c">${p.custom || '—'}</td>`).join('')}</tr></tbody></table></div>`;
    el.onclick = async e => {
      const b = e.target.closest('[data-plan]'), sp = e.target.closest('[data-saveprice]');
      if (b) {
        if (b.dataset.nocheckout) { $('#planNote').textContent = billing ? 'Este plan aún no tiene precio configurado en Stripe.' : 'El cobro automático aún no está activado: escribe a jroa@optionsbb.com para activar el plan ' + PLAN_NAME[b.dataset.plan] + '.'; return; }
        b.disabled = true; try { location.href = (await api('/api/billing/checkout', { method: 'POST', body: { plan: b.dataset.plan } })).url; } catch (er) { toast(er.message, true); } b.disabled = false;
      }
      if (sp) { try { await api('/api/admin/plan-price', { method: 'POST', body: { plan: sp.dataset.saveprice, label: $(`[data-price="${sp.dataset.saveprice}"]`).value } }); toast('Precio guardado'); } catch (er) { toast(er.message, true); } }
    };
  },
};

/* ------------------------------ Videos ------------------------------ */
OBB.views.videos = {
  cat: 'Todas', q: '',
  async render(el) {
    const admin = OBB.state.user.role === 'admin', self = this;
    let d; try { d = await api('/api/videos'); } catch (e) { return; }
    const draw = () => {
      const cats = ['Todas', ...new Set(d.videos.map(v => v.category))];
      const vids = d.videos.filter(v => (self.cat === 'Todas' || v.category === self.cat) && (!self.q || (v.title + ' ' + v.description).toLowerCase().includes(self.q.toLowerCase())));
      $('#vGrid').innerHTML = vids.length ? vids.map(v => `<article class="vid ${v.locked ? 'locked' : ''}" data-id="${v.id}">
        <button class="thumb" data-play="${v.id}" aria-label="${esc(v.title)}">${v.locked ? `<div class="lock">🔒<small>Plan ${esc(v.min_plan_name)}</small></div>` : `<img loading="lazy" src="https://i.ytimg.com/vi/${esc(v.yt_id)}/hqdefault.jpg" alt=""><span class="play">▶</span>`}</button>
        <div class="vi"><b>${esc(v.title)}</b><small class="muted">${esc(v.category)}${v.min_plan !== 'basico' ? ' · Plan ' + esc(v.min_plan_name) + '+' : ''}</small>${v.description ? `<p>${esc(v.description)}</p>` : ''}
        ${admin ? `<div class="stack"><select class="field" data-minplan="${v.id}">${['basico', 'intermedio', 'avanzado'].map(p => `<option value="${p}" ${v.min_plan === p ? 'selected' : ''}>${PLAN_NAME[p]}+</option>`).join('')}</select><button class="btn red" style="padding:3px 10px" data-del="${v.id}">Quitar</button></div>` : ''}</div></article>`).join('')
        : `<div class="empty">${d.videos.length ? 'No hay videos con ese filtro.' : admin ? 'Aún no hay videos. Agrega el primero con su enlace de YouTube.' : 'Pronto verás aquí los videos del canal.'}</div>`;
      $('#vCats').innerHTML = cats.map(c => `<button class="${c === self.cat ? 'on' : ''}" data-cat="${esc(c)}">${esc(c)}</button>`).join('');
    };
    el.innerHTML = `<div class="view-title"><h1>Biblioteca de <span>videos</span></h1><span class="muted">Del canal de YouTube de Options BB</span></div>
<div class="bar"><a class="btn red" href="${esc(safeUrl(d.links.youtube))}" target="_blank" rel="noopener noreferrer">▶ Canal de YouTube</a><a class="btn" href="${esc(safeUrl(d.links.web))}" target="_blank" rel="noopener noreferrer">◍ Sitio web</a>
  <input type="text" class="field" id="vQ" placeholder="Buscar video…" style="min-width:200px" value="${esc(self.q)}"></div>
<div class="seg wrap" id="vCats" style="margin-bottom:12px"></div>
${admin ? `<section class="panel yellow" style="margin-bottom:14px"><h2>Agregar video</h2><div class="cc-form">
  <div><label>Enlace o ID de YouTube</label><input class="field" id="vUrl" placeholder="https://youtu.be/…"></div>
  <div><label>Título <span class="muted">(vacío = lo tomo de YouTube)</span></label><input class="field" id="vTitle" maxlength="160"></div>
  <div><label>Categoría</label><select class="field" id="vCat">${d.categories.map(c => `<option>${esc(c)}</option>`).join('')}</select></div>
  <div><label>Disponible desde el plan</label><select class="field" id="vPlan"><option value="basico">Básico</option><option value="intermedio">Intermedio</option><option value="avanzado">Avanzado</option></select></div>
  <div style="grid-column:1/-1"><label>Descripción (opcional)</label><input class="field" id="vDesc" maxlength="600"></div></div>
  <div class="stack"><button class="btn green" id="vAdd">Agregar</button>${d.can_sync ? '<button class="btn" id="vSync">Traer últimos videos del canal</button>' : ''}</div>
  ${d.can_sync ? '' : '<p class="note">Para importar automáticamente los últimos videos del canal, define OBB_YT_CHANNEL_ID (empieza con “UC…”) y reinicia.</p>'}</section>` : ''}
<div class="vgrid" id="vGrid"></div>`;
    draw();
    $('#vQ').oninput = e => { self.q = e.target.value; draw(); };
    el.onclick = async e => {
      const c = e.target.closest('[data-cat]'), p = e.target.closest('[data-play]'), del = e.target.closest('[data-del]');
      if (c) { self.cat = c.dataset.cat; draw(); return; }
      if (p) {
        const v = d.videos.find(x => x.id == p.dataset.play);
        if (v.locked) { OBB.go('planes'); toast(`Este video es del plan ${v.min_plan_name} o superior`); return; }
        const m = document.createElement('div'); m.className = 'modal'; m.innerHTML = `<div class="mbox"><button class="x" aria-label="Cerrar">✕</button><div class="frame"><iframe src="https://www.youtube-nocookie.com/embed/${esc(v.yt_id)}?rel=0&autoplay=1" title="${esc(v.title)}" allow="accelerometer; encrypted-media; picture-in-picture; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></div><div class="mt"><b>${esc(v.title)}</b> <a href="https://www.youtube.com/watch?v=${esc(v.yt_id)}" target="_blank" rel="noopener noreferrer">Ver en YouTube</a></div></div>`;
        m.onclick = ev => { if (ev.target === m || ev.target.className === 'x') m.remove(); }; document.body.appendChild(m); return;
      }
      if (del && confirm('¿Quitar este video de la biblioteca?')) { try { await api('/api/admin/videos/' + del.dataset.del, { method: 'DELETE' }); self.render(el); } catch (er) { toast(er.message, true); } return; }
      if (e.target.id === 'vAdd') {
        try { await api('/api/admin/videos', { method: 'POST', body: { url: $('#vUrl').value, title: $('#vTitle').value, category: $('#vCat').value, min_plan: $('#vPlan').value, description: $('#vDesc').value } }); toast('Video agregado'); self.render(el); } catch (er) { toast(er.message, true); }
      }
      if (e.target.id === 'vSync') { try { const r = await api('/api/admin/videos/sync', { method: 'POST', body: {} }); toast(`Videos nuevos: ${r.added}`); self.render(el); } catch (er) { toast(er.message, true); } }
    };
    el.onchange = async e => { const s = e.target.closest('[data-minplan]'); if (s) { try { await api('/api/admin/videos/' + s.dataset.minplan, { method: 'POST', body: { min_plan: s.value } }); toast('Plan del video actualizado'); self.render(el); } catch (er) { toast(er.message, true); } } };
  },
};

/* ------------------------------ Señales ------------------------------ */
const COND = {
  sma_cross: { label: 'Cruce de medias móviles', f: [['fast', 'Rápida', 'int', 9], ['slow', 'Lenta', 'int', 21], ['dir', 'Dirección', ['up|Al alza', 'down|A la baja'], 'up']] },
  price_sma: { label: 'Precio vs media móvil', f: [['n', 'Periodo', 'int', 21], ['dir', 'Precio', ['above|Sobre la media', 'below|Bajo la media'], 'above']] },
  breakout: { label: 'Breakout alcista / bajista (ruptura)', f: [['n', 'Velas', 'int', 20], ['dir', 'Dirección', ['up|Alcista: rompe el máximo', 'down|Bajista: rompe el mínimo'], 'up'], ['vol_mult', 'Volumen mínimo (× promedio, 0 = no exigir)', 'num', 0]] },
  golden_cross: { label: 'Cruz dorada / cruz de la muerte', f: [['fast', 'Rápida', 'int', 50], ['slow', 'Lenta', 'int', 200], ['dir', 'Cruce', ['golden|Cruz dorada (alcista)', 'death|Cruz de la muerte (bajista)'], 'golden']] },
  doji: { label: 'Vela doji', f: [['max_body_pct', 'Cuerpo máximo % del rango', 'num', 10], ['kind', 'Tipo', ['any|Doji', 'dragonfly|Doji libélula (mecha abajo)', 'gravestone|Doji lápida (mecha arriba)'], 'any']] },
  engulfing: { label: 'Vela envolvente', f: [['dir', 'Tipo', ['bull|Envolvente alcista', 'bear|Envolvente bajista'], 'bull'], ['trend_bars', 'Tendencia previa en velas (0 = no exigir)', 'int', 0]] },
  candle: { label: 'Color de la vela', f: [['color', 'Color', ['green|Verde', 'red|Roja'], 'green'], ['min_body_pct', 'Cuerpo mínimo %', 'num', 50]] },
  streak: { label: 'Velas seguidas del mismo color', f: [['n', 'Cantidad', 'int', 3], ['color', 'Color', ['green|Verdes', 'red|Rojas'], 'red']] },
  volume_spike: { label: 'Volumen explosivo', f: [['mult', 'Veces el promedio', 'num', 2], ['n', 'Promedio de velas', 'int', 20]] },
  rsi: { label: 'RSI', f: [['n', 'Periodo', 'int', 14], ['op', 'Es', ['lt|Menor que', 'gt|Mayor que'], 'lt'], ['value', 'Nivel', 'num', 30]] },
  pct_move: { label: 'Cambio de precio %', f: [['bars', 'En velas', 'int', 6], ['op', 'Es', ['gt|Mayor que', 'lt|Menor que'], 'gt'], ['pct', 'Porcentaje', 'num', 1.5]] },
};

/* plantillas rápidas: un clic arma el indicador completo */
const RB_TEMPLATES = [
  ['gold', 'Cruz dorada (SMA 50 sobre SMA 200)', 'BULL', [{ type: 'golden_cross', fast: 50, slow: 200, dir: 'golden' }]],
  ['death', 'Cruz de la muerte (SMA 50 bajo SMA 200)', 'BEAR', [{ type: 'golden_cross', fast: 50, slow: 200, dir: 'death' }]],
  ['bkup', 'Breakout alcista con volumen', 'BULL', [{ type: 'breakout', n: 20, dir: 'up', vol_mult: 1.5 }]],
  ['bkdn', 'Breakout bajista con volumen', 'BEAR', [{ type: 'breakout', n: 20, dir: 'down', vol_mult: 1.5 }]],
  ['doji', 'Doji tras caída (posible giro)', 'BULL', [{ type: 'streak', n: 3, color: 'red' }, { type: 'doji', max_body_pct: 10, kind: 'any' }]],
  ['engb', 'Envolvente alcista tras caída', 'BULL', [{ type: 'engulfing', dir: 'bull', trend_bars: 4 }]],
  ['engr', 'Envolvente bajista tras alza', 'BEAR', [{ type: 'engulfing', dir: 'bear', trend_bars: 4 }]],
];

function ruleBuilder(host, { meta, onSave, saveLabel }) {
  let conds = [{ type: 'candle', color: 'green', min_body_pct: 50 }], side = 'BULL';
  const row = (c, i) => `<div class="cond" data-i="${i}"><select class="field" data-t="type">${Object.entries(COND).map(([k, v]) => `<option value="${k}" ${c.type === k ? 'selected' : ''}>${v.label}</option>`).join('')}</select>
    ${COND[c.type].f.map(([k, l, t]) => `<label class="inl">${l} ${Array.isArray(t) ? `<select class="field" data-k="${k}">${t.map(o => { const [v, n] = o.split('|'); return `<option value="${v}" ${c[k] === v ? 'selected' : ''}>${n}</option>`; }).join('')}</select>` : `<input class="field" data-k="${k}" inputmode="decimal" value="${esc(c[k])}" style="width:74px">`}</label>`).join('')}
    <button class="btn ghost" data-rm="${i}" style="padding:3px 9px" ${conds.length < 2 ? 'disabled' : ''} aria-label="Quitar condición">✕</button></div>`;
  const draw = () => {
    host.innerHTML = `<div class="cc-form">${meta ? `<div><label>Nombre</label><input class="field" id="rbName" maxlength="40" placeholder="Mi estrategia"></div>` : ''}
      <div><label>Tipo</label><div class="seg" id="rbSide"><button data-s="BULL" class="${side === 'BULL' ? 'on' : ''}">▲ Alcista</button><button data-s="BEAR" class="${side === 'BEAR' ? 'on' : ''}">▼ Bajista</button></div></div>
      ${meta === 'catalog' ? '<div><label>Mentor / fuente</label><input class="field" id="rbSrc" maxlength="60"></div><div><label>Idioma</label><select class="field" id="rbLang"><option value="ES">Español</option><option value="EN">Inglés</option></select></div><div style="grid-column:1/-1"><label>Descripción</label><input class="field" id="rbDesc" maxlength="300"></div>' : ''}</div>
      <div><label for="rbTpl">Plantillas rápidas</label><select class="field" id="rbTpl"><option value="">Elige un indicador para cargarlo…</option>${RB_TEMPLATES.map(t => `<option value="${t[0]}">${t[1]}</option>`).join('')}</select></div>
      <label style="margin-top:10px">Se activa cuando se cumplen <b>todas</b> estas condiciones en la misma vela de 5 min:</label><div id="rbConds">${conds.map(row).join('')}</div>
      <div class="stack"><button class="btn ghost" id="rbAdd" ${conds.length >= 6 ? 'disabled' : ''}>+ Condición</button><button class="btn green" id="rbSave">${saveLabel}</button></div><div class="err" id="rbErr" style="color:#ff8b95"></div>`;
  };
  const keep = () => { // conserva lo escrito antes de redibujar
    const n = $('#rbName'); if (n) host._meta = { name: n.value, src: ($('#rbSrc') || {}).value, lang: ($('#rbLang') || {}).value, desc: ($('#rbDesc') || {}).value };
  };
  const restore = () => { const m = host._meta; if (!m) return; if ($('#rbName')) $('#rbName').value = m.name || ''; if ($('#rbSrc')) $('#rbSrc').value = m.src || ''; if ($('#rbLang')) $('#rbLang').value = m.lang || 'ES'; if ($('#rbDesc')) $('#rbDesc').value = m.desc || ''; };
  const redraw = () => { keep(); draw(); restore(); };
  host.onclick = async e => {
    const sb = e.target.closest('[data-s]'), rm = e.target.closest('[data-rm]');
    if (sb) { side = sb.dataset.s; redraw(); }
    if (rm) { conds.splice(+rm.dataset.rm, 1); redraw(); }
    if (e.target.id === 'rbAdd') { conds.push({ type: 'candle', color: 'green', min_body_pct: 50 }); redraw(); }
    if (e.target.id === 'rbSave') {
      const rule = { side, conditions: conds.map(c => ({ ...c })) };
      const m = { name: ($('#rbName') || {}).value, source: ($('#rbSrc') || {}).value, language: ($('#rbLang') || {}).value, description: ($('#rbDesc') || {}).value };
      try { await onSave(rule, m); conds = [{ type: 'candle', color: 'green', min_body_pct: 50 }]; host._meta = null; draw(); } catch (er) { $('#rbErr').textContent = er.message; }
    }
  };
  host.onchange = e => {
    if (e.target.id === 'rbTpl') { const t = RB_TEMPLATES.find(v => v[0] === e.target.value); if (t) { side = t[2]; conds = t[3].map(c => ({ ...c })); keep(); draw(); restore(); const n = $('#rbName'); if (n && !n.value) n.value = t[1].split(' (')[0]; } return; }
    const c = e.target.closest('.cond'); if (!c) return; const i = +c.dataset.i;
    if (e.target.dataset.t) { const t = e.target.value; conds[i] = { type: t }; COND[t].f.forEach(([k, , , d]) => { conds[i][k] = d; }); redraw(); }
    else if (e.target.dataset.k) conds[i][e.target.dataset.k] = e.target.tagName === 'SELECT' ? e.target.value : e.target.value.replace(',', '.');
  };
  host.oninput = e => { const c = e.target.closest('.cond'); if (c && e.target.dataset.k && e.target.tagName === 'INPUT') conds[+c.dataset.i][e.target.dataset.k] = e.target.value.replace(',', '.'); };
  draw();
}

OBB.views.senales = {
  tab: 'catalog',
  async render(el) {
    const self = this, admin = OBB.state.user.role === 'admin';
    el.innerHTML = `<div class="view-title"><h1>Señales de <span>mentores</span></h1><span class="muted">Alarmas de estrategias clásicas y de la comunidad · velas de 5 min</span></div>
<div class="bar"><div class="seg" id="sgTabs"><button data-t="catalog">Catálogo de estrategias</button><button data-t="picks">Mi selección</button><button data-t="custom">Mis estrategias</button></div></div><div id="sgBody"><div class="empty">Cargando…</div></div>`;
    $('#sgTabs').onclick = e => { const b = e.target.closest('button'); if (b) { self.tab = b.dataset.t; draw(); } };
    let d;
    const load = async () => { try { d = await api('/api/signals'); OBB.onStatus && OBB.onStatus(d.status); draw(); } catch (e) { /* ya notificado */ } };
    const hits = h => {
      if (!h.length) return '<span class="muted">Sin señales ahora</span>';
      const fresh = Date.now() / 1000 - 900;
      return `<div class="hits">${h.slice(0, 14).map(x => `<button class="hit ${x.t > fresh ? 'new' : ''}" data-sym="${esc(x.symbol)}" title="${esc(x.sector || '')} · ${etTime(x.t)} ET · ${fmtNum(x.price)} (${fmtPct(x.change_pct)})">${esc(x.symbol)}${x.t > fresh ? ' <i>NUEVA</i>' : ''}</button>`).join('')}${h.length > 14 ? `<small class="muted">+${h.length - 14}</small>` : ''}</div>`;
    };
    const follow = s => `<button class="btn ${s.followed ? 'green' : 'ghost'}" style="padding:3px 10px" data-follow="${s.kind}:${s.id}" data-on="${s.followed ? 0 : 1}" aria-pressed="${s.followed}">${s.followed ? '★ Siguiendo' : '☆ Seguir'}</button>`;
    const card = (s, extra = '') => `<section class="panel ${s.side === 'BULL' ? 'green' : 'red'} sig"><h2><span class="${s.side === 'BULL' ? 'g' : 'r'}">${s.side === 'BULL' ? '▲' : '▼'}</span> ${esc(s.name)} <span class="badge-n">${s.hits.length}</span></h2>
      ${s.source ? `<div class="muted" style="font-size:12px">${esc(s.source)} · ${s.language === 'EN' ? 'Inglés' : 'Español'}</div>` : ''}${s.description ? `<p class="note" style="margin:4px 0">${esc(s.description)}</p>` : ''}
      ${s.text.length ? `<ul class="rtext">${s.text.map(t => `<li>${esc(t)}</li>`).join('')}</ul>` : ''}${hits(s.hits)}<div class="stack">${follow(s)}</div>${extra}</section>`;
    const draw = () => {
      if (!d) return; $$('#sgTabs button').forEach(b => b.classList.toggle('on', b.dataset.t === self.tab));
      const body = $('#sgBody');
      if (self.tab === 'catalog') {
        body.innerHTML = `<div class="sig-grid">${d.catalog.map(s => card(s, admin ? `<div class="stack"><button class="btn red" style="padding:3px 10px" data-delcat="${s.id}">Quitar del catálogo</button></div>` : '')).join('') || '<div class="empty">El catálogo está vacío.</div>'}</div>
        ${admin ? '<section class="panel yellow" style="margin-top:14px"><h2>Agregar estrategia al catálogo</h2><p class="note">Crea aquí las reglas de tus mentores (con su nombre) para que las vean los usuarios del plan Avanzado.</p><div id="catBuilder"></div></section>' : ''}
        <p class="note">Las señales se calculan con reglas objetivas sobre velas de 5 minutos. Son contenido educativo, no recomendaciones. Las alertas por correo/Telegram quedan como siguiente paso.</p>`;
        if (admin) ruleBuilder($('#catBuilder'), { meta: 'catalog', saveLabel: 'Agregar al catálogo', onSave: async (rule, m) => { await api('/api/admin/catalog', { method: 'POST', body: { name: m.name, source: m.source, language: m.language, description: m.description, rule } }); toast('Estrategia agregada'); load(); } });
      } else if (self.tab === 'picks') {
        const row = s => `<label class="pick"><input type="checkbox" data-pick="${s.kind}:${s.id}" ${s.followed ? 'checked' : ''}><span class="${s.side === 'BULL' ? 'up' : 'down'}">${s.side === 'BULL' ? '▲' : '▼'}</span> ${esc(s.name)} <small class="muted">${s.hits.length} señal(es)</small></label>`;
        const grp = (t, list) => `<div><h3 class="gh">${t}</h3>${list.length ? list.map(row).join('') : '<div class="muted" style="font-size:12.5px">Nada por aquí todavía.</div>'}</div>`;
        body.innerHTML = `<section class="panel yellow"><h2>Mi selección <span class="badge-n">${d.picks.length}</span></h2>${d.picks.length ? `<div class="sig-grid">${d.picks.map(s => card(s)).join('')}</div>` : '<div class="empty">Aún no sigues ninguna estrategia. Marca las que quieras abajo; verás aquí sus señales de un vistazo.</div>'}</section>
        <section class="panel cyan" style="margin-top:14px"><h2>Elige qué seguir</h2><div class="pick-grid">${grp('Estrategias base', d.core)}${grp('Catálogo', d.catalog)}${grp('Mis estrategias guardadas', d.custom)}</div>
        ${d.custom.length ? '' : '<p class="note">Crea tus propias estrategias en la pestaña “Mis estrategias” y aparecerán aquí para seguirlas.</p>'}</section>`;
      } else {
        const left = d.custom_limit - d.custom.length;
        body.innerHTML = `<div class="sig-grid">${d.custom.map(s => card(s, `<div class="stack"><button class="btn red" style="padding:3px 10px" data-delcus="${s.id}">Eliminar</button></div>`)).join('') || '<div class="empty">Aún no creas ninguna estrategia.</div>'}</div>
        <section class="panel cyan" style="margin-top:14px"><h2>Nueva estrategia personalizada <small class="muted">(${d.custom.length}/${d.custom_limit})</small></h2>${left > 0 ? '<div id="cusBuilder"></div>' : '<p class="note">Llegaste al límite de tu plan. Elimina una para crear otra.</p>'}</section>`;
        if (left > 0) ruleBuilder($('#cusBuilder'), { meta: 'custom', saveLabel: 'Guardar estrategia', onSave: async (rule, m) => { await api('/api/custom', { method: 'POST', body: { name: m.name, rule } }); toast('Estrategia guardada'); load(); } });
      }
    };
    el.addEventListener('change', async e => {
      const pk = e.target.closest('[data-pick]'); if (!pk) return; const [kind, ref] = pk.dataset.pick.split(':');
      try { await api('/api/picks', { method: 'POST', body: { kind, ref, on: pk.checked } }); load(); } catch (er) { toast(er.message, true); pk.checked = !pk.checked; }
    });
    el.addEventListener('click', async e => {
      const s = e.target.closest('[data-sym]'); if (s) { OBB.state.symbol = s.dataset.sym; OBB.go('comando'); return; }
      const fb = e.target.closest('[data-follow]');
      if (fb) { const [kind, ref] = fb.dataset.follow.split(':'); try { await api('/api/picks', { method: 'POST', body: { kind, ref, on: fb.dataset.on === '1' } }); load(); } catch (er) { toast(er.message, true); } return; }
      const dc = e.target.closest('[data-delcat]'), du = e.target.closest('[data-delcus]');
      try {
        if (dc && confirm('¿Quitar esta estrategia del catálogo?')) { await api('/api/admin/catalog/' + dc.dataset.delcat, { method: 'DELETE' }); load(); }
        if (du && confirm('¿Eliminar tu estrategia?')) { await api('/api/custom/' + du.dataset.delcus, { method: 'DELETE' }); load(); }
      } catch (er) { toast(er.message, true); }
    });
    await load(); setInterval2(load, 60000);
  },
  destroy() { clearTimers(); },
};
