from __future__ import annotations

import json
import threading

from botdailygi.runtime.logging import log
from botdailygi.runtime.paths import RESIN_NOTIFY_FILE
from botdailygi.runtime.state import atomic_write_json


DEFAULT_ENTRY = {"threshold": 200, "enabled": True, "notified": False, "notified_critical": False}
DEFAULTS = {"default": dict(DEFAULT_ENTRY), "accounts": {}}

_cache: dict = {}
_cache_mtime = 0.0
_lock = threading.Lock()


def _normalize_entry(data: dict | None) -> dict:
    merged = dict(DEFAULT_ENTRY)
    if isinstance(data, dict):
        merged.update({k: v for k, v in data.items() if k in DEFAULT_ENTRY})
    return merged


def _normalize_config(data: dict | None) -> dict:
    if not isinstance(data, dict):
        return {"default": dict(DEFAULT_ENTRY), "accounts": {}}
    if "default" in data or "accounts" in data:
        accounts_raw = data.get("accounts", {})
        accounts_map = {}
        if isinstance(accounts_raw, dict):
            for name, entry in accounts_raw.items():
                accounts_map[str(name)] = _normalize_entry(entry)
        return {
            "default": _normalize_entry(data.get("default")),
            "accounts": accounts_map,
        }
    # Backward compatibility for old single-account schema.
    return {"default": _normalize_entry(data), "accounts": {}}


def load_resin_config() -> dict:
    global _cache, _cache_mtime
    if not RESIN_NOTIFY_FILE.exists():
        return _normalize_config(None)
    with _lock:
        try:
            mtime = RESIN_NOTIFY_FILE.stat().st_mtime
        except OSError:
            return _normalize_config(None)
        if _cache_mtime == mtime:
            return dict(_cache)
        try:
            data = json.loads(RESIN_NOTIFY_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning(f"[resin_cfg] Cannot read {RESIN_NOTIFY_FILE.name}: {exc}")
            return _normalize_config(None)
        merged = _normalize_config(data)
        _cache = merged
        _cache_mtime = mtime
        return dict(merged)


def save_resin_config(config: dict) -> None:
    global _cache, _cache_mtime
    normalized = _normalize_config(config)
    atomic_write_json(RESIN_NOTIFY_FILE, normalized, ensure_ascii=False, indent=2)
    with _lock:
        _cache = normalized
        _cache_mtime = RESIN_NOTIFY_FILE.stat().st_mtime if RESIN_NOTIFY_FILE.exists() else 0.0


def get_account_resin_config(config: dict, account_name: str) -> dict:
    normalized = _normalize_config(config)
    merged = dict(normalized["default"])
    merged.update(normalized["accounts"].get(account_name, {}))
    return merged


def set_account_resin_config(config: dict, account_name: str, updates: dict) -> dict:
    normalized = _normalize_config(config)
    entry = dict(normalized["accounts"].get(account_name, normalized["default"]))
    entry.update({k: v for k, v in updates.items() if k in DEFAULT_ENTRY})
    normalized["accounts"][account_name] = entry
    return normalized
