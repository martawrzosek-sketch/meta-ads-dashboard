import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "actions.db"


def _conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def _init():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                key                TEXT PRIMARY KEY,
                market             TEXT,
                campaign_name      TEXT,
                action_type        TEXT,
                message            TEXT,
                recommended_action TEXT,
                status             TEXT DEFAULT 'todo',
                notes              TEXT DEFAULT '',
                created_at         TEXT,
                updated_at         TEXT
            )
        """)


_init()


def get_action(key: str):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM actions WHERE key = ?", (key,)).fetchone()
        return dict(row) if row else None


def upsert_action(key, market, campaign_name, action_type, message,
                  recommended_action, status="todo", notes=""):
    now = datetime.now().isoformat()
    with _conn() as conn:
        existing = conn.execute(
            "SELECT created_at FROM actions WHERE key = ?", (key,)
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        conn.execute("""
            INSERT OR REPLACE INTO actions
                (key, market, campaign_name, action_type, message,
                 recommended_action, status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (key, market, campaign_name, action_type, message,
              recommended_action, status, notes, created_at, now))


def update_status(key: str, status: str, notes: str = None):
    now = datetime.now().isoformat()
    with _conn() as conn:
        if notes is not None:
            conn.execute(
                "UPDATE actions SET status=?, notes=?, updated_at=? WHERE key=?",
                (status, notes, now, key)
            )
        else:
            conn.execute(
                "UPDATE actions SET status=?, updated_at=? WHERE key=?",
                (status, now, key)
            )


def get_all_actions():
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM actions ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def clear_done():
    with _conn() as conn:
        conn.execute("DELETE FROM actions WHERE status = 'done'")
