from __future__ import annotations

import json
import threading

from botdailygi.runtime.logging import log
from botdailygi.runtime.paths import USER_SETTINGS_FILE
from botdailygi.runtime.state import atomic_write_json


DEFAULT_SETTINGS = {
    "default_account": "",
    "aliases": {},
    "notifications": {
        "checkin": {"enabled": True, "remind_minutes": 30},
        "schedule": {"enabled": True, "remind_hours": 24},
        "history": {"enabled": True},
    },
}

_cache: dict = {}
_cache_mtime = 0.0
_lock = threading.Lock()


def _normalize_settings(data: dict | None) -> dict:
    merged = {
        "default_account": "",
        "aliases": {},
        "notifications": {
            "checkin": {"enabled": True, "remind_minutes": 30},
            "schedule": {"enabled": True, "remind_hours": 24},
            "history": {"enabled": True},
        },
    }
    if not isinstance(data, dict):
        return merged
    default_account = str(data.get("default_account", "") or "").strip()
    aliases = data.get("aliases", {})
    if isinstance(aliases, dict):
        merged["aliases"] = {str(k).strip().lower(): str(v).strip() for k, v in aliases.items() if str(k).strip()}
    if default_account:
        merged["default_account"] = default_account
    notifications = data.get("notifications", {})
    if isinstance(notifications, dict):
        for key in ("checkin", "schedule", "history"):
            raw = notifications.get(key, {})
            if isinstance(raw, dict):
                merged["notifications"][key].update(raw)
    return merged


def load_user_settings() -> dict:
    global _cache, _cache_mtime
    if not USER_SETTINGS_FILE.exists():
        return _normalize_settings(None)
    with _lock:
        try:
            mtime = USER_SETTINGS_FILE.stat().st_mtime
        except OSError:
            return _normalize_settings(None)
        if _cache_mtime == mtime:
            return dict(_cache)
        try:
            data = json.loads(USER_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning(f"[settings] Cannot read {USER_SETTINGS_FILE.name}: {exc}")
            return _normalize_settings(None)
        merged = _normalize_settings(data)
        _cache = merged
        _cache_mtime = mtime
        return dict(merged)


def save_user_settings(settings: dict) -> None:
    global _cache, _cache_mtime
    normalized = _normalize_settings(settings)
    atomic_write_json(USER_SETTINGS_FILE, normalized, ensure_ascii=False, indent=2)
    with _lock:
        _cache = normalized
        _cache_mtime = USER_SETTINGS_FILE.stat().st_mtime if USER_SETTINGS_FILE.exists() else 0.0


def invalidate_user_settings_cache() -> None:
    global _cache_mtime
    with _lock:
        _cache_mtime = 0.0


def get_default_account() -> str:
    return load_user_settings().get("default_account", "")


def set_default_account(name: str) -> dict:
    settings = load_user_settings()
    settings["default_account"] = str(name).strip()
    save_user_settings(settings)
    return settings


def clear_default_account() -> dict:
    return set_default_account("")


def get_alias_map() -> dict[str, str]:
    return dict(load_user_settings().get("aliases", {}))


def resolve_alias(name: str) -> str:
    raw = str(name).strip()
    if not raw:
        return ""
    settings = load_user_settings()
    alias = settings.get("aliases", {}).get(raw.lower())
    return alias or raw


def set_alias(alias: str, account_name: str) -> dict:
    settings = load_user_settings()
    aliases = dict(settings.get("aliases", {}))
    aliases[alias.strip().lower()] = account_name.strip()
    settings["aliases"] = aliases
    save_user_settings(settings)
    return settings


def remove_alias(alias: str) -> dict:
    settings = load_user_settings()
    aliases = dict(settings.get("aliases", {}))
    aliases.pop(alias.strip().lower(), None)
    settings["aliases"] = aliases
    save_user_settings(settings)
    return settings


def get_notification_settings() -> dict:
    return dict(load_user_settings().get("notifications", {}))


def update_notification_settings(**updates) -> dict:
    settings = load_user_settings()
    notifications = dict(settings.get("notifications", {}))
    for key, value in updates.items():
        if key in notifications and isinstance(value, dict):
            notifications[key].update(value)
    settings["notifications"] = notifications
    save_user_settings(settings)
    return settings
