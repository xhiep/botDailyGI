from __future__ import annotations

import sys

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


IS_WINDOWS = sys.platform == "win32"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    if IS_WINDOWS
    else "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

retry = Retry(
    total=3,
    backoff_factor=0.2,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=["GET", "POST"],
)
adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=retry)

HTTP = requests.Session()
HTTP.headers.update({"User-Agent": UA})
HTTP.mount("https://", adapter)
HTTP.mount("http://", adapter)
