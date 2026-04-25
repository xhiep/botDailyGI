from __future__ import annotations

import datetime as dt
from pathlib import Path

from botdailygi.clients.telegram import send_photo, send_text
from botdailygi.commands.common import ELEMENT_ICON, HINT_ABYSS, HINT_CHARS, HINT_STATS, hint_for
from botdailygi.commands.helpers import active_accounts, parallel_account_map
from botdailygi.i18n import t
from botdailygi.renderers.text import account_heading, display_name as fmt_display_name, divider, md_escape, meter_bar
from botdailygi.ui_constants import ICON_SUCCESS, ICON_INFO, ICON_DAMAGE, ICON_SHIELD, ICON_KILL, ICON_ENERGY
from botdailygi.runtime.state import VN_TZ
from botdailygi.services.hoyolab import (
    get_account_info_cached,
    get_characters,
    get_genshin_stats,
    get_spiral_abyss,
)
from botdailygi.services.progress import ProgressMessage
from botdailygi.ui_constants import DIVIDER_SHORT, DIVIDER_MEDIUM, DIVIDER_LONG


def cmd_uid(chat_id, _arg: str = "") -> None:
    items = active_accounts()
    if not items:
        send_text(chat_id, t("gen.no_login", chat_id))
        return
    lines = [t("uid.list_header", chat_id, count=len(items)), divider(DIVIDER_SHORT)]
    for index, (entry, cookies) in enumerate(items, 1):
        info = get_account_info_cached(cookies)
        name = entry.get("name", "?")
        if info:
            uid, nickname, region = info
            lines.append(
                f"{index}. {account_heading(name)}\n   {t('uid.info', chat_id, nickname=md_escape(nickname), uid=uid, region=md_escape(region))}"
            )
        else:
            lines.append(f"{index}. {account_heading(name)}\n   {t('acct.status_cookie_bad', chat_id)}")
    send_text(chat_id, "\n".join(lines))


def _stats_block(chat_id, account_name: str, cookies: dict, multi: bool) -> str:
    info = get_account_info_cached(cookies)
    if not info:
        prefix = account_heading(account_name) + "\n" if multi else ""
        return prefix + t("gen.no_uid", chat_id)
    uid, nickname, region = info
    payload = get_genshin_stats(cookies, uid, region)
    retcode = payload.get("retcode", -1)
    if retcode != 0:
        prefix = account_heading(account_name) + "\n" if multi else ""
        return prefix + t(
            "gen.api_error",
            chat_id,
            code=retcode,
            msg=payload.get("message", ""),
            hint=hint_for(retcode, chat_id, HINT_STATS),
        )
    data = payload.get("data", {})
    stats = data.get("stats", {})
    display_name = fmt_display_name(nickname, account_name, multi=multi)
    lines = [
        t("stats.title", chat_id, nickname=display_name),
        t("stats.uid_region", chat_id, uid=uid, region=region),
        divider(DIVIDER_SHORT),
        f"{t('stats.days', chat_id)} {stats.get('active_day_number', '?')}",
        f"{t('stats.achievement', chat_id)} {stats.get('achievement_number', '?')}",
        f"{t('stats.chars_owned', chat_id)} {stats.get('avatar_number', '?')}",
        f"{t('stats.waypoint', chat_id)} {stats.get('way_point_number', '?')}",
        f"{t('stats.domain', chat_id)} {stats.get('domain_number', '?')}",
        divider(DIVIDER_SHORT),
        t("stats.chests_hdr", chat_id),
        f"{t('stats.chest.luxurious', chat_id)} {stats.get('luxurious_chest_number', '?')}",
        f"{t('stats.chest.precious', chat_id)} {stats.get('precious_chest_number', '?')}",
        f"{t('stats.chest.exquisite', chat_id)} {stats.get('exquisite_chest_number', '?')}",
        f"{t('stats.chest.common', chat_id)} {stats.get('common_chest_number', '?')}",
        f"{t('stats.chest.remarkable', chat_id)} {stats.get('magic_chest_number', '?')}",
        divider(DIVIDER_SHORT),
        t("stats.oculi_hdr", chat_id),
        f"{t('stats.oculi.anemoculus', chat_id)} {stats.get('anemoculus_number', '?')}",
        f"{t('stats.oculi.geoculus', chat_id)} {stats.get('geoculus_number', '?')}",
        f"{t('stats.oculi.electroculus', chat_id)} {stats.get('electroculus_number', '?')}",
        f"{t('stats.oculi.dendroculus', chat_id)} {stats.get('dendroculus_number', '?')}",
        f"{t('stats.oculi.hydroculus', chat_id)} {stats.get('hydroculus_number', '?')}",
        f"{t('stats.oculi.pyroculus', chat_id)} {stats.get('pyroculus_number', '?')}",
    ]
    worlds = data.get("world_explorations", [])
    if worlds:
        lines.extend([divider(DIVIDER_LONG), t("stats.world_hdr", chat_id)])
        for world in sorted(worlds, key=lambda item: item.get("exploration_percentage", 0), reverse=True):
            percent = world.get("exploration_percentage", 0) / 10.0
            name = world.get("name", "?")[:16]
            bar = meter_bar(percent, 100)
            lines.append(f"  {name:<16} [{bar}] {percent:.1f}%")
    return "\n".join(lines)


