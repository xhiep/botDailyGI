from __future__ import annotations

import threading
import time


_status_cache: dict = {}
_status_lock = threading.Lock()
STATUS_TTL = 120
STATUS_MAX = 128


def invalidate_status_cache() -> None:
    with _status_lock:
        _status_cache.clear()


def get_status_snapshot(key):
    now_ts = time.time()
    with _status_lock:
        if len(_status_cache) > STATUS_MAX:
            stale = [item_key for item_key, item in _status_cache.items() if (now_ts - item.get("ts", 0)) >= STATUS_TTL]
            for item_key in stale:
                _status_cache.pop(item_key, None)
        entry = _status_cache.get(key)
        if entry and (now_ts - entry.get("ts", 0)) < STATUS_TTL:
            payload = entry["payload"]
            return {"uid": payload.get("uid"), "lines": list(payload.get("lines", []))}
    return None


def set_status_snapshot(key, payload: dict) -> None:
    with _status_lock:
        _status_cache[key] = {"ts": time.time(), "payload": {"uid": payload.get("uid"), "lines": list(payload.get("lines", []))}}
