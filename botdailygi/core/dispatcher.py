from __future__ import annotations

from botdailygi.clients.telegram import answer_callback, send_text
from botdailygi.commands.advanced import handle_restore_document
from botdailygi.commands.accounts import handle_cookie_document
from botdailygi.commands.system import cmd_help
from botdailygi.config import TELEGRAM_CHAT_ID
from botdailygi.core.commands import COMMANDS
from botdailygi.i18n import set_lang, t
from botdailygi.runtime.state import check_change_cooldown, mark_change
from botdailygi.services.status_cache import invalidate_status_cache


def authorized(chat_id) -> bool:
    return str(chat_id) == str(TELEGRAM_CHAT_ID)


def handle_text(chat_id, text: str) -> None:
    if not authorized(chat_id):
        send_text(chat_id, t("gen.unauthorized", chat_id))
        return
    raw = text.strip()
    if not raw:
        send_text(chat_id, t("gen.unknown_cmd", chat_id))
        return
    parts = raw.split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0]
    arg = parts[1].strip() if len(parts) > 1 else ""
    spec = COMMANDS.get(cmd)
    if not spec:
        send_text(chat_id, t("gen.unknown_cmd", chat_id))
        return
    spec.handler(chat_id, arg)


def handle_document(chat_id, document: dict) -> None:
    if not authorized(chat_id):
        send_text(chat_id, t("gen.unauthorized", chat_id))
        return
    if handle_restore_document(chat_id, document):
        return
    handle_cookie_document(chat_id, document)


def handle_callback(callback_id: str, chat_id, data: str) -> None:
    if not authorized(chat_id):
        answer_callback(callback_id, t("gen.unauthorized", chat_id))
        return
    if data.startswith("lang_"):
        selected = data.split("_", 1)[1]
        if selected not in {"vi", "en"}:
            answer_callback(callback_id, t("bot.unknown_cb", chat_id))
            return
        wait = check_change_cooldown(chat_id)
        if wait > 0:
            answer_callback(callback_id, t("gen.cooldown", chat_id, sec=wait))
            return
        mark_change(chat_id)
        set_lang(chat_id, selected)
        invalidate_status_cache()
        answer_callback(callback_id, t("lang.changed_cb", chat_id, name=t(f"lang.{selected}_name", chat_id)))
        cmd_help(chat_id)
        return
    if data.startswith("acctset:"):
        from botdailygi.services.user_settings import set_default_account
        from botdailygi.services.accounts import get_account_entry
        from botdailygi.services.status_cache import invalidate_status_cache as _invalidate_status_cache

        account_name = data.split(":", 1)[1]
        if not get_account_entry(account_name):
            answer_callback(callback_id, t("gen.no_login", chat_id))
            return
        set_default_account(account_name)
        _invalidate_status_cache()
        answer_callback(callback_id, f"Default: {account_name}")
        cmd_help(chat_id)
        return
    if data == "acctclear":
        from botdailygi.services.user_settings import clear_default_account
        from botdailygi.services.status_cache import invalidate_status_cache as _invalidate_status_cache

        clear_default_account()
        _invalidate_status_cache()
        answer_callback(callback_id, "Default cleared")
        cmd_help(chat_id)
        return
    answer_callback(callback_id, t("bot.unknown_cb", chat_id))
