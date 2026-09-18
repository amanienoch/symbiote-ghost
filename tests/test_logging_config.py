"""Structured logging and sensitive-exception suppression tests."""

from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path

from src.app.logging_config import (
    JsonFormatter,
    close_logging,
    configure_logging,
)


class LoggingTests(unittest.TestCase):
    def test_formatter_omits_exception_message_and_extras(self) -> None:
        error = RuntimeError("sensitive screen text")
        record = logging.LogRecord(
            name="symbiote",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="operation_failed",
            args=(),
            exc_info=(RuntimeError, error, None),
        )
        record.screen_text = "another sensitive value"

        encoded = JsonFormatter().format(record)
        payload = json.loads(encoded)

        self.assertEqual(payload["event"], "operation_failed")
        self.assertEqual(payload["exception_type"], "RuntimeError")
        self.assertNotIn("sensitive", encoded)
        self.assertNotIn("screen_text", payload)

    def test_logger_writes_valid_json_and_closes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_directory = Path(directory)
            logger = configure_logging(log_directory)
            try:
                logger.info("test_event")
            finally:
                close_logging(logger)

            lines = (log_directory / "application.jsonl").read_text(
                encoding="utf-8",
            ).splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["event"], "test_event")
            self.assertEqual(logger.handlers, [])


if __name__ == "__main__":
    unittest.main()