def cmd_stats(chat_id, _arg: str = "") -> None:
    items = active_accounts()
    if not items:
        send_text(chat_id, t("gen.no_login", chat_id))
        return
    progress = ProgressMessage.start(chat_id, t("stats.fetching", chat_id), action="typing")
    multi = len(items) > 1
    blocks = parallel_account_map(items, lambda item: _stats_block(chat_id, item[0].get("name", ""), item[1], multi))
    progress.done("\n\n".join(blocks))


def _characters_block(chat_id, account_name: str, cookies: dict, multi: bool) -> str:
    info = get_account_info_cached(cookies)
    if not info:
        prefix = account_heading(account_name) + "\n" if multi else ""
        return prefix + t("gen.no_uid", chat_id)
    uid, nickname, region = info
    payload = get_characters(cookies, uid, region)
    retcode = payload.get("retcode", -1)
    if retcode != 0:
        prefix = account_heading(account_name) + "\n" if multi else ""
        hint = hint_for(retcode, chat_id, HINT_CHARS) or t("hint.all_toggles", chat_id)
        return prefix + t("gen.api_error", chat_id, code=retcode, msg=payload.get("message", ""), hint=hint)
    characters = payload.get("data", {}).get("list", [])
    if not characters:
        return t("chars.none", chat_id) + "\n" + t("hint.char_detail2", chat_id)
    characters.sort(key=lambda item: (item.get("rarity", 0), item.get("level", 0)), reverse=True)
    five_star = [item for item in characters if item.get("rarity", 0) == 5]
    four_star = [item for item in characters if item.get("rarity", 0) == 4]
    display_name = fmt_display_name(nickname, account_name, multi=multi)
    lines = [
        t("chars.title", chat_id, nickname=display_name),
        t("chars.summary", chat_id, uid=uid, five=len(five_star), four=len(four_star), total=len(characters)),
        divider(DIVIDER_SHORT),
    ]
    if five_star:
        lines.append(t("chars.five_hdr", chat_id, count=len(five_star)))
        for character in five_star:
            icon = ELEMENT_ICON.get(character.get("element", ""), "•")
            constellation = character.get("actived_constellation_num", 0)
            level = character.get("level", 0)
            fetter = character.get("fetter", 0)
            heart = ICON_SUCCESS if fetter == 10 else f"{ICON_INFO}{fetter}"
            lines.append(f"  {icon} {character['name']}  Lv.{level} C{constellation} {heart}")
    if four_star:
        lines.append("\n" + t("chars.four_hdr", chat_id, count=len(four_star)))
        for character in four_star:
            icon = ELEMENT_ICON.get(character.get("element", ""), "•")
            constellation = character.get("actived_constellation_num", 0)
            level = character.get("level", 0)
            lines.append(f"  {icon} {character['name']}  Lv.{level} C{constellation}{' ' + ICON_SUCCESS if constellation == 6 else ''}")
    element_count: dict[str, int] = {}
    element_count_5: dict[str, int] = {}
    for character in characters:
        element = character.get("element", "")
        element_name = t(f"elem.{element}", chat_id) if element else "?"
        element_count[element_name] = element_count.get(element_name, 0) + 1
        if character.get("rarity", 0) == 5:
            element_count_5[element_name] = element_count_5.get(element_name, 0) + 1

    def _bar(data: dict[str, int]) -> str:
        return "  ".join(
            f"{icon}×{data[element_name]}"
            for element, icon in ELEMENT_ICON.items()
            for element_name in [t(f"elem.{element}", chat_id)]
            if data.get(element_name, 0) > 0
        )

    lines.extend(
        [
            divider(DIVIDER_SHORT),
            t("chars.total_bar", chat_id, bar=_bar(element_count)),
            t("chars.five_bar", chat_id, bar=_bar(element_count_5)),
        ]
    )
    return "\n".join(lines)


