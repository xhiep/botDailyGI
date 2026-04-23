from __future__ import annotations

import hashlib
import json
import random
import string
import threading
import time
from urllib.parse import urlencode

from botdailygi.clients.http import HTTP, UA
from botdailygi.i18n import t
from botdailygi.runtime.logging import log, log_throttled
from botdailygi.runtime.state import ACT_ID, DS_SALT, INFO_API, SIGN_API


_account_cache: dict[str, tuple[tuple, float]] = {}
_account_cache_lock = threading.Lock()
_account_cache_ttl = 300
_api_cache: dict[tuple, tuple[dict, float]] = {}
_api_cache_lock = threading.Lock()
_api_cache_ttls = {
    "resin": 45,
    "checkin": 60,
    "stats": 300,
    "chars": 300,
    "abyss": 600,
}


def make_ds(body: str = "", query: str = "") -> str:
    timestamp = int(time.time())
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    digest = hashlib.md5(f"salt={DS_SALT}&t={timestamp}&r={rand}&b={body}&q={query}".encode()).hexdigest()
    return f"{timestamp},{rand},{digest}"


def cookie_str(cookies: dict) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookies.items())


def safe_json(response) -> dict:
    try:
        return response.json()
    except Exception:
        return {"retcode": -1, "message": f"Invalid JSON (HTTP {response.status_code})"}


def base_headers(cookie_value: str) -> dict:
    return {
        "User-Agent": UA,
        "Referer": "https://act.hoyolab.com",
        "Origin": "https://act.hoyolab.com",
        "x-rpc-app_version": "1.5.0",
        "x-rpc-client_type": "5",
        "x-rpc-language": "vi-vn",
        "Cookie": cookie_value,
    }


def invalidate_account_cache() -> None:
    with _account_cache_lock:
        _account_cache.clear()


def invalidate_api_cache(*, account_key: str | None = None) -> None:
    with _api_cache_lock:
        if account_key is None:
            _api_cache.clear()
            return
        stale_keys = [key for key in _api_cache if key and key[1] == account_key]
        for key in stale_keys:
            _api_cache.pop(key, None)


def _cookie_cache_key(cookies: dict) -> str:
    return str(cookies.get("ltuid_v2") or cookies.get("account_id_v2") or "_default")


def _read_api_cache(kind: str, account_key: str, extra: tuple) -> dict | None:
    ttl = _api_cache_ttls.get(kind, 0)
    if ttl <= 0:
        return None
    key = (kind, account_key, *extra)
    with _api_cache_lock:
        entry = _api_cache.get(key)
        if entry and (time.time() - entry[1]) < ttl:
            return dict(entry[0])
    return None


def _write_api_cache(kind: str, account_key: str, extra: tuple, payload: dict) -> None:
    ttl = _api_cache_ttls.get(kind, 0)
    if ttl <= 0 or payload.get("retcode", -1) != 0:
        return
    key = (kind, account_key, *extra)
    with _api_cache_lock:
        _api_cache[key] = (dict(payload), time.time())


def get_account_info(cookies: dict):
    url = "https://api-os-takumi.hoyoverse.com/binding/api/getUserGameRolesByLtoken"
    try:
        response = HTTP.get(
            url,
            headers={
                "User-Agent": UA,
                "Referer": "https://www.hoyolab.com/",
                "Cookie": cookie_str(cookies),
            },
            params={"game_biz": "hk4e_global"},
            timeout=10,
        )
        payload = response.json()
    except Exception:
        return None
    if payload.get("retcode") != 0:
        return None
    roles = payload.get("data", {}).get("list", [])
    if not roles:
        return None
    preferred = ("os_asia", "os_euro", "os_usa", "os_cht")
    role = next((item for region in preferred for item in roles if item.get("region") == region), roles[0])
    return role["game_uid"], role["nickname"], role["region"]


def get_account_info_cached(cookies: dict):
    cache_key = cookies.get("ltuid_v2") or cookies.get("account_id_v2") or "_default"
    with _account_cache_lock:
        entry = _account_cache.get(cache_key)
        if entry and (time.time() - entry[1]) < _account_cache_ttl:
            return entry[0]
    info = get_account_info(cookies)
    if info:
        with _account_cache_lock:
            _account_cache[cache_key] = (info, time.time())
    return info


