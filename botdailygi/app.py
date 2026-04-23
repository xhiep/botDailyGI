from __future__ import annotations

import dataclasses
import socket
import threading
import time

from botdailygi.background.jobs import auto_checkin_loop, heartbeat_loop, resin_monitor_loop
from botdailygi.clients.http import HTTP, IS_WINDOWS
from botdailygi.clients.telegram import answer_callback, base_url, get_updates, send_text
from botdailygi.commands.accounts import cmd_accounts, cmd_addaccount, cmd_removeaccount, handle_cookie_document
from botdailygi.commands.checkin import cmd_checkin
from botdailygi.commands.profile import cmd_abyss, cmd_characters, cmd_stats, cmd_uid
from botdailygi.commands.redeem import cmd_blacklist, cmd_clearblacklist, cmd_redeem, cmd_redeemall
from botdailygi.commands.resin import cmd_resin, cmd_resinnotify
from botdailygi.commands.schedule import cmd_livestream
from botdailygi.commands.status import cmd_status
from botdailygi.commands.system import cmd_help, cmd_lang, cmd_start
from botdailygi.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from botdailygi.i18n import load_user_langs, set_lang, t
from botdailygi.runtime.logging import install_exception_hooks, log
from botdailygi.runtime.paths import ensure_runtime_dirs
from botdailygi.runtime.state import (
    check_change_cooldown,
    command_executor,
    mark_change,
    now_vn,
    startup_ready,
)
from botdailygi.services.accounts import ensure_accounts_file


@dataclasses.dataclass(frozen=True)
class CommandSpec:
    name: str
    handler: callable
    progress_enabled: bool
    input_type: str = "text"


COMMANDS: dict[str, CommandSpec] = {
    "/start": CommandSpec("/start", cmd_start, False),
    "/help": CommandSpec("/help", cmd_help, False),
    "/lang": CommandSpec("/lang", cmd_lang, False),
    "/status": CommandSpec("/status", cmd_status, True),
    "/livestream": CommandSpec("/livestream", cmd_livestream, False),
    "/uid": CommandSpec("/uid", cmd_uid, False),
    "/checkin": CommandSpec("/checkin", cmd_checkin, True),
    "/resin": CommandSpec("/resin", cmd_resin, True),
    "/resinnotify": CommandSpec("/resinnotify", cmd_resinnotify, False),
    "/stats": CommandSpec("/stats", cmd_stats, True),
    "/characters": CommandSpec("/characters", cmd_characters, True),
    "/abyss": CommandSpec("/abyss", cmd_abyss, True),
    "/redeem": CommandSpec("/redeem", cmd_redeem, True),
    "/redeemall": CommandSpec("/redeemall", cmd_redeemall, True),
    "/blacklist": CommandSpec("/blacklist", cmd_blacklist, False),
    "/clearblacklist": CommandSpec("/clearblacklist", cmd_clearblacklist, False),
    "/accounts": CommandSpec("/accounts", cmd_accounts, False),
    "/addaccount": CommandSpec("/addaccount", cmd_addaccount, True),
    "/removeaccount": CommandSpec("/removeaccount", cmd_removeaccount, False),
}


