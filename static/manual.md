# Manual de usuario · Options BB Centro de Comando

> Contenido educativo. No es asesoría financiera ni fiscal. Operar acciones y opciones conlleva riesgo de pérdida.

## 1. Qué es esta app
Options BB Centro de Comando reúne en un solo lugar: señales de estrategias sobre tus acciones, análisis de cada acción, el módulo de **Cover Call** (calculadora y simulador), el módulo de **401(k) y retiro**, el flujo de volumen a open interest de las opciones, rankings de estrategias, una biblioteca de videos y más. Lo que ves depende de tu **plan** de suscripción.

## 2. Primeros pasos
1. **Crea tu cuenta**: elige el plan con el que quieres hacer tu prueba gratis (7 días, sin tarjeta).
2. **Responde el cuestionario de Inicio** (4 preguntas). La app te muestra una ruta con los módulos que más te convienen según tu perfil: Conservador, Moderado, Crecimiento o Activo.
3. Cuando termine la prueba, entra a **Planes** y suscríbete para seguir usando la app. Sin suscripción activa solo verás Planes y Cuenta.

## 3. Qué incluye cada plan
| Módulo | Básico | Intermedio | Avanzado |
|---|---|---|---|
| Inicio, ¿Por dónde empiezo?, Centro de Comando, Mis listas, Análisis | Sí | Sí | Sí |
| Cover Call | Sí | Sí | Sí |
| 401(k) y retiro | Sí | Sí | Sí |
| Estrategias | 1 alcista + 1 bajista | 6 + 6 | 10 + 10 |
| Mi ETF (3 ETF Optionsbb y los tuyos), Dividendos, ¿Qué hubiera pasado si…? | Sí | Sí | Sí |
| Calculadora de opciones | No | Plantillas | Plantillas + patas libres |
| Sectores, Ranking, Desempeño | No | Sí | Sí |
| Flujo OI | No | No | Sí |
| Historial de Earnings | No | No | Sí |
| Gamma exposure (GEX) | No | No | Sí |
| Apalancados + Cover Call | No | No | Sí |
| Señales de mentores | No | No | Sí |
| Estrategias personalizadas | No | No | 2 |
| Videos | Los de nivel básico | Hasta nivel intermedio | Todos |

El menú solo muestra lo que tu plan incluye (así es más corto y claro). Lo demás lo ves en **Planes**.

## 4. Centro de Comando
- **Gráfico**: escribe un símbolo y elige el rango (1D, 5D, 1M, 3M, 1Y). Las flechas marcan señales recientes de las estrategias elegidas.
- **Estrategia alcista / bajista**: elige una estrategia de cada lado. El panel central dibuja el patrón y explica la regla. El número verde o rojo indica cuántas acciones tienen señal ahora.
- **Listas dinámicas**: acciones con señal ahora, con precio y % de cambio. Toca un símbolo para verlo en el gráfico.
- **Contratos con más volumen**: los contratos de opciones más negociados ahora.
- **Mis listas**: ahora vive en su propio menú (ver sección 4b).

## 4b. Mis listas
Tres cuadros de 10 acciones: **Lista Optionsbb · Poco riesgo**, **Riesgo moderado** y **Alto riesgo**. Cada cuadro tiene dos pestañas: **Lista Optionsbb** (la selección de Optionsbb) y **Mi lista** (tuya, hasta 10 acciones por nivel de riesgo; puedes agregar, quitar o pulsar *Copiar lista Optionsbb* para empezar desde ella). Por defecto ves el cambio de **Hoy**; marca los periodos que quieras: 7, 15, 30, 90, 180 y 360 días. Desde cada fila abres el **Análisis**.
Cuando agregas una empresa desde **Análisis** (botón *+ Mi lista*), eliges el nivel de riesgo y la app te lleva a **Mis listas** para que la veas agregada.

## 4c. ¿Por dónde empiezo?
Pantalla de bienvenida: qué plataforma usar (**Thinkorswim de Charles Schwab**, con paperMoney para practicar sin riesgo), cuánto dinero hace falta (100 acciones por contrato de cover call) y qué se puede esperar de forma realista. Incluye los mitos de «hazte rico en 3 semanas». En **Inicio** verás además una ilustración distinta según tu plan.

## 5. Análisis de acción
Escribe un símbolo y pulsa **Analizar**. Verás:
- **Cambio** de Hoy, 7, 15, 30, 90 y 360 días.
- **Resumen financiero**: gráfico de 90 días, posición en el rango de 52 semanas, distancia al máximo y mínimo, volatilidad anual, mayor caída del último año, RSI, medias móviles, tendencia y volumen contra su promedio.
- **Por temporalidad** (5 min, 15 min, 30 min, 1 hora y diario): tendencia, RSI y las estrategias con mejor historial en **esa** acción. Una etiqueta AHORA indica que la estrategia está activa en este momento.
- Botones para ver el gráfico, agregar a tu lista y **abrir el Cover Call con esa acción ya cargada**.

