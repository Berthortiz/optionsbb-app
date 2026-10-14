/* Arranque: acceso (login / registro), estructura general y enrutador */
const NAV = [['inicio', '⌂', 'Inicio'], ['comando', '▣', 'Centro de Comando'], ['listas', '☰', 'Mis listas'], ['analisis', '◈', 'Análisis'],
  { group: 'Ingresos', icon: '◎', items: [['covercall', '◎', 'Cover Call'], ['dividendos', '＄', 'Dividendos'], ['escenarios', '⟲', '¿Qué hubiera pasado?'], ['apalancados', '⚡', 'Apalancados + CC']] },
  { group: 'Mi cartera', icon: '◉', items: [['etf', '◉', 'Mi ETF'], ['k401', '⛨', '401(k)']] },
  { group: 'Mercado', icon: '◍', items: [['flujo', '↗', 'Flujo OI'], ['sectores', '◍', 'Sectores'], ['ranking', '★', 'Ranking'], ['desempeno', '▥', 'Desempeño']] },
  { group: 'Herramientas', icon: '⚙', items: [['opciones', '∑', 'Calculadora de opciones'], ['earnings', '◷', 'Earnings'], ['gex', '▦', 'Gamma (GEX)']] },
  ['senales', '⚡', 'Señales'],
  { group: 'Más', icon: '☰', items: [['empezar', '➤', '¿Por dónde empiezo?'], ['videos', '▶', 'Videos'], ['referidos', '♥', 'Referidos'], ['planes', '★', 'Planes'], ['manual', '?', 'Manual'], ['cuenta', '☺', 'Cuenta']] }];
const FLAT = NAV.flatMap(n => n.group ? n.items : [n]);
const VIEW_OF = Object.fromEntries(FLAT.map(n => [n[0], n[0]]));
const canUse = v => !!(OBB.state.user && OBB.state.user.modules.includes(v));
/* El menú solo muestra lo que el plan incluye (lo demás se ve en «Planes») */
const navBtn = ([id, ic, l]) => `<button data-v="${id}"><i>${ic}</i>${esc(t(l))}</button>`;
const navHtml = () => NAV.map(n => {
  if (!n.group) return canUse(n[0]) ? navBtn(n) : '';
  const items = n.items.filter(i => canUse(i[0]));
  if (items.length <= 1) return items.map(navBtn).join('');
  return `<div class="grp"><button class="gb" data-g="${n.group}" aria-haspopup="true" aria-expanded="false"><i>${n.icon}</i>${esc(t(n.group))} ▾</button><div class="dd hidden">${items.map(navBtn).join('')}</div></div>`;
}).join('');
let current = null;

OBB.onUnauthorized = () => { if (OBB.state.user) { OBB.state.user = null; OBB.showAuth('Tu sesión terminó. Inicia sesión de nuevo.'); } };
OBB.onPaywall = () => { if (OBB.state.user && OBB.state.user.access) { refreshMe().then(() => OBB.go('cuenta')); } };
OBB.onPlanLock = () => { toast('Ese módulo es de un plan superior', true); OBB.go('planes'); };
OBB.go = v => { if (location.hash !== '#' + v) location.hash = v; else route(); };

OBB.onStatus = s => {
  const b = $('#banner'); if (!b || !s) return;
  const admin = OBB.state.user && OBB.state.user.role === 'admin';
  if (s.mode === 'demo') { b.className = 'banner'; b.textContent = admin ? 'MODO DEMO — los datos de mercado son simulados. Conecta tu cuenta de Schwab en Cuenta → Conexión con Schwab para ver datos reales.' : 'Datos simulados con fines demostrativos.'; }
  else if (s.error) { b.className = 'banner err'; b.textContent = admin ? 'Aviso de datos: ' + s.error : 'Los datos podrían estar temporalmente desactualizados.'; }
  else { b.className = 'hidden'; }
};

async function refreshMe() {
  const d = await api('/api/me'); OBB.state.user = d.user; return d;
}

