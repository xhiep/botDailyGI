from __future__ import annotations

import json
import re
from pathlib import Path

from botdailygi.runtime.logging import log
from botdailygi.runtime.paths import ACCOUNTS_FILE, COOKIES_DIR
from botdailygi.runtime.state import account_cache_lock, atomic_write_json


_accounts_cache: list[dict] = []
_accounts_mtime: float = 0.0
_cookie_cache: dict[str, tuple[float, dict]] = {}


def ensure_accounts_file() -> None:
    if not ACCOUNTS_FILE.exists():
        atomic_write_json(ACCOUNTS_FILE, [], ensure_ascii=False, indent=2)


def slugify_account_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-_").lower()
    return slug or "account"


def read_accounts() -> list[dict]:
    global _accounts_cache, _accounts_mtime
    ensure_accounts_file()
    with account_cache_lock:
        try:
            mtime = ACCOUNTS_FILE.stat().st_mtime
        except OSError:
            return []
        if _accounts_cache and _accounts_mtime == mtime:
            return list(_accounts_cache)
        try:
            data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning(f"[accounts] Cannot read {ACCOUNTS_FILE.name}: {exc}")
            data = []
        if not isinstance(data, list):
            data = []
        _accounts_cache = data
        _accounts_mtime = mtime
        return list(data)


def write_accounts(accounts: list[dict]) -> None:
    global _accounts_cache, _accounts_mtime
    atomic_write_json(ACCOUNTS_FILE, accounts, ensure_ascii=False, indent=2)
    with account_cache_lock:
        _accounts_cache = list(accounts)
        _accounts_mtime = ACCOUNTS_FILE.stat().st_mtime if ACCOUNTS_FILE.exists() else 0.0


def invalidate_account_storage_cache() -> None:
    global _accounts_mtime
    with account_cache_lock:
        _accounts_mtime = 0.0


def list_accounts() -> list[dict]:
    return read_accounts()


def get_account_entry(name: str) -> dict | None:
    for entry in read_accounts():
        if entry.get("name", "").lower() == name.lower():
            return entry
    return None


def get_cookie_path_for_slug(slug: str) -> Path:
    return COOKIES_DIR / f"{slug}.json"


def read_cookie_file(path: str | Path) -> dict:
    cookie_path = Path(path)
    try:
        mtime = cookie_path.stat().st_mtime
    except OSError:
        _cookie_cache.pop(str(cookie_path), None)
        return {}
    cache_key = str(cookie_path)
    with account_cache_lock:
        entry = _cookie_cache.get(cache_key)
        if entry and entry[0] == mtime:
            return dict(entry[1])
    try:
        data = json.loads(cookie_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning(f"[accounts] Cannot read cookie file {cookie_path.name}: {exc}")
        return {}
    cookies = {
        item.get("name"): item.get("value")
        for item in data.get("cookies", [])
        if item.get("name") and item.get("value")
    }
    with account_cache_lock:
        _cookie_cache[cache_key] = (mtime, dict(cookies))
    return cookies


def invalidate_cookie_cache() -> None:
    with account_cache_lock:
        _cookie_cache.clear()


def valid_cookie_payload(cookies: dict) -> bool:
    return bool(cookies.get("ltoken_v2") and cookies.get("ltuid_v2"))


def all_account_cookies() -> list[tuple[dict, dict]]:
    results: list[tuple[dict, dict]] = []
    for entry in read_accounts():
        cookie_file = entry.get("cookie_file")
        if not cookie_file:
            continue
        cookies = read_cookie_file(COOKIES_DIR / cookie_file)
        if valid_cookie_payload(cookies):
            results.append((entry, cookies))
    return results


def add_account_entry(name: str, slug: str) -> tuple[bool, str]:
    accounts = read_accounts()
    if any(item.get("name", "").lower() == name.lower() for item in accounts):
        return False, f'Account "{name}" already exists'
    cookie_file = f"{slug}.json"
    if any(item.get("cookie_file", "").lower() == cookie_file.lower() for item in accounts):
        return False, f'Cookie file "{cookie_file}" already exists'
    accounts.append({"name": name, "slug": slug, "cookie_file": cookie_file})
    write_accounts(accounts)
    return True, ""


def remove_account_entry(name: str) -> tuple[bool, Path | str]:
    accounts = read_accounts()
    found = None
    new_accounts = []
    for entry in accounts:
        if entry.get("name", "").lower() == name.lower():
            found = entry
        else:
            new_accounts.append(entry)
    if not found:
        return False, f'Account "{name}" not found'
    write_accounts(new_accounts)
    return True, COOKIES_DIR / found["cookie_file"]
