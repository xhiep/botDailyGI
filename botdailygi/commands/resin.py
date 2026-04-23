from __future__ import annotations

import datetime as dt

from botdailygi.clients.telegram import send_text
from botdailygi.commands.common import HINT_RESIN, hint_for
from botdailygi.commands.helpers import active_accounts, parallel_account_map
from botdailygi.i18n import t
from botdailygi.renderers.text import account_heading, display_name as fmt_display_name, md_code, meter_bar
from botdailygi.runtime.state import check_change_cooldown, mark_change, now_vn, resin_wake_event
from botdailygi.services.hoyolab import get_account_info_cached, get_realtime_notes
from botdailygi.services.progress import ProgressMessage
from botdailygi.services.resin_config import (
    get_account_resin_config,
    load_resin_config,
    save_resin_config,
    set_account_resin_config,
)


def _resin_block(chat_id, account_name: str, cookies: dict, multi: bool) -> str:
    info = get_account_info_cached(cookies)
    if not info:
        prefix = account_heading(account_name) + "\n" if multi else ""
        return prefix + t("gen.no_uid", chat_id)
    uid, nickname, region = info
    payload = get_realtime_notes(cookies, uid, region)
    retcode = payload.get("retcode", -1)
    if retcode != 0:
        prefix = account_heading(account_name) + "\n" if multi else ""
        return prefix + t(
            "gen.api_error",
            chat_id,
            code=retcode,
            msg=payload.get("message", "unknown"),
            hint=hint_for(retcode, chat_id, HINT_RESIN),
        )

    data = payload["data"]
    current = data.get("current_resin", 0)
    maximum = data.get("max_resin", 200)
    eta_seconds = int(data.get("resin_recovery_time", "0"))
    bar = meter_bar(current, maximum, width=10)
    if eta_seconds <= 0:
        full_in = t("resin.full_done", chat_id)
        full_at = ""
    else:
        full_time = now_vn() + dt.timedelta(seconds=eta_seconds)
        hours, minutes = divmod(eta_seconds // 60, 60)
        duration = t("fmt.duration", chat_id, hh=hours, mm=minutes)
        full_in = t("resin.full_in", chat_id, hhmm=duration)
        full_at = f"\n{t('resin.full_at', chat_id, time=full_time.strftime('%H:%M  %d/%m/%Y'))}"
    expeditions = data.get("expeditions", [])
    expedition_done = sum(1 for expedition in expeditions if expedition.get("status") == "Finished")
    daily_done = data.get("finished_task_num", 0)
    daily_total = data.get("total_task_num", 4)
    reward = t("resin.claimed", chat_id) if data.get("is_extra_task_reward_received", False) else t("resin.unclaimed", chat_id)
    daily_icon = "✅" if daily_done >= daily_total else "❌"
    title_name = fmt_display_name(nickname, account_name, multi=multi)
    lines = [
        t("resin.title", chat_id, nickname=title_name),
        f"   [{bar}] {current}/{maximum}",
        full_in + full_at,
        t("resin.expedition", chat_id, done=expedition_done, total=len(expeditions)),
        t("resin.daily", chat_id, done=daily_done, total=daily_total, icon=daily_icon),
        t("resin.reward", chat_id, status=reward),
    ]
    transformer = data.get("transformer", {})
    if transformer.get("obtained"):
        key = "resin.transformer_rdy" if transformer.get("recovery_time", {}).get("reached") else "resin.transformer_wait"
        lines.append(t(key, chat_id))
    return "\n".join(lines)


def cmd_resin(chat_id, _arg: str = "") -> None:
    items = active_accounts()
    if not items:
        send_text(chat_id, t("gen.no_login", chat_id))
        return
    progress = ProgressMessage.start(chat_id, t("resin.fetching", chat_id), action="typing")
    multi = len(items) > 1
    blocks = parallel_account_map(items, lambda item: _resin_block(chat_id, item[0].get("name", ""), item[1], multi))
    progress.done("\n\n".join(blocks))


def cmd_resinnotify(chat_id, arg: str = "") -> None:
    config = load_resin_config()
    items = active_accounts()
    raw = (arg or "").strip()
    raw_lower = raw.lower()
    tokens = raw.split()

    def _status_text() -> None:
        if not items:
            send_text(chat_id, t("gen.no_login", chat_id))
            return
        if len(items) == 1:
            entry = items[0][0]
            account_cfg = get_account_resin_config(config, entry.get("name", ""))
            state = t("resin.notify.state_on", chat_id) if account_cfg.get("enabled") else t("resin.notify.state_off", chat_id)
            send_text(chat_id, t("resin.notify.status", chat_id, state=state, threshold=account_cfg.get("threshold", 200)))
            return
        lines = [t("resin.notify.multi_header", chat_id)]
        for entry, _cookies in items:
            account_name = entry.get("name", "?")
            account_cfg = get_account_resin_config(config, account_name)
            state = t("resin.notify.state_on", chat_id) if account_cfg.get("enabled") else t("resin.notify.state_off", chat_id)
            lines.append(
                t(
                    "resin.notify.multi_line",
                    chat_id,
                    name=md_code(account_name),
                    state=state,
                    threshold=account_cfg.get("threshold", 200),
                )
            )
        send_text(chat_id, "\n".join(lines))

    if not raw:
        _status_text()
        return

    if raw_lower in {"off", "0", "on"} or raw_lower.isdigit():
        wait = check_change_cooldown(chat_id)
        if wait > 0:
            send_text(chat_id, t("gen.cooldown", chat_id, sec=wait))
            return

    def _apply_for_account(account_name: str, action: str) -> bool:
        nonlocal config
        if action.isdigit():
            value = int(action)
            if not 1 <= value <= 200:
                send_text(chat_id, t("resin.notify.bad_val", chat_id))
                return False
            config = set_account_resin_config(
                config,
                account_name,
                {"threshold": value, "enabled": True, "notified": False, "notified_critical": False},
            )
            send_text(chat_id, t("resin.notify.account_set", chat_id, name=md_code(account_name), val=value))
            return True
        if action in {"off", "0"}:
            config = set_account_resin_config(
                config,
                account_name,
                {"enabled": False, "notified": False, "notified_critical": False},
            )
            send_text(chat_id, t("resin.notify.account_disabled", chat_id, name=md_code(account_name)))
            return True
        if action == "on":
            threshold = get_account_resin_config(config, account_name).get("threshold", 200)
            config = set_account_resin_config(
                config,
                account_name,
                {"enabled": True, "notified": False, "notified_critical": False},
            )
            send_text(chat_id, t("resin.notify.account_enabled", chat_id, name=md_code(account_name), threshold=threshold))
            return True
        return False

    if len(tokens) == 1 and len(items) <= 1:
        mark_change(chat_id)
        action = raw_lower
        if not items:
            send_text(chat_id, t("gen.no_login", chat_id))
            return
        account_name = items[0][0].get("name", "?")
        if _apply_for_account(account_name, action):
            save_resin_config(config)
            resin_wake_event.set()
        return

    if len(tokens) == 1:
        _status_text()
        send_text(chat_id, t("resin.notify.usage_multi", chat_id))
        return

    target_token = tokens[0]
    action = tokens[1].lower()
    wait = check_change_cooldown(chat_id)
    if wait > 0:
        send_text(chat_id, t("gen.cooldown", chat_id, sec=wait))
        return
    mark_change(chat_id)

    if target_token.lower() == "all":
        changed = False
        for entry, _cookies in items:
            changed = _apply_for_account(entry.get("name", "?"), action) or changed
        if changed:
            save_resin_config(config)
            resin_wake_event.set()
        return

    target_pair = next(
        ((entry, cookies) for entry, cookies in items if entry.get("name", "").lower() == target_token.lower()),
        None,
    )
    if not target_pair:
        send_text(chat_id, t("resin.notify.account_missing", chat_id, name=md_code(target_token)))
        return
    target_entry, target_cookies = target_pair
    if _apply_for_account(target_entry.get("name", "?"), action):
        save_resin_config(config)
        resin_wake_event.set()
        if action.isdigit():
            value = int(action)
            info = get_account_info_cached(target_cookies)
            if info:
                uid, _nickname, region = info
                data = get_realtime_notes(target_cookies, uid, region)
                if data.get("retcode") == 0:
                    current = data["data"].get("current_resin", 0)
                    maximum = data["data"].get("max_resin", 200)
                    if current >= value:
                        send_text(chat_id, t("resin.notify.reached", chat_id, val=value, max=maximum, cur=current))
                        return
                    seconds = (value - current) * 480
                    eta = now_vn() + dt.timedelta(seconds=seconds)
                    hours, minutes = divmod(seconds // 60, 60)
                    send_text(
                        chat_id,
                        t(
                            "resin.notify.pending",
                            chat_id,
                            val=value,
                            max=maximum,
                            cur=current,
                            need=value - current,
                            hhmm=t("fmt.duration", chat_id, hh=hours, mm=minutes),
                            eta=eta.strftime("%H:%M  %d/%m/%Y"),
                        ),
                    )
        return

    if raw_lower.isdigit():
        value = int(raw_lower)
        if not 1 <= value <= 200:
            send_text(chat_id, t("resin.notify.bad_val", chat_id))
            return
        return
    send_text(chat_id, t("resin.notify.usage_multi", chat_id))
