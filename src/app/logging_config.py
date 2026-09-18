"""Privacy-conscious JSON Lines logging with bounded disk usage."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "symbiote"
MAX_LOG_BYTES = 1_048_576
BACKUP_COUNT = 3


class JsonFormatter(logging.Formatter):
    """Exclude exception messages, tracebacks, locals, and arbitrary extras."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, str] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "event": record.getMessage(),
        }

        if record.exc_info and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__

        return json.dumps(payload, ensure_ascii=False)


def close_logging(logger: logging.Logger) -> None:
    """Flush and detach handlers owned by this application's logger."""
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def configure_logging(log_directory: Path) -> logging.Logger:
    """Configure the application logger; log only fixed event names."""
    log_directory.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    close_logging(logger)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = RotatingFileHandler(
        log_directory / "application.jsonl",
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
        delay=False,
    )
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger
