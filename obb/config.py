"""Configuración (todo por variables de entorno; ver README)."""
import os
import secrets
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def env(key, default=""):
    return os.environ.get(key, default)


DATA_DIR = Path(env("OBB_DATA", str(BASE / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "optionsbb.db"
STATIC_DIR = BASE / "static"


def _load_secret():
    if env("OBB_SECRET"):
        return env("OBB_SECRET").encode()
    p = DATA_DIR / "secret.key"
    if p.exists():
        return p.read_bytes()
    k = secrets.token_bytes(32)
    p.write_bytes(k)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return k


SECRET = _load_secret()

HOST = env("OBB_HOST", "127.0.0.1")
PORT = int(env("OBB_PORT", "8080"))
PUBLIC_URL = env("OBB_PUBLIC_URL", f"http://localhost:{PORT}").rstrip("/")

# Suscripción
TRIAL_DAYS = int(env("OBB_TRIAL_DAYS", "7"))
ADMIN_EMAIL = env("OBB_ADMIN_EMAIL", "").strip().lower()
COOKIE_SECURE = env("OBB_COOKIE_SECURE", "0") == "1"
PAST_DUE_GRACE_DAYS = 3

# Schwab (Thinkorswim) – developer.schwab.com
SCHWAB_KEY = env("SCHWAB_APP_KEY")
SCHWAB_SECRET = env("SCHWAB_APP_SECRET")
SCHWAB_CALLBACK = env("SCHWAB_CALLBACK", "https://127.0.0.1:8182")

# "auto": usa Schwab si ya hay token guardado, si no modo demo.  "1": demo forzado.  "0": solo Schwab.
DEMO = env("OBB_DEMO", "auto")

# Stripe (opcional)
STRIPE_SECRET = env("STRIPE_SECRET_KEY")
STRIPE_PRICE = env("STRIPE_PRICE_ID")  # precio único (compatibilidad): se asigna al plan indicado en OBB_STRIPE_DEFAULT_PLAN
STRIPE_PRICES = {  # un Price de Stripe por plan
    "basico": env("STRIPE_PRICE_BASICO"), "intermedio": env("STRIPE_PRICE_INTERMEDIO"), "avanzado": env("STRIPE_PRICE_AVANZADO"),
}
if STRIPE_PRICE and not any(STRIPE_PRICES.values()):
    STRIPE_PRICES[env("OBB_STRIPE_DEFAULT_PLAN", "avanzado")] = STRIPE_PRICE
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET")

TZ_NAME = "America/New_York"

# Biblioteca de videos / sitio web
YT_CHANNEL_URL = env("OBB_YT_CHANNEL_URL", "https://www.youtube.com/@optionsbb")
YT_CHANNEL_ID = env("OBB_YT_CHANNEL_ID")  # opcional: UC... para sincronizar los últimos videos por RSS
WEBSITE_URL = env("OBB_WEBSITE_URL", "https://www.optionsbb.com")

# Logos de las compañías (gráfico circular del ETF). {SYM} se reemplaza por el símbolo. Vacío = sin logos (se muestran las siglas).
LOGO_URL = env("LOGO_URL", "")

# Datos externos opcionales (earnings / dividendos). Sin clave, esos módulos usan datos simulados en demo o avisan.
FINNHUB_KEY = env("FINNHUB_API_KEY")
ALPHAVANTAGE_KEY = env("ALPHAVANTAGE_API_KEY")
