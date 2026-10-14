"""Reloj de mercado (hora del Este, lunes-viernes). No conoce feriados."""
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OPEN = dtime(9, 30)
CLOSE = dtime(16, 0)
BARS_PER_DAY = 78  # velas de 5 min


def now_et() -> datetime:
    return datetime.now(ET)


def is_bday(d: date) -> bool:
    return d.weekday() < 5


def prev_bday(d: date) -> date:
    d = d - timedelta(days=1)
    while not is_bday(d):
        d -= timedelta(days=1)
    return d


def next_bday(d: date) -> date:
    d = d + timedelta(days=1)
    while not is_bday(d):
        d += timedelta(days=1)
    return d


def last_bday(d: date) -> date:
    while not is_bday(d):
        d -= timedelta(days=1)
    return d


def bdays_back(d: date, n: int):
    out = []
    for _ in range(n):
        d = prev_bday(d)
        out.append(d)
    return out


def market_state(now: datetime | None = None) -> str:
    now = now or now_et()
    if not is_bday(now.date()):
        return "closed"
    t = now.time()
    if t < OPEN:
        return "pre"
    if t < CLOSE:
        return "open"
    return "closed"


def effective_session(now: datetime | None = None):
    """(fecha de la sesión que se muestra, número de velas de 5 min disponibles)."""
    now = now or now_et()
    d = now.date()
    st = market_state(now)
    if st == "open":
        mins = (now.hour * 60 + now.minute) - (9 * 60 + 30)
        return d, min(BARS_PER_DAY, mins // 5 + 1)
    if st == "pre":
        return prev_bday(d), BARS_PER_DAY
    return last_bday(d), BARS_PER_DAY


def bar_epoch(d: date, k: int) -> int:
    """Epoch (s) de la vela k (0..77) del día d."""
    return int((datetime.combine(d, OPEN, tzinfo=ET) + timedelta(minutes=5 * k)).timestamp())
