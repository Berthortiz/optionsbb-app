/* Gráficos: velas (canvas), barras/equity (SVG) y diagramas de patrones */
const C = { green: '#19f56a', red: '#ff2b3d', yellow: '#ffd21a', cyan: '#2ec8ff', grid: 'rgba(120,160,220,.16)', axis: '#8fa6c9' };

/* ======================= velas ======================= */
function drawCandles(canvas, tipEl, data) {
  const st = canvas._st = { data, hover: -1 };
  const render = () => {
    const d = st.data; if (!d || !d.candles.length) return;
    const dpr = window.devicePixelRatio || 1, W = canvas.clientWidth, H = canvas.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    const g = canvas.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, W, H);
    const L = 4, R = 52, T = 10, B = 20, pw = W - L - R, ph = H - T - B, cs = d.candles, n = cs.length;
    let lo = Infinity, hi = -Infinity;
    cs.forEach((c, i) => { lo = Math.min(lo, c.l); hi = Math.max(hi, c.h); [d.sma9[i], d.sma21[i]].forEach(v => { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }); });
    const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
    const X = i => L + (i + 0.5) * pw / n, Y = p => T + (hi - p) / (hi - lo) * ph;
    g.font = '11px "Segoe UI",sans-serif'; g.textBaseline = 'middle';
    for (let k = 0; k <= 4; k++) {
      const p = lo + (hi - lo) * k / 4, y = Y(p);
      g.strokeStyle = C.grid; g.lineWidth = 1; g.beginPath(); g.moveTo(L, y); g.lineTo(L + pw, y); g.stroke();
      g.fillStyle = C.axis; g.textAlign = 'left'; g.fillText(p.toFixed(p >= 100 ? 1 : 2), L + pw + 6, y);
    }
    // eje X
    g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.fillStyle = C.axis;
    const intraday = d.range === '1D' || d.range === '5D', tl = Math.max(2, Math.min(6, Math.floor(pw / 90)));
    for (let k = 0; k < tl; k++) {
      const i = Math.round((n - 1) * k / (tl - 1)); g.fillText(intraday ? etTime(cs[i].t, d.range === '5D') : etDay(cs[i].t), Math.min(Math.max(X(i), 24), L + pw - 24), H - 5);
    }
    // medias
    const line = (arr, col) => { g.strokeStyle = col; g.lineWidth = 1.6; g.beginPath(); let on = false; arr.forEach((v, i) => { if (v == null) return; on ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)); on = true; }); g.stroke(); };
    line(d.sma21, C.yellow); line(d.sma9, C.cyan);
    // velas
    const bw = Math.max(1.5, Math.min(14, pw / n * 0.62));
    cs.forEach((c, i) => {
      const up = c.c >= c.o, col = up ? C.green : C.red, x = X(i);
      // velas «huecas»: solo el borde, sin relleno (no cansa la vista)
      g.strokeStyle = col; g.lineWidth = 1.1;
      const y1 = Y(Math.max(c.o, c.c)), y2 = Y(Math.min(c.o, c.c)), bh = Math.max(1.5, y2 - y1);
      g.beginPath(); g.moveTo(x, Y(c.h)); g.lineTo(x, y1); g.moveTo(x, y1 + bh); g.lineTo(x, Y(c.l)); g.stroke();
      if (bw < 3) { g.beginPath(); g.moveTo(x, y1); g.lineTo(x, y1 + bh); g.stroke(); } else g.strokeRect(x - bw / 2 + 0.5, y1 + 0.5, bw - 1, Math.max(1, bh - 1));
    });
    // señales
    const bull = d.marks.filter(m => m.side === 'BULL'), bear = d.marks.filter(m => m.side === 'BEAR');
    const mark = (m, last) => {
      const c = cs[m.i]; if (!c) return; const isBull = m.side === 'BULL', col = isBull ? C.green : C.red, x = X(m.i);
      const yTip = isBull ? Y(c.l) + 4 : Y(c.h) - 4, dir = isBull ? 1 : -1;
      g.fillStyle = col; g.beginPath(); g.moveTo(x, yTip); g.lineTo(x - 5, yTip + dir * 8); g.lineTo(x + 5, yTip + dir * 8); g.closePath(); g.fill();
      if (!last) return;
      const txt = isBull ? 'SEÑAL ALCISTA' : 'SEÑAL BAJISTA'; g.font = 'bold 10.5px "Segoe UI",sans-serif';
      const tw = g.measureText(txt).width + 14, h = 18; let bx = Math.min(Math.max(x - tw / 2, L), L + pw - tw), by = yTip + dir * 10 + (isBull ? 0 : -h);
      by = Math.min(Math.max(by, 2), H - B - h - 2);
      g.fillStyle = isBull ? '#0f5f2b' : '#7a1019'; g.strokeStyle = col; g.lineWidth = 1.5;
      g.beginPath(); g.roundRect ? g.roundRect(bx, by, tw, h, 4) : g.rect(bx, by, tw, h); g.fill(); g.stroke();
      g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(txt, bx + tw / 2, by + h / 2 + 0.5);
    };
    bull.forEach((m, k) => mark(m, k === bull.length - 1)); bear.forEach((m, k) => mark(m, k === bear.length - 1));
    // cruz
    if (st.hover >= 0 && cs[st.hover]) {
      const x = X(st.hover); g.strokeStyle = 'rgba(200,220,255,.35)'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(x, T); g.lineTo(x, T + ph); g.stroke(); g.setLineDash([]);
    }
  };
  st.render = render; render();
  if (!canvas._bound) {
    canvas._bound = true;
    new ResizeObserver(() => canvas._st && canvas._st.render()).observe(canvas);
    canvas.addEventListener('mousemove', e => {
      const s = canvas._st; if (!s || !s.data.candles.length) return;
      const r = canvas.getBoundingClientRect(), n = s.data.candles.length, pw = r.width - 56;
      const i = Math.max(0, Math.min(n - 1, Math.floor((e.clientX - r.left - 4) / pw * n))); s.hover = i; s.render();
      const c = s.data.candles[i], intr = s.data.range === '1D' || s.data.range === '5D';
      tipEl.innerHTML = `<b>${intr ? etTime(c.t, true) : etDay(c.t)}</b> &nbsp;O ${c.o.toFixed(2)} H ${c.h.toFixed(2)} L ${c.l.toFixed(2)} <b class="${c.c >= c.o ? 'up' : 'down'}">C ${c.c.toFixed(2)}</b>`;
      tipEl.classList.remove('hidden');
      tipEl.style.left = Math.min(e.clientX - r.left + 12, r.width - tipEl.offsetWidth - 4) + 'px'; tipEl.style.top = '4px';
    });
    canvas.addEventListener('mouseleave', () => { const s = canvas._st; if (s) { s.hover = -1; s.render(); } tipEl.classList.add('hidden'); });
  }
}

