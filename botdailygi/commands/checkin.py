from __future__ import annotations

from botdailygi.clients.telegram import send_text
from botdailygi.i18n import t
from botdailygi.renderers.text import divider
from botdailygi.runtime.state import manual_checkin_lock
from botdailygi.services.hoyolab import invalidate_api_cache
from botdailygi.services.checkin import do_checkin_for_all
from botdailygi.services.progress import ProgressMessage
from botdailygi.services.status_cache import invalidate_status_cache
from botdailygi.ui_constants import DIVIDER_MEDIUM


def _render_checkin_result(chat_id, result: dict) -> str:
    kind = result.get("kind")
    if kind == "no_cookie":
        return t("checkin.auto.no_cookie", chat_id, err=t("cookie.not_found", chat_id))
    if kind == "success":
        return t("checkin.auto.success", chat_id, label=result["label"])
    if kind == "already":
        return t("checkin.auto.already", chat_id, label=result["label"])
    if kind == "already2":
        return t("checkin.auto.already2", chat_id, label=result["label"], msg=result.get("message", ""))
    if kind == "failed":
        return t(
            "checkin.auto.failed",
            chat_id,
            label=result["label"],
            retries=result.get("retries", 1),
            msg=result.get("message", "unknown"),
        )
    return t(
        "checkin.auto.error",
        chat_id,
        label=result.get("label", "checkin"),
        retries=result.get("retries", 1),
        e=result.get("error", "unknown"),
    )


def cmd_checkin(chat_id, _arg: str = "") -> None:
    if not manual_checkin_lock.acquire(blocking=False):
        send_text(chat_id, t("checkin.busy", chat_id))
        return
    progress = ProgressMessage.start(chat_id, t("checkin.checking", chat_id), action="typing")
    try:
        invalidate_status_cache()
        invalidate_api_cache()
        results = do_checkin_for_all(label=t("checkin.manual.label", chat_id), max_retries=1)
        progress.done(f"{t('checkin.header', chat_id)}\n{divider(DIVIDER_MEDIUM)}\n" + "\n".join(_render_checkin_result(chat_id, result) for result in results))
    except Exception as exc:
        progress.fail(t("gen.error", chat_id, e=exc))
    finally:
        manual_checkin_lock.release()
