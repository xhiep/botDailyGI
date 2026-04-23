from __future__ import annotations

import json
import re
from threading import Lock

from botdailygi.i18n.catalog import STRINGS, VI_TO_EN
from botdailygi.runtime.logging import log
from botdailygi.runtime.paths import USER_LANGS_FILE
from botdailygi.runtime.state import atomic_write_json


_user_langs: dict[str, str] = {}
_user_langs_lock = Lock()
_sorted_vi_keys = sorted(VI_TO_EN, key=len, reverse=True)
_translate_re = (
    re.compile("|".join(re.escape(key) for key in _sorted_vi_keys))
    if _sorted_vi_keys
    else re.compile(r"(?!)")
)


def load_user_langs() -> None:
    global _user_langs
    if not USER_LANGS_FILE.exists():
        return
    try:
        data = json.loads(USER_LANGS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning(f"[lang] Cannot read {USER_LANGS_FILE.name}: {exc}")
        return
    if isinstance(data, dict):
        with _user_langs_lock:
            _user_langs = {str(k): str(v) for k, v in data.items()}


def get_lang(chat_id) -> str:
    with _user_langs_lock:
        return _user_langs.get(str(chat_id), "vi")


def set_lang(chat_id, language: str) -> None:
    with _user_langs_lock:
        _user_langs[str(chat_id)] = language
        snapshot = dict(_user_langs)
    try:
        atomic_write_json(USER_LANGS_FILE, snapshot, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.warning(f"[lang] Cannot write {USER_LANGS_FILE.name}: {exc}")


def t(key: str, chat_id=None, lang: str | None = None, **kwargs) -> str:
    language = lang or (get_lang(chat_id) if chat_id is not None else "vi")
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(language) or entry.get("vi") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return text
    return text


def translate_str(text: str, language: str) -> str:
    if language == "vi" or not text:
        return text
    return _translate_re.sub(lambda match: VI_TO_EN[match.group()], text)
