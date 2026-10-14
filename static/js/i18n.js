/* Idiomas: español (base), inglés y portugués. Los textos se escriben en español y se traducen por coincidencia exacta
   con el diccionario OBB.EN (static/js/i18n-en.js). Para añadir un idioma: agrega su diccionario y su código en OBB.LANGS. */
OBB.LANGS = { es: 'Español', en: 'English', pt: 'Português' };
OBB.DICT = { en: {}, pt: {} };
OBB.lang = 'es';
try { const s = localStorage.getItem('obb_lang'); if (OBB.LANGS[s]) OBB.lang = s; } catch (e) { /* sin almacenamiento */ }
/* Los textos con cifras se buscan con las cifras sustituidas por {} (p. ej. «En {} días» → «In {} days») */
const NUM_RE = /[−+-]?\$?\d[\d,.]*%?/g;
const _tpl = {};
const tplList = (lang, d) => _tpl[lang] || (_tpl[lang] = Object.keys(d).filter(k => k.includes('{*}')).map(k => {
  const toks = k.split(/(\{\*\}|\{\})/); const types = []; let src = '^';
  toks.forEach(x => { if (x === '{*}') { types.push('*'); src += '(.+?)'; } else if (x === '{}') { types.push('#'); src += '(\\u0001\\d+\\u0002)'; } else src += x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); });
  return [new RegExp(src + '$'), types, d[k]];
}));
const trCore = (d, k) => {
  if (d[k]) return d[k];
  const nums = k.match(NUM_RE) || []; let n = 0;
  const km = k.replace(NUM_RE, () => `\u0001${n++}\u0002`), k2 = k.replace(NUM_RE, '{}');
  const restore = s => s.replace(/\u0001(\d+)\u0002/g, (_, i) => nums[i]);
  const fill = (tpl, st, ns) => { let a = 0, b = 0; return tpl.replace(/\{\*\}|\{\}/g, m => (m === '{}' ? ns[b++] : st[a++]) ?? ''); };
  if (nums.length && d[k2]) return fill(d[k2], [], nums);
  for (const [re, types, tpl] of tplList(OBB.lang, d)) {
    const m = km.match(re); if (!m) continue;
    const st = [], ns = []; types.forEach((ty, i) => (ty === '*' ? st : ns).push(m[i + 1]));
    return restore(fill(tpl, st, ns));
  }
  return null;
};
const trText = (d, k) => {
  k = k.replace(/\s+/g, ' ');
  const r = trCore(d, k); if (r) return r;
  const m = k.match(/^([▲▼☆✓⚠⬇▶◍✉⏱●🎁]\s?|\d+\.\s)(.+)$/);       // prefijos decorativos o numeración
  if (m) { const r2 = trCore(d, m[2]); if (r2) return m[1] + r2; }
  const sf = k.match(/^(.+?)(\s[▲▼])$/);                      // flecha de orden en encabezados de tabla
  if (sf) { const r3 = trCore(d, sf[1]); if (r3) return r3 + sf[2]; }
  return null;
};
const t = s => { if (OBB.lang === 'es' || typeof s !== 'string') return s; const d = OBB.DICT[OBB.lang]; return (d && trText(d, s.trim())) || s; };
OBB.setLang = l => { if (!OBB.LANGS[l]) return; OBB.lang = l; try { localStorage.setItem('obb_lang', l); } catch (e) { /* ok */ } document.documentElement.lang = l; };
document.documentElement.lang = OBB.lang;

/* Traduce los textos que aparecen en pantalla (nodos de texto y algunos atributos) */
OBB.translateTree = root => {
  if (OBB.lang === 'es' || !root) return;
  const d = OBB.DICT[OBB.lang] || {};
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = []; while (w.nextNode()) nodes.push(w.currentNode);
  nodes.forEach(n => {
    const raw = n.nodeValue, k = raw.trim(); if (!k) return;
    const v = trText(d, k); if (v) n.nodeValue = raw.replace(k, v);
  });
  if (root.querySelectorAll) [...(root.matches && root.matches('[placeholder],[title],[aria-label]') ? [root] : []), ...root.querySelectorAll('[placeholder],[title],[aria-label]')].forEach(e => {
    ['placeholder', 'title', 'aria-label'].forEach(a => { const x = e.getAttribute(a); const v = x && trText(d, x.trim()); if (v) e.setAttribute(a, v); });
  });
};
document.addEventListener('DOMContentLoaded', () => {
  const app = document.body; if (!app) return;
  let busy = false;
  new MutationObserver(ms => {
    if (OBB.lang === 'es' || busy) return; busy = true;
    ms.forEach(m => m.addedNodes.forEach(n => OBB.translateTree(n.nodeType === 1 ? n : n.parentNode)));
    busy = false;
  }).observe(app, { childList: true, subtree: true });
});