def check_cookie_status(cookies: dict, chat_id=None) -> str:
    url = "https://bbs-api-os.hoyolab.com/community/user/wapi/getUserFullInfo"
    try:
        response = HTTP.get(
            url,
            headers={"User-Agent": UA, "Referer": "https://www.hoyolab.com", "Cookie": cookie_str(cookies)},
            timeout=10,
        )
        payload = response.json()
        if payload.get("retcode") == 0:
            return t("cookie.status_ok", chat_id, nickname=payload["data"]["user_info"]["nickname"])
        return t("cookie.status_err", chat_id, code=payload.get("retcode"), msg=payload.get("message", ""))
    except Exception as exc:
        return t("cookie.status_fail", chat_id, e=exc)


def _game_record_get(urls: list[str], *, cookies: dict, params: dict, log_label: str) -> dict:
    cookie_value = cookie_str(cookies)
    query = urlencode(params)
    headers = base_headers(cookie_value)
    headers["x-rpc-tool-version"] = "v5.0.0-ys"
    headers["x-rpc-page"] = "v5.0.0-ys"
    for url in urls:
        try:
            headers["DS"] = make_ds(body="", query=query)
            response = HTTP.get(url, headers=headers, params=params, timeout=15)
            payload = safe_json(response)
            retcode = payload.get("retcode", -99)
            message = payload.get("message", "")[:50]
            if response.status_code == 200 and retcode == 0:
                log.debug(f"[{log_label}] HTTP {response.status_code} rc={retcode} msg={message}")
            else:
                log_throttled(
                    30,
                    f"hoyolab.get.{log_label}.{url}.{response.status_code}.{retcode}",
                    300,
                    f"[{log_label}] HTTP {response.status_code} rc={retcode} msg={message}",
                )
            if response.status_code == 200 and retcode not in (-99, -1):
                return payload
        except Exception as exc:
            log_throttled(30, f"hoyolab.get.exc.{log_label}.{url}", 300, f"[{log_label}] {url}: {exc}")
    return {"retcode": -1, "message": f"{log_label} API unreachable"}


def _game_record_post(urls: list[str], *, cookies: dict, body: dict, log_label: str) -> dict:
    cookie_value = cookie_str(cookies)
    body_text = json.dumps(body, separators=(",", ":"), sort_keys=True)
    headers = base_headers(cookie_value)
    headers["Content-Type"] = "application/json"
    headers["x-rpc-tool-version"] = "v5.0.0-ys"
    headers["x-rpc-page"] = "v5.0.0-ys"
    for url in urls:
        try:
            headers["DS"] = make_ds(body=body_text, query="")
            response = HTTP.post(url, headers=headers, data=body_text, timeout=15)
            payload = safe_json(response)
            retcode = payload.get("retcode", -99)
            message = payload.get("message", "")[:50]
            if response.status_code == 200 and retcode == 0:
                log.debug(f"[{log_label}] HTTP {response.status_code} rc={retcode} msg={message}")
            else:
                log_throttled(
                    30,
                    f"hoyolab.post.{log_label}.{url}.{response.status_code}.{retcode}",
                    300,
                    f"[{log_label}] HTTP {response.status_code} rc={retcode} msg={message}",
                )
            if response.status_code == 200 and retcode not in (-99, -1):
                return payload
        except Exception as exc:
            log_throttled(30, f"hoyolab.post.exc.{log_label}.{url}", 300, f"[{log_label}] {url}: {exc}")
    return {"retcode": -1, "message": f"{log_label} API unreachable"}


def get_realtime_notes(cookies: dict, uid, region) -> dict:
    account_key = _cookie_cache_key(cookies)
    extra = (str(uid), str(region))
    cached = _read_api_cache("resin", account_key, extra)
    if cached:
        return cached
    payload = _game_record_get(
        [
            "https://bbs-api-os.hoyolab.com/game_record/genshin/api/dailyNote",
            "https://sg-public-api.hoyolab.com/game_record/genshin/api/dailyNote",
        ],
        cookies=cookies,
        params={"role_id": str(uid), "server": region},
        log_label="resin",
    )
    _write_api_cache("resin", account_key, extra, payload)
    return payload


