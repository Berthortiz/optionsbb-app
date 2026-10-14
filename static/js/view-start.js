/* Ilustraciones de bienvenida por nivel + pantalla «¿Por dónde empiezo?» (personajes originales) */
(function () {
  const SKIN = ['#f2c9a0', '#d9a06f', '#a8734a'];
  const person = (x, y, shirt, o = {}) => {
    const skin = SKIN[o.skin || 0], face = o.face || 'worry';
    const mouth = face === 'happy' ? `<path d="M${x - 5} ${y - 41}q5 6 10 0" stroke="#432" stroke-width="2" fill="none"/>`
      : `<path d="M${x - 5} ${y - 38}q5 -5 10 0" stroke="#432" stroke-width="2" fill="none"/>`;
    const sweat = face === 'worry' ? `<path d="M${x + 14} ${y - 58}q4 7 0 10q-4 -3 0 -10z" fill="#7cc7ff"/>` : '';
    const hat = o.hat ? `<path d="M${x - 15} ${y - 54}a15 13 0 0 1 30 0z" fill="#ffc933"/><rect x="${x - 17}" y="${y - 55}" width="34" height="4" rx="2" fill="#e6a900"/>` : `<path d="M${x - 14} ${y - 52}a14 12 0 0 1 28 -2v4z" fill="${o.hair || '#3b2a20'}"/>`;
    return `<g>${o.shadow === false ? '' : `<ellipse cx="${x}" cy="${y + 40}" rx="22" ry="5" fill="#000" opacity=".25"/>`}
      <rect x="${x - 9}" y="${y + 12}" width="7" height="28" rx="3" fill="#2a3550"/><rect x="${x + 2}" y="${y + 12}" width="7" height="28" rx="3" fill="#2a3550"/>
      <rect x="${x - 15}" y="${y - 30}" width="30" height="46" rx="10" fill="${shirt}"/>
      <rect x="${x - 21}" y="${y - 26}" width="8" height="30" rx="4" fill="${shirt}"/><rect x="${x + 13}" y="${y - 26}" width="8" height="30" rx="4" fill="${shirt}"/>
      <circle cx="${x}" cy="${y - 44}" r="15" fill="${skin}"/>${hat}
      <circle cx="${x - 5}" cy="${y - 46}" r="2" fill="#222"/><circle cx="${x + 5}" cy="${y - 46}" r="2" fill="#222"/>${mouth}${sweat}</g>`;
  };
  const coin = (x, y, r, txt, op = 1) => `<g opacity="${op}"><circle cx="${x}" cy="${y}" r="${r}" fill="#f5c542" stroke="#b8860b" stroke-width="2"/><text x="${x}" y="${y + r / 3}" text-anchor="middle" font-size="${r * 1.1}" font-weight="700" fill="#8a6200">${txt}</text></g>`;

  const sceneBasic = () => `<svg viewBox="0 0 560 260" role="img" aria-label="Trabajadores cuyo dinero en el banco pierde valor">
    <rect width="560" height="260" rx="14" fill="#0c1a33"/><rect y="215" width="560" height="45" fill="#10233f"/>
    <g><path d="M30 95l70 -35l70 35z" fill="#5b6f94"/><rect x="40" y="95" width="120" height="8" fill="#7b8fb5"/>
      ${[50, 75, 100, 125, 145].map(x => `<rect x="${x}" y="105" width="10" height="75" fill="#aab8d6"/>`).join('')}
      <rect x="30" y="180" width="140" height="10" fill="#7b8fb5"/><rect x="22" y="190" width="156" height="12" fill="#5b6f94"/>
      <text x="100" y="92" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">BANCO</text></g>
    ${coin(70, 225, 12, '$')}${coin(110, 228, 10, '$', .7)}${coin(145, 230, 8, '¢', .5)}
    <path d="M60 148l22 18l-12 3" fill="none"/>
    ${person(230, 170, '#e0566a', { hat: true, face: 'worry' })}${person(285, 175, '#4aa3df', { hat: true, face: 'worry', skin: 1 })}${person(340, 170, '#6bbf6b', { face: 'worry', skin: 2, hair: '#222' })}
    <g><rect x="395" y="40" width="150" height="100" rx="12" fill="#14325a" stroke="#38d6ff" stroke-width="2"/>
      <text x="470" y="72" text-anchor="middle" font-size="22" font-weight="800" fill="#38d6ff">401(k)</text>
      <path d="M415 118l30 -22l25 14l30 -30l30 12" stroke="#6af0a0" stroke-width="4" fill="none" stroke-dasharray="6 5"/>
      <text x="470" y="132" text-anchor="middle" font-size="11" fill="#cfe6ff">FUTURO</text></g>
    <rect x="465" y="140" width="10" height="75" fill="#8a6b3f"/><rect x="420" y="180" width="100" height="22" rx="6" fill="#8a6b3f"/>
    <text x="470" y="196" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">HOY → 20 años</text>
    <path d="M195 70v-20m0 20l-8 -8m8 8l8 -8" stroke="#ff6b78" stroke-width="4" fill="none"/>
    <text x="215" y="62" font-size="14" font-weight="700" fill="#ff8b95">el dinero se deprecia</text></svg>`;

  const sceneMid = () => `<svg viewBox="0 0 560 260" role="img" aria-label="Inversores con algunas acciones y poco conocimiento">
    <rect width="560" height="260" rx="14" fill="#0c1a33"/><rect y="215" width="560" height="45" fill="#10233f"/>
    ${[[40, 40, '#2ecc71', 'AAPL', '+2%'], [150, 30, '#ff5a6a', 'TSLA', '−5%'], [260, 45, '#2ecc71', 'NVDA', '+1%'], [370, 28, '#ff5a6a', 'AMZN', '−3%']].map(([x, y, c, s, p]) => `
      <g><rect x="${x}" y="${y}" width="95" height="60" rx="8" fill="#14325a" stroke="${c}" stroke-width="2"/><text x="${x + 10}" y="${y + 22}" font-size="14" font-weight="700" fill="#fff">${s}</text>
      <text x="${x + 10}" y="${y + 46}" font-size="16" font-weight="700" fill="${c}">${p}</text></g>`).join('')}
    ${person(120, 170, '#e0a43a', { face: 'worry' })}${person(200, 175, '#9b6bd6', { face: 'worry', skin: 1 })}
    <g><ellipse cx="300" cy="150" rx="70" ry="38" fill="#fff" opacity=".95"/><circle cx="238" cy="190" r="8" fill="#fff" opacity=".95"/><circle cx="224" cy="204" r="4" fill="#fff" opacity=".95"/>
      <text x="300" y="146" text-anchor="middle" font-size="13" font-weight="700" fill="#14325a">¿Compro?</text><text x="300" y="164" text-anchor="middle" font-size="13" font-weight="700" fill="#14325a">¿Vendo? ¿Espero?</text></g>
    <text x="500" y="170" text-anchor="middle" font-size="64" font-weight="800" fill="#ffc933" opacity=".9">?</text>
    <text x="480" y="205" text-anchor="middle" font-size="12" fill="#cfe6ff">algo de bolsa, poco método</text></svg>`;

  const sceneAdv = () => `<svg viewBox="0 0 560 260" role="img" aria-label="Inversor con herramientas pero sin rentabilidad">
    <rect width="560" height="260" rx="14" fill="#0c1a33"/><rect y="200" width="560" height="60" fill="#10233f"/>
    ${[[60, 25, 'GREEKS'], [190, 15, 'CADENA'], [320, 25, 'P&L']].map(([x, y, l], i) => `
      <g><rect x="${x}" y="${y}" width="115" height="80" rx="8" fill="#0a1424" stroke="#38d6ff" stroke-width="2"/><text x="${x + 8}" y="${y + 16}" font-size="11" fill="#38d6ff">${l}</text>
      <path d="M${x + 10} ${y + 62}l20 -18l18 10l22 -26l24 30l16 -12" stroke="${i === 2 ? '#ff5a6a' : '#6af0a0'}" stroke-width="3" fill="none"/></g>`).join('')}
    ${person(250, 185, '#38d6ff', { face: 'worry', shadow: false })}
    <rect x="30" y="165" width="400" height="14" rx="5" fill="#5b4630"/><rect x="60" y="179" width="8" height="30" fill="#5b4630"/><rect x="392" y="179" width="8" height="30" fill="#5b4630"/>
    <g><rect x="445" y="60" width="100" height="90" rx="12" fill="#2a1420" stroke="#ff5a6a" stroke-width="2"/>
      <text x="495" y="92" text-anchor="middle" font-size="12" fill="#ffb3bb">Resultado</text><text x="495" y="124" text-anchor="middle" font-size="26" font-weight="800" fill="#ff5a6a">≈ $0</text><text x="495" y="142" text-anchor="middle" font-size="11" fill="#ffb3bb">sin rentabilidad</text></g>
    <text x="230" y="238" text-anchor="middle" font-size="12" fill="#cfe6ff">muchas herramientas · estrategia sin construir</text></svg>`;

  const SCENES = { basico: sceneBasic, intermedio: sceneMid, avanzado: sceneAdv };
  const COPY = {
    basico: ['Tu dinero en el banco se deprecia', 'La inflación le quita poder de compra cada año y el 401(k) solo crece si lo pones a trabajar. Si no empiezas hoy, tu futuro será igual que tu presente.'],
    intermedio: ['Ya invirtiste, pero sin un método', 'Tienes algunas acciones, pero decides con poca información. Falta una estrategia que genere ingresos mientras esperas.'],
    avanzado: ['Tienes las herramientas, aún no la rentabilidad', 'Gráficos, cadenas, griegas… pero sin una estrategia probada el resultado no llega. El Centro de Comando es para construirla.'],
  };
  const FOOT = 'En Optionsbb te acompañamos a hacer más efectiva tu estrategia y, si no la tienes, la construimos juntos.';

  OBB.hero = async function (plan) {
    let g = { bank_pays: 1.43, bank_charges: 26 };
    try { g = await api('/api/guide'); } catch (e) { /* valores por defecto */ }
    const [h, p] = COPY[plan] || COPY.basico;
    const bank = plan === 'basico' ? `<div class="bankbox"><b>¿Quién gana?</b>
      <div class="bk"><span>El banco te paga</span><strong class="up">${g.bank_pays}% anual</strong></div>
      <div class="bk"><span>El banco te cobra</span><strong class="down">${g.bank_charges}% anual</strong></div>
      <small>Tasas de referencia editables por el administrador; revisa las de tu banco.</small></div>` : '';
    return `<section class="panel cyan hero hero-${plan}"><div class="hero-art">${(SCENES[plan] || sceneBasic)()}</div>
      <div class="hero-tx"><h2>${h}</h2><p>${p}</p>${bank}<p class="hero-foot">${FOOT}</p>
      <div class="stack"><button class="btn green" data-go="empezar">¿Por dónde empiezo?</button></div></div></section>`;
  };

  /* ---------- «¿Por dónde empiezo?» ---------- */
  const profeta = () => `<svg viewBox="0 0 180 200" role="img" aria-label="Profeta calvo"><ellipse cx="90" cy="190" rx="50" ry="7" fill="#000" opacity=".25"/>
    <path d="M45 190l15 -95h60l15 95z" fill="#7a5cc9"/><path d="M75 95l15 30l15 -30z" fill="#e9dcff"/>
    <rect x="125" y="100" width="8" height="85" fill="#8a6b3f" transform="rotate(12 129 140)"/><circle cx="143" cy="98" r="9" fill="#ffd54a"/>
    <circle cx="90" cy="62" r="32" fill="#f2c9a0"/><path d="M62 52q28 -30 56 0" fill="#fbd9b3"/>
    <circle cx="80" cy="60" r="4" fill="#222"/><circle cx="100" cy="60" r="4" fill="#222"/><path d="M74 54l10 -3M96 51l10 3" stroke="#222" stroke-width="2"/>
    <path d="M70 80q20 16 40 0q-6 22 -20 24q-14 -2 -20 -24z" fill="#ddd"/><path d="M60 95l-25 -30" stroke="#f2c9a0" stroke-width="9" stroke-linecap="round"/></svg>`;
  const ferrari = () => `<svg viewBox="0 0 260 200" role="img" aria-label="Vendedor con auto rojo y humo"><ellipse cx="130" cy="188" rx="110" ry="7" fill="#000" opacity=".25"/>
    <path d="M30 150q10 -35 55 -38l45 -2q25 -28 55 -2l35 6q22 6 25 36z" fill="#e5242c"/><path d="M95 112q20 -22 45 -2z" fill="#9fd8ff"/>
    <circle cx="80" cy="152" r="17" fill="#222"/><circle cx="80" cy="152" r="7" fill="#aaa"/><circle cx="195" cy="152" r="17" fill="#222"/><circle cx="195" cy="152" r="7" fill="#aaa"/>
    <g fill="#9aa4b5" opacity=".8"><circle cx="22" cy="140" r="10"/><circle cx="8" cy="124" r="13" opacity=".7"/><circle cx="22" cy="104" r="16" opacity=".5"/><circle cx="6" cy="80" r="14" opacity=".35"/></g>
    <rect x="130" y="62" width="84" height="24" rx="4" fill="#fff"/><text x="172" y="79" text-anchor="middle" font-size="12" font-weight="800" fill="#e5242c">ALQUILADO</text>
    <g transform="translate(222 80)"><circle cx="0" cy="0" r="14" fill="#f2c9a0"/><path d="M-14 -4q14 -16 28 0q-6 -8 -14 -8t-14 8z" fill="#111"/><rect x="-12" y="-4" width="10" height="5" rx="2" fill="#111"/><rect x="2" y="-4" width="10" height="5" rx="2" fill="#111"/><path d="M-5 8q5 4 10 0" stroke="#432" stroke-width="2" fill="none"/>
    <rect x="-12" y="14" width="24" height="34" rx="8" fill="#1d1d1d"/></g></svg>`;

  OBB.views.empezar = {
    async render(el) {
      let g = { cc_low: 0.5, cc_high: 2, quotes: [] };
      try { g = await api('/api/guide'); } catch (e) { /* defecto */ }
      const rows = (g.quotes || []).filter(q => q.price).map(q => `<tr><td><b>${esc(q.symbol)}</b></td><td>${fmtMoney(q.price)}</td><td>${fmtMoney(q.price * 100)}</td>
        <td>${fmtMoney(q.price * 100 * g.cc_low / 100)} – ${fmtMoney(q.price * 100 * g.cc_high / 100)}</td></tr>`).join('');
      el.innerHTML = `<div class="view-title"><h1>¿Por dónde <span>empiezo?</span></h1><span class="muted">Plataforma, dinero necesario y expectativas realistas</span></div>
      <div class="grid2">
      <section class="panel cyan"><h2>1. La plataforma</h2>
        <p>Te recomendamos <b>Thinkorswim de Charles Schwab</b>. En Schwab las acciones cuestan <b>$0 de comisión</b> y las opciones <b>$0.65 por contrato</b>. Incluye <b>paperMoney</b>, un simulador con dinero virtual para practicar antes de arriesgar un dólar.</p>
        <p class="muted">Para operar opciones Schwab exige mínimos de cuenta y aprobación por niveles; consulta los requisitos vigentes en schwab.com antes de abrir la cuenta.</p></section>
      <section class="panel green"><h2>2. ¿Cuánto dinero necesito?</h2>
        <p>Para el cover call necesitas <b>100 acciones por contrato</b>. El capital depende del precio de la acción:</p>
        <table class="tbl"><thead><tr><th>Acción</th><th>Precio</th><th>100 acciones</th><th>Prima mensual orientativa</th></tr></thead><tbody>${rows || '<tr><td colspan="4" class="muted">Sin precios disponibles</td></tr>'}</tbody></table>
        <p class="muted">Prima orientativa: ${g.cc_low}% – ${g.cc_high}% mensual del valor de las acciones. Varía con la volatilidad y no está garantizada. Puedes empezar en paperMoney sin capital.</p></section></div>
      <section class="panel yellow"><h2>3. ¿Cuánto puedo ganar?</h2>
        <p>Con cover call, un rango razonable de primas es de <b>${g.cc_low}% a ${g.cc_high}% mensual</b> sobre el capital en acciones, <b>mientras la acción no caiga</b>. Si la acción baja, la prima amortigua parte de la pérdida pero no la elimina; si sube mucho, limitas la ganancia por encima del strike.</p>
        <p><b>Nadie puede prometerte un resultado.</b> Operar acciones y opciones conlleva riesgo de pérdida.</p></section>
      <section class="panel red"><h2>¿Es verdad lo que dicen?</h2>
        <div class="myths">
          <div class="myth"><div class="fig">${profeta()}</div><div class="bubble">“¡Sígueme y serás millonario con $500!”<br><em>(El profeta no dice que él vive de vender el curso.)</em></div><div class="stamp">MENTIRA</div></div>
          <div class="myth"><div class="fig">${ferrari()}</div><div class="bubble">“Me hice rico en 3 semanas… mira mi Ferrari.”<br><em>(Es alquilado, y lo único que sube es el humo.)</em></div><div class="stamp">MENTIRA</div></div>
        </div>
        <p>La riqueza con bolsa se construye con <b>método, riesgo controlado y tiempo</b>. En Optionsbb te acompañamos a construir tu estrategia, sin humo.</p></section>`;
    },
  };
})();
