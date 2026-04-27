from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from botdailygi.services import accounts
from botdailygi.services.user_settings import get_default_account, resolve_alias


def active_accounts():
    return accounts.all_account_cookies()


def selected_active_accounts(account_name: str | None = None):
    if not account_name:
        return active_accounts()
    target = resolve_alias(account_name).lower()
    return [
        item
        for item in active_accounts()
        if item[0].get("name", "").lower() == target
    ]


def active_account_names() -> list[str]:
    return [entry.get("name", "") for entry, _cookies in active_accounts()]


def default_or_selected_accounts(account_name: str | None = None):
    target = account_name or get_default_account()
    return selected_active_accounts(target if target else None)


def parallel_account_map(items, fn, *, max_workers: int = 4):
    if not items:
        return []
    workers = min(max(len(items), 1), max_workers)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="CmdAcct") as executor:
        return list(executor.map(fn, items))
