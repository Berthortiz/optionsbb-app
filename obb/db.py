"""SQLite mínimo (una conexión compartida con lock)."""
import sqlite3
import threading

from . import config

_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  name TEXT DEFAULT '',
  pw_hash TEXT NOT NULL,
  role TEXT DEFAULT 'user',
  created_at INTEGER NOT NULL,
  trial_ends INTEGER,
  sub_status TEXT DEFAULT 'none',   -- none | active | past_due | canceled
  sub_ends INTEGER,
  stripe_customer TEXT
);
CREATE TABLE IF NOT EXISTS watchlist(
  sector TEXT NOT NULL, symbol TEXT NOT NULL, PRIMARY KEY(sector, symbol)
);
CREATE TABLE IF NOT EXISTS contract_snaps(
  snap_date TEXT NOT NULL,           -- fecha ET de la foto
  kind TEXT NOT NULL,                -- CLOSE (volumen del día D) | MORNING (OI de la mañana D+1)
  occ TEXT NOT NULL,
  underlying TEXT NOT NULL,
  cp TEXT NOT NULL,                  -- C | P
  strike REAL NOT NULL,
  expiry TEXT NOT NULL,
  volume INTEGER DEFAULT 0,
  oi INTEGER DEFAULT 0,
  last REAL,
  PRIMARY KEY(snap_date, kind, occ)
);
CREATE INDEX IF NOT EXISTS ix_snap_kind ON contract_snaps(kind, snap_date);
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT, symbol TEXT, period_start TEXT, period_end TEXT,
  source TEXT, uploaded_at INTEGER, is_demo INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS trades(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_id INTEGER NOT NULL, strategy TEXT NOT NULL,
  entry_ts TEXT, exit_ts TEXT, pnl REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_trades_report ON trades(report_id);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS cc_sims(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL,
  created_at INTEGER NOT NULL, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cc_user ON cc_sims(user_id);
CREATE TABLE IF NOT EXISTS videos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, yt_id TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
  description TEXT DEFAULT '', category TEXT DEFAULT 'General', min_plan TEXT DEFAULT 'basico',
  published TEXT, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS custom_strategies(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL,
  side TEXT NOT NULL, rule TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_custom_user ON custom_strategies(user_id);
CREATE TABLE IF NOT EXISTS user_prefs(
  user_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(user_id, key)
);
CREATE TABLE IF NOT EXISTS user_watch(
  user_id INTEGER NOT NULL, symbol TEXT NOT NULL, added_at INTEGER NOT NULL, PRIMARY KEY(user_id, symbol)
);
CREATE TABLE IF NOT EXISTS user_etfs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, positions TEXT NOT NULL DEFAULT '[]', created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS user_picks(
  user_id INTEGER NOT NULL, kind TEXT NOT NULL, ref TEXT NOT NULL, added_at INTEGER NOT NULL, PRIMARY KEY(user_id, kind, ref)
);
CREATE TABLE IF NOT EXISTS holdings(
  user_id INTEGER NOT NULL, symbol TEXT NOT NULL, shares REAL NOT NULL, cost REAL NOT NULL, PRIMARY KEY(user_id, symbol)
);
CREATE TABLE IF NOT EXISTS referrals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER NOT NULL, referred_id INTEGER NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'registered', created_at INTEGER NOT NULL, qualified_at INTEGER
);
CREATE INDEX IF NOT EXISTS ix_ref_referrer ON referrals(referrer_id);
CREATE TABLE IF NOT EXISTS referral_rewards(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, kind TEXT NOT NULL, pct INTEGER DEFAULT 0, months INTEGER DEFAULT 0,
  milestone INTEGER DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending', created_at INTEGER NOT NULL, applied_at INTEGER,
  note TEXT DEFAULT '', manual INTEGER DEFAULT 0, done INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_rw_user ON referral_rewards(user_id);
CREATE TABLE IF NOT EXISTS catalog_strategies(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, source TEXT DEFAULT '', language TEXT DEFAULT 'ES',
  side TEXT NOT NULL, description TEXT DEFAULT '', rule TEXT NOT NULL, created_at INTEGER NOT NULL
);
"""


def _migrate(c):
    cols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    if "plan" not in cols:  # usuarios existentes conservan acceso completo
        c.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'avanzado'")
    for col, ddl in (("ref_code", "TEXT"), ("referred_by", "INTEGER"), ("reward_until", "INTEGER")):
        if col not in cols:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_users_refcode ON users(ref_code)")


def conn():
    global _conn
    with _lock:
        if _conn is None:
            c = sqlite3.connect(str(config.DB_PATH), check_same_thread=False, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA foreign_keys=ON")
            c.executescript(SCHEMA)
            _migrate(c)
            _conn = c
        return _conn


def q(sql, args=()):
    with _lock:
        return conn().execute(sql, args).fetchall()


def q1(sql, args=()):
    rows = q(sql, args)
    return rows[0] if rows else None


def x(sql, args=()):
    with _lock:
        return conn().execute(sql, args).lastrowid


def many(sql, rows):
    rows = list(rows)
    if not rows:
        return
    with _lock:
        c = conn()
        c.execute("BEGIN")
        try:
            c.executemany(sql, rows)
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise


def kv_get(key, default=None):
    r = q1("SELECT value FROM kv WHERE key=?", (key,))
    return r["value"] if r else default


def kv_set(key, value):
    x("INSERT INTO kv(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
