# GameTech Store

Tienda web de juegos y hardware gaming hecha con Flask. Además de vender (cuentas, carrito, pago con MercadoPago y facturas), su parte
más importante es un **motor de hardware** que dice qué juegos corre tu equipo, qué piezas son compatibles entre sí, qué mejora comprar
y cuál es la mejor PC para tu presupuesto.

Proyecto académico de Ingeniería de Software II.

## Qué incluye

- **Catálogo**: 8 juegos y 28 componentes de hardware (7 tipos, 4 opciones cada uno: CPU, GPU, RAM, placa madre, fuente de poder,
  refrigeración y gabinete).
- **Cuentas**: registro con verificación por correo, inicio de sesión, lista de deseos y panel de administración (`/admin`).
- **Compra**: carrito, checkout con MercadoPago (Checkout Pro, que incluye PSE), confirmación del pago por webhook, correo de
  confirmación y factura electrónica en PDF con código QR. Las órdenes tienen estados finales (`rejected`, `cancelled`) y el stock se
  descuenta y se restituye una sola vez.
- **Analizador de hardware** (`/analizador-hardware`): elige CPU, GPU y RAM y obtén el nivel del equipo, el cuello de botella, la calidad
  y los FPS estimados en cada juego, y mejoras concretas del catálogo.
- **Configurador de PC** (`/configurador-pc`): arma tu PC pieza por pieza con verificación de compatibilidad en vivo, o pídele al asesor
  la mejor PC para un presupuesto y un uso.
- **API GraphQL** de solo lectura del catálogo (`/graphql`).
- Seguridad: CSRF, límite de peticiones, cabeceras de seguridad y Sentry opcional.

## Motor único de hardware

Toda pantalla que opina sobre hardware llama a los mismos módulos, que son puros (no usan Flask ni la base de datos) y por eso se
prueban de forma exhaustiva. Dos pantallas nunca pueden contradecirse.

| Módulo | Responsabilidad |
|---|---|
| `utils/hardware_engine.py` | Rendimiento: puntuación del sistema, calidad y FPS por juego, limitante (CPU, GPU, RAM o VRAM) y cuello de botella. |
| `utils/compatibilidad.py` | Encaje: socket, tipo de memoria (DDR4/DDR5), fuente de poder, enfriador y gabinete. Estados `ok`, `justa`, `incompatible` y `sin_datos`. |
| `utils/recomendador.py` | Qué pieza comprar: opciones del catálogo ordenadas por **mejor relación precio/rendimiento** (puntaje por dólar), con avisos de lo que obliga a cambiar. |
| `utils/asesor.py` | SmartBuildAdvisor: la mejor PC completa y compatible para un presupuesto y un uso. |
| `utils/benchmark_escala.py` | Escala única de puntajes, derivada de PassMark (CPU: Single Thread Rating x 2,56; GPU: G3D Mark x 0,615). |
| `utils/catalogo_hardware.py` | Los 28 componentes con sus datos de compatibilidad. |

Principios:

- **Un dato que falta no es un cero.** Un componente sin benchmark, una VRAM desconocida o una capacidad de RAM ilegible producen
  `sin_datos`, nunca "no corre", "balanceado" ni un valor inventado.
- **Los requisitos de los juegos salen de piezas de referencia** en la misma escala que el hardware. El mínimo y el recomendado son los
  publicados por el desarrollador (Steam); el nivel ultra es criterio del proyecto y está marcado así en el código
  (`scripts/populate_game_requirements.py`).
- **La pantalla no calcula nada.** El JavaScript (`static/js/hardware_analyzer.js`, `static/js/pc_builder.js`,
  `static/js/compatibilidad.js`) solo arma la petición y pinta la respuesta; sus pruebas se ejecutan con Node.

### Endpoints del motor

| Ruta | Qué hace |
|---|---|
| `/api/analizar-hardware` | Análisis de CPU + GPU + RAM: nivel, cuello de botella, juegos y mejoras (`upgrades`). |
| `/api/verificar-configuracion` | Compatibilidad de cualquier subconjunto de piezas, más el rendimiento del equipo. |
| `/api/armar-pc` | La mejor PC compatible para `{presupuesto, uso}` con uso `gaming`, `esports` o `aaa`. |

## Instalación

Requisitos: Python 3.14 (desarrollado y probado con 3.14.3) y, opcionalmente, Node.js para las pruebas de JavaScript.

```bash
git clone https://github.com/IntenseCord/GameTech-Store-IS2.git
cd GameTech-Store-IS2
python -m venv venv
venv\Scripts\activate          # en macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # en Windows: copy .env.example .env
```

Completa `.env` (el archivo nunca se sube al repositorio; no pegues credenciales en el código ni en el chat):