/* ---------- pantalla de acceso ---------- */
OBB.showAuth = async function (message) {
  clearTimers(); current = null;
  let cfg = { trial_days: 7, plans: [] }; try { cfg = await api('/api/config'); } catch (e) { /* servidor caído */ }
  let mode = 'login', plan = 'avanzado';
  const urlRef = (new URLSearchParams(location.search).get('ref') || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 12);
  try { if (urlRef) { localStorage.setItem('obb_ref', urlRef); mode = 'register'; } } catch (e) { /* sin almacenamiento */ }
  let refCode = urlRef; try { refCode = refCode || localStorage.getItem('obb_ref') || ''; } catch (e) { /* ignorar */ }
  const app = $('#app');
  const paint = () => {
    app.innerHTML = `<div class="auth"><div class="panel cyan card">
      <div class="logo"><img src="/logo.png" alt="Options BB"><b>OPTIONS <span>BB</span></b><small>Trading Technology. Built Around Your Strategy.</small></div>
      <div class="langsw" role="group" aria-label="Idioma" style="justify-content:center;margin-bottom:8px">${Object.keys(OBB.LANGS).map(k => `<button type="button" data-lang="${k}" class="${OBB.lang === k ? 'on' : ''}">${k.toUpperCase()}</button>`).join('')}</div>
      <div class="tabs"><button class="${mode === 'login' ? 'on' : ''}" data-m="login">Entrar</button><button class="${mode === 'register' ? 'on' : ''}" data-m="register">Crear cuenta</button></div>
      ${mode === 'register' ? `<div class="promo">Prueba gratis de <b>${cfg.trial_days} días</b>, sin tarjeta. Después continúas con la suscripción mensual.</div>
      <div class="planpick" role="radiogroup" aria-label="Plan de prueba">${cfg.plans.map(p => `<button type="button" role="radio" aria-checked="${p.id === plan}" class="${p.id === plan ? 'on' : ''}" data-plan="${p.id}"><b>${esc(p.name)}</b><small>${p.bull}+${p.bear} estrategias${p.custom ? ' · +' + p.custom + ' propias' : ''}</small></button>`).join('')}</div>` : ''}
      <form id="authForm" novalidate>
        ${mode === 'register' ? '<label for="aName">Nombre</label><input class="field" id="aName" autocomplete="name" maxlength="80">' : ''}
        <label for="aEmail">Correo</label><input class="field" id="aEmail" type="email" autocomplete="email" required>
        <label for="aPass">Contraseña ${mode === 'register' ? '(mínimo 8 caracteres)' : ''}</label><input class="field" id="aPass" type="password" autocomplete="${mode === 'register' ? 'new-password' : 'current-password'}" required>
        ${mode === 'register' ? '<label for="aRef">Código de referido (opcional)</label><input class="field" id="aRef" maxlength="12" autocomplete="off" style="text-transform:uppercase" value="' + esc(refCode) + '">' : ''}
        <div class="err" id="aErr" role="alert">${esc(message || '')}</div>
        <button class="btn green" style="width:100%;margin-top:8px" type="submit">${mode === 'login' ? 'Entrar' : `Empezar mis ${cfg.trial_days} días gratis`}</button>
      </form></div></div>`;
    $$('.langsw button').forEach(b => b.onclick = () => { OBB.setLang(b.dataset.lang); paint(); });
    $$('.tabs button').forEach(b => b.onclick = () => { mode = b.dataset.m; message = ''; paint(); });
    $$('.planpick button').forEach(b => b.onclick = () => { plan = b.dataset.plan; $$('.planpick button').forEach(x => { x.classList.toggle('on', x === b); x.setAttribute('aria-checked', x === b); }); });
    $('#authForm').onsubmit = async e => {
      e.preventDefault();
      const body = { email: $('#aEmail').value, password: $('#aPass').value, name: $('#aName') ? $('#aName').value : '', plan, ref: $('#aRef') ? $('#aRef').value.trim() : '' };
      try {
        const d = await api(mode === 'login' ? '/api/auth/login' : '/api/auth/register', { method: 'POST', body });
        OBB.state.user = d.user; try { localStorage.removeItem('obb_ref'); } catch (e) { /* ignorar */ } startApp();
      } catch (er) { $('#aErr').textContent = er.message; }
    };
    $('#aEmail').focus();
  };
  paint();
};

