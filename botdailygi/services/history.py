from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime, timezone

from botdailygi.runtime.logging import log
from botdailygi.runtime.paths import HISTORY_FILE
from botdailygi.runtime.state import atomic_write_json


_lock = threading.Lock()


def _parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    item = json.loads(line)
    return item if isinstance(item, dict) else None


def _read_lines() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        rows = []
        for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
            item = _parse_line(line)
            if item:
                rows.append(item)
        return rows
    except Exception as exc:
        log.warning(f"[history] Cannot read {HISTORY_FILE.name}: {exc}")
        return []


def append_history(kind: str, account_name: str, payload: dict) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "account": account_name,
        "payload": payload,
    }
    with _lock:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent_history(*, account: str | None = None, kind: str | None = None, limit: int = 20) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    candidates: deque[dict] = deque(maxlen=max(limit * 5, limit, 20))
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                item = _parse_line(line)
                if item:
                    candidates.append(item)
    except Exception as exc:
        log.warning(f"[history] Cannot read {HISTORY_FILE.name}: {exc}")
        return []
    filtered = []
    for row in reversed(candidates):
        if account and str(row.get("account", "")).lower() != account.lower():
            continue
        if kind and row.get("kind") != kind:
            continue
        filtered.append(row)
        if len(filtered) >= limit:
            break
    return filtered


def snapshot_history_state() -> dict:
    if not HISTORY_FILE.exists():
        return {"count": 0, "last": None}
    count = 0
    last = None
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                item = _parse_line(line)
                if item:
                    count += 1
                    last = item
    except Exception as exc:
        log.warning(f"[history] Cannot read {HISTORY_FILE.name}: {exc}")
        return {"count": 0, "last": None}
    return {"count": count, "last": last}


def export_history(path) -> None:
    rows = _read_lines()
    atomic_write_json(path, rows, ensure_ascii=False, indent=2)
