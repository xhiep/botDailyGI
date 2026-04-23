from __future__ import annotations

from botdailygi.clients.telegram import send_buttons, send_text
from botdailygi.i18n import get_lang, set_lang, t
from botdailygi.runtime.state import check_change_cooldown, mark_change
from botdailygi.services.status_cache import invalidate_status_cache


def cmd_start(chat_id, _arg: str = "") -> None:
    send_buttons(
        chat_id,
        t("start.msg", chat_id),
        [
            [{"text": t("lang.en_btn", chat_id), "callback_data": "lang_en"}],
            [{"text": t("lang.vi_btn", chat_id), "callback_data": "lang_vi"}],
        ],
    )


def cmd_help(chat_id, _arg: str = "") -> None:
    send_text(chat_id, t("help.body", chat_id))


def cmd_lang(chat_id, arg: str = "") -> None:
    arg = (arg or "").strip().lower()
    if arg in {"vi", "en"}:
        wait = check_change_cooldown(chat_id)
        if wait > 0:
            send_text(chat_id, t("gen.cooldown", chat_id, sec=wait))
            return
        mark_change(chat_id)
        set_lang(chat_id, arg)
        invalidate_status_cache()
        name = t("lang.vi_name" if arg == "vi" else "lang.en_name", chat_id)
        send_text(chat_id, t("lang.changed", chat_id, name=name))
        cmd_help(chat_id)
        return
    current = get_lang(chat_id)
    send_buttons(
        chat_id,
        t("lang.current", chat_id, cur=current.upper()),
        [
            [{"text": t("lang.en_btn", chat_id), "callback_data": "lang_en"}],
            [{"text": t("lang.vi_btn", chat_id), "callback_data": "lang_vi"}],
        ],
    )
