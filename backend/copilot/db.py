"""Read-only SQLite access and schema description for the prompt."""

import sqlite3
from pathlib import Path


def connect_readonly(path: str | Path) -> sqlite3.Connection:
    # mode=ro makes SQLite itself reject writes, as a second layer behind the SQL validator.
    conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def describe_schema(conn: sqlite3.Connection, sample_rows: int = 2) -> str:
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    parts = []
    for t in tables:
        cols = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
        col_text = ", ".join(f"{c['name']} {c['type']}" for c in cols)
        rows = conn.execute(f'SELECT * FROM "{t}" LIMIT {sample_rows}').fetchall()
        sample = "; ".join(str(tuple(r)) for r in rows)
        parts.append(f"TABLE {t} ({col_text})\n  sample: {sample}")
    return "\n".join(parts)


def run_query(conn: sqlite3.Connection, sql: str) -> tuple[list[str], list[list]]:
    cur = conn.execute(sql)
    columns = [d[0] for d in cur.description or []]
    return columns, [list(r) for r in cur.fetchall()]
