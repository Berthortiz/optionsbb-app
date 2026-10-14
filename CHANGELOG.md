# Historial de versiones · Options BB Centro de Comando

Cada entrega lleva número de versión (se ve al pie de la app y en `obb/version.py`).
Regla: cambios grandes → sube el segundo número (2.1, 2.2…); correcciones → el tercero (2.0.1).

## 3.1.0 · 13 oct 2026
**Referidos (nuevo menú «Referidos»)**
- Código y enlace personal. Un referido cuenta cuando **paga** su primera suscripción (no durante la prueba).
- 1 referido pagado → **20 % de descuento** el mes siguiente (cola: uno activo a la vez).
- 10 referidos → **6 meses gratis de Avanzado**; 20 referidos → **1 año gratis** (los premios se acumulan: 6 + 12 = 18 meses; el administrador puede ajustarlo).
- Administrador: lista de referidos y avisos «pendiente de aplicar a mano» si el cupón de Stripe no pudo aplicarse.
**Correcciones y mejoras**
- Encabezado: «OPTIONSBB» ya no tapa «COMANDO».
- **Mercado › Sectores**: restaurados los 11 sectores con sus empresas; la lista queda **definitiva dentro de la app** (ya no se lee ningún Excel) y el administrador puede agregar o quitar empresas.
- Velas del detalle de una acción: **solo borde** (colores suaves).
- **Dividendos**: calculadora por número de acciones o monto a invertir, ingreso mensual/anual y proyección de crecimiento.
- **Earnings**: últimos **12 reportes**, sorpresa de EPS, tendencia, barra de movimiento y racha.
- **¿Qué hubiera pasado si…?**: biblioteca de casos de estudio por categoría (9 oficiales), el administrador puede crear casos y cada usuario guarda los suyos.
- **Estrategia personalizada**: nuevos indicadores cruce dorado / cruz de la muerte, breakout alcista y bajista (con volumen), doji, vela envolvente, más plantillas rápidas.
- Historial de escaneo de señales ampliado a 5 días.
- Traducciones ES/EN/PT actualizadas (1310 textos). 55 pruebas automáticas.
**Notas / límites**
- El cruce dorado se evalúa en velas de 5 minutos (intradía), no en velas diarias.
- Los precios de los casos de estudio son ilustrativos.
- Aplicación del cupón de Stripe y APIs en vivo (Finnhub, Alpha Vantage, Schwab) sin probar con datos reales.
**Pendiente para la próxima versión**: indicador sobre la acción que indique si está en **aceleración o consolidación** (el cliente lo enviará).

