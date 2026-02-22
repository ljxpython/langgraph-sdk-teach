from __future__ import annotations

from fastapi_src.core.logging import get_logger
from fastapi_src.db.sqlite import get_connection


class ThreadRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._logger = get_logger(__name__)

    def get_thread_id(self, user_id: str) -> str | None:
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT thread_id FROM user_threads WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                self._logger.debug("repo.thread.get miss user_id=%s", user_id)
                return None
            value = row["thread_id"]
            self._logger.debug("repo.thread.get hit user_id=%s", user_id)
            return str(value) if value else None

    def upsert_thread_id(self, user_id: str, thread_id: str) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_threads(user_id, thread_id, updated_at)
                VALUES(?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, thread_id),
            )
            conn.commit()
            self._logger.info("repo.thread.upsert user_id=%s thread_id=%s", user_id, thread_id)