> P/E, ganancias, dividendos y capitalización se añadirán al enlazar la cuenta de Schwab. Hoy el resumen sale de precio, volumen y opciones.

## 6. Cover Call
Un cover call consiste en vender un contrato de opción call por cada 100 acciones que ya tienes. Cobras una **prima** a cambio de aceptar vender tus acciones al **strike** si al vencimiento el precio lo supera.

### 6.1 Calculadora
1. Escribe el precio actual, tu costo por acción, el número de acciones (múltiplos de 100) y las fechas.
2. Pega la cadena de **calls** del vencimiento (columnas Strike, Bid, Ask y opcionalmente Delta, Volumen y OI). En Thinkorswim: abre la cadena, selecciona las filas de calls, copia y pega. También puedes usar la opción **Un strike a mano**.
3. Elige qué strike vender: **1.º** (el inmediato sobre el precio), **5.º** u otro número.
4. Pulsa **Calcular**.

Te muestra, en palabras: cuánto cobras, **a qué precio te ejercen**, cuánto subió o debe subir, tu ganancia máxima, lo que ganas si la acción no se mueve, el punto de equilibrio y un gráfico. La tabla de todos los strikes te deja tocar cualquiera para recalcular. Spread en rojo significa que el bid y el ask están muy separados o hay poco open interest: la prima real puede ser menor.

**¿Prima en Bid o en punto medio?** Bid es lo conservador. El punto medio es lo habitual al poner una orden límite, pero puede tardar en llenarse.

### 6.2 Cómo elegir el strike
- **Strike inmediato superior**: cobras más prima, pero casi renuncias a la subida y te ejercen con más probabilidad.
- **5.º strike sobre el precio**: cobras menos, pero dejas subir la acción antes de topar tu ganancia. Si te ejercen, la ganancia máxima suele ser mayor.
- La calculadora compara ambos y te dice **sobre qué precio gana el 5.º strike**.
- Revisa si hay **earnings** antes del vencimiento: el precio puede saltar más allá de cualquier strike.

### 6.3 Simulador mensual
1. Indica la acción, las acciones, el costo, la regla de strike y **por cuántos meses** quieres simular (1 a 36).
2. Pulsa **Crear los meses**. Para cada mes escribe fecha de venta, vencimiento, precio al vender, la cadena de calls, el strike que vendiste (opcional) y el precio al vencimiento.
3. Pulsa **Simular**. Si en un mes te ejercen, la app asume que **recompras las acciones** al precio del mes siguiente y sigues vendiendo.
4. **Comparar 1.º vs 5.º strike** corre ambos escenarios con los mismos datos.
5. **Guardar simulación** la deja en la pestaña Guardadas.

Resultado: ganancia total, rendimiento y anualizado, primas cobradas, veces ejercida, comparación con **solo mantener la acción**, mayor caída y la subida que dejaste de ganar.

> El ejercicio se evalúa solo al vencimiento. En la práctica puede ocurrir antes, sobre todo antes de un dividendo.

## 7. 401(k) y retiro
El objetivo de este módulo es mostrar que **el dinero quieto pierde poder de compra** y comparar caminos con tus propios números.

- **Proyección**: compara **Efectivo**, **Acciones** y **Acciones + Cover Call**, en dólares futuros o en dólares de hoy. Si escribes tu salario y lo que aporta tu empresa, calcula ese aporte (dinero gratis que no conviene dejar pasar).
- **Meta de retiro**: dado el ingreso mensual que quieres (en dólares de hoy), calcula cuánto necesitas ahorrar cada mes en efectivo y cuánto invirtiendo.
- **Comisiones**: cuánto te cuesta pagar 1 % en vez de 0.1 % de comisión anual.
- **Mi cartera**: guarda tus posiciones, mira su valor y ganancia, y pulsa **Cover Call** en una fila para abrir la calculadora con esa acción cargada.

Todos los rendimientos son **supuestos que tú editas**, no promesas. Límites 2026 del IRS: empleado en 401(k) $24,500 e IRA $7,500 (cambian cada año).

> Un 401(k) normal ofrece un menú fijo de fondos. Las opciones (como el cover call) solo se pueden usar si tu plan tiene una ventana de corretaje y tu broker aprueba opciones. En una IRA es más común. Consulta con tu plan o tu broker.