def get_characters(cookies: dict, uid, region) -> dict:
    account_key = _cookie_cache_key(cookies)
    extra = (str(uid), str(region))
    cached = _read_api_cache("chars", account_key, extra)
    if cached:
        return cached
    payload = _game_record_post(
        [
            "https://bbs-api-os.hoyolab.com/game_record/genshin/api/character/list",
            "https://sg-public-api.hoyolab.com/game_record/genshin/api/character/list",
            "https://bbs-api-os.hoyolab.com/game_record/genshin/api/character",
        ],
        cookies=cookies,
        body={"role_id": str(uid), "server": region},
        log_label="chars",
    )
    _write_api_cache("chars", account_key, extra, payload)
    return payload


def get_genshin_stats(cookies: dict, uid, region) -> dict:
    account_key = _cookie_cache_key(cookies)
    extra = (str(uid), str(region))
    cached = _read_api_cache("stats", account_key, extra)
    if cached:
        return cached
    payload = _game_record_get(
        [
            "https://bbs-api-os.hoyolab.com/game_record/genshin/api/index",
            "https://sg-public-api.hoyolab.com/game_record/genshin/api/index",
        ],
        cookies=cookies,
        params={"role_id": str(uid), "server": region},
        log_label="stats",
    )
    _write_api_cache("stats", account_key, extra, payload)
    return payload


def get_spiral_abyss(cookies: dict, uid, region, schedule_type: int = 1) -> dict:
    account_key = _cookie_cache_key(cookies)
    extra = (str(uid), str(region), int(schedule_type))
    cached = _read_api_cache("abyss", account_key, extra)
    if cached:
        return cached
    payload = _game_record_get(
        [
            "https://bbs-api-os.hoyolab.com/game_record/genshin/api/spiralAbyss",
            "https://sg-public-api.hoyolab.com/game_record/genshin/api/spiralAbyss",
        ],
        cookies=cookies,
        params={"role_id": str(uid), "server": region, "schedule_type": str(schedule_type)},
        log_label="abyss",
    )
    _write_api_cache("abyss", account_key, extra, payload)
    return payload


def redeem_one(cookies: dict, uid, region, code: str, lang_code: str = "en-us") -> tuple[bool, str, int]:
    url = "https://sg-hk4e-api.hoyoverse.com/common/apicdkey/api/webExchangeCdkeyHyl"
    params = {
        "uid": str(uid),
        "region": region,
        "game_biz": "hk4e_global",
        "lang": lang_code,
        "cdkey": code,
    }
    try:
        response = HTTP.get(url, headers=base_headers(cookie_str(cookies)), params=params, timeout=15)
        payload = safe_json(response)
        retcode = payload.get("retcode", -1)
        message = payload.get("message", "unknown")
        return retcode == 0, message, retcode
    except Exception as exc:
        return False, str(exc), -1


def get_checkin_info(cookies: dict) -> dict:
    account_key = _cookie_cache_key(cookies)
    cached = _read_api_cache("checkin", account_key, ())
    if cached:
        return cached
    headers = {
        "User-Agent": UA,
        "Referer": "https://www.hoyolab.com",
        "Origin": "https://www.hoyolab.com",
        "Cookie": cookie_str(cookies),
    }
    response = HTTP.get(INFO_API, params={"act_id": ACT_ID}, headers=headers, timeout=15)
    payload = response.json()
    _write_api_cache("checkin", account_key, (), payload)
    return payload


def sign_checkin(cookies: dict) -> dict:
    account_key = _cookie_cache_key(cookies)
    headers = {
        "User-Agent": UA,
        "Referer": "https://www.hoyolab.com",
        "Origin": "https://www.hoyolab.com",
        "Cookie": cookie_str(cookies),
    }
    response = HTTP.post(SIGN_API, json={"act_id": ACT_ID}, headers=headers, timeout=15)
    payload = response.json()
    invalidate_api_cache(account_key=account_key)
    return payload