/* ======================= barras (reporte) ======================= */
function svgBars({ cats, series, yMax, pct }) {
  const W = 520, H = 280, L = 46, R = 12, T = 14, B = 54, pw = W - L - R, ph = H - T - B;
  const max = yMax || Math.max(1, ...series.flatMap(s => s.values.map(v => v || 0)));
  const stepN = pct ? 0.2 : Math.max(1, Math.ceil(Math.ceil(max * 1.15) / 5)), nice = pct ? 1.2 : stepN * 5;
  const Y = v => T + ph - (v / nice) * ph;
  let out = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
  const steps = pct ? [0, .2, .4, .6, .8, 1, 1.2] : Array.from({ length: 6 }, (_, i) => stepN * i);
  steps.forEach(v => { out += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="#d9d9d9"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#555">${pct ? Math.round(v * 100) + '%' : v}</text>`; });
  const gw = pw / cats.length, bw = Math.min(46, gw * 0.7 / series.length);
  cats.forEach((c, i) => {
    const cx = L + gw * (i + 0.5);
    series.forEach((s, k) => {
      const v = s.values[i]; if (v == null) return;
      const x = cx - bw * series.length / 2 + k * bw, y = Y(v);
      out += `<rect x="${x}" y="${y}" width="${bw - 1}" height="${Math.max(0, Y(0) - y)}" fill="${s.color}"/>`;
      out += `<text x="${x + bw / 2}" y="${y - 4}" text-anchor="middle" font-size="11" font-weight="700" fill="#333">${pct ? Math.round(v * 100) + '%' : v}</text>`;
    });
    const label = c.length > 22 ? c.slice(0, 21) + '…' : c;
    out += `<text x="${cx}" y="${H - B + 16}" text-anchor="middle" font-size="11" fill="#333">${esc(label)}</text>`;
  });
  out += `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#888"/>`;
  if (series.length > 1) series.forEach((s, k) => { out += `<rect x="${L + 120 * k + 90}" y="${H - 16}" width="10" height="10" fill="${s.color}"/><text x="${L + 120 * k + 104}" y="${H - 7}" font-size="11" fill="#333">${esc(s.name)}</text>`; });
  return out + '</svg>';
}

function svgEquity(points) {
  if (!points.length) return '';
  const W = 900, H = 230, L = 62, R = 14, T = 12, B = 26, pw = W - L - R, ph = H - T - B;
  const vals = [0, ...points.map(p => p.cum)], lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * .1 || 1;
  const Y = v => T + (hi + pad - v) / (hi - lo + 2 * pad) * ph, X = i => L + (points.length === 1 ? pw / 2 : i * pw / (points.length - 1));
  let o = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
  for (let k = 0; k <= 4; k++) { const v = lo - pad + (hi - lo + 2 * pad) * k / 4; o += `<line x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" stroke="rgba(120,160,220,.16)"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="#8fa6c9">${(v < 0 ? '−$' : '$') + nf0.format(Math.abs(Math.round(v)))}</text>`; }
  o += `<line x1="${L}" x2="${W - R}" y1="${Y(0)}" y2="${Y(0)}" stroke="#6c86b3" stroke-dasharray="4 3"/>`;
  const pts = points.map((p, i) => `${X(i)},${Y(p.cum)}`).join(' ');
  o += `<polygon points="${L},${Y(0)} ${pts} ${X(points.length - 1)},${Y(0)}" fill="rgba(25,245,106,.12)"/><polyline points="${pts}" fill="none" stroke="${C.green}" stroke-width="2.4"/>`;
  points.forEach((p, i) => { o += `<circle cx="${X(i)}" cy="${Y(p.cum)}" r="4" fill="${p.pnl >= 0 ? C.green : C.red}" stroke="#04101f"><title>#${p.n} ${esc(p.strategy)}: ${fmtMoney(p.pnl)} → acumulado ${fmtMoney(p.cum)}</title></circle>`; });
  return o + '</svg>';
}

/* ======================= diagramas de patrones ======================= */
const PATTERNS = {
  vela_verde: { side: 'BULL', title: 'VELA VERDE', sub: 'PATRÓN DE 5 VELAS', entry: 'SEÑAL DE ENTRADA · VELA 5', hi: 4,
    candles: [[70, 52, 74, 48], [62, 42, 66, 38], [44, 40, 50, 34], [40, 64, 68, 36], [62, 88, 92, 58]],
    rule: 'Regla de la app: 3 velas rojas seguidas y luego 2 verdes; la vela 5 cierra por encima del cierre de la vela 4.' },
  martillo: { side: 'BULL', title: 'MARTILLO', sub: 'REVERSIÓN TRAS CAÍDA', entry: 'SEÑAL DE ENTRADA · VELA 4', hi: 3,
    candles: [[80, 62, 84, 58], [66, 48, 70, 44], [52, 34, 56, 30], [34, 38, 39, 12]], labels: ['ROJA', 'ROJA', 'ROJA', 'MARTILLO'],
    rule: 'Regla de la app: tras 3 velas bajistas, una vela con mecha inferior larga (≥ 60 % del rango) y cuerpo pequeño.' },
  cruce_alcista: { side: 'BULL', title: 'CRUCE DE MEDIAS MÓVILES', sub: 'CRUCE ALCISTA', entry: 'SEÑAL DE ENTRADA · CRUCE',
    lines: { a: [[50, 150], [150, 152], [250, 148], [330, 140], [400, 118], [470, 95], [520, 80]], b: [[50, 128], [150, 130], [250, 134], [330, 136], [400, 134], [470, 128], [520, 124]], cross: [344, 136], la: 'SMA 9', lb: 'SMA 21' },
    rule: 'Regla de la app: la media móvil de 9 periodos cruza hacia arriba la de 21 (velas de 5 minutos).' },
  ruptura_resistencia: { side: 'BULL', title: 'RUPTURA DE RESISTENCIA', sub: 'ROMPE EL MÁXIMO RECIENTE', entry: 'SEÑAL DE ENTRADA · VELA 6', hi: 5, level: { p: 61, label: 'RESISTENCIA' },
    candles: [[40, 48, 52, 36], [48, 44, 54, 40], [44, 54, 58, 42], [54, 50, 60, 46], [50, 58, 61, 47], [58, 80, 84, 56]], labels: ['', '', '', '', '', 'RUPTURA'],
    rule: 'Regla de la app: la vela cierra por encima del máximo de las 20 velas anteriores.' },
  vela_roja_apertura: { side: 'BEAR', title: 'VELA ROJA DE APERTURA', sub: 'PRIMERA VELA DE LA SESIÓN', entry: 'SEÑAL · VELA DE APERTURA', hi: 0, level: { p: 62, label: 'CIERRE ANTERIOR' },
    candles: [[58, 24, 60, 20], [24, 32, 36, 20], [32, 26, 38, 22]], labels: ['ROJA', '', ''],
    rule: 'Regla de la app: la primera vela del día es roja (cuerpo ≥ 50 % del rango) y cierra por debajo del cierre anterior.' },
  estrella_fugaz: { side: 'BEAR', title: 'ESTRELLA FUGAZ', sub: 'REVERSIÓN TRAS SUBIDA', entry: 'SEÑAL DE ENTRADA · VELA 4', hi: 3,
    candles: [[20, 34, 37, 18], [32, 46, 49, 30], [44, 58, 61, 42], [58, 56, 88, 54]], labels: ['VERDE', 'VERDE', 'VERDE', 'ESTRELLA'],
    rule: 'Regla de la app: tras 3 velas alcistas, una vela con mecha superior larga (≥ 60 % del rango) y cuerpo pequeño.' },
  cruce_bajista: { side: 'BEAR', title: 'CRUCE DE MEDIAS MÓVILES', sub: 'CRUCE BAJISTA', entry: 'SEÑAL DE ENTRADA · CRUCE',
    lines: { a: [[50, 100], [150, 98], [250, 102], [330, 110], [400, 138], [470, 160], [520, 172]], b: [[50, 122], [150, 120], [250, 116], [330, 114], [400, 116], [470, 122], [520, 128]], cross: [341, 114], la: 'SMA 9', lb: 'SMA 21' },
    rule: 'Regla de la app: la media móvil de 9 periodos cruza hacia abajo la de 21 (velas de 5 minutos).' },
  ruptura_soporte: { side: 'BEAR', title: 'RUPTURA DE SOPORTE', sub: 'ROMPE EL MÍNIMO RECIENTE', entry: 'SEÑAL DE ENTRADA · VELA 6', hi: 5, level: { p: 40, label: 'SOPORTE' },
    candles: [[62, 54, 66, 50], [54, 58, 62, 48], [58, 48, 60, 46], [48, 52, 56, 42], [52, 44, 54, 41], [44, 20, 46, 16]], labels: ['', '', '', '', '', 'RUPTURA'],
    rule: 'Regla de la app: la vela cierra por debajo del mínimo de las 20 velas anteriores.' },
  envolvente_alcista: { side: 'BULL', title: 'ENVOLVENTE ALCISTA', sub: 'REVERSIÓN DE 2 VELAS', entry: 'SEÑAL DE ENTRADA · VELA 2', hi: 1,
    candles: [[62, 48, 65, 45], [46, 74, 77, 44]], labels: ['ROJA', 'ENVOLVENTE'],
    rule: 'Regla de la app: una vela verde cuyo cuerpo envuelve por completo el cuerpo de la vela roja anterior.' },
  estrella_manana: { side: 'BULL', title: 'ESTRELLA DE LA MAÑANA', sub: 'REVERSIÓN DE 3 VELAS', entry: 'SEÑAL DE ENTRADA · VELA 3', hi: 2,
    candles: [[84, 52, 86, 50], [48, 46, 52, 42], [50, 80, 84, 48]], labels: ['ROJA LARGA', 'ESTRELLA', 'VERDE'],
    rule: 'Regla de la app: vela roja larga, vela pequeña de indecisión y vela verde que cierra sobre la mitad de la primera.' },
  tres_soldados: { side: 'BULL', title: 'TRES SOLDADOS BLANCOS', sub: 'AVANCE SOSTENIDO', entry: 'SEÑAL DE ENTRADA · VELA 3', hi: 2,
    candles: [[30, 44, 47, 28], [42, 58, 61, 40], [56, 74, 77, 54]], labels: ['VERDE', 'VERDE', 'VERDE'],
    rule: 'Regla de la app: tres velas verdes de cuerpo grande, cada una abre dentro de la anterior y cierra más alto.' },
  harami_alcista: { side: 'BULL', title: 'HARAMI ALCISTA', sub: 'POSIBLE AGOTAMIENTO BAJISTA', entry: 'SEÑAL DE ENTRADA · VELA 2', hi: 1,
    candles: [[84, 50, 87, 47], [58, 70, 73, 56]], labels: ['ROJA LARGA', 'HARAMI'],
    rule: 'Regla de la app: vela verde pequeña contenida dentro del cuerpo de una vela roja grande anterior.' },
  rebote_sma21: { side: 'BULL', title: 'REBOTE EN SMA 21', sub: 'RETROCESO EN TENDENCIA ALCISTA', entry: 'SEÑAL DE ENTRADA · VELA 4', hi: 3, level: { p: 53, label: 'SMA 21' },
    candles: [[50, 58, 61, 48], [58, 68, 71, 56], [68, 56, 70, 52], [54, 70, 73, 52]], labels: ['', '', 'RETROCESO', 'REBOTE'],
    rule: 'Regla de la app: con la SMA 21 subiendo, la vela anterior toca la media y la actual cierra verde por encima de ella.' },
  volumen_alcista: { side: 'BULL', title: 'VOLUMEN EXPLOSIVO', sub: 'VELA VERDE FUERTE', entry: 'SEÑAL DE ENTRADA · VELA 4', hi: 3,
    candles: [[44, 46, 49, 42], [46, 44, 48, 42], [44, 47, 50, 43], [46, 80, 84, 44]], labels: ['', '', '', 'VOL ×2'],
    rule: 'Regla de la app: vela verde con cuerpo ≥ 50 % del rango y volumen mayor a 2 veces el promedio de 20 velas.' },
  envolvente_bajista: { side: 'BEAR', title: 'ENVOLVENTE BAJISTA', sub: 'REVERSIÓN DE 2 VELAS', entry: 'SEÑAL DE ENTRADA · VELA 2', hi: 1,
    candles: [[48, 62, 65, 45], [66, 36, 69, 33]], labels: ['VERDE', 'ENVOLVENTE'],
    rule: 'Regla de la app: una vela roja cuyo cuerpo envuelve por completo el cuerpo de la vela verde anterior.' },
  estrella_tarde: { side: 'BEAR', title: 'ESTRELLA DE LA TARDE', sub: 'REVERSIÓN DE 3 VELAS', entry: 'SEÑAL DE ENTRADA · VELA 3', hi: 2,
    candles: [[40, 74, 76, 38], [78, 80, 84, 74], [76, 44, 78, 42]], labels: ['VERDE LARGA', 'ESTRELLA', 'ROJA'],
    rule: 'Regla de la app: vela verde larga, vela pequeña de indecisión y vela roja que cierra bajo la mitad de la primera.' },
  tres_cuervos: { side: 'BEAR', title: 'TRES CUERVOS NEGROS', sub: 'CAÍDA SOSTENIDA', entry: 'SEÑAL DE ENTRADA · VELA 3', hi: 2,
    candles: [[76, 60, 79, 57], [62, 46, 65, 43], [48, 30, 51, 27]], labels: ['ROJA', 'ROJA', 'ROJA'],
    rule: 'Regla de la app: tres velas rojas de cuerpo grande, cada una abre dentro de la anterior y cierra más bajo.' },
  harami_bajista: { side: 'BEAR', title: 'HARAMI BAJISTA', sub: 'POSIBLE AGOTAMIENTO ALCISTA', entry: 'SEÑAL DE ENTRADA · VELA 2', hi: 1,
    candles: [[40, 74, 77, 37], [66, 56, 69, 53]], labels: ['VERDE LARGA', 'HARAMI'],
    rule: 'Regla de la app: vela roja pequeña contenida dentro del cuerpo de una vela verde grande anterior.' },
  rechazo_sma21: { side: 'BEAR', title: 'RECHAZO EN SMA 21', sub: 'REBOTE EN TENDENCIA BAJISTA', entry: 'SEÑAL DE ENTRADA · VELA 4', hi: 3, level: { p: 53, label: 'SMA 21' },
    candles: [[60, 50, 62, 48], [50, 40, 52, 38], [40, 52, 55, 38], [54, 40, 56, 38]], labels: ['', '', 'REBOTE', 'RECHAZO'],
    rule: 'Regla de la app: con la SMA 21 bajando, la vela anterior toca la media y la actual cierra roja por debajo de ella.' },
  volumen_bajista: { side: 'BEAR', title: 'VOLUMEN EXPLOSIVO', sub: 'VELA ROJA FUERTE', entry: 'SEÑAL DE ENTRADA · VELA 4', hi: 3,
    candles: [[46, 44, 49, 42], [44, 46, 48, 42], [46, 43, 49, 41], [44, 10, 46, 8]], labels: ['', '', '', 'VOL ×2'],
    rule: 'Regla de la app: vela roja con cuerpo ≥ 50 % del rango y volumen mayor a 2 veces el promedio de 20 velas.' },
};

function patternSVG(id) {
  const P = PATTERNS[id]; if (!P) return '';
  const W = 560, H = 262;
  let mn = Infinity, mx = -Infinity;
  (P.candles || []).forEach(k => { mn = Math.min(mn, k[3]); mx = Math.max(mx, k[2]); });
  if (P.level) { mn = Math.min(mn, P.level.p - 3); mx = Math.max(mx, P.level.p + 3); }
  const y = p => 172 - (p - mn) / ((mx - mn) || 1) * 130, hiCol = P.side === 'BULL' ? '#7dffa9' : '#ff8c96';
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(P.title)}"><defs><filter id="gl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>`;
  if (P.lines) {
    const pl = (pts, col) => `<polyline points="${pts.map(p => p.join(',')).join(' ')}" fill="none" stroke="${col}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" filter="url(#gl)"/>`;
    const L = P.lines;
    s += pl(L.b, C.yellow) + pl(L.a, C.cyan);
    s += `<circle cx="${L.cross[0]}" cy="${L.cross[1]}" r="17" fill="none" stroke="${hiCol}" stroke-width="4" filter="url(#gl)"/>`;
    s += `<text x="520" y="${L.a[6][1] + (P.side === 'BULL' ? -10 : 22)}" text-anchor="end" fill="${C.cyan}" font-weight="800" font-size="15">${L.la}</text>`;
    s += `<text x="520" y="${L.b[6][1] + (P.side === 'BULL' ? 24 : -10)}" text-anchor="end" fill="${C.yellow}" font-weight="800" font-size="15">${L.lb}</text>`;
    s += `<text x="${L.cross[0]}" y="${L.cross[1] + (P.side === 'BULL' ? 42 : -30)}" text-anchor="middle" fill="${hiCol}" font-weight="900" font-size="15">${esc(P.entry)}</text>`;
    return s + '</svg>';
  }
  const n = P.candles.length, left = 40, usable = 480, step = usable / n, bw = Math.min(58, step * 0.62);
  if (P.level) {
    const ly = y(P.level.p); s += `<line x1="22" x2="538" y1="${ly}" y2="${ly}" stroke="${C.yellow}" stroke-width="2.5" stroke-dasharray="9 6"/><text x="538" y="${ly - 7}" text-anchor="end" fill="${C.yellow}" font-weight="800" font-size="13">${P.level.label}</text>`;
  }
  P.candles.forEach(([o, c, h, l], i) => {
    const cx = left + (i + .5) * step, up = c >= o, col = up ? '#18f060' : '#f02a2a', top = y(Math.max(o, c)), bot = y(Math.min(o, c));
    s += `<line x1="${cx}" x2="${cx}" y1="${y(h)}" y2="${y(l)}" stroke="${col}" stroke-width="4"/>`;
    s += `<rect x="${cx - bw / 2}" y="${top}" width="${bw}" height="${Math.max(5, bot - top)}" fill="${col}" rx="2"/>`;
    if (i === P.hi) {
      s += `<rect x="${cx - bw / 2 - 9}" y="${y(h) - 10}" width="${bw + 18}" height="${y(l) - y(h) + 20}" fill="none" stroke="${hiCol}" stroke-width="3" rx="6" filter="url(#gl)"/>`;
      s += `<text x="${Math.min(Math.max(cx, 150), W - 150)}" y="16" text-anchor="middle" fill="${hiCol}" font-weight="900" font-size="14">${esc(P.entry)}</text>`;
    }
    const lab = (P.labels && P.labels[i] != null && P.labels[i] !== '') ? P.labels[i] : (P.labels ? '' : (up ? 'VERDE' : 'ROJA'));
    const ccol = up ? '#18f060' : '#f02a2a';
    s += `<circle cx="${cx}" cy="214" r="15" fill="none" stroke="${ccol}" stroke-width="3"/><text x="${cx}" y="219.5" text-anchor="middle" fill="#fff" font-weight="800" font-size="15">${i + 1}</text>`;
    if (lab) s += `<text x="${cx}" y="248" text-anchor="middle" fill="${ccol}" font-weight="800" font-size="12.5">${esc(lab)}</text>`;
  });
  return s + '</svg>';
}
