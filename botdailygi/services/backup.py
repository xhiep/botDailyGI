from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from botdailygi.runtime.paths import (
    ACCOUNTS_FILE,
    CODES_BLACKLIST_FILE,
    HISTORY_FILE,
    RESIN_NOTIFY_FILE,
    USER_LANGS_FILE,
    USER_SETTINGS_FILE,
    COOKIES_DIR,
)


BACKUP_FILES = (
    ACCOUNTS_FILE,
    RESIN_NOTIFY_FILE,
    USER_LANGS_FILE,
    USER_SETTINGS_FILE,
    CODES_BLACKLIST_FILE,
    HISTORY_FILE,
)


def build_backup_archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in BACKUP_FILES:
            if path.exists():
                zf.write(path, arcname=path.name)
        if COOKIES_DIR.exists():
            for file_path in COOKIES_DIR.glob("*.json"):
                zf.write(file_path, arcname=f"cookies/{file_path.name}")
        zf.writestr(
            "backup_manifest.json",
            json.dumps(
                {
                    "files": [path.name for path in BACKUP_FILES if path.exists()],
                    "cookies": [file.name for file in COOKIES_DIR.glob("*.json")] if COOKIES_DIR.exists() else [],
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    return buffer.getvalue()


def _safe_extract_path(base_dir: Path, member_name: str) -> Path | None:
    base = base_dir.resolve()
    target = (base / member_name).resolve()
    if base == target or base in target.parents:
        return target
    return None


def restore_backup_archive(archive_path: Path) -> list[str]:
    extracted: list[str] = []
    base_dir = ACCOUNTS_FILE.parent
    with zipfile.ZipFile(archive_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            target = _safe_extract_path(base_dir, member.filename)
            if not target:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as source, target.open("wb") as dest:
                dest.write(source.read())
            extracted.append(member.filename)
    return extracted
