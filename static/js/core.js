/* Núcleo: utilidades, API, formatos */
window.OBB = { state: { user: null, symbol: 'SPY', bull: 'vela_verde', bear: 'vela_roja_apertura', patternSide: 'BULL' }, views: {}, timers: [] };

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

class ApiError extends Error { constructor(status, msg, data) { super(msg); this.status = status; this.data = data || {}; } }

async function api(path, { method = 'GET', body, raw, headers = {} } = {}) {
  const opt = { method, credentials: 'same-origin', headers: { 'X-OBB': '1', ...headers } };
  if (body !== undefined) {
    if (body instanceof ArrayBuffer || body instanceof Blob) opt.body = body;
    else { opt.body = JSON.stringify(body); opt.headers['Content-Type'] = 'application/json'; }
  }
  let r;
  try { r = await fetch(path, opt); } catch (e) { throw new ApiError(0, 'Sin conexión con el servidor'); }
  if (raw && r.ok) return r;
  let data = {};
  try { data = await r.json(); } catch (e) { /* sin cuerpo */ }
  if (!r.ok) {
    if (r.status === 401 && OBB.onUnauthorized) OBB.onUnauthorized();
    if (r.status === 402 && OBB.onPaywall) OBB.onPaywall(data.reason);
    if (r.status === 403 && data.reason === 'plan' && OBB.onPlanLock) OBB.onPlanLock();
    throw new ApiError(r.status, data.error || ('Error ' + r.status), data);
  }
  return data;
}

function toast(msg, bad) {
  const d = document.createElement('div');
  if (bad) d.className = 'bad';
  d.textContent = msg;
  $('#toast').appendChild(d);
  setTimeout(() => d.remove(), bad ? 6000 : 3500);
}

/* ---------- formatos ---------- */
const nf0 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtInt = n => (n == null ? '—' : nf0.format(n));
const fmtNum = n => (n == null ? '—' : nf2.format(n));
const fmtSigned = n => (n == null ? '—' : (n > 0 ? '+' : n < 0 ? '−' : '') + nf0.format(Math.abs(n)));
const fmtPct = (n, sign = true) => (n == null ? '—' : (sign && n > 0 ? '+' : n < 0 ? '−' : '') + nf2.format(Math.abs(n)) + '%');
const fmtMoney = n => (n == null ? '—' : (n < 0 ? '−$' : '$') + nf2.format(Math.abs(n)));
const cls = n => (n > 0 ? 'up' : n < 0 ? 'down' : '');
const MONTHS_L = { es: ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'], en: ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'], pt: ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'] };
const MON = () => MONTHS_L[OBB.lang] || MONTHS_L.es;
const LOC = () => ({ es: 'es-US', en: 'en-US', pt: 'pt-BR' }[OBB.lang] || 'es-US');
const fmtDate = iso => { if (!iso) return '—'; const [y, m, d] = iso.slice(0, 10).split('-'); return `${+d} ${MON()[+m - 1]} ${y.slice(2)}`; };
const fmtExp = iso => { const [y, m, d] = iso.split('-'); return `${d}${MONTHS_L.en[+m - 1]}${y.slice(2)}`; };  // formato de vencimiento de opciones: 9OCT26
const etTime = (t, withDate) => new Intl.DateTimeFormat(LOC(), Object.assign({ timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false }, withDate ? { month: 'short', day: 'numeric' } : {})).format(new Date(t * 1000));
const etDay = t => new Intl.DateTimeFormat(LOC(), { timeZone: 'America/New_York', month: 'short', day: 'numeric' }).format(new Date(t * 1000));
const fmtTs = ts => (ts ? new Date(ts * 1000).toLocaleString(LOC(), { dateStyle: 'medium', timeStyle: 'short' }) : '—');

function setInterval2(fn, ms) { const id = setInterval(fn, ms); OBB.timers.push(id); return id; }
function clearTimers() { OBB.timers.forEach(clearInterval); OBB.timers = []; }
