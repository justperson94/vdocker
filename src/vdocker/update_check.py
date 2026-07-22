from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from rich.console import Console
from rich.text import Text

from . import __version__


CHECK_INTERVAL = 24 * 60 * 60
REQUEST_TIMEOUT = 2.0
LATEST_RELEASE_URL = (
    "https://api.github.com/repos/justperson94/vdocker/releases/latest"
)
UPGRADE_COMMAND = (
    "curl -fsSL "
    "https://raw.githubusercontent.com/justperson94/vdocker/main/install.sh | sh"
)


def _cache_path() -> Path:
    if cache_home := os.environ.get("XDG_CACHE_HOME"):
        return Path(cache_home) / "vdocker" / "update-check.json"
    if os.name == "nt" and (local_app_data := os.environ.get("LOCALAPPDATA")):
        return Path(local_app_data) / "vdocker" / "update-check.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "vdocker" / "update-check.json"
    return Path.home() / ".cache" / "vdocker" / "update-check.json"


def _recently_checked(cache_file: Path, now: float) -> bool:
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return now - float(data["checked_at"]) < CHECK_INTERVAL
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False


def _write_cache(cache_file: Path, now: float, latest: str | None) -> None:
    temporary = cache_file.with_name(f".{cache_file.name}.{os.getpid()}.tmp")
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps({"checked_at": now, "latest": latest}) + "\n",
            encoding="utf-8",
        )
        temporary.replace(cache_file)
    except OSError:
        pass
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _fetch_latest_version() -> str:
    request = Request(
        LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"vdocker/{__version__}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        data: Any = json.load(response)
    tag = data.get("tag_name") if isinstance(data, dict) else None
    if not isinstance(tag, str):
        raise ValueError("latest release has no tag_name")
    return tag


def _release_parts(version: str) -> tuple[int, ...] | None:
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _is_newer(latest: str, current: str) -> bool:
    latest_parts = _release_parts(latest)
    current_parts = _release_parts(current)
    if latest_parts is None or current_parts is None:
        return False
    width = max(len(latest_parts), len(current_parts))
    return latest_parts + (0,) * (width - len(latest_parts)) > (
        current_parts + (0,) * (width - len(current_parts))
    )


def check_for_update(
    current: str = __version__,
    *,
    cache_file: Path | None = None,
    now: float | None = None,
) -> str | None:
    """Return a newer release once per interval; all failures are silent."""
    if _release_parts(current) is None:
        return None

    checked_at = time.time() if now is None else now
    path = _cache_path() if cache_file is None else cache_file
    if _recently_checked(path, checked_at):
        return None

    latest = None
    try:
        latest = _fetch_latest_version()
    except Exception:
        pass
    _write_cache(path, checked_at, latest)

    if latest is not None and _is_newer(latest, current):
        return latest.removeprefix("v")
    return None


def notify_if_update_available(console: Console) -> None:
    if os.environ.get("VDOCKER_NO_UPDATE_CHECK", "").lower() in {
        "1", "true", "yes", "on",
    }:
        return
    if os.environ.get("_VDOCKER_COMPLETE"):
        return

    latest = check_for_update()
    if latest is None:
        return

    console.print()
    console.print(
        "[bold cyan]⬆ Update available:[/bold cyan] "
        f"vdocker [dim]{__version__}[/dim] → [bold green]{latest}[/bold green]"
    )
    console.print("  [dim]Upgrade with:[/dim]")
    command = Text("  ")
    command.append(UPGRADE_COMMAND, style="yellow")
    console.print(command, soft_wrap=True)
