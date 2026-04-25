from __future__ import annotations

import datetime as dt

from botdailygi.clients.telegram import send_text
from botdailygi.config import STREAM_HOUR, STREAM_MINUTE
from botdailygi.i18n import t
from botdailygi.renderers.text import divider
from botdailygi.runtime.state import VN_TZ, now_vn
from botdailygi.services.schedule import VERSIONS_FALLBACK, get_current_version, get_versions
from botdailygi.ui_constants import DIVIDER_LONG


def cmd_livestream(chat_id, _arg: str = "") -> None:
    now = now_vn()
    try:
        versions = get_versions()
    except Exception:
        versions = VERSIONS_FALLBACK
    current_version = get_current_version()
    lines = [
        t("live.title", chat_id),
        t("live.cur_ver", chat_id, ver=current_version),
        divider(DIVIDER_LONG),
    ]
    found_any = False
    for version, patch_date in versions:
        try:
            patch_day = dt.date.fromisoformat(patch_date)
            stream_day = patch_day - dt.timedelta(days=12)
            stream_time = dt.datetime(stream_day.year, stream_day.month, stream_day.day, STREAM_HOUR, STREAM_MINUTE, tzinfo=VN_TZ)
            patch_time = dt.datetime(patch_day.year, patch_day.month, patch_day.day, 11, 0, tzinfo=VN_TZ)
            diff_live = (stream_time.date() - now.date()).days
            diff_patch = (patch_time.date() - now.date()).days
            if diff_patch < -1:
                continue
            found_any = True
            if diff_live < 0:
                live_text = t("live.stream_passed", chat_id, time=stream_time.strftime("%H:%M %d/%m"))
                live_icon = "✅"
            elif diff_live == 0:
                live_text = t("live.stream_today", chat_id, time=stream_time.strftime("%H:%M"))
                live_icon = "🔴"
            else:
                live_text = t("live.stream_future", chat_id, time=stream_time.strftime("%H:%M  %d/%m/%Y"), days=diff_live)
                live_icon = "📺"
            if diff_patch < 0:
                patch_text = t("live.patch_running", chat_id, time=patch_time.strftime("%d/%m/%Y"))
                patch_icon = "🟢"
            elif diff_patch == 0:
                patch_text = t("live.patch_today", chat_id, time=patch_time.strftime("%d/%m/%Y"))
                patch_icon = "🔥"
            else:
                patch_text = t("live.patch_future", chat_id, time=patch_time.strftime("%d/%m/%Y"), days=diff_patch)
                patch_icon = "🗓"
            lines.extend(
                [
                    t("live.ver_header", chat_id, ver=version),
                    f"  {live_icon} {t('live.stream_lbl', chat_id)} {live_text}",
                    f"  {patch_icon} {t('live.patch_lbl', chat_id)} {patch_text}",
                    "",
                ]
            )
        except Exception:
            continue
    if not found_any:
        lines.append(t("live.no_schedule", chat_id))
    lines.extend(
        [
            divider(DIVIDER_LONG),
            t("live.default_time", chat_id, h=STREAM_HOUR, m=STREAM_MINUTE),
        ]
    )
    send_text(chat_id, "\n".join(lines))
