"""SQLite: ulanyjylar we stiller."""
from __future__ import annotations

import json
import sqlite3
import time

from .config import DB_PATH
from .default_styles import DEFAULT_STYLES


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, "
            "username TEXT, joined INTEGER, made INTEGER DEFAULT 0)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS styles (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT, data TEXT, active INTEGER DEFAULT 1, created INTEGER)"
        )
        c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        cols = {r[1] for r in c.execute("PRAGMA table_info(users)")}
        if "status" not in cols:  # köne bazany täzelemek
            c.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending'")
        if "notified" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN notified INTEGER DEFAULT 0")
        if c.execute("SELECT COUNT(*) FROM styles").fetchone()[0] == 0:
            for s in DEFAULT_STYLES:
                c.execute(
                    "INSERT INTO styles (name, data, created) VALUES (?, ?, ?)",
                    (s["name"], json.dumps(s, ensure_ascii=False), int(time.time())),
                )


# ---------- users ----------
def add_user(uid: int, name: str, username: str | None):
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO users (id, name, username, joined) VALUES (?, ?, ?, ?)",
            (uid, name, username, int(time.time())),
        )


# ---------- sazlamalar ----------
def get_setting(key: str) -> str | None:
    with _conn() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r[0] if r else None


def set_setting(key: str, value: str):
    with _conn() as c:
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


# ---------- rugsat (access) ----------
# status: pending (garaşýar) | approved (rugsat berildi) | blocked (ret edildi)
def get_user(uid: int):
    with _conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def get_status(uid: int) -> str | None:
    u = get_user(uid)
    return u["status"] if u else None


def set_status(uid: int, status: str):
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO users (id, name, username, joined) VALUES (?, '', NULL, ?)",
                  (uid, int(time.time())))
        c.execute("UPDATE users SET status=? WHERE id=?", (status, uid))


def mark_notified(uid: int) -> bool:
    """Admine haýyş ilkinji gezek iberilýän bolsa True."""
    with _conn() as c:
        cur = c.execute("UPDATE users SET notified=1 WHERE id=? AND notified=0", (uid,))
        return cur.rowcount > 0


def list_users(status: str, limit: int = 40):
    with _conn() as c:
        return c.execute("SELECT * FROM users WHERE status=? ORDER BY joined DESC LIMIT ?",
                         (status, limit)).fetchall()


def count_status(status: str) -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM users WHERE status=?", (status,)).fetchone()[0]


def inc_made(uid: int):
    with _conn() as c:
        c.execute("UPDATE users SET made = made + 1 WHERE id = ?", (uid,))


def stats():
    with _conn() as c:
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        made = c.execute("SELECT COALESCE(SUM(made),0) FROM users").fetchone()[0]
        styles = c.execute("SELECT COUNT(*) FROM styles WHERE active=1").fetchone()[0]
    return users, made, styles


def all_user_ids():
    with _conn() as c:
        return [r[0] for r in c.execute("SELECT id FROM users")]


# ---------- styles ----------
def list_styles():
    with _conn() as c:
        rows = c.execute("SELECT id, data FROM styles WHERE active=1 ORDER BY id").fetchall()
    out = []
    for r in rows:
        d = json.loads(r["data"])
        d["id"] = r["id"]
        out.append(d)
    return out


def get_style(sid: int):
    with _conn() as c:
        r = c.execute("SELECT id, data FROM styles WHERE id=? AND active=1", (sid,)).fetchone()
    if not r:
        return None
    d = json.loads(r["data"])
    d["id"] = r["id"]
    return d


def add_style(style: dict) -> int:
    style = {k: v for k, v in style.items() if k != "id"}
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO styles (name, data, created) VALUES (?, ?, ?)",
            (style["name"], json.dumps(style, ensure_ascii=False), int(time.time())),
        )
        return cur.lastrowid


def delete_style(sid: int):
    with _conn() as c:
        c.execute("UPDATE styles SET active=0 WHERE id=?", (sid,))
