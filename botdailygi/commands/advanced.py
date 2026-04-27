from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from botdailygi.clients.telegram import download_file, get_file, send_document, send_text
from botdailygi.commands.helpers import active_accounts, default_or_selected_accounts, parallel_account_map, selected_active_accounts
from botdailygi.i18n import t
from botdailygi.renderers.text import account_heading, divider, md_code, md_escape, meter_bar
from botdailygi.runtime.logging import log
from botdailygi.runtime.paths import LOG_FILE
from botdailygi.runtime.state import PendingRestore, pending_restores, pending_restores_lock
from botdailygi.services import accounts
from botdailygi.services.backup import build_backup_archive, restore_backup_archive
from botdailygi.services.history import recent_history, snapshot_history_state
from botdailygi.services.hoyolab import get_account_info_cached, get_checkin_info, get_realtime_notes
from botdailygi.services.resin_config import load_resin_config, save_resin_config
from botdailygi.services.user_settings import (
    clear_default_account,
    get_alias_map,
    get_default_account,
    get_notification_settings,
    remove_alias,
    resolve_alias,
    set_alias,
    set_default_account,
    update_notification_settings,
)
from botdailygi.ui_constants import DIVIDER_LONG, DIVIDER_MEDIUM, DIVIDER_SHORT, ICON_ERROR, ICON_INFO, ICON_SUCCESS


def _default_account_name() -> str:
    return get_default_account().strip()


def _status_block(chat_id, entry: dict, cookies: dict, *, default_name: str = "") -> list[str]:
    info = get_account_info_cached(cookies)
    account_name = entry.get("name", "?")
    lines = [account_heading(account_name)]
    if not info:
        lines.append("  " + t("gen.no_uid", chat_id))
        return lines
    uid, nickname, region = info
    lines.append("  " + t("uid.info", chat_id, nickname=md_escape(nickname), uid=uid, region=md_escape(region)))
    notes = get_realtime_notes(cookies, uid, region)
    if notes.get("retcode") == 0:
        data = notes.get("data", {})
        current = data.get("current_resin", 0)
        maximum = data.get("max_resin", 200)
        bar = meter_bar(current, maximum, width=10)
        checkin = get_checkin_info(cookies).get("data", {})
        icon = ICON_SUCCESS if checkin.get("is_sign") else ICON_ERROR
        lines.append(f"  Resin [{bar}] {current}/{maximum}")
        lines.append(f"  Check-in: {icon} ({checkin.get('total_sign_day', '?')} days)")
    else:
        lines.append("  " + t("gen.api_error", chat_id, code=notes.get("retcode", -1), msg=notes.get("message", "")))
    if default_name.lower() == account_name.lower():
        lines.append(f"  {ICON_INFO} default")
    return lines


def cmd_dashboard(chat_id, arg: str = "") -> None:
    raw = (arg or "").strip()
    target = resolve_alias(raw) if raw else ""
    items = selected_active_accounts(target if target else None)
    if not items:
        send_text(chat_id, t("gen.no_login", chat_id))
        return
    lines = ["Dashboard", divider(DIVIDER_LONG)]
    if target:
        lines.append(f"{ICON_INFO} selected: {md_code(target)}")
    default_name = _default_account_name()
    blocks = parallel_account_map(items, lambda item: _status_block(chat_id, item[0], item[1], default_name=default_name))
    for index, block in enumerate(blocks, 1):
        if index > 1:
            lines.append(divider(DIVIDER_MEDIUM))
        lines.extend(block)
    lines.append(divider(DIVIDER_SHORT))
    lines.append(f"Accounts: {len(items)}")
    send_text(chat_id, "\n".join(lines))


def cmd_overview(chat_id, arg: str = "") -> None:
    raw = (arg or "").strip()
    target = resolve_alias(raw) if raw else _default_account_name()
    items = default_or_selected_accounts(target if target else None)
    if not items:
        send_text(chat_id, t("gen.no_login", chat_id))
        return
    lines = ["Overview", divider(DIVIDER_LONG)]
    if target:
        lines.append(f"{ICON_INFO} account: {md_code(target)}")
    default_name = _default_account_name()
    blocks = parallel_account_map(items, lambda item: _status_block(chat_id, item[0], item[1], default_name=default_name))
    for index, block in enumerate(blocks, 1):
        if index > 1:
            lines.append(divider(DIVIDER_MEDIUM))
        lines.extend(block)
    send_text(chat_id, "\n".join(lines))


def _history_summary(payload: dict) -> str:
    if "current" in payload and "max" in payload:
        return f"{payload.get('current')}/{payload.get('max')}"
    if "checked" in payload:
        state = "checked" if payload.get("checked") else "pending"
        return f"{state}, {payload.get('days', '?')} days"
    if "characters" in payload:
        return f"{payload.get('characters')} chars, {payload.get('achievements')} achievements"
    if "kind" in payload:
        return str(payload.get("kind"))
    return payload.get("summary") or payload.get("state") or ""


