import sqlite3

from app import config

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    filename         TEXT    NOT NULL,
    size             INTEGER NOT NULL,
    content_type     TEXT    NOT NULL,
    upload_timestamp TEXT    NOT NULL,
    storage_path     TEXT    NOT NULL
);
"""


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
    finally:
        conn.close()


def query_documents(page: int, page_size: int) -> tuple[list[dict], int]:
    """Return (documents, total) for the given page. Shared by API and pages."""
    offset = (page - 1) * page_size
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY id DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows], total