## 7b. Mi ETF
Arriba tienes los **3 ETF de Optionsbb** (Poco riesgo, Riesgo moderado y Alto riesgo). Eliges uno y ves al lado su composición y la cantidad de acciones. Esos ETF **son fijos**: solo cambias el **monto a invertir** y las acciones se ajustan en la misma proporción; únicamente el administrador puede cambiar sus acciones. Para otra mezcla, pulsa **Crear mi ETF a partir de este**, o crea uno nuevo y usa **Agregar acciones desde otro ETF** (de los 3 de Optionsbb o de los tuyos).
Arma tu propio ETF: escribe el símbolo, elige si indicas **acciones** o **dólares** y pulsa *Agregar*. Puedes tener hasta 5 ETF con 20 acciones cada uno.
- **Composición**: gráfico circular con el logo y el **% de peso** de cada acción (por valor actual). Si el logo no carga, verás las siglas.
- **Tabla de rendimiento**: elige el periodo (30 a 360 días), a cuántos % fuera del dinero vendes el call y, si quieres, una volatilidad propia. Para cada acción verás: *sin cover call*, *cover call (ingreso)* y la **suma de las 2**, además de si estuvo **sin movimiento** o **en movimiento**. Abajo, subtotales y total del ETF.
- **Importante**: el cover call solo cubre lotes de **100 acciones** (si tienes 250, cubres 200). Las primas son estimadas con un modelo; úsalo para comparar, no como promesa.

## 7c. ¿Qué hubiera pasado si…?
Ejemplos como **BYND** (acción que cae mes tras mes) y **MSFT** (empresa sólida que se queda quieta o retrocede): cuánto habría generado el cover call y qué parte de la pérdida habría amortizado. Los ejemplos usan precios ilustrativos que **puedes cambiar** por los reales; también puedes usar el historial de cualquier símbolo.

## 7d. Apalancados + Cover Call (Avanzado)
NVDL, AMDL, TSLL, TQQQ y otros instrumentos apalancados con cover call. Incluye avisos de riesgo (reinicio diario y decadencia por volatilidad), un simulador y una calculadora de decadencia. Son instrumentos de **alto riesgo**: solo con dinero que puedas perder.

## 7e. Dividendos
Tabla de las acciones de tus listas con su rendimiento anual, el pago por acción, la frecuencia y el ingreso anual con 100 acciones. En los planes Intermedio y Avanzado puedes abrir el **historial de pagos** de una acción y su crecimiento anual. Con 100 acciones cobras el dividendo y además puedes vender un cover call cada mes: dos ingresos sobre las mismas acciones. Los datos de pagos requieren las claves de datos configuradas por el administrador; en modo DEMO son simulados.

## 7f. Idioma
Arriba a la derecha elige **ES**, **EN** o **PT**. Se traducen menús, títulos, tablas, mensajes y este manual. Limitaciones: la traducción la hizo Claude sin revisión de un hablante nativo; los nombres de sectores y de algunos símbolos quedan en inglés; los textos que escribes tú (nombres de ETF, estrategias, videos) no se traducen.

## 7g. Referidos
Menú **Referidos**: copia tu código o enlace. Cuando alguien que refieres **paga** su suscripción, ganas 20 % de descuento el mes siguiente. Con 10 referidos pagados, 6 meses gratis de Avanzado; con 20, un año gratis.

## 7h. Novedades 3.1
- **Dividendos**: calcula por número de acciones o monto a invertir.
- **Earnings**: últimos 12 reportes con tendencia.
- **¿Qué hubiera pasado si…?**: elige un caso de estudio de la lista o guarda el tuyo.
- **Estrategia personalizada**: cruce dorado, breakout alcista/bajista, doji y vela envolvente.
- **Sectores**: el administrador puede agregar o quitar empresas.

## 8. Herramientas
### Calculadora de opciones (Intermedio y Avanzado)
Elige una estrategia (call comprado, put comprado, cover call, put vendido con efectivo, put protector, spreads, straddle, iron condor), el símbolo o el precio, la volatilidad y los días al vencimiento. Verás el **costo o crédito**, la **ganancia y pérdida máximas**, los **puntos de equilibrio**, la **probabilidad de ganar** y las **griegas**, con un gráfico al vencimiento y la curva de «hoy». En Avanzado puedes armar hasta 6 **patas libres** y escribir tu propia prima. Las primas se estiman con Black-Scholes.
### Historial de Earnings (Avanzado)
Elige una acción y verás cómo se movió el precio en cada reporte anterior: gap de apertura, cambio del día, rango y día siguiente, más el movimiento medio. Todo se calcula **automáticamente** con las fechas de reporte (Finnhub) y los precios (Schwab); no se captura nada a mano.
### Gamma exposure – GEX (Avanzado)
Muestra por strike la exposición gamma de calls y puts para un vencimiento, la **pared de calls** (posible resistencia), la **pared de puts** (posible soporte), el **gamma flip** y si el régimen es de gamma positiva (movimientos más contenidos) o negativa (movimientos más amplios). Es una estimación con un supuesto sobre la posición de los dealers.

