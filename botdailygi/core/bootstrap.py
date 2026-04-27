from __future__ import annotations

import socket
import threading
import time

from botdailygi.background.jobs import auto_checkin_loop, heartbeat_loop, reminder_loop, resin_monitor_loop
from botdailygi.clients.http import HTTP, IS_WINDOWS
from botdailygi.clients.telegram import base_url, get_updates, send_text
from botdailygi.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from botdailygi.core.commands import register_commands
from botdailygi.core.dispatcher import handle_callback, handle_document, handle_text
from botdailygi.i18n import load_user_langs, t
from botdailygi.runtime.logging import install_exception_hooks, log
from botdailygi.runtime.paths import ensure_runtime_dirs
from botdailygi.runtime.state import command_executor, now_vn, startup_ready
from botdailygi.services.accounts import ensure_accounts_file


def validate_config() -> bool:
    ok = True
    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN missing")
        ok = False
    if not TELEGRAM_CHAT_ID:
        log.error("TELEGRAM_CHAT_ID missing")
        ok = False
    if not ok:
        return False
    try:
        response = HTTP.get(f"{base_url()}/getMe", timeout=8)
        payload = response.json()
        if not payload.get("ok"):
            log.error(f"Telegram token invalid: {payload.get('description', 'unknown')}")
            return False
        bot_name = payload.get("result", {}).get("username", "?")
        log.info(f"[startup] Telegram token OK - @{bot_name}")
        return True
    except Exception as exc:
        log.error(f"Cannot connect to Telegram: {exc}")
        return False


def start_background_threads() -> None:
    threading.Thread(target=auto_checkin_loop, daemon=True, name="CheckIn").start()
    threading.Thread(target=resin_monitor_loop, daemon=True, name="ResinMon").start()
    threading.Thread(target=heartbeat_loop, daemon=True, name="Heartbeat").start()
    threading.Thread(target=reminder_loop, daemon=True, name="Reminder").start()


def send_startup_message() -> None:
    send_text(
        TELEGRAM_CHAT_ID,
        t(
            "bot.startup",
            TELEGRAM_CHAT_ID,
            host=socket.gethostname(),
            os="Win" if IS_WINDOWS else "Linux/Android",
            time=now_vn().strftime("%H:%M:%S  %d/%m/%Y"),
        )
        + "\n\n"
        + t("bot.type_help", TELEGRAM_CHAT_ID),
    )


def process_update(update: dict) -> int:
    next_offset = update["update_id"] + 1
    message = update.get("message")
    if message:
        chat_id = message.get("chat", {}).get("id")
        if message.get("text"):
            command_executor.submit(handle_text, chat_id, message["text"])
        elif message.get("document"):
            command_executor.submit(handle_document, chat_id, message["document"])
        return next_offset
    callback = update.get("callback_query")
    if callback:
        callback_id = callback.get("id")
        data = callback.get("data", "")
        chat_id = callback.get("message", {}).get("chat", {}).get("id")
        handle_callback(callback_id, chat_id, data)
    return next_offset


def run_poll_loop() -> None:
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = process_update(update)
        except KeyboardInterrupt:
            send_text(TELEGRAM_CHAT_ID, t("bot.stopping", TELEGRAM_CHAT_ID))
            break
        except Exception as exc:
            log.exception(f"[main] Poll loop error: {exc}")
            time.sleep(5)


def main() -> None:
    ensure_runtime_dirs()
    ensure_accounts_file()
    load_user_langs()
    install_exception_hooks()
    log.info(f"Bot starting on {socket.gethostname()}")
    log.info(f"   OS      : {'Windows' if IS_WINDOWS else 'Linux/Android'}")
    log.info(f"   Chat ID : {TELEGRAM_CHAT_ID}")
    log.info(f"   Time VN : {now_vn():%H:%M:%S  %d/%m/%Y}")
    if not validate_config():
        log.error("Bot stopped - fix config and run again.")
        return
    register_commands()
    start_background_threads()
    send_startup_message()
    startup_ready.set()
    run_poll_loop()
