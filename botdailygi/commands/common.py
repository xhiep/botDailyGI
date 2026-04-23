from __future__ import annotations

from botdailygi.i18n import t


HINT_RESIN = {
    10001: "hint.cookie_expired",
    -100: "hint.cookie_expired",
    10307: "hint.realtime_notes",
    -10001: "hint.realtime_notes",
    10102: "hint.set_public",
}
HINT_STATS = {
    10001: "hint.cookie_expired",
    -100: "hint.cookie_expired",
    10102: "hint.set_public",
    10307: "hint.view_profile",
}
HINT_CHARS = {
    10001: "hint.cookie_expired",
    -100: "hint.cookie_expired",
    10307: "hint.char_detail",
    10102: "hint.set_public",
    1034: "hint.captcha",
}
HINT_ABYSS = {
    10001: "hint.cookie_expired",
    -100: "hint.cookie_expired",
    10102: "hint.set_public",
}

ELEMENT_ICON = {
    "Pyro": "🔥",
    "Hydro": "💧",
    "Anemo": "🌬️",
    "Electro": "⚡",
    "Dendro": "🌿",
    "Cryo": "❄️",
    "Geo": "🪨",
}


def hint_for(retcode, chat_id, mapping: dict) -> str:
    key = mapping.get(retcode) or mapping.get(int(retcode) if isinstance(retcode, str) and retcode.lstrip("-").isdigit() else retcode)
    return t(key, chat_id) if key else ""
