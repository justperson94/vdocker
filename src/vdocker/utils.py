from __future__ import annotations

from datetime import datetime, timezone

from rich.text import Text


def format_size(size_bytes: int | None) -> str:
    if size_bytes is None or size_bytes < 0:
        return "N/A"
    if size_bytes == 0:
        return "0B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    if i == 0:
        return f"{int(size)}B"
    return f"{size:.1f}{units[i]}"


def format_created(created: str) -> str:
    if not created:
        return ""
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s ago"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m ago"
        elif total_seconds < 86400:
            return f"{total_seconds // 3600}h ago"
        else:
            return f"{total_seconds // 86400}d ago"
    except (ValueError, TypeError):
        return ""


def format_uptime(started_at: str | None, status: str) -> str:
    if status != "running" or not started_at:
        return status.capitalize()

    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - start
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"Up {total_seconds}s"
        elif total_seconds < 3600:
            return f"Up {total_seconds // 60}m"
        elif total_seconds < 86400:
            return f"Up {total_seconds // 3600}h"
        else:
            return f"Up {total_seconds // 86400}d"
    except (ValueError, TypeError):
        return status.capitalize()


_EXIT_CODE_HINTS = {
    0: "success",
    1: "application error",
    125: "docker: container failed to run",
    126: "command found but not executable",
    127: "command not found",
    255: "exit status out of range",
}

_SIGNAL_HINTS = {
    "SIGKILL": "killed by docker kill, OOM, or kill -9",
    "SIGTERM": "terminated by docker stop",
    "SIGSEGV": "segmentation fault",
    "SIGINT": "interrupted (Ctrl+C)",
    "SIGABRT": "aborted",
}


def describe_exit_code(code: int, oom_killed: bool = False) -> str:
    """Human-readable meaning of a container exit code."""
    if oom_killed:
        return "SIGKILL — killed by the OOM killer (out of memory)"
    if code in _EXIT_CODE_HINTS:
        return _EXIT_CODE_HINTS[code]
    if 128 < code < 165:
        signum = code - 128
        try:
            import signal
            name = signal.Signals(signum).name
        except ValueError:
            return f"fatal signal {signum}"
        hint = _SIGNAL_HINTS.get(name)
        return f"{name} — {hint}" if hint else name
    return ""


STATUS_STYLES = {
    "running": "green",
    "exited": "red",
    "paused": "yellow",
    "created": "dim",
    "restarting": "yellow",
}


def status_style(status: str) -> str:
    return STATUS_STYLES.get(status, "white")


def status_text(status: str, started_at: str | None) -> Text:
    label = format_uptime(started_at, status)
    style = status_style(status)
    return Text(label, style=style)
