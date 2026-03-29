"""Logging configuration helpers for the trading bot."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile

LOG_FILE_NAME = "trading_bot.log"
_LOGGING_CONFIGURED = False


def get_log_file_path() -> Path:
    """Return the absolute path to the application log file."""
    if is_vercel_runtime():
        return Path(tempfile.gettempdir()) / LOG_FILE_NAME
    return Path(__file__).resolve().parents[1] / LOG_FILE_NAME


def setup_logging() -> Path:
    """Configure file-based DEBUG logging and return the log file path."""
    global _LOGGING_CONFIGURED

    log_file_path = get_log_file_path()
    if _LOGGING_CONFIGURED:
        return log_file_path

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    logging.captureWarnings(True)
    _LOGGING_CONFIGURED = True

    logging.getLogger(__name__).debug(
        "Logging configured successfully. log_file=%s", log_file_path
    )
    return log_file_path


def is_vercel_runtime() -> bool:
    """Return True when the app is running inside Vercel."""
    return os.getenv("VERCEL") == "1"
