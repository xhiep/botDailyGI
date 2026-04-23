from __future__ import annotations


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
