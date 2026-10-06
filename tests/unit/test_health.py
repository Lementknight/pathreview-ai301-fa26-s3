"""Regression test for the /health Postgres probe (issue #61)."""

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routes.health import health_check


class _AwaitableSession:
    """Wrap a sync Session so the route can await ``execute``.

    SQLAlchemy's own statement coercion still runs, against in-memory SQLite,
    so no Postgres or async driver is needed.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    async def execute(self, statement):
        return self._session.execute(statement)


def _run_health_check() -> dict:
    engine = create_engine("sqlite://")
    try:
        with Session(engine) as session:
            try:
                return asyncio.run(health_check(db=_AwaitableSession(session)))
            except HTTPException as exc:
                return exc.detail
    finally:
        engine.dispose()


@pytest.mark.unit
def test_postgres_probe_reports_healthy_when_database_answers() -> None:
    """A bare "SELECT 1" string is rejected by SQLAlchemy 2.x before it reaches the database."""
    body = _run_health_check()
    assert body["dependencies"]["postgres"] == "healthy"