## 3.0.0 · 11 oct 2026  (incluye los cambios 2.1 y 2.2)
**2.1 · Mi ETF, Mis listas, idiomas**
- **Mi ETF**: arriba los **3 ETF fijos de Optionsbb** (Poco riesgo, Riesgo moderado, Alto riesgo) con su composición y cantidad de acciones; el usuario solo cambia el **monto a invertir**. Solo el administrador cambia acciones/cantidades (Editar (administrador)). Para otra mezcla: «Crear mi ETF a partir de este» o «Agregar acciones desde otro ETF» (de los 3 de Optionsbb o de los propios).
- Gráfico circular con **colores pastel más claros** y **logos** (cadena de respaldo: `/logos/SIM.png` → `LOGO_URL` → favicon del sitio → siglas).
- **Mis listas** pasa a ser su propio menú; al agregar una empresa desde Análisis eliges el nivel de riesgo y la app te lleva a verla en la lista.
- **Idiomas ES / EN / PT** en toda la app (diccionarios con cifras y mensajes del servidor, selector también en el login) y **manual traducido** (`manual.en.md`, `manual.pt.md`).
**2.2 · Bienvenida**
- **Ilustraciones por nivel** en Inicio: Básico (trabajadores, dinero que se deprecia, 401(k); «¿Quién gana?»: el banco paga 1.43 % / cobra 26 %, editable), Intermedio (inversores con poca información), Avanzado (herramientas sin rentabilidad) + mensaje «En Optionsbb te acompañamos…».
- Pantalla **¿Por dónde empiezo?**: Thinkorswim de Charles Schwab (acciones $0, opciones $0.65 por contrato, paperMoney), capital necesario (100 acciones por contrato) y expectativas realistas, con los cartoons del profeta calvo y el del Ferrari alquilado («MENTIRA»).
**3.0 · Nuevos módulos**
- **Calculadora de opciones** (Intermedio: plantillas; Avanzado: hasta 6 patas libres y prima propia): costo/crédito, ganancia y pérdida máximas, equilibrios, probabilidad de ganar, griegas, curva al vencimiento y de «hoy».
- **Historial de earnings** (Avanzado): movimiento del precio en cada reporte, **calculado automáticamente** (fechas Finnhub + velas diarias de Schwab, 5 años).
- **Dividendos** (todos los planes; historial desde Intermedio): rendimiento, pago, frecuencia, ingreso con 100 acciones, crecimiento.
- **Gamma exposure – GEX** (Avanzado): paredes de calls y puts por strike y vencimiento, gamma flip, GEX neto y régimen.
**Técnico**
- Nuevos endpoints: `/api/opcalc`, `/api/earnings`, `/api/dividends`, `/api/dividends/table`, `/api/gex`, `/api/guide`, `/api/admin/guide`, `/api/etfs/official*`.
- Variables opcionales: `FINNHUB_API_KEY`, `ALPHAVANTAGE_API_KEY`. Las llamadas a Finnhub, Alpha Vantage y a los campos de gamma/fundamentales de Schwab **no pudieron probarse** sin acceso a internet real; en DEMO usan datos simulados.
- Traducciones: fuentes y generador en `tools/i18n/` (`python tools/i18n/generate.py`).
- 44 pruebas automáticas.

## 2.0.0 · 11 oct 2026
**Diseño y menú**
- Sectores: señales con colores más suaves y marcos azules (el mismo azul del cuadro de datos de la calculadora de Cover Call).
- El menú muestra solo lo que incluye el plan del usuario; se agrupó en Ingresos / Mi cartera / Mercado / Más.
- **Flujo OI pasa a ser solo del plan Avanzado** (Intermedio conserva Sectores, Ranking y Desempeño).
**Nuevo**
- Centro de Comando: tres listas **Optionsbb** de 10 acciones (Poco riesgo, Riesgo moderado, Alto riesgo) + **Mi lista** editable por nivel; el administrador puede cambiar las listas base.
- **Mi ETF**: ETF propio (hasta 5), acciones o dólares por posición, gráfico circular con logos y % de peso, tabla de rendimiento sin movimiento / en movimiento, sin cover call / con cover call / suma.
- **¿Qué hubiera pasado si…?**: ejemplos BYND y MSFT (precios ilustrativos editables) o historial de un símbolo; % de pérdida amortizada.
- **Apalancados + Cover Call** (Avanzado): NVDL, AMDL, TSLL, CONL, MSTU, PLTU, TQQQ, SOXL, SPXL; avisos de riesgo, simulador y calculadora de decadencia.
- Nota destacada de Cover Call («tus acciones nunca más permanecerán inactivas…», «estrategia silenciosa», «100 acciones por contrato») en Cover Call, listas, ETF, escenarios y apalancados.
- Idiomas: selector ES/EN con diccionario (menús y títulos principales); base para añadir más idiomas.
- Motor de cover call de recubrimiento (`obb/overlay.py`) con primas estimadas (Black-Scholes).
**Seguridad / técnico**
- Las peticiones PUT también exigen la cabecera anti-CSRF.
- Logos de compañías configurables con `LOGO_URL` (vacío = solo siglas).
- 38 pruebas automáticas.

## 1.0.0 · 10 oct 2026
Base: login, prueba de 7 días, 3 planes, Cover Call, videos, señales y catálogo, lista de seguimiento, análisis, ranking, 401(k), inicio por perfil y manual.