## 8b. Mercado
### Flujo OI (solo Avanzado)
Compara el volumen de opciones de un día con el open interest de la mañana siguiente. Si el OI sube mucho respecto al volumen, probablemente se **abrieron** posiciones nuevas; si baja, se **cerraron**. No distingue compra de venta.
### Sectores
Las acciones clave de cada sector con su precio, % de cambio, relación puts/calls y señales.
### Ranking
Muestra las estrategias **más efectivas por temporalidad** (5 min, 15 min, 30 min, 1 hora y diario). Cada señal se mide por el cambio del precio 5 velas después. Verás señales, % de aciertos, rendimiento promedio, factor de beneficio, **en qué acciones está activa ahora** y **en cuáles ha funcionado mejor**. Solo entran estrategias con 20 señales o más.
### Desempeño
Sube el reporte exportado de Thinkorswim (Strategy Report) y mira qué tan efectiva fue cada estrategia en el backtest.

## 9. Señales (Avanzado)
- **Catálogo de estrategias**: estrategias por reglas, con la lista de acciones que las cumplen ahora. Toca **Seguir** para guardarlas.
- **Mi selección**: reúne las estrategias que sigues (base, catálogo o propias) con sus señales. Marca o desmarca en “Elige qué seguir”.
- **Mis estrategias**: crea hasta 2 estrategias propias con el constructor de reglas: cruces de medias, rupturas, RSI, volumen, color de vela y cambio de precio. Se activan cuando se cumplen **todas** las condiciones en la misma vela de 5 minutos.

## 10. Videos
Biblioteca de videos del canal de YouTube de Options BB. Filtra por categoría o busca por título. Los videos de un nivel superior aparecen con candado.

## 11. Planes y cuenta
- **Planes**: compara y suscríbete. Puedes cambiar de plan cuando quieras.
- **Cuenta**: tu estado (prueba, activa, vencida), la fecha de renovación, administrar la suscripción y cerrar sesión.

## 12. Para el administrador
- **Iniciar la app**: abre una consola en la carpeta (en el Explorador, haz clic en la barra de direcciones, escribe `cmd` y Enter) y ejecuta `python server.py`. Abre `http://127.0.0.1:8080`. Crea tu usuario con `python server.py create-admin tu@correo.com`.
- **Usuarios** (Cuenta): activar días de pago, extender la prueba, revocar, cambiar el plan o hacer administrador.
- **Precios**: escríbelos en la pantalla Planes.
- **Videos**: agrega por enlace de YouTube, con categoría y plan mínimo.
- **Catálogo de señales**: agrega las reglas de tus mentores con su nombre.
- **Acciones por sector**: sube el Excel en Cuenta → Datos y listas.
- **Reporte de Desempeño**: sube el archivo exportado de Thinkorswim.
- **Datos reales**: enlaza Schwab en Cuenta → Conexión con Schwab (el permiso dura 7 días).
- **ETF de Optionsbb**: el administrador puede cambiar sus acciones y cantidades desde Mi ETF → *Editar (administrador)*.
- **Earnings y dividendos**: configura las variables `FINNHUB_API_KEY` y `ALPHAVANTAGE_API_KEY` (planes gratuitos) para fechas de reportes e historial de dividendos.
- **Tasas del banco y primas orientativas** de las pantallas de bienvenida: se editan con el servicio de administrador `/api/admin/guide`.

## 13. Glosario
| Término | Significado |
|---|---|
| Strike | Precio al que se puede ejercer la opción |
| Prima | Dinero que cobras al vender la opción |
| Ejercida (assigned) | Te compran las acciones al strike |
| Equilibrio | Precio bajo el cual empiezas a perder en un cover call |
| Bid / Ask | Precio al que compran / venden en el mercado |
| Delta | Aproximación de la probabilidad de que la opción termine en el dinero |
| Open interest (OI) | Contratos abiertos |
| RSI | Indicador de fuerza: sobre 70 sobrecomprada, bajo 30 sobrevendida |
| SMA | Media móvil simple |
| Factor de beneficio | Ganancias totales entre pérdidas totales |

## 14. Problemas frecuentes
- **“Windows can't find … cmd”**: no escribas `cmd` con un archivo seleccionado. Haz clic en un espacio vacío, pulsa Ctrl + L, escribe `cmd` y Enter.
- **Windows bloquea `iniciar.bat`**: abre una consola en la carpeta y ejecuta `python server.py`.
- **Datos simulados**: mientras Schwab no esté enlazado, la app muestra datos de demostración y lo avisa en la barra amarilla.
- **No veo un módulo**: tiene candado porque es de un plan superior.
- **Una acción no carga**: revisa el símbolo. Con datos reales, solo funcionan símbolos que existan en Schwab.
