from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from botdailygi.clients.telegram import send_text
from botdailygi.i18n import get_lang, t
from botdailygi.renderers.text import divider, md_code, md_escape
from botdailygi.runtime.paths import CODES_BLACKLIST_FILE
from botdailygi.runtime.state import check_change_cooldown, mark_change, redeem_lock
from botdailygi.services import accounts
from botdailygi.services.codes import (
    HOYOLAB_LANG,
    invalidate_blacklist_cache,
    load_blacklist,
    load_codes_from_file,
    redeem_batch,
    should_blacklist,
)
from botdailygi.services.hoyolab import get_account_info_cached, redeem_one
from botdailygi.services.progress import ProgressMessage
from botdailygi.ui_constants import DIVIDER_MEDIUM, DIVIDER_LONG


def _parallel_account_map(items, fn, *, max_workers: int = 4):
    if not items:
        return []
    workers = min(max(len(items), 1), max_workers)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="RedeemAcct") as executor:
        return list(executor.map(fn, items))


def _render_batch_result(chat_id, account_name: str, nickname: str, results: dict) -> str:
    prefix = f"{md_code(account_name)} " if account_name else ""
    lines = [t("code.redeem.summary", chat_id, prefix=prefix, nickname=md_escape(nickname)), divider(DIVIDER_MEDIUM)]
    if results["ok"]:
        lines.append(t("code.redeem.ok", chat_id, count=len(results["ok"]), codes=", ".join(md_code(code) for code in results["ok"])))
    if results["fail_bl"]:
        lines.append(t("code.redeem.fail_bl", chat_id, count=len(results["fail_bl"])))
        for code, reason_key, message in results["fail_bl"]:
            lines.append(f"  • {md_code(code)} · {t(reason_key, chat_id)}: {md_escape(message[:60])}")
    if results["fail_other"]:
        lines.append(t("code.redeem.fail_other", chat_id, count=len(results["fail_other"])))
        for code, message in results["fail_other"]:
            lines.append(f"  • {md_code(code)} · {md_escape(message[:60])}")
    if results["skipped"]:
        lines.append(t("code.redeem.skipped", chat_id, count=len(results["skipped"])))
    return "\n".join(lines)


def _redeem_single_for_account(chat_id, entry: dict, cookies: dict, code: str, api_lang: str, multi: bool) -> str:
    info = get_account_info_cached(cookies)
    account_name = entry.get("name", "") if multi else ""
    if not info:
        return t("gen.no_uid", chat_id) + (f" {md_code(account_name)}" if account_name else "")
    uid, _nickname, region = info
    ok, message, retcode = redeem_one(cookies, uid, region, code, api_lang)
    label = f"{md_code(account_name)} {md_code(code)}" if account_name else md_code(code)
    if ok:
        return t("code.success", chat_id, code=label)
    should_add, reason_key = should_blacklist(message, retcode)
    if should_add:
        from botdailygi.services.codes import add_to_blacklist

        add_to_blacklist(code, reason_key)
        return t("code.failed_bl", chat_id, code=label, msg=md_escape(message), reason=t(reason_key, chat_id))
    return t("code.failed", chat_id, code=label, msg=md_escape(message))


def _redeem_batch_for_account(chat_id, entry: dict, cookies: dict, codes: list[str], api_lang: str, multi: bool) -> str:
    info = get_account_info_cached(cookies)
    if not info:
        return t("gen.no_uid", chat_id) + (f" {md_code(entry.get('name', ''))}" if multi else "")
    uid, nickname, region = info
    results = redeem_batch(codes=codes, cookies=cookies, uid=uid, region=region, lang_code=api_lang)
    return _render_batch_result(chat_id, entry.get("name", "") if multi else "", nickname, results)


