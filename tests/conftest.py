"""Fixtures for testing."""

import logging
import pytest
from homeassistant.components import recorder
from homeassistant.components.recorder import migration
from homeassistant.helpers import recorder as recorder_helper
from sqlalchemy.orm import Session

disable_loggers = ["sqlalchemy.engine.Engine"]


def pytest_configure():
    for logger_name in disable_loggers:
        logger = logging.getLogger(logger_name)
        logger.disabled = True


@pytest.fixture(autouse=True)
def recorder_annotation_compatibility(monkeypatch):
    """Resolve the type-only import inspected by recorder's autospec fixture."""
    monkeypatch.setattr(migration, "Recorder", recorder.Recorder, raising=False)
    monkeypatch.setattr(recorder_helper, "Session", Session, raising=False)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    recorder_annotation_compatibility, recorder_mock, enable_custom_integrations
):
    pass
