"""Fuentes de datos: Schwab (Thinkorswim) real y un proveedor DEMO con datos simulados.

Interfaz común:
    quotes(symbols)        -> {SYM: {price, prev_close, change, change_pct, volume}}
    history(symbol, rng)   -> [{t,o,h,l,c,v}]   rng: SCAN | BT (10 días de 5 min) | 1D | 5D | 1M | 3M | 1Y
    chain(symbol, as_of)   -> [{occ, underlying, cp, strike, expiry, volume, oi, last, bid, ask, dte}]
"""
import base64
import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from functools import lru_cache

from . import clock, config, db


class ProviderError(Exception):
    pass


class NotAuthorized(ProviderError):
    pass


def occ_symbol(sym: str, expiry: str, cp: str, strike: float) -> str:
    y, m, d = expiry.split("-")
    return f"{sym:<6}{y[2:]}{m}{d}{cp}{int(round(strike * 1000)):08d}"


# ======================================================================
#  SCHWAB
# ======================================================================
class SchwabProvider:
    name = "schwab"
    BASE = "https://api.schwabapi.com"

    # ---- OAuth ----
    def configured(self) -> bool:
        return bool(config.SCHWAB_KEY and config.SCHWAB_SECRET)

    def auth_url(self) -> str:
        if not self.configured():
            raise ProviderError("Falta SCHWAB_APP_KEY / SCHWAB_APP_SECRET")
        qs = urllib.parse.urlencode({"client_id": config.SCHWAB_KEY, "redirect_uri": config.SCHWAB_CALLBACK})
        return f"{self.BASE}/v1/oauth/authorize?{qs}"

    def _token_request(self, fields: dict) -> dict:
        basic = base64.b64encode(f"{config.SCHWAB_KEY}:{config.SCHWAB_SECRET}".encode()).decode()
        req = urllib.request.Request(
            self.BASE + "/v1/oauth/token", data=urllib.parse.urlencode(fields).encode(), method="POST",
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise NotAuthorized(f"Schwab rechazó la autorización ({e.code}). Repite el login de Schwab.")
        except Exception as e:
            raise ProviderError(f"No se pudo contactar a Schwab: {e}")

    def _save(self, tok: dict, old: dict | None = None):
        now = int(time.time())
        data = {
            "access_token": tok["access_token"],
            "refresh_token": tok.get("refresh_token") or (old or {}).get("refresh_token"),
            "access_expires": now + int(tok.get("expires_in", 1800)),
            # el refresh token de Schwab dura 7 días desde que se emite
            "refresh_obtained": now if tok.get("refresh_token") and tok.get("refresh_token") != (old or {}).get("refresh_token") else (old or {}).get("refresh_obtained", now),
        }
        db.kv_set("schwab_token", json.dumps(data))
        return data

    def exchange_code(self, code_or_url: str):
        s = (code_or_url or "").strip()
        if "code=" in s:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(s).query)
            s = (qs.get("code") or [""])[0]
        s = urllib.parse.unquote(s)
        if not s:
            raise ProviderError("No se encontró el parámetro code en la URL pegada")
        tok = self._token_request({"grant_type": "authorization_code", "code": s, "redirect_uri": config.SCHWAB_CALLBACK})
        self._save(tok)

    def _tok(self):
        raw = db.kv_get("schwab_token")
        return json.loads(raw) if raw else None

    def status(self) -> dict:
        t = self._tok()
        if not t:
            return {"connected": False, "configured": self.configured()}
        left = t["refresh_obtained"] + 7 * 86400 - time.time()
        return {"connected": left > 0, "configured": self.configured(), "refresh_days_left": round(left / 86400, 1)}

    def has_token(self) -> bool:
        return self._tok() is not None

    def _access(self):
        t = self._tok()
        if not t:
            raise NotAuthorized("Schwab no está conectado")
        if t["access_expires"] - 60 < time.time():
            if t["refresh_obtained"] + 7 * 86400 < time.time():
                raise NotAuthorized("El token de Schwab venció (dura 7 días). Vuelve a conectar la cuenta.")
            new = self._token_request({"grant_type": "refresh_token", "refresh_token": t["refresh_token"]})
            t = self._save(new, t)
        return t["access_token"]

    def _get(self, path: str, params: dict):
        url = f"{self.BASE}{path}?{urllib.parse.urlencode(params)}"
        for attempt in (1, 2):
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._access()}", "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=25) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code == 401 and attempt == 1:
                    t = self._tok()
                    t["access_expires"] = 0
                    db.kv_set("schwab_token", json.dumps(t))
                    continue
                if e.code == 429:
                    raise ProviderError("Schwab: límite de peticiones (429)")
                raise ProviderError(f"Schwab {path}: HTTP {e.code}")
            except NotAuthorized:
                raise
            except Exception as e:
                raise ProviderError(f"Schwab {path}: {e}")

    # ---- datos ----
    def quotes(self, symbols):
        out = {}
        symbols = list(symbols)
        for i in range(0, len(symbols), 50):
            chunk = symbols[i:i + 50]
            data = self._get("/marketdata/v1/quotes", {"symbols": ",".join(chunk), "fields": "quote"})
            for sym, v in data.items():
                q = v.get("quote") or {}
                last, close = q.get("lastPrice"), q.get("closePrice")
                if last is None:
                    continue
                pct = (last / close - 1) * 100 if close else q.get("netPercentChange", 0.0)
                out[sym] = {"price": last, "prev_close": close, "change": last - (close or last),
                            "change_pct": pct, "volume": q.get("totalVolume", 0)}
        return out

    def history(self, symbol, rng="SCAN"):
        spec = {
            "SCAN": dict(periodType="day", period=5, frequencyType="minute", frequency=5),
            "BT": dict(periodType="day", period=10, frequencyType="minute", frequency=5),
            "1D": dict(periodType="day", period=1, frequencyType="minute", frequency=5),
            "5D": dict(periodType="day", period=5, frequencyType="minute", frequency=30),
            "1M": dict(periodType="month", period=1, frequencyType="daily", frequency=1),
            "3M": dict(periodType="month", period=3, frequencyType="daily", frequency=1),
            "1Y": dict(periodType="year", period=1, frequencyType="daily", frequency=1),
            "5Y": dict(periodType="year", period=5, frequencyType="daily", frequency=1),
        }[rng]
        data = self._get("/marketdata/v1/pricehistory", {"symbol": symbol, "needExtendedHoursData": "false", **spec})
        return [{"t": int(c["datetime"] // 1000), "o": c["open"], "h": c["high"], "l": c["low"], "c": c["close"], "v": c.get("volume", 0)}
                for c in data.get("candles", [])]

    def fundamentals(self, symbol):
        data = self._get("/marketdata/v1/instruments", {"symbol": symbol, "projection": "fundamental"})
        for it in (data.get("instruments") or []):
            f = it.get("fundamental") or {}
            return {"div_amount": f.get("divAmount"), "div_yield": f.get("divYield"), "div_date": (f.get("divExDate") or f.get("divPayDate") or "")[:10] or None,
                    "div_freq": f.get("divFreq"), "pe": f.get("peRatio")}
        return {}

    def chain(self, symbol, as_of=None):
        today = clock.now_et().date()
        data = self._get("/marketdata/v1/chains", {
            "symbol": symbol, "contractType": "ALL", "strikeCount": 40, "includeUnderlyingQuote": "false",
            "fromDate": today.isoformat(), "toDate": (today + timedelta(days=45)).isoformat(),
        })
        out = []
        for key, cp in (("callExpDateMap", "C"), ("putExpDateMap", "P")):
            for exp_key, strikes in (data.get(key) or {}).items():
                expiry = exp_key.split(":")[0]
                for strike_s, contracts in strikes.items():
                    for c in contracts:
                        strike = float(c.get("strikePrice", strike_s))
                        out.append({
                            "occ": (c.get("symbol") or occ_symbol(symbol, expiry, cp, strike)).strip(),
                            "underlying": symbol, "cp": cp, "strike": strike, "expiry": expiry,
                            "volume": int(c.get("totalVolume") or 0), "oi": int(c.get("openInterest") or 0),
                            "last": c.get("last") or c.get("mark") or 0.0,
                            "bid": c.get("bid") or 0.0, "ask": c.get("ask") or 0.0,
                            "dte": c.get("daysToExpiration"),
                            "gamma": c.get("gamma") if isinstance(c.get("gamma"), (int, float)) and c.get("gamma") == c.get("gamma") else None,
                            "iv": (c["volatility"] / 100.0) if isinstance(c.get("volatility"), (int, float)) and c["volatility"] > 0 else None,
                        })
        return out


# ======================================================================
#  DEMO (datos simulados, deterministas)
# ======================================================================
def _h(*key) -> float:
    """Uniforme [0,1) determinista a partir de una llave."""
    d = hashlib.blake2b("|".join(map(str, key)).encode(), digest_size=8).digest()
    return int.from_bytes(d, "big") / 2 ** 64


def _g(*key) -> float:
    """Normal estándar determinista (Box-Muller)."""
    u1 = max(_h(*key, "a"), 1e-12)
    u2 = _h(*key, "b")
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


BASE_PRICES = {
    "SPY": 542, "QQQ": 468, "NVDA": 132, "AVGO": 168, "AMD": 152, "ANET": 108, "PLTR": 42, "GOOGL": 163, "META": 516,
    "NFLX": 689, "TTD": 98, "APP": 62, "AMZN": 178, "TSLA": 248, "MELI": 1650, "CAVA": 118, "DECK": 160, "COST": 880,
    "WMT": 68, "CELH": 52, "MNST": 52, "ELF": 130, "LLY": 780, "NVO": 125, "HIMS": 22, "VRTX": 465, "ISRG": 370,
    "JPM": 205, "BLK": 860, "COIN": 215, "HOOD": 24, "IBKR": 142, "GE": 160, "CARR": 66, "ETN": 310, "PH": 560,
    "HUBB": 400, "FANG": 175, "CEG": 240, "VST": 105, "LNG": 188, "OXY": 55, "FCX": 44, "NUE": 150, "STLD": 125,
    "MP": 18, "CRH": 80, "PLD": 125, "CCI": 110, "EQIX": 810, "WELL": 125, "VICI": 32, "NRG": 90, "SO": 85,
    "DUK": 108, "AAPL": 189, "MSFT": 417, "MU": 120,
}
BIG_LIQ = {"SPY": 120000, "QQQ": 80000, "NVDA": 60000, "TSLA": 55000, "AAPL": 50000, "AMD": 28000, "AMZN": 26000,
           "META": 22000, "PLTR": 30000, "COIN": 20000, "MU": 15000, "NFLX": 12000, "AVGO": 14000, "GOOGL": 16000}
EPOCH = date(2015, 1, 5)  # lunes


def _bord(d: date) -> int:
    """Ordinal de día hábil."""
    n = (d - EPOCH).days
    return n // 7 * 5 + min(n % 7, 4)


def _base_price(sym):
    return BASE_PRICES.get(sym) or round(20 + _h(sym, "bp") * 380, 2)


def _sigma(sym):
    return 0.012 + 0.02 * _h(sym, "sg")


def _liq(sym):
    return BIG_LIQ.get(sym) or int(5000 + 9000 * _h(sym, "lq"))


_walks = {}
ANCHOR = date(2026, 10, 7)


def _price(sym, n):
    """Cierre diario simulado del día hábil n."""
    w = _walks.get(sym)
    need = max(n, _bord(ANCHOR)) + 400
    if w is None or len(w) <= need:
        w = [1.0] if w is None else w
        mu, sg = 0.0004, _sigma(sym)
        for k in range(len(w), need + 1):
            w.append(w[-1] * math.exp(mu - 0.5 * sg * sg + sg * _g(sym, "w", k)))
        _walks[sym] = w
    factor = _base_price(sym) / w[_bord(ANCHOR)]
    return w[n] * factor


class DemoProvider:
    name = "demo"
    STRATS_N = 11  # 0..7 inyectan señales, 8..10 ninguna

    # ---------- diario ----------
    def _daily(self, sym, d):
        n = _bord(d)
        c = _price(sym, n)
        pc = _price(sym, n - 1)
        o = pc * (1 + 0.003 * _g(sym, "gap", n))
        h = max(o, c) * (1 + abs(_g(sym, "h", n)) * 0.006)
        l = min(o, c) * (1 - abs(_g(sym, "l", n)) * 0.006)
        return {"o": o, "h": h, "l": l, "c": c, "v": int(2e6 * (0.5 + _h(sym, "v", n)) * (_liq(sym) / 10000))}

    # ---------- intradía ----------
    def _day_bars(self, sym, d, nbars=clock.BARS_PER_DAY):
        day = self._daily(sym, d)
        o, c, sg = day["o"], day["c"], _sigma(sym)
        steps = [_g(sym, "i", d.isoformat(), k) * sg / math.sqrt(78) * 0.9 * o for k in range(78)]
        cum, s = [0.0], 0.0
        for z in steps:
            s += z
            cum.append(s)
        path = [o + (c - o) * k / 78 + (cum[k] - cum[78] * k / 78) for k in range(79)]
        bars = []
        for k in range(nbars):
            bo, bc = path[k], path[k + 1]
            hi = max(bo, bc) * (1 + abs(_g(sym, "bh", d.isoformat(), k)) * 0.0006)
            lo = min(bo, bc) * (1 - abs(_g(sym, "bl", d.isoformat(), k)) * 0.0006)
            vol = int(day["v"] / 78 * (0.4 + 1.6 * _h(sym, "bv", d.isoformat(), k)) * (1.8 if k < 6 or k > 70 else 1))
            bars.append({"t": clock.bar_epoch(d, k), "o": bo, "h": hi, "l": lo, "c": bc, "v": vol})
        return bars

    @staticmethod
    def _bar(t, o, c, s, v=1000):
        return {"t": t, "o": o, "h": max(o, c) + 0.3 * s, "l": min(o, c) - 0.3 * s, "c": c, "v": v}

    def _scenario(self, sym, d):
        return int(_h(sym, "scen", d.isoformat()) * self.STRATS_N)

    def _inject(self, bars, scen, first_idx_today):
        """Modifica el final de la serie para que dispare la estrategia `scen` (solo demo)."""
        n = len(bars)
        if scen > 7 or n < 40:
            return bars
        T = [b["t"] for b in bars]

        def rewrite(start, closes, s):
            p = bars[start - 1]["c"] if start > 0 else bars[start]["o"]
            prev = p
            for j, cl in enumerate(closes):
                bars[start + j] = self._bar(T[start + j], prev, cl, s, bars[start + j]["v"])
                prev = cl

        p = bars[-6]["c"]
        s = p * 0.0012
        if scen == 0:      # vela verde: R R R V V
            rewrite(n - 5, [p - 1.2 * s, p - 2.2 * s, p - 2.6 * s, p - 1.6 * s, p + 0.4 * s], s)
        elif scen == 1:    # martillo
            p = bars[-5]["c"]
            rewrite(n - 4, [p - s, p - 2 * s, p - 3 * s], s)
            o, c = p - 3 * s, p - 2.8 * s
            bars[-1] = {"t": T[-1], "o": o, "h": c + 0.05 * s, "l": o - 1.4 * s, "c": c, "v": bars[-1]["v"]}
        elif scen == 5:    # estrella fugaz
            p = bars[-5]["c"]
            rewrite(n - 4, [p + s, p + 2 * s, p + 3 * s], s)
            o, c = p + 3 * s, p + 2.8 * s
            bars[-1] = {"t": T[-1], "o": o, "h": o + 1.4 * s, "l": c - 0.05 * s, "c": c, "v": bars[-1]["v"]}
        elif scen in (2, 6):  # cruce de medias
            sign = 1 if scen == 2 else -1
            norm, m = [1.0], None
            for j in range(32):
                norm.append(norm[-1] * (1 - sign * 0.0012))
            for j in range(1, 30):
                norm.append(norm[-1] * (1 + sign * 0.0045))
                sm9 = sum(norm[-9:]) / 9
                sm21 = sum(norm[-21:]) / 21
                if (sm9 > sm21) if sign == 1 else (sm9 < sm21):
                    m = j
                    break
            if m is None or 32 + m + 1 >= n:
                return bars
            L = 32 + m
            p0 = bars[n - L - 1]["c"]
            rewrite(n - L, [p0 * x for x in norm[1:]], p0 * 0.0012)
        elif scen in (3, 7):  # ruptura de resistencia / soporte
            if scen == 3:
                M = max(b["h"] for b in bars[-21:-1])
                o, c = bars[-2]["c"], M * 1.002
                bars[-1] = {"t": T[-1], "o": o, "h": c * 1.0004, "l": min(o, c) * 0.9995, "c": c, "v": bars[-1]["v"] * 2}
            else:
                mn = min(b["l"] for b in bars[-21:-1])
                o, c = bars[-2]["c"], mn * 0.998
                bars[-1] = {"t": T[-1], "o": o, "h": max(o, c) * 1.0005, "l": c * 0.9996, "c": c, "v": bars[-1]["v"] * 2}
        elif scen == 4:    # vela roja de apertura
            f = first_idx_today
            if f is None or f < 1:
                return bars
            old_c = bars[f]["c"]
            o = bars[f - 1]["c"] * 1.0005
            c = o * 0.994
            bars[f] = {"t": T[f], "o": o, "h": o * 1.0008, "l": c * 0.9992, "c": c, "v": bars[f]["v"] * 2}
            ratio = c / old_c
            for k in range(f + 1, n):
                b = bars[k]
                bars[k] = {"t": b["t"], "o": b["o"] * ratio, "h": b["h"] * ratio, "l": b["l"] * ratio, "c": b["c"] * ratio, "v": b["v"]}
        return bars

    @lru_cache(maxsize=1024)
    def _bars5(self, sym, ndays, eff_date, nbars):
        days = [eff_date]
        for _ in range(ndays - 1):
            days.insert(0, clock.prev_bday(days[0]))
        bars, first_today = [], None
        for d in days:
            if d == eff_date:
                first_today = len(bars)
                bars += self._day_bars(sym, d, nbars)
            else:
                bars += self._day_bars(sym, d)
        return tuple(dict(b) for b in self._inject([dict(b) for b in bars], self._scenario(sym, eff_date), first_today))

    def _bars(self, sym, ndays=2):
        d, nb = clock.effective_session()
        return [dict(b) for b in self._bars5(sym, ndays, d, nb)]

    # ---------- interfaz ----------
    def quotes(self, symbols):
        out = {}
        d, _ = clock.effective_session()
        for sym in symbols:
            bars = self._bars(sym, 1)
            price = bars[-1]["c"]
            pc = self._daily(sym, clock.prev_bday(d))["c"]
            out[sym] = {"price": price, "prev_close": pc, "change": price - pc, "change_pct": (price / pc - 1) * 100,
                        "volume": sum(b["v"] for b in bars)}
        return out

    def history(self, symbol, rng="SCAN"):
        d, nb = clock.effective_session()
        if rng == "SCAN":
            return self._bars(symbol, 5)
        if rng == "BT":
            return self._bars(symbol, 10)
        if rng == "1D":
            return self._bars(symbol, 1)
        if rng == "5D":
            b5 = self._bars(symbol, 5)
            out = []
            for i in range(0, len(b5), 6):
                g = b5[i:i + 6]
                out.append({"t": g[0]["t"], "o": g[0]["o"], "h": max(x["h"] for x in g), "l": min(x["l"] for x in g),
                            "c": g[-1]["c"], "v": sum(x["v"] for x in g)})
            return out
        days = {"1M": 22, "3M": 66, "1Y": 252, "5Y": 1260}[rng]
        ds = [d]
        for _ in range(days - 1):
            ds.insert(0, clock.prev_bday(ds[0]))
        out = []
        for x in ds:
            r = self._daily(symbol, x)
            out.append({"t": int(datetime.combine(x, clock.CLOSE, tzinfo=clock.ET).timestamp()), **r})
        last = self._bars(symbol, 1)[-1]["c"]  # que el último cierre coincida con el precio actual
        out[-1]["c"] = last
        out[-1]["h"] = max(out[-1]["h"], last)
        out[-1]["l"] = min(out[-1]["l"], last)
        return out

    def fundamentals(self, symbol):
        known = {"KO", "PEP", "JNJ", "PG", "MCD", "VZ", "T", "XOM", "CVX", "DUK", "SO", "WMT", "HD", "JPM", "O", "MSFT", "AAPL", "AVGO", "COST", "V", "MA", "SCHD", "SPY", "QQQ"}
        none = {"TSLA", "AMZN", "GOOGL", "NVDA", "AMD", "COIN", "PLTR", "HOOD", "AFRM", "SOFI", "MSTR", "RIVN", "UNH_", "LLY_", "BYND", "F_"}
        pays = symbol in known or (symbol not in none and _h(symbol, "pays") > 0.5)
        y = round(0.5 + 3.5 * _h(symbol, "dy"), 2) if pays else 0.0
        px = _base_price(symbol)
        return {"div_amount": round(px * y / 100 / 4, 3), "div_yield": y, "div_date": None, "div_freq": 4 if y else None, "pe": round(10 + 25 * _h(symbol, "pe"), 1)}

    # ---------- opciones ----------
    def _expiries(self, d):
        out, x = [], d
        while len(out) < 4:
            if x.weekday() == 4 and x >= d:
                out.append(x)
            x += timedelta(days=1)
        return out

    def _weights(self, sym, strike, spot, exp, d):
        m = strike / spot - 1
        w = math.exp(-0.5 * (m / 0.05) ** 2)
        dte = (exp - d).days
        ew = 1.0 if dte <= 3 else 0.7 if dte <= 10 else 0.45 if dte <= 17 else 0.3
        return w, ew

    def _vol_full(self, sym, exp, cp, strike, d, spot):
        w, ew = self._weights(sym, strike, spot, exp, d)
        k = (sym, exp.isoformat(), cp, strike, d.isoformat())
        v = _liq(sym) * w * ew * 0.6 * math.exp(0.7 * _g(*k, "v"))
        if _h(*k, "spike") < 0.03:
            v *= 4
        if cp == "P":
            v *= 0.8 + 0.2 * _h(sym, "pbias") * 2
        return int(v)

    OI_START = date(2026, 9, 24)  # el OI simulado acumula conv*volumen desde esta fecha

    def _oi_morning(self, sym, exp, cp, strike, d, spot):
        """OI de la mañana de d = base estable + suma de (conversión * volumen) de cada día anterior.
        Así  OI(d+1) - OI(d) = conversión(d) * volumen(d)  exactamente (en datos reales lo calcula la OCC)."""
        ref = _price(sym, _bord(ANCHOR))
        w, ew = self._weights(sym, strike, ref, exp, exp - timedelta(days=7))
        base = _liq(sym) * w * 0.7 * (3 + 2 * _h(sym, exp.isoformat(), cp, strike, "oi"))
        delta, day = 0.0, self.OI_START
        while day < d:
            conv = -0.7 + 1.6 * _h(sym, exp.isoformat(), cp, strike, day.isoformat(), "conv")
            delta += conv * self._vol_full(sym, exp, cp, strike, day, _price(sym, _bord(day)))
            day = clock.next_bday(day)
        return max(0, int(base + delta))

    def chain(self, symbol, as_of=None):
        if as_of is None:
            d, nb = clock.effective_session()
            frac = nb / clock.BARS_PER_DAY
            spot = self._bars(symbol, 1)[-1]["c"]
        else:
            d, frac, spot = as_of, 1.0, _price(symbol, _bord(as_of))
        step = 0.5 if spot < 20 else 1 if spot < 50 else 2.5 if spot < 150 else 5 if spot < 400 else 10
        atm = round(spot / step) * step
        out = []
        for exp in self._expiries(d):
            for i in range(-10, 11):
                strike = round(atm + i * step, 2)
                if strike <= 0:
                    continue
                for cp in ("C", "P"):
                    vol = int(self._vol_full(symbol, exp, cp, strike, d, spot) * frac)
                    oi = self._oi_morning(symbol, exp, cp, strike, d, spot)
                    dte = (exp - d).days
                    intrinsic = max(spot - strike, 0) if cp == "C" else max(strike - spot, 0)
                    tv = spot * 0.35 * _sigma(symbol) * math.sqrt(max(dte, 0.5)) * math.exp(-0.5 * ((strike / spot - 1) / 0.06) ** 2)
                    last = round(intrinsic + tv, 2)
                    out.append({"occ": occ_symbol(symbol, exp.isoformat(), cp, strike), "underlying": symbol, "cp": cp,
                                "strike": strike, "expiry": exp.isoformat(), "volume": vol, "oi": oi, "last": last,
                                "bid": round(last * 0.98, 2), "ask": round(last * 1.02, 2), "dte": dte,
                                "gamma": None, "iv": round(_sigma(symbol) * math.sqrt(252) * (1 + 1.5 * abs(strike / spot - 1)), 4)})
        return out


# ======================================================================
def get_provider():
    sch = SchwabProvider()
    mode = config.DEMO
    if mode == "1":
        return DemoProvider()
    if mode == "0" or (mode == "auto" and sch.has_token()):
        return sch
    return DemoProvider()
