# OPTIONS BB · Centro de Comando

App web (Python, sin dependencias externas) con login, prueba gratis, suscripción mensual y estas pantallas:
**Centro de Comando** (como tu diseño) · **Flujo OI** (volumen → open interest) · **Sectores** · **Desempeño** (reporte de estrategias de Thinkorswim) · **Cuenta/Admin**.

## 1. Arrancar (modo DEMO, sin credenciales)
Requisitos: Python 3.10+. No necesita instalar nada para arrancar. Opcional: `python -m pip install openpyxl` (solo para el botón "Descargar Excel") y, en Windows, `python -m pip install tzdata`.
```
python server.py create-admin tu@correo.com      # crea tu usuario administrador
python server.py                                  # abre http://127.0.0.1:8080
```
Windows: doble clic en `iniciar.bat`. Sin credenciales de Schwab la app usa **datos simulados** (banner amarillo).

## 2. Datos reales de Schwab / Thinkorswim
1. developer.schwab.com → crea una app (Market Data) y obtén App Key y Secret. Callback: `https://127.0.0.1:8182`.
2. Define las variables y reinicia: `SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`, `SCHWAB_CALLBACK`.
3. `python server.py schwab-login` (o Cuenta → Conexión con Schwab) y pega la URL final a la que te redirige.
4. **El permiso de Schwab vence cada 7 días**: repite el paso 3 semanalmente.
Límite de Schwab ≈120 peticiones/min: la app las reparte y comparte el resultado entre todos los usuarios.

## 3. Volumen → Open Interest
Dos fotos automáticas por día hábil (hora del Este): **4:15 pm** (volumen del día D + OI previo) y **9:00 am** (OI de D+1).
`ΔOI = OI₁ − OI₀`, `%OI = ΔOI/OI₀`, `conversión = ΔOI/volumen` (≥ +50 % *apertura probable*, ≤ −50 % *cierre probable*).
Limitaciones: no distingue compra de venta; contratos que vencen se marcan "Vencido"; no conoce feriados (si el mercado cierra, la foto saldrá repetida).

## 4. Reporte de desempeño
En TOS: Charts → Strategies → Show Report → Trade List → clic derecho → Export to File. Súbelo en **Desempeño** (admin).
Acepta CSV/XLSX con columnas `Strategy` + `Trade P/L` (o `Estrategia` + `P/L`). Botón **Descargar Excel** genera el mismo formato "Resumen/Datos".

## 5. Suscripciones
- Registro = prueba gratis de `OBB_TRIAL_DAYS` días (7 por defecto). Vencida la prueba o la suscripción, la API responde 402 y la app solo deja ver "Cuenta".
- Cobro automático con **Stripe**: `STRIPE_SECRET_KEY`, un precio mensual por plan (`STRIPE_PRICE_BASICO`, `STRIPE_PRICE_INTERMEDIO`, `STRIPE_PRICE_AVANZADO`; `STRIPE_PRICE_ID` sigue funcionando y se asigna al plan `OBB_STRIPE_DEFAULT_PLAN`, por defecto avanzado), `STRIPE_WEBHOOK_SECRET`; webhook → `https://TU-DOMINIO/api/billing/webhook` (eventos: checkout.session.completed, invoice.paid, invoice.payment_failed, customer.subscription.updated/deleted).
- Sin Stripe puedes activar clientes a mano en Cuenta → Usuarios (+30 días pago, +7 prueba, revocar).

## 5b. Planes (Básico / Intermedio / Avanzado)
El plan se aplica **en el servidor** (un usuario no puede saltarse el bloqueo cambiando la pantalla).
| | Básico | Intermedio | Avanzado |
|---|---|---|---|
| Centro de Comando (acciones) | ✔ | ✔ | ✔ |
| Estrategias | 1 alcista + 1 bajista | 6 + 6 (las del Básico + 5 y 5) | 10 + 10 (todas) |
| Cover Call | ✔ | ✔ | ✔ |
| Flujo OI · Sectores · Desempeño | — | ✔ | ✔ |
| Señales de mentores | — | — | ✔ |
| Estrategias personalizadas | — | — | 2 |
| Videos | según el plan mínimo de cada video | | |
- Al registrarse el usuario elige el plan de su prueba gratis. El administrador puede cambiar el plan de cualquiera en Cuenta → Usuarios.
- Precios: escríbelos en **Planes** (como administrador) y quedan visibles para todos (no hay precios inventados).
- Qué estrategia va en cada plan: campo `tier` en `obb/strategies.py` (1 Básico, 2 Intermedio, 3 Avanzado).

## 5c. Cover Call
- **Calculadora**: pega la cadena de CALLS (Strike, Bid, Ask y opcional Delta/Volumen/OI) o escribe un strike y su prima. Resume a qué precio te ejercen, cuánto ganas, equilibrio y gráfico, y compara el 1.º vs el 5.º strike sobre el precio.
- **Simulador mensual**: te pregunta cuántos meses (1–36), pide mes a mes la cadena, el strike (o usa la regla por defecto) y el precio al vencimiento. Si te ejercen, recompra las acciones al precio del mes siguiente y sigue vendiendo. Compara contra solo mantener la acción y puede correr 1.º vs 5.º strike. Se pueden guardar simulaciones.
- Se evalúa solo al vencimiento (el ejercicio anticipado, sobre todo antes de dividendos, no se simula).