def cmd_history(chat_id, arg: str = "") -> None:
    tokens = (arg or "").split()
    account = None
    limit = 10
    for token in tokens:
        if token.isdigit():
            limit = max(1, min(50, int(token)))
        else:
            account = resolve_alias(token)
    rows = recent_history(account=account, limit=limit)
    if not rows:
        send_text(chat_id, "History is empty.")
        return
    lines = [f"History {f'({account})' if account else ''}", divider(DIVIDER_MEDIUM)]
    for row in rows:
        ts = row.get("ts", "")[:19].replace("T", " ")
        payload = row.get("payload", {})
        kind = row.get("kind", "?")
        acc = row.get("account", "?")
        summary = _history_summary(payload)
        if isinstance(summary, dict):
            summary = json.dumps(summary, ensure_ascii=False)
        lines.append(f"{ts}  {kind}  {acc}  {summary}".strip())
    lines.append(divider(DIVIDER_SHORT))
    lines.append(f"Total: {snapshot_history_state().get('count', 0)}")
    send_text(chat_id, "\n".join(lines))


def cmd_backup(chat_id, _arg: str = "") -> None:
    with tempfile.NamedTemporaryFile(prefix="botdailygi_backup_", suffix=".zip", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        temp_path.write_bytes(build_backup_archive())
        send_document(chat_id, temp_path, caption="botDailyGI backup")
    finally:
        temp_path.unlink(missing_ok=True)


def cmd_restore(chat_id, _arg: str = "") -> None:
    now = time.time()
    with pending_restores_lock:
        pending_restores[str(chat_id)] = PendingRestore(
            chat_id=str(chat_id),
            progress_message_id=None,
            created_at=now,
            expires_at=now + 15 * 60,
        )
    send_text(chat_id, "Send a `.zip` backup file now to restore settings and accounts.", parse_mode=None)


def handle_restore_document(chat_id, document: dict) -> bool:
    with pending_restores_lock:
        pending = pending_restores.get(str(chat_id))
    if not pending:
        return False
    if time.time() > pending.expires_at:
        with pending_restores_lock:
            pending_restores.pop(str(chat_id), None)
        send_text(chat_id, "Restore session expired.", parse_mode=None)
        return True
    file_name = str(document.get("file_name", ""))
    if not file_name.lower().endswith(".zip"):
        send_text(chat_id, "Only `.zip` backup files are accepted.", parse_mode=None)
        return True
    file_id = document.get("file_id")
    if not file_id:
        send_text(chat_id, "Could not read the uploaded file.", parse_mode=None)
        return True
    telegram_file = get_file(file_id)
    if not telegram_file or not telegram_file.get("file_path"):
        send_text(chat_id, "Could not read the uploaded file.", parse_mode=None)
        return True
    with tempfile.NamedTemporaryFile(prefix="botdailygi_restore_", suffix=".zip", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        if not download_file(telegram_file["file_path"], temp_path):
            send_text(chat_id, "Download failed.", parse_mode=None)
            return True
        extracted = restore_backup_archive(temp_path)
        accounts.invalidate_account_storage_cache()
        accounts.invalidate_cookie_cache()
        save_resin_config(load_resin_config())
        update_notification_settings()
        send_text(chat_id, f"Restore complete: {len(extracted)} files.")
        return True
    except Exception as exc:
        log.warning(f"[restore] failed: {exc}")
        send_text(chat_id, f"Restore failed: {exc}")
        return True
    finally:
        temp_path.unlink(missing_ok=True)
        with pending_restores_lock:
            pending_restores.pop(str(chat_id), None)


def cmd_default(chat_id, arg: str = "") -> None:
    raw = (arg or "").strip()
    if not raw:
        current = get_default_account() or "-"
        send_text(chat_id, f"Default account: {current}")
        return
    if raw.lower() in {"clear", "off", "none"}:
        clear_default_account()
        send_text(chat_id, "Default account cleared.")
        return
    name = resolve_alias(raw)
    if not accounts.get_account_entry(name):
        send_text(chat_id, f'Account "{name}" not found.')
        return
    set_default_account(name)
    send_text(chat_id, f"Default account set to {name}.")


def cmd_alias(chat_id, arg: str = "") -> None:
    tokens = (arg or "").split()
    if not tokens:
        aliases = get_alias_map()
        if not aliases:
            send_text(chat_id, "No aliases configured.")
            return
        lines = ["Aliases", divider(DIVIDER_SHORT)]
        for alias, target in sorted(aliases.items()):
            lines.append(f"{alias} -> {target}")
        send_text(chat_id, "\n".join(lines))
        return
    if tokens[0].lower() in {"rm", "remove", "del", "delete", "off"}:
        if len(tokens) < 2:
            send_text(chat_id, "Usage: /alias remove <alias>")
            return
        remove_alias(tokens[1])
        send_text(chat_id, f"Alias removed: {tokens[1]}")
        return
    if len(tokens) < 2:
        send_text(chat_id, "Usage: /alias <alias> <account>")
        return
    alias, target = tokens[0], resolve_alias(tokens[1])
    if not accounts.get_account_entry(target):
        send_text(chat_id, f'Account "{target}" not found.')
        return
    set_alias(alias, target)
    send_text(chat_id, f"Alias {alias} -> {target}")


def cmd_renameaccount(chat_id, arg: str = "") -> None:
    tokens = (arg or "").split()
    if len(tokens) < 2:
        send_text(chat_id, "Usage: /renameaccount <old> <new>")
        return
    old_name = resolve_alias(tokens[0])
    new_name = " ".join(tokens[1:])
    ok, result = accounts.rename_account_entry(old_name, new_name)
    if not ok:
        send_text(chat_id, result)
        return
    default_name = get_default_account()
    if default_name.lower() == old_name.lower():
        set_default_account(new_name)
    send_text(chat_id, f"Renamed {old_name} -> {new_name}")


def cmd_health(chat_id, _arg: str = "") -> None:
    from botdailygi.runtime.state import get_network_health

    health = get_network_health()
    lines = [
        "Health",
        divider(DIVIDER_SHORT),
        f"Telegram poll: {health.get('telegram_poll_state', '?')}",
        f"DNS streak: {health.get('poll_dns_fail_streak', 0)}",
        f"Poll streak: {health.get('poll_fail_streak', 0)}",
        f"Threads: {len(active_accounts())} account(s)",
    ]
    send_text(chat_id, "\n".join(lines))


def cmd_logs(chat_id, arg: str = "") -> None:
    limit = 40
    if (arg or "").strip().isdigit():
        limit = max(5, min(200, int(arg.strip())))
    if not LOG_FILE.exists():
        send_text(chat_id, "Log file is empty.")
        return
    lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]
    if not lines:
        send_text(chat_id, "Log file is empty.")
        return
    with tempfile.NamedTemporaryFile(prefix="botdailygi_logs_", suffix=".txt", delete=False) as handle:
        temp_path = Path(handle.name)
    try:
        temp_path.write_text("\n".join(lines), encoding="utf-8")
        send_document(chat_id, temp_path, caption=f"Last {len(lines)} log lines")
    finally:
        temp_path.unlink(missing_ok=True)


def cmd_notify(chat_id, arg: str = "") -> None:
    tokens = (arg or "").split()
    settings = get_notification_settings()
    if not tokens:
        lines = [
            "Notification rules",
            divider(DIVIDER_MEDIUM),
            f"checkin: {'on' if settings.get('checkin', {}).get('enabled', True) else 'off'}",
            f"schedule: {'on' if settings.get('schedule', {}).get('enabled', True) else 'off'}",
            f"history: {'on' if settings.get('history', {}).get('enabled', True) else 'off'}",
            f"resin: use /resinnotify",
        ]
        send_text(chat_id, "\n".join(lines))
        return
    if len(tokens) < 2:
        send_text(chat_id, "Usage: /notify <checkin|schedule|history> <on|off>")
        return
    key = tokens[0].lower()
    value = tokens[1].lower() in {"on", "1", "true", "yes"}
    if key not in {"checkin", "schedule", "history"}:
        send_text(chat_id, "Usage: /notify <checkin|schedule|history> <on|off>")
        return
    update_notification_settings(**{key: {"enabled": value}})
    send_text(chat_id, f"{key} notifications {'enabled' if value else 'disabled'}.")


def cmd_bulk(chat_id, arg: str = "") -> None:
    tokens = [token.strip().lower() for token in (arg or "").replace(",", " ").split() if token.strip()]
    if not tokens:
        send_text(chat_id, "Usage: /bulk <status|resin|stats|characters|abyss|uid|checkin> [more...]")
        return
    from botdailygi.core.commands import COMMANDS

    outputs = []
    for token in tokens:
        name = token if token.startswith("/") else f"/{token}"
        spec = COMMANDS.get(name)
        if not spec:
            outputs.append(f"{name}: unknown")
            continue
        try:
            spec.handler(chat_id, "")
            outputs.append(f"{name}: ok")
        except Exception as exc:
            outputs.append(f"{name}: {exc}")
    send_text(chat_id, "\n".join(outputs))
