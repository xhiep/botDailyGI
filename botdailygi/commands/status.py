from __future__ import annotations

import datetime as dt
import socket
import threading

from botdailygi.clients.http import IS_WINDOWS
from botdailygi.clients.telegram import send_text
from botdailygi.commands.helpers import active_accounts, parallel_account_map
from botdailygi.i18n import t
from botdailygi.renderers.text import account_heading, divider, md_code, md_escape, meter_bar
from botdailygi.runtime.logging import log
from botdailygi.runtime.paths import LOG_FILE
from botdailygi.runtime.state import (
    STREAM_HOUR,
    STREAM_MINUTE,
    command_executor,
    get_network_health,
    manual_checkin_lock,
    now_vn,
    redeem_lock,
    uptime_str,
)
from botdailygi.services.hoyolab import check_cookie_status, get_account_info_cached, get_checkin_info, get_realtime_notes
from botdailygi.services.progress import ProgressMessage
from botdailygi.services.resin_config import get_account_resin_config, load_resin_config
from botdailygi.services.schedule import get_versions
from botdailygi.services.status_cache import get_status_snapshot, set_status_snapshot


def _checkin_line(chat_id, cookies: dict) -> str | None:
    try:
        info = get_checkin_info(cookies).get("data", {})
        icon = t("status.checked", chat_id) if info.get("is_sign") else t("status.not_checked", chat_id)
        return t("status.checkin_line", chat_id, icon=icon, total=info.get("total_sign_day", "?"))
    except Exception:
        return None


def _build_account_snapshot(chat_id, entry: dict, cookies: dict) -> dict:
    payload = {"uid": None, "lines": []}
    info = get_account_info_cached(cookies)
    if not info:
        payload["lines"].append("  " + t("acct.status_cookie_bad", chat_id))
        return payload
    uid, nickname, region = info
    payload["uid"] = uid
    payload["lines"].append("  " + t("uid.info", chat_id, nickname=md_escape(nickname), uid=uid, region=md_escape(region)))
    payload["lines"].append("  " + t("status.cookie_line", chat_id, status=check_cookie_status(cookies, chat_id)))
    data = get_realtime_notes(cookies, uid, region)
    if data.get("retcode") == 0:
        notes = data["data"]
        current = notes.get("current_resin", 0)
        maximum = notes.get("max_resin", 200)
        eta_seconds = int(notes.get("resin_recovery_time", "0"))
        bar = meter_bar(current, maximum, width=10)
        eta_text = (
            t("status.eta_full", chat_id)
            if eta_seconds <= 0
            else t("status.eta_at", chat_id, time=(now_vn() + dt.timedelta(seconds=eta_seconds)).strftime("%H:%M %d/%m"))
        )
        payload["lines"].append("  " + t("status.resin_bar", chat_id, bar=bar, cur=current, max=maximum, eta=eta_text))
    else:
        retcode = data.get("retcode", -1)
        message = data.get("message", "")
        payload["lines"].append(f"  ⚠️ Resin: lỗi rc={retcode}" + (f" ({message})" if message else ""))
    line = _checkin_line(chat_id, cookies)
    if line:
        payload["lines"].append("  " + line)
    return payload


def _cached_snapshot(chat_id, entry: dict, cookies: dict) -> dict:
    key = (str(chat_id), entry.get("slug"), cookies.get("ltuid_v2") or cookies.get("account_id_v2") or entry.get("name"))
    cached = get_status_snapshot(key)
    if cached:
        return cached
    payload = _build_account_snapshot(chat_id, entry, cookies)
    set_status_snapshot(key, payload)
    return payload