## 5d. Videos y Señales
- **Videos**: el administrador agrega videos por enlace de YouTube (con plan mínimo y categoría). Para importar los últimos videos del canal define `OBB_YT_CHANNEL_ID` (empieza con `UC…`). Enlaces del canal y el sitio: `OBB_YT_CHANNEL_URL` (por defecto https://www.youtube.com/@optionsbb) y `OBB_WEBSITE_URL`. Un video bloqueado por plan no revela su ID.
- **Señales (Avanzado)**: catálogo de estrategias por reglas (el administrador agrega las de sus mentores con su nombre) + 2 estrategias personalizadas por usuario con un constructor de reglas (cruces de medias, rupturas, RSI, volumen, color de vela…). Las incluidas de fábrica son genéricas, no de un mentor en particular.

## 5e. Lista de seguimiento, Análisis, Ranking, 401(k), Inicio y Manual
- **Lista de seguimiento** (Centro de Comando): hasta 30 acciones propias o importadas por sector; % de cambio Hoy (por defecto), 7, 15, 30, 90 y 360 días a elección del usuario.
- **Señales → Mi selección**: el usuario marca estrategias del catálogo/núcleo y añade las suyas (Avanzado).
- **Análisis de acción**: resumen financiero (rango 52 sem, volatilidad, RSI, SMAs, opciones) y tendencia/mejores estrategias por temporalidad (5m, 15m, 30m, 1h, diario). P/E, EPS y dividendos llegan al enlazar Schwab.
- **Ranking** (Intermedio+): estrategias por temporalidad con señales, % aciertos, rendimiento promedio (cambio 5 velas después, mín. 20 señales), acciones donde están activas y donde mejor funcionaron.
- **401(k) y retiro** (todos los planes): proyección efectivo vs acciones vs acciones+cover call (dólares futuros y de hoy), meta de retiro, impacto de comisiones y cartera propia. Supuestos editables; límites 2026: 401(k) $24,500, IRA $7,500. Cover call en 401(k) solo con ventana de corretaje y aprobación del broker.
- **Inicio**: cuestionario de 4 preguntas → perfil (conservador/moderado/crecimiento/activo) y ruta de módulos según el plan.
- **Manual**: en la app (menú Más) desde `static/manual.md`.
- Temas de Schwab: no hay evidencia de que su API exponga las listas temáticas; se ofrecen listas propias por sector.

## 5f. Versión 2.0 (ver CHANGELOG.md)
- Listas Optionsbb (3×10) editables por el admin: `POST /api/admin/default-lists {"low":[...],"mid":[...],"high":[...]}`; cada usuario tiene además «Mi lista» por nivel.
- Mi ETF, ¿Qué hubiera pasado si…?, Apalancados + Cover Call (Avanzado). Primas estimadas: `obb/overlay.py`. Ejemplos y lista de apalancados: `obb/scenarios.py`.
- Logos del ETF: variable `LOGO_URL` (por defecto un servicio público de logos; vacío = siglas). Idiomas: `static/js/i18n-en.js`.
- Flujo OI solo en Avanzado; el menú oculta lo que el plan no incluye.

## 5g. Versión 3.0 (ver CHANGELOG.md)
- Datos opcionales: `FINNHUB_API_KEY` (fechas de earnings) y `ALPHAVANTAGE_API_KEY` (historial de dividendos), ambas con plan gratuito. Sin ellas, en modo real esas pantallas muestran el aviso; en DEMO usan datos simulados.
- GEX y fundamentales usan los campos de la API de Schwab (gamma, volatilidad, dividendos); si falta el gamma se calcula con Black-Scholes.
- ETF de Optionsbb, listas base y tasas del banco/primas orientativas las edita el administrador (`/api/admin/official-etfs`, `/api/admin/default-lists`, `/api/admin/guide`).
- Idiomas: `python tools/i18n/generate.py` regenera `i18n-en.js` e `i18n-pt.js` desde `tools/i18n/fuentes/*.txt` (formato `español ||| inglés ||| portugués`; `{}` = cifra, `{*}` = texto libre).

## 5h. Versión 3.1 (ver CHANGELOG.md)
Referidos, sectores definitivos dentro de la app (sin Excel), dividendos con calculadora, earnings de 12 reportes, casos de estudio, nuevos indicadores. Kit de despliegue en `deploy/` (app.optionsbb.com).

## 6. Producción
Ponla detrás de HTTPS (Caddy/nginx/Cloudflare) y define `OBB_HOST=0.0.0.0`, `OBB_PUBLIC_URL=https://…`, `OBB_COOKIE_SECURE=1`, `OBB_TRUST_PROXY=1`, `OBB_ADMIN_EMAIL`. Haz respaldo de la carpeta `data/` (base de datos y clave).
Otras variables: `OBB_PORT`, `OBB_DATA`, `OBB_DEMO` (1 fuerza demo, 0 exige Schwab).

## 7. Importante
- Las reglas de las estrategias de `obb/strategies.py` son definiciones genéricas del patrón (p. ej. vela verde = 3 rojas + 2 verdes). **Ajústalas a tu thinkScript real (OBB_VVV3, OBB_VRV…).**
- La conexión a Schwab y Stripe está escrita según su documentación pero **no pudo probarse con cuentas reales** en el entorno de desarrollo: pruébala primero en modo prueba/sandbox.
- Pruebas: `python -m unittest discover -s tests`. Contenido educativo, no es asesoría financiera.
