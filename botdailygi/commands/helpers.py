from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from botdailygi.services import accounts


def active_accounts():
    return accounts.all_account_cookies()


def parallel_account_map(items, fn, *, max_workers: int = 4):
    if not items:
        return []
    workers = min(max(len(items), 1), max_workers)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="CmdAcct") as executor:
        return list(executor.map(fn, items))
