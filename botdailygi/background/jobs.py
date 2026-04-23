from __future__ import annotations

import datetime as dt
import socket
import threading
import time

from botdailygi.clients.telegram import send_text
from botdailygi.config import TELEGRAM_CHAT_ID
from botdailygi.i18n import t
from botdailygi.renderers.text import display_name as fmt_display_name
from botdailygi.runtime.logging import log
from botdailygi.runtime.state import (
    checkin_wake_event,
    heartbeat_wake_event,
    manual_checkin_lock,
    now_vn,
    redeem_lock,
    resin_wake_event,
    uptime_str,
)
from botdailygi.services import accounts
from botdailygi.services.checkin import do_checkin_for_all
from botdailygi.services.hoyolab import get_account_info, get_account_info_cached, get_checkin_info, get_realtime_notes
from botdailygi.services.resin_config import (
    get_account_resin_config,
    load_resin_config,
    save_resin_config,
    set_account_resin_config,
)


def _render_checkin_lines(results: list[dict]) -> str:
    from botdailygi.commands.checkin import _render_checkin_result

    return "\n".join(_render_checkin_result(TELEGRAM_CHAT_ID, item) for item in results)


def _next_resin_check_seconds(current: int, maximum: int, eta_seconds: int, threshold: int, threshold_critical: int) -> int:
    if current < threshold:
        resin_needed = max(threshold - current, 0)
        predicted = resin_needed * 480
        if eta_seconds > 0:
            predicted = min(predicted, eta_seconds)
        return max(predicted, 60)
    if threshold_critical > threshold and current < threshold_critical:
        return max((threshold_critical - current) * 480, 300)
    return 1800


def auto_checkin_loop() -> None:
    schedule = [(9, 0), (21, 0)]
    log.info("Auto check-in thread ready (09:00 and 21:00 VN)")
    while True:
        try:
            now = now_vn()
            next_slot = None
            for hour, minute in schedule:
                slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if slot <= now:
                    slot += dt.timedelta(days=1)
                if next_slot is None or slot < next_slot:
                    next_slot = slot
            sleep_seconds = max((next_slot - now).total_seconds(), 0)
            woke_early = checkin_wake_event.wait(timeout=sleep_seconds)
            checkin_wake_event.clear()
            actual = now_vn()
            if woke_early and actual + dt.timedelta(seconds=30) < next_slot:
                log.info(f"[auto_checkin] Early wake at {actual:%H:%M:%S %d/%m}; ignore until {next_slot:%H:%M %d/%m}")
                continue
            delay_seconds = int((actual - next_slot).total_seconds())
            if delay_seconds > 90:
                log.warning(f"[auto_checkin] Delayed {delay_seconds}s vs slot {next_slot:%H:%M %d/%m}")
            if not manual_checkin_lock.acquire(blocking=False):
                log.info("[auto_checkin] Manual check-in lock busy, skip this run")
                continue
            try:
                label = t("checkin.auto.label_sched", TELEGRAM_CHAT_ID, time=next_slot.strftime("%H:%M"))
                results = do_checkin_for_all(label=label)
                send_text(TELEGRAM_CHAT_ID, _render_checkin_lines(results))
            finally:
                manual_checkin_lock.release()
        except Exception as exc:
            log.exception(f"[auto_checkin] Unexpected loop error: {exc}")
            time.sleep(10)


