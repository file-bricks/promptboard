"""Logging configuration for PromptBoard.

Logs to a rotating file under ``%LOCALAPPDATA%\\PromptBoard\\promptboard.log``
on Windows (or ``~/.promptboard/`` elsewhere). Console output is INFO by
default, file output is DEBUG.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def default_log_dir() -> Path:
    """Return the default log directory.

    Uses ``%LOCALAPPDATA%`` on Windows, ``~/.promptboard`` elsewhere.
    """
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "PromptBoard"
    return Path.home() / ".promptboard"


def configure_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
) -> Path:
    """Configure root logging with console + rotating file handler.

    Returns the log file path actually used (useful for the
    Settings tab to display).
    """
    if log_file is None:
        log_dir = default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "promptboard.log"

    root = logging.getLogger()
    # Avoid duplicate handlers when called twice (e.g. test harness).
    if any(getattr(h, "_promptboard_marker", False) for h in root.handlers):
        return log_file

    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setLevel(getattr(logging, level.upper(), logging.INFO))
    console.setFormatter(fmt)
    console._promptboard_marker = True  # type: ignore[attr-defined]
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        file_handler._promptboard_marker = True  # type: ignore[attr-defined]
        root.addHandler(file_handler)
    except OSError as exc:
        root.warning("Konnte Logdatei nicht öffnen (%s): %s", log_file, exc)

    return log_file
