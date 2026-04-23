from __future__ import annotations

import logging
import sys
import threading
import time
from logging.handlers import RotatingFileHandler

from botdailygi.runtime.paths import LOG_FILE, ensure_runtime_dirs


ensure_runtime_dirs()

log = logging.getLogger("botdailygi")
if not log.handlers:
    log.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        LOG_FILE,
        encoding="utf-8",
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    log.addHandler(stream_handler)
    log.propagate = False


_throttle_lock = threading.Lock()
_throttle_state: dict[str, float] = {}


def log_throttled(level: int, key: str, interval_seconds: float, message: str) -> bool:
    now_ts = time.time()
    with _throttle_lock:
        last_ts = _throttle_state.get(key, 0.0)
        if (now_ts - last_ts) < interval_seconds:
            return False
        _throttle_state[key] = now_ts
    log.log(level, message)
    return True


def _log_uncaught(prefix: str, exc_type, exc_value, exc_tb) -> None:
    try:
        log.critical(prefix, exc_info=(exc_type, exc_value, exc_tb))
    except Exception:
        pass


def install_exception_hooks() -> None:
    def _sys_excepthook(exc_type, exc_value, exc_tb):
        _log_uncaught("[fatal] Uncaught exception", exc_type, exc_value, exc_tb)

    def _thread_excepthook(args):
        _log_uncaught(
            f"[thread:{args.thread.name}] Uncaught exception",
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
        )

    sys.excepthook = _sys_excepthook
    threading.excepthook = _thread_excepthook
