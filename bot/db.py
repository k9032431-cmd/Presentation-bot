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