/* ---------- estructura ---------- */
function shell() {
  const u = OBB.state.user;
  $('#app').innerHTML = `
<div id="banner" class="hidden"></div>
<header class="topbar">
  <div class="brand"><img src="/logo.png" alt=""><div><b>OPTIONS <span>BB</span></b><small>Trading Technology. Built Around Your Strategy.</small></div></div>
  <nav class="nav" id="nav">${navHtml()}</nav>
  <div class="langsw" role="group" aria-label="Idioma">${Object.keys(OBB.LANGS).map(k => `<button data-lang="${k}" class="${OBB.lang === k ? 'on' : ''}">${k.toUpperCase()}</button>`).join('')}</div>
</header>
<main id="main"></main>
<footer class="footer">
  <div class="brand"><img src="/logo.png" alt=""><div><b>OPTIONS <span>BB</span></b><small>Trading Technology. Built Around Your Strategy.</small></div></div>
  <div class="feat"><div><b>ThinkScript</b><span>Desarrolla tus estrategias</span></div><div><b>Scanners</b><span>Más oportunidades</span></div><div><b>Alerts</b><span>En tiempo real</span></div><div><b>Conditional Orders</b><span>Gestión automatizada</span></div></div>
  <div class="contact">◍ www.optionsbb.com<br>✉ jroa@optionsbb.com</div>
  <div class="contact"><span style="color:var(--red)">▶</span> @optionsbb<br><span class="badge">⚡ Electric Income Reducer</span></div>
</footer>
<div class="legal">${esc(t('Contenido educativo, no es asesoría financiera. Operar acciones y opciones conlleva riesgo de pérdida. Los datos pueden tener retraso o ser simulados.'))} · v${esc(OBB.version || '')}</div>`;
  $$('.langsw button').forEach(b => b.onclick = () => { OBB.setLang(b.dataset.lang); startApp(); });
  $('#nav').onclick = e => {
    const g = e.target.closest('.gb');
    if (g) { const dd = g.nextElementSibling, open = dd.classList.contains('hidden'); $$('#nav .dd').forEach(x => x.classList.add('hidden')); dd.classList.toggle('hidden', !open); g.setAttribute('aria-expanded', open); e.stopPropagation(); return; }
    const b = e.target.closest('button[data-v]'); if (b) { $$('#nav .dd').forEach(x => x.classList.add('hidden')); OBB.go(b.dataset.v); }
  };
  document.addEventListener('click', e => { if (!e.target.closest('#nav')) $$('#nav .dd').forEach(x => x.classList.add('hidden')); });
}

function route() {
  const u = OBB.state.user; if (!u) return;
  let v = (location.hash || '#inicio').slice(1);
  if (!VIEW_OF[v]) v = 'inicio';
  if (!u.access && !['cuenta', 'planes'].includes(v)) v = 'cuenta';
  if (u.access && !canUse(v)) v = 'planes';
  if (current && OBB.views[current].destroy) OBB.views[current].destroy();
  clearTimers(); current = v;
  $$('#nav button[data-v]').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  $$('#nav .gb').forEach(b => b.classList.toggle('on', !!b.nextElementSibling.querySelector(`[data-v="${v}"]`)));
  const main = $('#main'); const fresh = main.cloneNode(false); main.replaceWith(fresh);  // quita listeners anteriores
  try { OBB.views[v].render(fresh); } catch (e) { console.error(e); fresh.innerHTML = '<div class="empty">Error al mostrar la vista.</div>'; }
}

function startApp() {
  shell(); route();
  const p = new URLSearchParams(location.search);
  if (p.get('pago') === 'ok') {
    history.replaceState(null, '', location.pathname + location.hash);
    toast('¡Gracias! Estamos activando tu suscripción…');
    let n = 0; const t = setInterval(async () => { n++; await refreshMe().catch(() => { }); if (OBB.state.user.reason === 'active' || n > 8) { clearInterval(t); startApp(); } }, 2500);
  }
}

window.addEventListener('hashchange', route);
(async function init() {
  try { const cfg = await api('/api/config'); OBB.version = cfg.version; OBB.logo = (cfg.links || {}).logo || ''; } catch (e) { /* sin servidor */ }
  try { await refreshMe(); startApp(); } catch (e) { OBB.showAuth(); }
})();
