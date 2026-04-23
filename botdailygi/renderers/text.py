from __future__ import annotations


def divider(width: int = 20, *, char: str = "─") -> str:
    return char * max(width, 1)


def meter_bar(current: int | float, maximum: int | float, *, width: int = 10, filled: str = "█", empty: str = "░") -> str:
    if maximum <= 0:
        return empty * width
    ratio = max(0.0, min(float(current) / float(maximum), 1.0))
    fill = min(width, max(0, int(ratio * width)))
    return filled * fill + empty * (width - fill)


def md_escape(value) -> str:
    text = "" if value is None else str(value)
    for old, new in (
        ("\\", "\\\\"),
        ("`", "\\`"),
        ("*", "\\*"),
        ("_", "\\_"),
        ("[", "\\["),
    ):
        text = text.replace(old, new)
    return text


def md_code(value) -> str:
    text = "" if value is None else str(value).replace("`", "'")
    return f"`{text}`"


def account_tag(name: str) -> str:
    return f"({md_code(name)})"


def account_heading(name: str, *, icon: str = "👤") -> str:
    return f"{icon} {md_code(name)}"


def display_name(nickname: str, account_name: str | None = None, *, multi: bool = False) -> str:
    nick = md_escape(nickname)
    if multi and account_name:
        return f"{nick} {account_tag(account_name)}"
    return nick
