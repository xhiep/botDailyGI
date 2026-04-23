from __future__ import annotations

import time
from pathlib import Path

from botdailygi.clients.http import HTTP
from botdailygi.config import TELEGRAM_BOT_TOKEN
from botdailygi.runtime.logging import log, log_throttled
from botdailygi.runtime.state import report_poll_failure, report_poll_success


_BASE_URL = ""


def base_url() -> str:
    global _BASE_URL
    if not _BASE_URL:
        _BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    return _BASE_URL


def _telegram_json(response, action: str, *, chat_id=None) -> dict:
    try:
        data = response.json()
    except Exception as exc:
        log.warning(f"[{action}] Telegram JSON error (chat={chat_id}): {exc} / HTTP {response.status_code}")
        return {}
    if data.get("ok"):
        return data
    log.warning(
        f"[{action}] Telegram reject (chat={chat_id}) "
        f"code={data.get('error_code')} desc={data.get('description', '')}"
    )
    return {}


def send_chat_action(chat_id, action: str) -> bool:
    try:
        response = HTTP.post(
            f"{base_url()}/sendChatAction",
            data={"chat_id": chat_id, "action": action},
            timeout=10,
        )
        return bool(_telegram_json(response, "sendChatAction", chat_id=chat_id))
    except Exception as exc:
        log.warning(f"[sendChatAction] chat={chat_id}: {exc}")
        return False


def send_text(chat_id, text: str, *, parse_mode: str | None = "Markdown") -> int | None:
    remaining = text if isinstance(text, str) else str(text)
    last_message_id = None
    max_len = 4000
    while remaining:
        if len(remaining) <= max_len:
            chunk = remaining
            remaining = ""
        else:
            cut_at = remaining.rfind("\n", 0, max_len)
            if cut_at == -1:
                cut_at = remaining.rfind(" ", 0, max_len)
            if cut_at == -1:
                cut_at = max_len
            chunk = remaining[:cut_at]
            remaining = remaining[cut_at:].lstrip(" \n")
        payload = {"chat_id": chat_id, "text": chunk}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            response = HTTP.post(f"{base_url()}/sendMessage", data=payload, timeout=15)
            data = _telegram_json(response, "sendMessage", chat_id=chat_id)
            if not data and parse_mode:
                fallback = HTTP.post(
                    f"{base_url()}/sendMessage",
                    data={"chat_id": chat_id, "text": chunk},
                    timeout=15,
                )
                data = _telegram_json(fallback, "sendMessage.fallback", chat_id=chat_id)
            if not data:
                return last_message_id
            last_message_id = data.get("result", {}).get("message_id")
        except Exception as exc:
            log.warning(f"[sendMessage] chat={chat_id}: {exc}")
            return last_message_id
    return last_message_id


def send_buttons(chat_id, text: str, buttons: list[list[dict]]) -> int | None:
    try:
        response = HTTP.post(
            f"{base_url()}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "reply_markup": {"inline_keyboard": buttons},
            },
            timeout=15,
        )
        data = _telegram_json(response, "sendMessage.buttons", chat_id=chat_id)
        if data:
            return data.get("result", {}).get("message_id")
        return send_text(chat_id, text, parse_mode=None)
    except Exception as exc:
        log.warning(f"[sendMessage.buttons] chat={chat_id}: {exc}")
        return send_text(chat_id, text, parse_mode=None)


def edit_text(chat_id, message_id: int, text: str, *, buttons: list[list[dict]] | None = None) -> bool:
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if buttons is not None:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    try:
        response = HTTP.post(f"{base_url()}/editMessageText", json=payload, timeout=15)
        try:
            data = response.json()
        except Exception as exc:
            log.warning(f"[editMessageText] Telegram JSON error (chat={chat_id}): {exc} / HTTP {response.status_code}")
            data = {}
        if data.get("ok"):
            return True
        description = str(data.get("description", ""))
        if "message is not modified" in description.lower():
            return True
        if data:
            log.warning(
                f"[editMessageText] Telegram reject (chat={chat_id}) "
                f"code={data.get('error_code')} desc={description}"
            )
        fallback = HTTP.post(
            f"{base_url()}/editMessageText",
            json={"chat_id": chat_id, "message_id": message_id, "text": text},
            timeout=15,
        )
        try:
            fallback_data = fallback.json()
        except Exception as exc:
            log.warning(
                f"[editMessageText.fallback] Telegram JSON error (chat={chat_id}): {exc} / HTTP {fallback.status_code}"
            )
            return False
        if "message is not modified" in str(fallback_data.get("description", "")).lower():
            return True
        return bool(_telegram_json(fallback, "editMessageText.fallback", chat_id=chat_id))
    except Exception as exc:
        log.warning(f"[editMessageText] chat={chat_id} msg={message_id}: {exc}")
        return False


def answer_callback(callback_id: str, text: str = "", *, show_alert: bool = False) -> bool:
    try:
        response = HTTP.post(
            f"{base_url()}/answerCallbackQuery",
            json={
                "callback_query_id": callback_id,
                "text": text[:180] if text else "",
                "show_alert": show_alert,
            },
            timeout=10,
        )
        return bool(_telegram_json(response, "answerCallbackQuery"))
    except Exception as exc:
        log.warning(f"[answerCallback] id={callback_id}: {exc}")
        return False


def send_photo(chat_id, photo_path: str | Path, *, caption: str = "") -> bool:
    try:
        with Path(photo_path).open("rb") as handle:
            response = HTTP.post(
                f"{base_url()}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": handle},
                timeout=60,
            )
        return bool(_telegram_json(response, "sendPhoto", chat_id=chat_id))
    except Exception as exc:
        log.warning(f"[sendPhoto] chat={chat_id}: {exc}")
        return False


def send_document(chat_id, file_path: str | Path, *, caption: str = "") -> bool:
    try:
        with Path(file_path).open("rb") as handle:
            response = HTTP.post(
                f"{base_url()}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": handle},
                timeout=60,
            )
        return bool(_telegram_json(response, "sendDocument", chat_id=chat_id))
    except Exception as exc:
        log.warning(f"[sendDocument] chat={chat_id}: {exc}")
        return False


def get_file(file_id: str) -> dict | None:
    try:
        response = HTTP.get(f"{base_url()}/getFile", params={"file_id": file_id}, timeout=20)
        data = _telegram_json(response, "getFile")
        return data.get("result") if data else None
    except Exception as exc:
        log.warning(f"[getFile] {file_id}: {exc}")
        return None


def download_file(file_path: str, destination: str | Path) -> bool:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    try:
        response = HTTP.get(url, timeout=60)
        response.raise_for_status()
        target.write_bytes(response.content)
        return True
    except Exception as exc:
        log.warning(f"[download_file] {file_path}: {exc}")
        return False


def get_updates(offset=None) -> list[dict]:
    params = {"timeout": 30, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        params["offset"] = offset
    try:
        response = HTTP.get(f"{base_url()}/getUpdates", params=params, timeout=35)
        data = response.json()
        if data.get("ok"):
            report_poll_success()
            return data.get("result", [])
        report_poll_failure(data.get("description", "getUpdates failed"))
        return []
    except Exception as exc:
        report_poll_failure(exc)
        error_text = str(exc)
        if "NameResolutionError" in error_text or "Failed to resolve" in error_text:
            log_throttled(
                30,
                "telegram.getupdates.dns_fail",
                300,
                "[getUpdates] DNS fail - sleep 30s for network recovery",
            )
        time.sleep(30)
        return []
