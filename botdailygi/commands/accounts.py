from __future__ import annotations

import os
import tempfile
from pathlib import Path

from botdailygi.clients.telegram import download_file, get_file, send_text
from botdailygi.i18n import t
from botdailygi.renderers.text import account_heading, divider, md_code, md_escape
from botdailygi.runtime.logging import log
from botdailygi.runtime.state import resin_wake_event
from botdailygi.services import accounts
from botdailygi.services.account_import import (
    IMPORT_TIMEOUT_SECS,
    MAX_COOKIE_UPLOAD_BYTES,
    get_pending_import,
    import_cookie_json,
    start_pending_import,
)
from botdailygi.services.hoyolab import get_account_info_cached, invalidate_api_cache
from botdailygi.services.progress import ProgressMessage
from botdailygi.services.status_cache import invalidate_status_cache


def cmd_accounts(chat_id, _arg: str = "") -> None:
    entries = accounts.list_accounts()
    if not entries:
        send_text(chat_id, t("acct.empty", chat_id))
        return
    lines = [t("acct.list_header", chat_id, count=len(entries)), divider(20)]
    for index, entry in enumerate(entries, 1):
        name = entry.get("name", "?")
        cookie_path = accounts.COOKIES_DIR / entry.get("cookie_file", "")
        cookies = accounts.read_cookie_file(cookie_path)
        if accounts.valid_cookie_payload(cookies):
            info = get_account_info_cached(cookies)
            if info:
                uid, nickname, region = info
                status = t("acct.status_ok", chat_id, nickname=md_escape(nickname), uid=uid, region=md_escape(region))
            else:
                status = t("acct.status_cookie_bad", chat_id)
        elif cookie_path.exists():
            status = t("acct.status_no_cookie", chat_id)
        else:
            status = t("acct.status_no_file", chat_id)
        lines.append(f"{index}. {account_heading(name, icon='🗂️')}\n   {status}")
        if index < len(entries):
            lines.append(divider(20))
    lines.append(divider(20))
    lines.append(t("acct.list_footer", chat_id))
    send_text(chat_id, "\n".join(lines))


def cmd_addaccount(chat_id, arg: str = "") -> None:
    name = (arg or "").strip()
    if not name:
        send_text(chat_id, t("acct.add_usage", chat_id))
        return
    existing_entry = accounts.get_account_entry(name)
    slug = accounts.slugify_account_name(name)
    target_path = accounts.get_cookie_path_for_slug(slug)
    if target_path.exists() and not existing_entry:
        send_text(chat_id, t("acct.add_file_dup", chat_id, name=name, file=target_path.name))
        return
    opening_key = "acct.update_import_open" if existing_entry else "acct.add_import_open"
    waiting_key = "acct.update_import_wait" if existing_entry else "acct.add_import_wait"
    progress = ProgressMessage.start(chat_id, t(opening_key, chat_id, name=md_escape(name)), action="upload_document")
    pending = start_pending_import(chat_id, name, progress.message_id)
    minutes = IMPORT_TIMEOUT_SECS // 60
    progress.done(
        t(waiting_key, chat_id, name=md_escape(name), minutes=minutes, file=md_code(pending.cookie_file)),
        action="upload_document",
    )


def cmd_removeaccount(chat_id, arg: str = "") -> None:
    name = (arg or "").strip()
    if not name:
        send_text(chat_id, t("acct.remove_usage", chat_id))
        return
    ok, result = accounts.remove_account_entry(name)
    if not ok:
        send_text(chat_id, t("acct.remove_error", chat_id, name=name, err=result))
        return
    deleted_file = False
    cookie_path = Path(result)
    if cookie_path.exists():
        try:
            cookie_path.unlink()
            deleted_file = True
        except Exception as exc:
            log.warning(f"[removeaccount] Cannot delete {cookie_path}: {exc}")
    accounts.invalidate_cookie_cache()
    invalidate_api_cache()
    invalidate_status_cache()
    resin_wake_event.set()
    send_text(
        chat_id,
        t(
            "acct.remove_success",
            chat_id,
            name=name,
            file_note=t("acct.remove_file_deleted", chat_id) if deleted_file else "",
        ),
    )


def handle_cookie_document(chat_id, document: dict) -> None:
    pending = get_pending_import(chat_id)
    if not pending:
        send_text(chat_id, t("acct.import.no_pending", chat_id))
        return
    progress = ProgressMessage(chat_id=chat_id, message_id=pending.progress_message_id)
    file_name = str(document.get("file_name", ""))
    file_size = int(document.get("file_size") or 0)
    if not file_name.lower().endswith(".json"):
        progress.fail(t("acct.import.bad_type", chat_id))
        return
    if file_size > MAX_COOKIE_UPLOAD_BYTES:
        progress.fail(t("acct.import.too_large", chat_id, size=file_size, max_size=MAX_COOKIE_UPLOAD_BYTES))
        return
    file_id = document.get("file_id")
    if not file_id:
        progress.fail(t("acct.import.bad_file", chat_id))
        return
    progress.update(t("acct.import.downloading", chat_id, name=md_escape(pending.account_name)), action="upload_document")
    telegram_file = get_file(file_id)
    if not telegram_file or not telegram_file.get("file_path"):
        progress.fail(t("acct.import.bad_file", chat_id))
        return
    fd, temp_name = tempfile.mkstemp(prefix="cookie_", suffix=".json")
    os.close(fd)
    Path(temp_name).unlink(missing_ok=True)
    temp_path = Path(temp_name)
    try:
        if not download_file(telegram_file["file_path"], temp_path):
            progress.fail(t("acct.import.download_fail", chat_id))
            return
        progress.update(t("acct.import.validating", chat_id, name=md_escape(pending.account_name)), action="typing")
        result = import_cookie_json(chat_id, pending, temp_path)
        accounts.invalidate_cookie_cache()
        invalidate_api_cache()
        invalidate_status_cache()
        resin_wake_event.set()
        if result.get("uid"):
            success_key = "acct.import.updated" if result.get("updated") else "acct.import.success"
            progress.done(
                t(
                    success_key,
                    chat_id,
                    name=md_escape(result["name"]),
                    nickname=md_escape(result["nickname"]),
                    uid=result["uid"],
                    region=md_escape(result["region"]),
                )
            )
        else:
            done_key = "acct.update_success_no_info" if result.get("updated") else "acct.add_success_no_info"
            progress.done(t(done_key, chat_id, name=md_escape(result["name"])))
    except Exception as exc:
        progress.fail(t("acct.import.failed", chat_id, err=exc))
    finally:
        temp_path.unlink(missing_ok=True)