def cmd_characters(chat_id, _arg: str = "") -> None:
    items = active_accounts()
    if not items:
        send_text(chat_id, t("gen.no_login", chat_id))
        return
    progress = ProgressMessage.start(chat_id, t("chars.fetching", chat_id), action="typing")
    multi = len(items) > 1
    blocks = parallel_account_map(items, lambda item: _characters_block(chat_id, item[0].get("name", ""), item[1], multi))
    progress.done("\n\n".join(blocks))


def _char_name(item: dict, live_names: dict[int, str]) -> str:
    from botdailygi.renderers.abyss import AVATAR_NAMES

    name = (item.get("name") or "").strip()
    if name:
        return name
    avatar_id = item.get("avatar_id") or item.get("id")
    if not avatar_id:
        return "?"
    avatar_id = int(avatar_id)
    return live_names.get(avatar_id) or AVATAR_NAMES.get(avatar_id) or f"?#{avatar_id % 10000}"


def _abyss_block(chat_id, account_name: str, cookies: dict, multi: bool, schedule_type: int, label: str) -> tuple[str, Path | None]:
    from botdailygi.renderers.abyss import render_abyss_image

    info = get_account_info_cached(cookies)
    if not info:
        prefix = account_heading(account_name) + "\n" if multi else ""
        return prefix + t("gen.no_uid", chat_id), None
    uid, nickname, region = info
    payload = get_spiral_abyss(cookies, uid, region, schedule_type)
    retcode = payload.get("retcode", -1)
    if retcode != 0:
        prefix = account_heading(account_name) + "\n" if multi else ""
        return (
            prefix + t("gen.api_error", chat_id, code=retcode, msg=payload.get("message", ""), hint=hint_for(retcode, chat_id, HINT_ABYSS)),
            None,
        )
    abyss = payload.get("data", {})
    if not abyss.get("is_unlock"):
        return t("abyss.locked", chat_id), None
    display_name = fmt_display_name(nickname, account_name, multi=multi)
    live_names: dict[int, str] = {}
    try:
        chars_payload = get_characters(cookies, uid, region)
        if chars_payload.get("retcode") == 0:
            for character in chars_payload.get("data", {}).get("list", []):
                avatar_id = character.get("id")
                char_name = (character.get("name") or "").strip()
                if avatar_id and char_name:
                    live_names[int(avatar_id)] = char_name
    except Exception:
        pass
    for rank_key in ("damage_rank", "take_damage_rank", "kill_rank", "energy_skill_rank", "reveal_rank", "defeat_rank"):
        for item in abyss.get(rank_key, []):
            avatar_id = item.get("avatar_id") or item.get("id")
            name = (item.get("name") or "").strip()
            if avatar_id and name and int(avatar_id) not in live_names:
                live_names[int(avatar_id)] = name

    image_path = render_abyss_image(abyss, display_name, label, live_names)
    caption = t(
        "abyss.caption",
        chat_id,
        label=label,
        nickname=display_name,
        stars=abyss.get("total_star", 0),
        floor=abyss.get("max_floor", "?"),
        battles=abyss.get("total_battle_times") or abyss.get("total_battles", 0),
    )
    if image_path:
        return caption, Path(image_path)

    total_star = abyss.get("total_star", 0)
    max_floor = abyss.get("max_floor", "?")
    total_battles = abyss.get("total_battle_times") or abyss.get("total_battles", 0)
    total_wins = abyss.get("total_win_times") or abyss.get("total_wins", 0)
    lines = [
        t("abyss.text_header", chat_id, label=label, nickname=display_name),
        t(
            "abyss.text_period",
            chat_id,
            start=dt.datetime.fromtimestamp(int(abyss.get("start_time", 0)), VN_TZ).strftime("%d/%m"),
            end=dt.datetime.fromtimestamp(int(abyss.get("end_time", 0)), VN_TZ).strftime("%d/%m/%Y"),
        ),
            divider(DIVIDER_SHORT),
        t("abyss.stats", chat_id, stars=total_star, floor=max_floor, battles=total_battles, wins=total_wins),
        divider(DIVIDER_SHORT),
    ]
    for key, icon in (("damage_rank", ICON_DAMAGE), ("take_damage_rank", ICON_SHIELD), ("kill_rank", ICON_KILL), ("energy_skill_rank", ICON_ENERGY)):
        top = (abyss.get(key) or [None])[0]
        if top:
            lines.append(f"{icon} {top.get('value', 0):,}  ← {_char_name(top, live_names)}")
    reveal = abyss.get("reveal_rank", [])
    if reveal:
        lines.append(divider(DIVIDER_LONG))
        names = [f"{_char_name(item, live_names)} ×{item.get('value', 0)}" for item in reveal[:5]]
        lines.append("• " + "  |  ".join(names[:3]))
        if len(names) > 3:
            lines.append("   " + "  |  ".join(names[3:]))
    footer_key = "abyss.footer_cur" if schedule_type == 1 else "abyss.footer_prev"
    lines.extend([divider(DIVIDER_LONG), t(footer_key, chat_id)])
    return "\n".join(lines), None


def cmd_abyss(chat_id, arg: str = "") -> None:
    items = active_accounts()
    if not items:
        send_text(chat_id, t("gen.no_login", chat_id))
        return
    schedule_type = 2 if (arg or "").strip() in {"2", "prev", "previous"} else 1
    label = t("abyss.label_prev", chat_id) if schedule_type == 2 else t("abyss.label_cur", chat_id)
    progress = ProgressMessage.start(chat_id, t("abyss.fetching", chat_id, label=label), action="upload_photo")
    multi = len(items) > 1
    blocks = []
    images: list[tuple[str, Path]] = []
    results = parallel_account_map(
        items,
        lambda item: _abyss_block(chat_id, item[0].get("name", ""), item[1], multi, schedule_type, label),
        max_workers=3,
    )
    for text, image_path in results:
        if image_path:
            images.append((text, image_path))
        else:
            blocks.append(text)
    if images and not blocks:
        progress.done(t("abyss.ready_img", chat_id, count=len(images)), action="upload_photo")
    else:
        progress.done("\n\n".join(blocks) if blocks else t("abyss.ready_img", chat_id, count=len(images)))
    for caption, image_path in images:
        send_photo(chat_id, image_path, caption=caption)
        image_path.unlink(missing_ok=True)
