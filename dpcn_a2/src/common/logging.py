"""Logging configuration for DPCN Group 24 pipeline."""

import logging
import os
import re
import sys
from pathlib import Path

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class SecretFilter(logging.Filter):
    """Strip api_key from all log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = re.sub(r"([?&])api_key=[^&\s]+", r"\1api_key=***REDACTED***", record.msg)
        return True


def get_logger(name: str, log_filename: str = "pipeline.log") -> logging.Logger:
    """Create a logger with both console and file handlers, redacting API keys."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    secret_filter = SecretFilter()

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%H:%M:%S")
    ch.setFormatter(ch_formatter)
    ch.addFilter(secret_filter)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOGS_DIR / log_filename, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    fh.setFormatter(fh_formatter)
    fh.addFilter(secret_filter)
    logger.addHandler(fh)

    return logger