| Variable | Para qué sirve |
|---|---|
| `FLASK_ENV` | `development` o `production`. |
| `SECRET_KEY` | Clave de la app. En desarrollo, si falta, se genera una; en producción es obligatoria. |
| `DATABASE_URL` | Si se omite, se usa SQLite local (`instance/gametech_store.db`). Para PostgreSQL (Neon): `postgresql://usuario:clave@host/base?sslmode=require`. |
| `ADMIN_PASSWORD` | **Obligatoria**: contraseña del usuario `admin` que se crea al sembrar la base; si falta, la app no arranca. |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS` | Servidor SMTP (Gmail: `smtp.gmail.com`, `587`, `True`). |
| `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` | Cuenta de correo saliente (con Gmail, una contraseña de aplicación). |
| `MERCADOPAGO_ACCESS_TOKEN` | Token de MercadoPago. En desarrollo usa uno de pruebas; no uses el de producción para probar. |
| `MERCADOPAGO_WEBHOOK_SECRET` | Clave de webhooks (distinta del token); valida las notificaciones de `/webhooks/mercadopago`. |
| `SENTRY_DSN`, `APP_VERSION` | Monitoreo de errores (opcional). |

### Base de datos y catálogo

```bash
python app.py                              # crea las tablas, el usuario admin y siembra una base vacía
python scripts/sincronizar_catalogo.py     # catálogo completo: juegos, 28 componentes y requisitos
```

`python app.py` solo siembra una base **vacía**. `scripts/sincronizar_catalogo.py` es el camino para una base que ya tiene datos: agrega
lo que falte, completa los datos de compatibilidad de lo existente sin tocar precio ni stock, y carga los requisitos de los juegos.
Es idempotente: repetirlo no cambia nada. Para actualizar el esquema de una base existente usa `flask db upgrade`
(migraciones en `migrations/`).

Con la aplicación en marcha (`python app.py`) abre `http://localhost:5000`. Páginas principales: `/tienda`, `/hardware`,
`/configurador-pc`, `/analizador-hardware`, `/graphql` y `/admin`.

## Pruebas

```bash
pytest
```

- Cerca de 700 pruebas: unitarias (TDD), escenarios de comportamiento en español con `pytest-bdd` (`tests/features/` y
  `tests/step_defs/`), recorridos completos de un cliente y pruebas del JavaScript con Node (se omiten si Node no está instalado).
- `tests/conftest.py` fuerza SQLite en memoria antes de importar la app: **las pruebas nunca tocan la base real**.
- `pytest.ini` convierte en error las advertencias de APIs obsoletas, para que no se acumulen.
- `tests/test_readme.py` verifica que este README mencione todas las variables de `.env.example`, que lo que nombra exista y que las
  cifras de la demostración coincidan con lo que el motor calcula.

## Demostración guiada

Casos que muestran lo que el motor sabe. Las cifras se comprueban en las pruebas.

1. **Cuello de botella y mejora concreta.** En `/analizador-hardware` elige Ryzen 5 5600 + GTX 1650 + Vengeance LPX 16GB DDR4. La GPU
   es el cuello de botella; la mejor relación precio/rendimiento es la **RX 7600**: $349.99, +135% y 32.57 pts/$. La RTX 4070 no se
   propone porque dejaría a la CPU como cuello de botella.
2. **VRAM.** Con Core i5-12400F + RTX 4060 + 16 GB, Red Dead Redemption 2 y Baldur's Gate 3 no llegan a Ultra: piden 11 GB de VRAM y la
   GPU tiene 8 GB. El analizador lo dice ("Limitado por VRAM") y recomienda la RTX 4070.
3. **Fuente que no alcanza.** En `/configurador-pc` elige Core i7-13700K + RTX 4070 + CX550 550W: la configuración necesita al menos
   650 W.
4. **Por un milímetro.** El enfriador AK620 mide 160 mm y el gabinete MasterBox Q300L admite 159 mm: incompatible.
5. **Asesor.** Con $1000 para gaming arma una PC de $979.93: Core i5-12400F, MAG B660M Mortar WiFi DDR4, Vengeance LPX 16GB DDR4,
   RX 7600, RM750e 750W, AK400 y MasterBox Q300L, todo compatible. Dice que con $245.00 más ($1224.93 en total) subes de 29 a 32 puntos.
   Con $2000 para eSports arma una de $1779.93, pero avisa que la misma calidad en esos juegos se consigue desde $954.93. El presupuesto
   mínimo para una PC compatible es $704.93.

## Estructura del proyecto

```
app.py, config.py, database.py   aplicación Flask, configuración y siembra de la base
controllers/                     rutas: tienda, hardware, analizador, carrito, auth, admin, webhooks, factura, GraphQL
models/                          modelos SQLAlchemy (usuarios, juegos, hardware, órdenes, carrito)
utils/                           motor de hardware, pagos, correo, facturas y utilidades
scripts/                         carga de requisitos y benchmarks, y sincronizar_catalogo.py
templates/, static/              vistas HTML, CSS y JavaScript
migrations/                      migraciones de Alembic
tests/                           pruebas (unitarias, BDD, recorridos y JavaScript)
```

## Limitaciones conocidas

- **La CPU se mide por un solo hilo** (Single Thread Rating de PassMark): un procesador de 2 núcleos con buen hilo puede puntuar más que
  uno de 4 núcleos más lento.
- **Los precios del catálogo son de referencia del proyecto**, no precios de lista verificados; se ajustan desde el panel de administración.
- **Algunos datos son estimaciones**: el TDP de los enfriadores líquidos (DeepCool no lo publica) y el largo de la GTX 1650. Los
  puntajes de PassMark son de consultas de octubre de 2026 y varían unos puntos por día.
- **Nivel ultra y velocidad de la RAM**: son criterios del proyecto (están marcados como tales en el código).
- En la ficha de hardware, los botones "Lista de deseos" y "Comparar" solo muestran un aviso.
