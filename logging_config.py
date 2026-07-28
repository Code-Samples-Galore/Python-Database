"""Centralised Loguru configuration.

Loguru's ``logger`` is a process-wide singleton, so every sink added to it
receives every record. Adding an "app" sink and a "database" sink without an
explicit ``filter`` therefore writes an identical copy of every message to
both files. Each sink below is scoped to the modules it is meant to cover.

``setup_logging`` is idempotent: ``database`` and ``main`` both call it, and
importing them in the same process must not stack duplicate handlers.
"""

import os
import sys

from loguru import logger

DEFAULT_LOG_DIR = os.environ.get("LOG_DIR", "logs")
DEFAULT_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Records emitted from these modules go to database.log; everything else
# goes to app.log.
_DATABASE_MODULES = frozenset({"database"})

_configured = False


def _is_database_record(record):
    return record["name"] in _DATABASE_MODULES


def _is_app_record(record):
    return not _is_database_record(record)


def setup_logging(log_dir=None, level=None):
    """Configure the console and file sinks, at most once per process."""
    global _configured
    if _configured:
        return

    log_dir = DEFAULT_LOG_DIR if log_dir is None else log_dir
    level = DEFAULT_LOG_LEVEL if level is None else level.upper()

    os.makedirs(log_dir, exist_ok=True)

    # Drop Loguru's default DEBUG-to-stderr handler; it interleaved debug
    # noise with the Rich tables the CLI prints.
    logger.remove()
    logger.add(sys.stderr, level=level)
    logger.add(
        os.path.join(log_dir, "app.log"),
        rotation="1 MB",
        retention="10 days",
        level=level,
        filter=_is_app_record,
    )
    logger.add(
        os.path.join(log_dir, "database.log"),
        rotation="1 MB",
        retention="10 days",
        level=level,
        filter=_is_database_record,
    )

    _configured = True


def reset_logging():
    """Undo :func:`setup_logging`. Intended for tests."""
    global _configured
    logger.remove()
    _configured = False
