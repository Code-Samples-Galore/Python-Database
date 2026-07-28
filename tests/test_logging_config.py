import importlib
import os

import pytest
from loguru import logger

import logging_config


@pytest.fixture
def restore_logging():
    """Put the suite's own logging back after a test reconfigures it."""
    yield
    logging_config.reset_logging()
    logging_config.setup_logging()


def test_code_dir_points_at_the_code():
    assert logging_config.CODE_DIR == os.path.dirname(
        os.path.abspath(logging_config.__file__)
    )
    assert os.path.isfile(os.path.join(logging_config.CODE_DIR, "database.py"))


def test_default_log_dir_is_anchored_to_the_code_dir(monkeypatch):
    """With LOG_DIR unset the default must not depend on the working directory."""
    monkeypatch.delenv("LOG_DIR", raising=False)
    was_configured = logging_config._configured
    try:
        reloaded = importlib.reload(logging_config)
        assert reloaded.DEFAULT_LOG_DIR == os.path.join(reloaded.CODE_DIR, "logs")
        assert os.path.isabs(reloaded.DEFAULT_LOG_DIR)
    finally:
        monkeypatch.undo()
        importlib.reload(logging_config)
        logging_config._configured = was_configured


def test_records_are_routed_by_module():
    assert logging_config._is_database_record({"name": "database"})
    assert not logging_config._is_app_record({"name": "database"})
    for module in ("main", "__main__", "logging_config"):
        assert logging_config._is_app_record({"name": module})


def test_sinks_do_not_share_records(tmp_path, restore_logging):
    """Each file gets only its own module's records, not a copy of everything."""
    logging_config.reset_logging()
    logging_config.setup_logging(log_dir=str(tmp_path), level="INFO")

    logger.patch(lambda r: r.update(name="database")).info("db-only-message")
    logger.patch(lambda r: r.update(name="main")).info("app-only-message")

    # Closing the sinks flushes them.
    logging_config.reset_logging()

    app_log = (tmp_path / "app.log").read_text()
    db_log = (tmp_path / "database.log").read_text()

    assert "app-only-message" in app_log
    assert "db-only-message" not in app_log
    assert "db-only-message" in db_log
    assert "app-only-message" not in db_log


def test_setup_logging_is_idempotent(tmp_path, restore_logging):
    """A second call must not stack a duplicate handler."""
    logging_config.reset_logging()
    logging_config.setup_logging(log_dir=str(tmp_path), level="INFO")
    logging_config.setup_logging(log_dir=str(tmp_path), level="INFO")

    logger.patch(lambda r: r.update(name="main")).info("written-once")
    logging_config.reset_logging()

    app_log = (tmp_path / "app.log").read_text()
    assert app_log.count("written-once") == 1
