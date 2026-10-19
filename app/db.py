"""
One shared database connection pool for the whole application.

Every route that touches the database goes through here.

Usage:

    from app.db import query_all, query_one, execute

    rows = query_all("SELECT id, title FROM courses ORDER BY course_number")
    user = query_one("SELECT * FROM users WHERE email = %s", (email,))
    execute("UPDATE users SET verified = TRUE WHERE id = %s", (user_id,))
"""

import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def init_pool() -> None:
    """Open the pool once, when the app starts."""
    global _pool
    if _pool is not None:
        return

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
        )

    _pool = ConnectionPool(
        url,
        min_size=1,
        max_size=5,          # Neon's free tier is not generous — keep this low
        kwargs={"row_factory": dict_row},
        open=True,
    )


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _get_pool() -> ConnectionPool:
    if _pool is None:
        init_pool()
    assert _pool is not None
    return _pool


# ---------------------------------------------------------------------
#  The three helpers you will actually use.
#
#  ALWAYS pass values as the second argument, never by building the SQL
#  string yourself:
#
#      GOOD:  query_one("SELECT * FROM users WHERE email = %s", (email,))
#      BAD:   query_one(f"SELECT * FROM users WHERE email = '{email}'")
#
#  The bad version is a SQL injection hole.
# ---------------------------------------------------------------------


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT and return every row as a dict."""
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Run a SELECT and return the first row, or None."""
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql: str, params: tuple = ()) -> dict | None:
    """
    Run an INSERT, UPDATE or DELETE.

    If the statement ends with RETURNING, the returned row comes back.
    The transaction commits when the `with` block exits cleanly, and
    rolls back if an exception is raised — so a failed insert leaves
    nothing behind.
    """
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description is not None:
                return cur.fetchone()
            return None