def resin_monitor_loop() -> None:
    log.info("Resin monitor thread ready")
    account_info_cache: dict[str, tuple[str, str, str, float]] = {}
    resin_state_cache: dict[str, dict] = {}
    cache_ttl = 3600
    force_refresh = False
    while True:
        config = load_resin_config()
        account_items = accounts.all_account_cookies()
        if not account_items:
            resin_state_cache.clear()
            resin_wake_event.wait(timeout=1800)
            force_refresh = resin_wake_event.is_set()
            resin_wake_event.clear()
            continue
        next_wake_at: float | None = None
        changed = False
        any_enabled = False
        multi = len(account_items) > 1
        try:
            now_ts = time.time()
            live_accounts = {entry.get("name", "?") for entry, _cookies in account_items}
            for cached_name in list(resin_state_cache):
                if cached_name not in live_accounts:
                    resin_state_cache.pop(cached_name, None)
            for entry, cookies in account_items:
                account_name = entry.get("name", "?")
                account_cfg = get_account_resin_config(config, account_name)
                if not account_cfg.get("enabled"):
                    resin_state_cache.pop(account_name, None)
                    continue
                any_enabled = True
                cached = account_info_cache.get(account_name)
                if not cached or (time.time() - cached[3]) > cache_ttl:
                    info = get_account_info(cookies)
                    if not info:
                        next_due_at = time.time() + 1800
                        resin_state_cache[account_name] = {"next_check_at": next_due_at}
                        next_wake_at = next_due_at if next_wake_at is None else min(next_wake_at, next_due_at)
                        continue
                    cached = (info[0], info[1], info[2], time.time())
                    account_info_cache[account_name] = cached
                state = resin_state_cache.get(account_name)
                cookie_key = cookies.get("ltuid_v2") or cookies.get("account_id_v2") or account_name
                if (
                    not force_refresh
                    and state
                    and state.get("cookie_key") == cookie_key
                    and state.get("next_check_at", 0) > now_ts
                ):
                    next_due_at = float(state["next_check_at"])
                    next_wake_at = next_due_at if next_wake_at is None else min(next_wake_at, next_due_at)
                    continue
                uid, nickname, region, _cached_at = cached
                payload = get_realtime_notes(cookies, uid, region)
                if payload.get("retcode", -1) != 0:
                    account_info_cache.pop(account_name, None)
                    next_due_at = time.time() + 1800
                    resin_state_cache[account_name] = {"next_check_at": next_due_at, "cookie_key": cookie_key}
                    next_wake_at = next_due_at if next_wake_at is None else min(next_wake_at, next_due_at)
                    continue
                data = payload["data"]
                current = data.get("current_resin", 0)
                maximum = data.get("max_resin", 200)
                eta_seconds = int(data.get("resin_recovery_time", "0"))
                threshold = min(account_cfg.get("threshold", maximum), maximum)
                threshold_critical = min(threshold + 8, maximum)
                critical_active = threshold_critical > threshold
                display_name = fmt_display_name(nickname, account_name, multi=multi)

                if current >= threshold and not account_cfg.get("notified", False):
                    full_text = t("resin.alert.full_str", TELEGRAM_CHAT_ID) if eta_seconds <= 0 else f"{current}/{maximum}"
                    hint = t("resin.alert.hint_critical", TELEGRAM_CHAT_ID, critical=threshold_critical) if critical_active else ""
                    if send_text(
                        TELEGRAM_CHAT_ID,
                        t(
                            "resin.alert.threshold",
                            TELEGRAM_CHAT_ID,
                            nickname=display_name,
                            full_str=full_text,
                            threshold=threshold,
                            max=maximum,
                            hint=hint,
                        ),
                    ):
                        config = set_account_resin_config(config, account_name, {"notified": True})
                        account_cfg = get_account_resin_config(config, account_name)
                        changed = True
                elif critical_active and current >= threshold_critical:
                    if not account_cfg.get("notified_critical", False):
                        if send_text(
                            TELEGRAM_CHAT_ID,
                            t(
                                "resin.alert.critical",
                                TELEGRAM_CHAT_ID,
                                nickname=display_name,
                                cur=current,
                                max=maximum,
                                remain=maximum - current,
                            ),
                        ):
                            config = set_account_resin_config(config, account_name, {"notified_critical": True})
                            changed = True
                if current < threshold:
                    reset_flags = {}
                    if account_cfg.get("notified", False):
                        reset_flags["notified"] = False
                    if account_cfg.get("notified_critical", False):
                        reset_flags["notified_critical"] = False
                    if reset_flags:
                        config = set_account_resin_config(config, account_name, reset_flags)
                        changed = True

                sleep_seconds = _next_resin_check_seconds(
                    current=current,
                    maximum=maximum,
                    eta_seconds=eta_seconds,
                    threshold=threshold,
                    threshold_critical=threshold_critical,
                )
                next_due_at = time.time() + sleep_seconds
                resin_state_cache[account_name] = {
                    "cookie_key": cookie_key,
                    "current": current,
                    "threshold": threshold,
                    "next_check_at": next_due_at,
                }
                next_wake_at = next_due_at if next_wake_at is None else min(next_wake_at, next_due_at)

            if changed:
                save_resin_config(config)
            if not any_enabled:
                timeout = 1800
            elif next_wake_at is None:
                timeout = 1800
            else:
                timeout = max(int(next_wake_at - time.time()), 60)
            resin_wake_event.wait(timeout=timeout)
            force_refresh = resin_wake_event.is_set()
            resin_wake_event.clear()
        except Exception as exc:
            log.warning(f"[resin] Loop error: {exc}")
            resin_wake_event.wait(timeout=1800)
            force_refresh = resin_wake_event.is_set()
            resin_wake_event.clear()


