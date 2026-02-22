from __future__ import annotations

from typing import Any

from fastapi_src.core.logging import get_logger
from fastapi_src.db.sqlite import get_connection


class RunLogRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._logger = get_logger(__name__)

    def append(
        self,
        *,
        user_id: str,
        thread_id: str,
        run_id: str | None,
        endpoint: str,
        event: str,
        status: str,
        error: str | None = None,
    ) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO run_logs(user_id, thread_id, run_id, endpoint, event, status, error)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, thread_id, run_id, endpoint, event, status, error),
            )
            conn.commit()
            self._logger.debug(
                "repo.run_log.append user_id=%s thread_id=%s endpoint=%s event=%s status=%s",
                user_id,
                thread_id,
                endpoint,
                event,
                status,
            )

    def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, thread_id, run_id, endpoint, event, status, error, created_at
                FROM run_logs
                WHERE user_id = ?
                ORDER BY id ASC
                """,
                (user_id,),
            ).fetchall()
            self._logger.debug("repo.run_log.list user_id=%s count=%s", user_id, len(rows))
            return [dict(row) for row in rows]