def cmd_status(chat_id, _arg: str = "") -> None:
    progress = ProgressMessage.start(chat_id, t("status.fetching", chat_id), action="typing")
    lines = [
        t("status.header", chat_id),
        t("status.host_line", chat_id, host=socket.gethostname(), os="Win" if IS_WINDOWS else "Linux"),
        t("status.time_line", chat_id, time=now_vn().strftime("%H:%M:%S  %d/%m/%Y")),
        t("status.uptime_line", chat_id, uptime=uptime_str()),
        divider(12),
    ]
    items = active_accounts()
    if not items:
        lines.append(t("gen.no_login", chat_id))
    else:
        seen_uids: dict[str, str] = {}
        snapshots = parallel_account_map(items, lambda item: (item[0], _cached_snapshot(chat_id, item[0], item[1])))
        for index, (entry, snapshot) in enumerate(snapshots):
            account_name = entry.get("name", "?")
            lines.append(account_heading(account_name))
            uid = snapshot.get("uid")
            if uid and uid in seen_uids:
                for line in snapshot.get("lines", []):
                    if "Resin:" in line or "Nhựa:" in line:
                        lines.append(f"  ⚠️ Resin: xem tài khoản {md_code(seen_uids[uid])} (cùng UID)")
                    else:
                        lines.append(line)
            else:
                if uid:
                    seen_uids[uid] = account_name
                lines.extend(snapshot.get("lines", []))
            if index < len(items) - 1:
                lines.append(divider(20))
    try:
        now = now_vn()
        for version, patch_date in get_versions():
            patch_day = dt.date.fromisoformat(patch_date)
            stream_day = patch_day - dt.timedelta(days=12)
            stream_time = dt.datetime(stream_day.year, stream_day.month, stream_day.day, STREAM_HOUR, STREAM_MINUTE, tzinfo=now.tzinfo)
            if stream_time > now:
                days = (stream_time.date() - now.date()).days
                if days == 0:
                    lines.append(t("status.live_today", chat_id, ver=version, time=stream_time.strftime("%H:%M")))
                else:
                    lines.append(
                        t(
                            "status.live_future",
                            chat_id,
                            ver=version,
                            time=stream_time.strftime("%H:%M  %d/%m/%Y"),
                            days=days,
                        )
                    )
                break
    except Exception:
        pass
    lines.append(divider(12))
    alive_map = {thread.name: thread.is_alive() for thread in threading.enumerate()}
    thread_parts = []
    any_dead = False
    for name, label in (("CheckIn", "CheckIn"), ("ResinMon", "ResinMon"), ("Heartbeat", "Heartbeat")):
        alive = alive_map.get(name, False)
        any_dead = any_dead or not alive
        thread_parts.append(f"{label} {'✓' if alive else '✗'}")
    lines.append("Threads: " + " | ".join(thread_parts))
    if any_dead:
        lines.append("⚠️ Có background thread đã dừng.")
    lock_parts = []
    if redeem_lock.locked():
        lock_parts.append("redeem")
    if manual_checkin_lock.locked():
        lock_parts.append("checkin")
    lines.append("Locks: " + (", ".join(lock_parts) if lock_parts else "rảnh"))
    try:
        lines.append(f"CmdPool: {command_executor._work_queue.qsize()} lệnh chờ")
    except Exception:
        pass
    try:
        network = get_network_health()
        state_map = {
            "starting": "đang khởi tạo",
            "ok": "ổn định",
            "degraded_dns": f"mất DNS x{network.get('poll_dns_fail_streak', 0)}",
            "degraded_other": f"lỗi polling x{network.get('poll_fail_streak', 0)}",
        }
        lines.append("Network: Telegram poll " + state_map.get(network.get("telegram_poll_state"), "không rõ"))
    except Exception:
        pass
    try:
        config = load_resin_config()
        if items:
            resin_parts = []
            for entry, _cookies in items:
                account_name = entry.get("name", "?")
                account_cfg = get_account_resin_config(config, account_name)
                state_text = "bật" if account_cfg.get("enabled", True) else "tắt"
                resin_parts.append(f"{md_code(account_name)}={state_text}/{account_cfg.get('threshold', 200)}")
            lines.append("ResinCfg: " + ", ".join(resin_parts))
        else:
            default_cfg = config.get("default", {})
            state_text = "bật" if default_cfg.get("enabled", True) else "tắt"
            lines.append(f"ResinCfg: {state_text}, ngưỡng={default_cfg.get('threshold', 200)}")
    except Exception:
        pass
    try:
        size = LOG_FILE.stat().st_size
        size_text = f"{size / 1024 / 1024:.1f} MB" if size >= 1024 * 1024 else f"{size // 1024} KB"
        lines.append(f"📄 bot.log: {size_text} / 2 MB")
    except Exception as exc:
        log.debug(f"[status] Cannot read log file size: {exc}")
    progress.done("\n".join(lines), action="typing")