def cmd_redeem(chat_id, arg: str = "") -> None:
    code = (arg or "").strip().upper()
    if not code:
        send_text(chat_id, t("code.usage", chat_id))
        return
    blacklist = load_blacklist()
    if code in blacklist:
        send_text(chat_id, t("code.blacklisted", chat_id, code=md_code(code), reason=blacklist[code]))
        return
    account_cookies = accounts.all_account_cookies()
    if not account_cookies:
        send_text(chat_id, t("gen.no_login", chat_id))
        return
    if not redeem_lock.acquire(blocking=False):
        send_text(chat_id, t("code.redeem_busy", chat_id))
        return
    progress = ProgressMessage.start(chat_id, t("code.redeeming", chat_id, code=md_code(code)), action="typing")
    try:
        api_lang = HOYOLAB_LANG.get(get_lang(chat_id), "en-us")
        multi = len(account_cookies) > 1
        lines = _parallel_account_map(
            account_cookies,
            lambda item: _redeem_single_for_account(chat_id, item[0], item[1], code, api_lang, multi),
        )
        progress.done("\n".join(lines))
    finally:
        redeem_lock.release()


def cmd_redeemall(chat_id, _arg: str = "") -> None:
    if not redeem_lock.acquire(blocking=False):
        send_text(chat_id, t("code.redeem_busy2", chat_id))
        return
    try:
        codes = load_codes_from_file()
        if not codes:
            send_text(chat_id, t("code.no_codes", chat_id))
            return
        account_cookies = accounts.all_account_cookies()
        if not account_cookies:
            send_text(chat_id, t("gen.no_login", chat_id))
            return
        progress = ProgressMessage.start(chat_id, t("code.redeem.batch_start", chat_id, count=len(codes)), action="typing")
        api_lang = HOYOLAB_LANG.get(get_lang(chat_id), "en-us")
        multi = len(account_cookies) > 1
        summaries = _parallel_account_map(
            account_cookies,
            lambda item: _redeem_batch_for_account(chat_id, item[0], item[1], codes, api_lang, multi),
        )
        progress.done("\n\n".join(summaries))
    finally:
        redeem_lock.release()


def cmd_blacklist(chat_id, arg: str = "") -> None:
    blacklist = load_blacklist()
    if not blacklist:
        send_text(chat_id, t("code.bl_empty", chat_id))
        return
    raw = (arg or "").strip()
    page = 1
    query = ""
    if raw.isdigit():
        page = max(1, int(raw))
    elif raw:
        query = raw.lower()
    page_size = 10
    items = [(code, reason) for code, reason in sorted(blacklist.items()) if not query or query in code.lower() or query in str(reason).lower()]
    start = (page - 1) * page_size
    page_items = items[start : start + page_size]
    lines = [t("code.bl_header", chat_id, count=len(items)), divider(DIVIDER_MEDIUM)]
    for code, reason in page_items:
        reason_text = t(reason, chat_id) if reason.startswith("code.reason.") else reason
        lines.append(f"  • {md_code(code)} — {reason_text}")
    if len(items) > start + page_size:
        lines.append(divider(DIVIDER_MEDIUM))
        lines.append(f"Page {page}/{(len(items) - 1) // page_size + 1}")
    lines.extend([divider(DIVIDER_MEDIUM), t("code.bl_footer", chat_id)])
    send_text(chat_id, "\n".join(lines))


def cmd_clearblacklist(chat_id, _arg: str = "") -> None:
    blacklist = load_blacklist()
    if not blacklist:
        send_text(chat_id, t("code.bl_already_empty", chat_id))
        return
    wait = check_change_cooldown(chat_id)
    if wait > 0:
        send_text(chat_id, t("gen.cooldown", chat_id, sec=wait))
        return
    try:
        mark_change(chat_id)
        try:
            os.remove(CODES_BLACKLIST_FILE)
        except Exception as exc:
            send_text(chat_id, t("code.clear_error", chat_id, e=exc))
            return
    except Exception as exc:
        send_text(chat_id, t("code.clear_error", chat_id, e=exc))
        return
    invalidate_blacklist_cache()
    send_text(chat_id, t("code.cleared", chat_id, count=len(blacklist)))
