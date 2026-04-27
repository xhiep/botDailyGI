from __future__ import annotations

import dataclasses

from botdailygi.clients.http import HTTP
from botdailygi.clients.telegram import base_url
from botdailygi.commands.advanced import cmd_alias, cmd_backup, cmd_bulk, cmd_dashboard, cmd_default, cmd_health, cmd_history, cmd_logs, cmd_notify, cmd_overview, cmd_renameaccount, cmd_restore
from botdailygi.commands.accounts import cmd_accounts, cmd_addaccount, cmd_removeaccount
from botdailygi.commands.checkin import cmd_checkin
from botdailygi.commands.profile import cmd_abyss, cmd_characters, cmd_stats, cmd_uid
from botdailygi.commands.redeem import cmd_blacklist, cmd_clearblacklist, cmd_redeem, cmd_redeemall
from botdailygi.commands.resin import cmd_resin, cmd_resinnotify
from botdailygi.commands.schedule import cmd_livestream
from botdailygi.commands.status import cmd_status
from botdailygi.commands.system import cmd_help, cmd_lang, cmd_start
from botdailygi.runtime.logging import log


@dataclasses.dataclass(frozen=True)
class CommandSpec:
    name: str
    handler: callable
    progress_enabled: bool
    input_type: str = "text"


COMMANDS: dict[str, CommandSpec] = {
    "/start": CommandSpec("/start", cmd_start, False),
    "/help": CommandSpec("/help", cmd_help, False),
    "/dashboard": CommandSpec("/dashboard", cmd_dashboard, True),
    "/overview": CommandSpec("/overview", cmd_overview, True),
    "/history": CommandSpec("/history", cmd_history, False),
    "/backup": CommandSpec("/backup", cmd_backup, False),
    "/restore": CommandSpec("/restore", cmd_restore, False),
    "/default": CommandSpec("/default", cmd_default, False),
    "/alias": CommandSpec("/alias", cmd_alias, False),
    "/renameaccount": CommandSpec("/renameaccount", cmd_renameaccount, False),
    "/health": CommandSpec("/health", cmd_health, False),
    "/logs": CommandSpec("/logs", cmd_logs, False),
    "/notify": CommandSpec("/notify", cmd_notify, False),
    "/bulk": CommandSpec("/bulk", cmd_bulk, False),
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

COMMANDS_VI = [
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
    {"command": "dashboard", "description": "Tong hop status tat ca account"},
    {"command": "overview", "description": "Xem tong quan 1 account hoac default"},
    {"command": "history", "description": "Lich su resin/checkin/stats"},
    {"command": "backup", "description": "Sao luu runtime thanh file zip"},
    {"command": "restore", "description": "Khoi phuc runtime tu file zip"},
    {"command": "default", "description": "Dat account mac dinh"},
    {"command": "alias", "description": "Dat alias cho account"},
    {"command": "renameaccount", "description": "Doi ten account"},
    {"command": "health", "description": "Trang thai he thong"},
    {"command": "logs", "description": "Lay log gan nhat"},
    {"command": "notify", "description": "Quan ly rule thong bao"},
    {"command": "bulk", "description": "Chay nhieu lenh lien tiep"},
]

COMMANDS_EN = [
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
    {"command": "dashboard", "description": "Aggregate status for all accounts"},
    {"command": "overview", "description": "Overview for one account or default"},
    {"command": "history", "description": "History for resin/check-in/stats"},
    {"command": "backup", "description": "Export runtime as a zip backup"},
    {"command": "restore", "description": "Restore runtime from a zip backup"},
    {"command": "default", "description": "Set the default account"},
    {"command": "alias", "description": "Create or list account aliases"},
    {"command": "renameaccount", "description": "Rename an account"},
    {"command": "health", "description": "System health report"},
    {"command": "logs", "description": "Fetch recent log lines"},
    {"command": "notify", "description": "Manage notification rules"},
    {"command": "bulk", "description": "Run multiple commands in sequence"},
]


def register_commands() -> None:
    try:
        vi_response = HTTP.post(f"{base_url()}/setMyCommands", json={"commands": COMMANDS_VI}, timeout=10)
        en_response = HTTP.post(
            f"{base_url()}/setMyCommands",
            json={"commands": COMMANDS_EN, "language_code": "en"},
            timeout=10,
        )
        ok_vi = vi_response.json().get("ok")
        ok_en = en_response.json().get("ok")
        if ok_vi and ok_en:
            log.info(f"[commands] Registered {len(COMMANDS_VI)} commands (VI + EN)")
        else:
            log.warning(f"[commands] setMyCommands: vi={ok_vi} en={ok_en}")
    except Exception as exc:
        log.warning(f"[commands] Failed to register commands: {exc}")
