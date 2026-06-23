"""
Shared logging configuration for localizer-ai backend.

Usage in any module:
    from app.logger import get_logger
    log = get_logger(__name__)
    log.info("something happened")
"""

import logging
import logging.config

_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # keep uvicorn / rq loggers alive
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    # Quieten noisy third-party loggers
    "loggers": {
        "uvicorn.access": {"level": "WARNING"},
        "rq.worker": {"level": "INFO"},
    },
}

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        logging.config.dictConfig(_LOGGING_CONFIG)
        _configured = True


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

def get_logger(name: str) -> logging.Logger:
    """Return a named logger, applying shared config on first call."""
    _ensure_configured()
    return logging.getLogger(name)