def register_commands() -> None:
    commands_vi = [
        {"command": "status", "description": "Trang thai bot + resin + lich"},
        {"command": "livestream", "description": "Lich livestream va patch Genshin sap toi"},
        {"command": "uid", "description": "UID va nickname"},
        {"command": "checkin", "description": "Diem danh HoYoLAB ngay"},
        {"command": "stats", "description": "Thong ke tong hop tai khoan"},
        {"command": "characters", "description": "Danh sach nhan vat"},
        {"command": "resin", "description": "Nhua + expedition + daily"},
        {"command": "resinnotify", "description": "Thong bao nhua (vd: /resinnotify 140)"},
        {"command": "abyss", "description": "Spiral Abyss ky nay (hoac /abyss 2 ky truoc)"},
        {"command": "redeem", "description": "Doi 1 gift code (vd: /redeem ABC123)"},
        {"command": "redeemall", "description": "Doi toan bo code trong codes.txt"},
        {"command": "blacklist", "description": "Xem code bi blacklist"},
        {"command": "clearblacklist", "description": "Xoa toan bo blacklist"},
        {"command": "accounts", "description": "Danh sach tai khoan HoYoLAB"},
        {"command": "addaccount", "description": "Them moi hoac cap nhat cookie: /addaccount <ten>"},
        {"command": "removeaccount", "description": "Xoa tai khoan: /removeaccount <ten>"},
        {"command": "lang", "description": "Doi ngon ngu: /lang vi hoac /lang en"},
        {"command": "help", "description": "Xem toan bo danh sach lenh"},
    ]
    commands_en = [
        {"command": "status", "description": "Bot status + resin + schedule"},
        {"command": "livestream", "description": "Genshin version/stream schedule"},
        {"command": "uid", "description": "UID and nickname"},
        {"command": "checkin", "description": "Check-in on HoYoLAB now"},
        {"command": "stats", "description": "Account stats summary"},
        {"command": "characters", "description": "Character list"},
        {"command": "resin", "description": "Resin + expedition + daily"},
        {"command": "resinnotify", "description": "Resin alert (e.g. /resinnotify 140)"},
        {"command": "abyss", "description": "Spiral Abyss this period (/abyss 2 = prev)"},
        {"command": "redeem", "description": "Redeem 1 gift code (e.g. /redeem ABC123)"},
        {"command": "redeemall", "description": "Redeem all codes in codes.txt"},
        {"command": "blacklist", "description": "View blacklisted codes"},
        {"command": "clearblacklist", "description": "Clear entire blacklist"},
        {"command": "accounts", "description": "List HoYoLAB accounts"},
        {"command": "addaccount", "description": "Add account or refresh cookie by JSON"},
        {"command": "removeaccount", "description": "Remove an account"},
        {"command": "lang", "description": "Change language: /lang vi or /lang en"},
        {"command": "help", "description": "Show full command list"},
    ]
    try:
        vi_response = HTTP.post(f"{base_url()}/setMyCommands", json={"commands": commands_vi}, timeout=10)
        en_response = HTTP.post(
            f"{base_url()}/setMyCommands",
            json={"commands": commands_en, "language_code": "en"},
            timeout=10,
        )
        ok_vi = vi_response.json().get("ok")
        ok_en = en_response.json().get("ok")
        if ok_vi and ok_en:
            log.info(f"[commands] Registered {len(commands_vi)} commands (VI + EN)")
        else:
            log.warning(f"[commands] setMyCommands: vi={ok_vi} en={ok_en}")
    except Exception as exc:
        log.warning(f"[commands] Failed to register commands: {exc}")


def _authorized(chat_id) -> bool:
    return str(chat_id) == str(TELEGRAM_CHAT_ID)


def _validate_config() -> bool:
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


def handle_text(chat_id, text: str) -> None:
    if not _authorized(chat_id):
        send_text(chat_id, t("gen.unauthorized", chat_id))
        return
    raw = text.strip()
    parts = raw.split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0]
    arg = parts[1].strip() if len(parts) > 1 else ""
    spec = COMMANDS.get(cmd)
    if not spec:
        send_text(chat_id, t("gen.unknown_cmd", chat_id))
        return
    spec.handler(chat_id, arg)


def handle_document(chat_id, document: dict) -> None:
    if not _authorized(chat_id):
        send_text(chat_id, t("gen.unauthorized", chat_id))
        return
    handle_cookie_document(chat_id, document)


def handle_callback(callback_id: str, chat_id, data: str) -> None:
    if not _authorized(chat_id):
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
        answer_callback(callback_id, t("lang.changed_cb", chat_id, name=t(f"lang.{selected}_name", chat_id)))
        cmd_help(chat_id)
        return
    answer_callback(callback_id, t("bot.unknown_cb", chat_id))


def main() -> None:
    ensure_runtime_dirs()
    ensure_accounts_file()
    load_user_langs()
    install_exception_hooks()
    log.info(f"Bot starting on {socket.gethostname()}")
    log.info(f"   OS      : {'Windows' if IS_WINDOWS else 'Linux/Android'}")
    log.info(f"   Chat ID : {TELEGRAM_CHAT_ID}")
    log.info(f"   Time VN : {now_vn():%H:%M:%S  %d/%m/%Y}")
    if not _validate_config():
        log.error("Bot stopped - fix config and run again.")
        return
    register_commands()
    threading.Thread(target=auto_checkin_loop, daemon=True, name="CheckIn").start()
    threading.Thread(target=resin_monitor_loop, daemon=True, name="ResinMon").start()
    threading.Thread(target=heartbeat_loop, daemon=True, name="Heartbeat").start()
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
    startup_ready.set()
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message")
                if message:
                    chat_id = message.get("chat", {}).get("id")
                    if message.get("text"):
                        command_executor.submit(handle_text, chat_id, message["text"])
                    elif message.get("document"):
                        command_executor.submit(handle_document, chat_id, message["document"])
                    continue
                callback = update.get("callback_query")
                if callback:
                    callback_id = callback.get("id")
                    data = callback.get("data", "")
                    chat_id = callback.get("message", {}).get("chat", {}).get("id")
                    handle_callback(callback_id, chat_id, data)
        except KeyboardInterrupt:
            send_text(TELEGRAM_CHAT_ID, t("bot.stopping", TELEGRAM_CHAT_ID))
            break
        except Exception as exc:
            log.exception(f"[main] Poll loop error: {exc}")
            time.sleep(5)
