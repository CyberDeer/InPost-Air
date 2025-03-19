"""Fixtures for testing."""

import logging
import pytest

disable_loggers = ["sqlalchemy.engine.Engine"]


def pytest_configure():
    for logger_name in disable_loggers:
        logger = logging.getLogger(logger_name)
        logger.disabled = True


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    pass
