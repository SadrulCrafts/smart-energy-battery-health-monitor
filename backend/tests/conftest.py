"""
conftest.py
-----------
Shared test set-up. Every API test gets its own empty in-memory database, so
tests never touch backend/data/monitor.db and never depend on each other.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers the readings table)
from app.database import Base, get_db
from app.main import app
from app.services.alerts import alert_tracker


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",                                # in memory, gone after the test
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,                       # one shared connection for all threads
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def test_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = test_db
    alert_tracker.reset()
    yield TestClient(app)          # no "with": the start-up code (real database) is not run
    app.dependency_overrides.clear()
    alert_tracker.reset()
    engine.dispose()


def reading(**changes):
    """A valid simulated reading; pass keyword arguments to change fields."""
    body = {
        "source": "simulated",
        "device_id": "test-device",
        "voltage_v": 3.85,
        "current_a": -0.40,
        "temperature_c": 26.0,
    }
    body.update(changes)
    return body
