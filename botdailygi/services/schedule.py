from __future__ import annotations

import datetime as dt
import re
import threading
import time

from botdailygi.clients.http import HTTP, UA
from botdailygi.config import STREAM_HOUR, STREAM_MINUTE
from botdailygi.runtime.logging import log
from botdailygi.runtime.state import VN_TZ, now_vn, today_vn


VERSIONS_FALLBACK = [
    ("6.0", "2025-09-10"),
    ("6.1", "2025-10-22"),
    ("6.2", "2025-12-03"),
    ("6.3", "2026-01-14"),
    ("6.4", "2026-02-25"),
    ("6.5", "2026-04-08"),
    ("6.6", "2026-05-20"),
    ("6.7", "2026-07-01"),
    ("6.8", "2026-08-12"),
    ("6.9", "2026-09-23"),
]

_cache: list[tuple[str, str]] = []
_cache_time = 0.0
_cache_ttl = 6 * 3600
_lock = threading.Lock()


def _vkey(version: str):
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def fetch_versions_from_web() -> list[tuple[str, str]]:
    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    found: dict[str, str] = {}
    today = today_vn()
    window_days = 365
    try:
        response = HTTP.get("https://genshin-impact.fandom.com/wiki/Version", headers=headers, timeout=12)
        for version, day_string in re.findall(r"(\d\.\d+)[^\d]{1,60}?(\d{4}-\d{2}-\d{2})", response.text):
            date_obj = dt.date.fromisoformat(day_string)
            if abs((date_obj - today).days) <= window_days:
                found.setdefault(version, day_string)
    except Exception as exc:
        log.debug(f"[versions/fandom] {exc}")
    try:
        response = HTTP.get("https://paimon.moe/api/version", headers=headers, timeout=8)
        if response.status_code == 200:
            payload = response.json()
            items = payload if isinstance(payload, list) else payload.get("data", [])
            for item in items:
                version = str(item.get("version", "")).strip()
                end = str(item.get("end", "") or item.get("date_end", "")).strip()[:10]
                if not re.match(r"\d+\.\d+", version) or not re.match(r"\d{4}-\d{2}-\d{2}", end):
                    continue
                date_obj = dt.date.fromisoformat(end)
                if abs((date_obj - today).days) <= window_days:
                    found.setdefault(version, end)
    except Exception as exc:
        log.debug(f"[versions/paimon] {exc}")
    return sorted(found.items(), key=lambda item: _vkey(item[0])) if found else []


def get_versions() -> list[tuple[str, str]]:
    global _cache, _cache_time
    with _lock:
        if _cache and (time.time() - _cache_time) < _cache_ttl:
            return list(_cache)
    fetched = fetch_versions_from_web()
    merged = dict(VERSIONS_FALLBACK)
    fallback_map = dict(VERSIONS_FALLBACK)
    today = today_vn()
    max_drift = 7
    for version, patch_date in fetched:
        if version in fallback_map:
            try:
                hard_date = dt.date.fromisoformat(fallback_map[version])
                web_date = dt.date.fromisoformat(patch_date)
                drift = abs((web_date - hard_date).days)
                if hard_date >= today and drift > max_drift:
                    log.warning(
                        f"[versions] v{version}: web={patch_date} drift {drift}d vs hardcoded={fallback_map[version]}"
                    )
                    continue
            except Exception:
                pass
        merged[version] = patch_date
    result = sorted(merged.items(), key=lambda item: _vkey(item[0]))
    with _lock:
        _cache = result
        _cache_time = time.time()
    return result


def get_current_version() -> str:
    today = today_vn()
    current = None
    for version, patch_date in get_versions():
        try:
            if dt.date.fromisoformat(patch_date) <= today:
                current = version
            else:
                break
        except Exception:
            pass
    return current or "?"


def next_livestream() -> tuple[str | None, dt.datetime | None]:
    now = now_vn()
    for version, patch_date in get_versions():
        try:
            patch_day = dt.date.fromisoformat(patch_date)
            stream_day = patch_day - dt.timedelta(days=12)
            stream_time = dt.datetime(
                stream_day.year,
                stream_day.month,
                stream_day.day,
                STREAM_HOUR,
                STREAM_MINUTE,
                tzinfo=VN_TZ,
            )
            if stream_time > now:
                return version, stream_time
        except Exception:
            pass
    return None, None
