from __future__ import annotations

import json
import time
from pathlib import Path

from botdailygi.runtime.logging import log
from botdailygi.runtime.state import PendingCookieImport, pending_imports, pending_imports_lock
from botdailygi.runtime.state import atomic_write_json
from botdailygi.services import accounts
from botdailygi.services.hoyolab import get_account_info, invalidate_account_cache


IMPORT_TIMEOUT_SECS = 10 * 60
MAX_COOKIE_UPLOAD_BYTES = 1_000_000


def cleanup_expired_imports() -> None:
    now = time.time()
    with pending_imports_lock:
        expired = [chat_id for chat_id, item in pending_imports.items() if item.expires_at <= now]
        for chat_id in expired:
            pending_imports.pop(chat_id, None)


def get_pending_import(chat_id) -> PendingCookieImport | None:
    cleanup_expired_imports()
    with pending_imports_lock:
        return pending_imports.get(str(chat_id))


def start_pending_import(chat_id, account_name: str, progress_message_id: int | None) -> PendingCookieImport:
    existing = accounts.get_account_entry(account_name)
    slug = existing.get("slug") if existing else accounts.slugify_account_name(account_name)
    cookie_file = existing.get("cookie_file") if existing and existing.get("cookie_file") else f"{slug}.json"
    entry = PendingCookieImport(
        chat_id=str(chat_id),
        account_name=account_name,
        account_slug=slug,
        cookie_file=cookie_file,
        replace_existing=bool(existing),
        progress_message_id=progress_message_id,
        created_at=time.time(),
        expires_at=time.time() + IMPORT_TIMEOUT_SECS,
    )
    with pending_imports_lock:
        pending_imports[str(chat_id)] = entry
    return entry


def clear_pending_import(chat_id) -> None:
    with pending_imports_lock:
        pending_imports.pop(str(chat_id), None)


def _normalize_storage_state(payload: dict) -> dict:
    cookies = payload.get("cookies")
    if not isinstance(cookies, list):
        raise ValueError("storage-state JSON missing cookies array")
    normalized = []
    for item in cookies:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if not name or value in (None, ""):
            continue
        normalized.append(dict(item))
    result = {"cookies": normalized}
    if isinstance(payload.get("origins"), list):
        result["origins"] = payload["origins"]
    return result


def _cookie_map(storage_state: dict) -> dict:
    return {
        item.get("name"): item.get("value")
        for item in storage_state.get("cookies", [])
        if item.get("name") and item.get("value")
    }


def import_cookie_json(chat_id, pending: PendingCookieImport, source_path: str | Path) -> dict:
    path = Path(source_path)
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    storage_state = _normalize_storage_state(payload)
    cookies = _cookie_map(storage_state)
    if not cookies.get("ltoken_v2") or not cookies.get("ltuid_v2"):
        raise ValueError("missing ltoken_v2 or ltuid_v2 in cookie JSON")

    target_path = accounts.COOKIES_DIR / pending.cookie_file
    existing_entry = accounts.get_account_entry(pending.account_name)
    if target_path.exists() and not pending.replace_existing and not existing_entry:
        raise ValueError(f"cookie file {target_path.name} already exists")

    atomic_write_json(target_path, storage_state, ensure_ascii=False, indent=2)
    if not existing_entry:
        ok, err = accounts.add_account_entry(pending.account_name, pending.account_slug)
        if not ok:
            target_path.unlink(missing_ok=True)
            raise ValueError(err)

    accounts.invalidate_cookie_cache()
    invalidate_account_cache()
    info = get_account_info(cookies)
    result = {
        "name": pending.account_name,
        "cookie_file": target_path.name,
        "uid": None,
        "nickname": None,
        "region": None,
        "updated": bool(existing_entry),
    }
    if info:
        result["uid"], result["nickname"], result["region"] = info
    clear_pending_import(chat_id)
    log.info(f"[account_import] Imported cookie for {pending.account_name} -> {target_path.name}")
    return result