def heartbeat_loop() -> None:
    interval_hours = 12
    log.info(f"Heartbeat thread ready ({interval_hours}h)")
    heartbeat_wake_event.wait(timeout=interval_hours * 3600)
    heartbeat_wake_event.clear()
    while True:
        try:
            extra = ""
            account_items = accounts.all_account_cookies()
            if account_items:
                parts = []
                multi = len(account_items) > 1
                for entry, cookies in account_items:
                    info = get_account_info_cached(cookies)
                    if not info:
                        continue
                    uid, nickname, region = info
                    payload = get_realtime_notes(cookies, uid, region)
                    if payload.get("retcode") != 0:
                        continue
                    data = payload["data"]
                    current = data.get("current_resin", 0)
                    maximum = data.get("max_resin", 200)
                    eta_seconds = int(data.get("resin_recovery_time", "0"))
                    fill = int(current / maximum * 10)
                    bar = "█" * fill + "░" * (10 - fill)
                    eta_text = (
                        t("status.eta_full", TELEGRAM_CHAT_ID)
                        if eta_seconds <= 0
                        else t(
                            "status.eta_at",
                            TELEGRAM_CHAT_ID,
                            time=(now_vn() + dt.timedelta(seconds=eta_seconds)).strftime("%H:%M %d/%m"),
                        )
                    )
                    checkin_data = get_checkin_info(cookies).get("data", {})
                    icon = t("status.checked", TELEGRAM_CHAT_ID) if checkin_data.get("is_sign") else t("status.not_checked", TELEGRAM_CHAT_ID)
                    display_name = fmt_display_name(nickname, entry.get("name", "?"), multi=multi)
                    header = f"\n✨ {display_name}" if multi else ""
                    parts.append(
                        header
                        + t("heartbeat.resin", TELEGRAM_CHAT_ID, bar=bar, cur=current, max=maximum, eta=eta_text)
                        + t("heartbeat.checkin", TELEGRAM_CHAT_ID, icon=icon, total=checkin_data.get("total_sign_day", "?"))
                    )
                extra = "".join(parts)

            thread_parts = []
            for name, label in (("CheckIn", "📅 CheckIn"), ("ResinMon", "⚗️ ResinMon"), ("Heartbeat", "💓 Heartbeat")):
                alive = any(thread.name == name and thread.is_alive() for thread in threading.enumerate())
                thread_parts.append(f"{label} {'✅' if alive else '❌'}")
            locks_text = ", ".join(
                name for name, lock in (("redeem", redeem_lock), ("checkin", manual_checkin_lock)) if lock.locked()
            ) or "rảnh"
            send_text(
                TELEGRAM_CHAT_ID,
                t(
                    "heartbeat.msg",
                    TELEGRAM_CHAT_ID,
                    host=socket.gethostname(),
                    time=now_vn().strftime("%H:%M:%S  %d/%m/%Y"),
                    uptime=uptime_str(),
                    extra=extra
                    + "\n━━━━━━━━━━━━━━━━━━━━\n"
                    + "🧵 "
                    + " | ".join(thread_parts)
                    + f"\n🔐 Locks: {locks_text}",
                ),
            )
        except Exception as exc:
            log.warning(f"[heartbeat] Loop error: {exc}")
        heartbeat_wake_event.wait(timeout=interval_hours * 3600)
        heartbeat_wake_event.clear()
