from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from botdailygi.runtime.logging import log
from botdailygi.runtime.state import checkin_retry_event
from botdailygi.services import accounts
from botdailygi.services.hoyolab import get_checkin_info, sign_checkin


def wait_checkin_retry(wait_minutes: int) -> None:
    woke = checkin_retry_event.wait(timeout=wait_minutes * 60)
    if woke:
        checkin_retry_event.clear()


def do_checkin_for_one(*, label: str, cookies: dict, account_name: str, max_retries: int = 3, retry_wait_min=None) -> dict:
    retry_waits = [5, 15, 30]
    multi = len(accounts.list_accounts()) > 1
    display_label = f"[{account_name}] {label}" if multi and account_name else label
    for attempt in range(1, max_retries + 1):
        try:
            info = get_checkin_info(cookies).get("data", {})
            if info.get("is_sign"):
                log.info(f"[checkin] {display_label} already signed")
                return {"ok": True, "kind": "already", "label": display_label, "total_days": info.get("total_sign_day", "?")}
            response = sign_checkin(cookies)
            retcode = response.get("retcode", -1)
            message = response.get("message", "unknown")
            if retcode == 0:
                log.info(f"[checkin] {display_label} success")
                return {"ok": True, "kind": "success", "label": display_label}
            if any(token in message.lower() for token in ["already", "đã điểm danh", "signed in", "traveler, check-in"]):
                return {"ok": True, "kind": "already2", "label": display_label, "message": message}
            if attempt < max_retries:
                wait_mins = retry_waits[min(attempt - 1, len(retry_waits) - 1)] if retry_wait_min is None else retry_wait_min
                log.info(f"[checkin] {display_label} failed attempt {attempt}: rc={retcode} msg={message}; retry in {wait_mins}m")
                wait_checkin_retry(wait_mins)
                continue
            return {"ok": False, "kind": "failed", "label": display_label, "message": message, "retries": max_retries}
        except Exception as exc:
            if attempt < max_retries:
                wait_mins = retry_waits[min(attempt - 1, len(retry_waits) - 1)] if retry_wait_min is None else retry_wait_min
                log.info(f"[checkin] {display_label} network error attempt {attempt}: {exc}; retry in {wait_mins}m")
                wait_checkin_retry(wait_mins)
                continue
            return {"ok": False, "kind": "error", "label": display_label, "error": str(exc), "retries": max_retries}
    return {"ok": False, "kind": "error", "label": display_label, "error": "unknown", "retries": max_retries}


def do_checkin_for_all(*, label: str, max_retries: int = 3, retry_wait_min=None) -> list[dict]:
    valid_accounts = accounts.all_account_cookies()
    if not valid_accounts:
        return [{"ok": False, "kind": "no_cookie"}]
    workers = min(max(len(valid_accounts), 1), 4)
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="CheckInJob") as executor:
        futures = [
            executor.submit(
                do_checkin_for_one,
                label=label,
                cookies=cookies,
                account_name=entry.get("name", ""),
                max_retries=max_retries,
                retry_wait_min=retry_wait_min,
            )
            for entry, cookies in valid_accounts
        ]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as exc:
                log.exception(f"[checkin] Unexpected worker error: {exc}")
                results.append({"ok": False, "kind": "error", "label": label, "error": str(exc), "retries": max_retries})
    return results
