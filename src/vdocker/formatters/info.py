from __future__ import annotations

from rich.console import Console
from rich.text import Text

from ..utils import (
    describe_exit_code,
    format_created,
    format_size,
    format_uptime,
    status_style,
)
from .base import BaseFormatter

_SENSITIVE_ENV = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL", "AUTH")


def mask_env(env: list[str]) -> list[tuple[str, str]]:
    """Split KEY=VALUE pairs, masking values of sensitive-looking keys."""
    pairs = []
    for item in env:
        key, sep, value = item.partition("=")
        if sep and any(s in key.upper() for s in _SENSITIVE_ENV):
            value = "********"
        pairs.append((key, value))
    return pairs


class InfoFormatter(BaseFormatter):
    def __init__(self, console: Console, json_output: bool = False,
                 show_env: bool = False):
        super().__init__(console, json_output)
        self.show_env = show_env

    def _rows(self, rows: list[tuple[str, Text | str]]) -> None:
        if not rows:
            return
        width = max(max(len(label) for label, _ in rows), 10)
        for label, value in rows:
            line = Text()
            line.append(f"  {label:<{width}}  ", style="dim")
            if isinstance(value, Text):
                line.append_text(value)
            else:
                line.append(str(value))
            self.console.print(line)

    def _section(self, title: str) -> None:
        self.console.print()
        self.console.print(Text(f"  {title}", style="bold"))

    def render_rich(self, d: dict) -> None:
        con = self.console
        running = d["status"] == "running"
        health = d["health"]

        # --- Header ---
        header = Text()
        header.append(d["name"], style=f"bold {status_style(d['status'])}")
        header.append("  ")
        if running:
            label = format_uptime(d["started_at"], d["status"])
            if health:
                label += f" ({health['status']})"
            style = "red" if health and health["status"] == "unhealthy" else "green"
            header.append(label, style=style)
        else:
            stopped = d["status"] in ("exited", "dead", "restarting")
            label = d["status"].capitalize()
            if stopped and d["exit_code"] is not None:
                label += f" ({d['exit_code']})"
                ago = format_created(d["finished_at"] or "")
                if ago:
                    label += f"  {ago}"
            header.append(label, style=status_style(d["status"]))
        con.print(header)
        con.print()

        # --- Identity ---
        rows: list[tuple[str, Text | str]] = [
            ("ID", d["id"][:12]),
            ("Image", d["image"]),
        ]
        if d["command"]:
            cmd = d["command"].replace("\n", " ").strip()
            if len(cmd) > 70:
                cmd = cmd[:70] + "…"
            rows.append(("Command", f'"{cmd}"'))
        rows.append(("Created", format_created(d["created"])))
        if d["project"]:
            proj = Text(d["project"], style="cyan")
            if d["working_dir"]:
                proj.append(f"  {d['working_dir']}", style="dim")
            rows.append(("Project", proj))
        if d["service"]:
            rows.append(("Service", d["service"]))
        self._rows(rows)

        # --- State ---
        self._section("State")
        rows = []
        if running or d["status"] == "paused":
            # paused containers are alive — they never exited
            rows.append(("Started", format_created(d["started_at"] or "")))
        elif d["status"] in ("exited", "dead", "restarting") \
                and d["exit_code"] is not None:
            code = Text(str(d["exit_code"]), style="red bold")
            hint = describe_exit_code(d["exit_code"], d["oom_killed"])
            if hint:
                code.append(f"  {hint}", style="dim")
            rows.append(("Exit code", code))
            if d["oom_killed"]:
                oom = Text("true", style="red")
                if d["memory_limit"]:
                    oom.append(
                        f"  (memory limit {format_size(d['memory_limit'])})",
                        style="dim",
                    )
                rows.append(("OOMKilled", oom))
            if d["error"]:
                rows.append(("Error", Text(d["error"], style="red")))
            if d["finished_at"]:
                rows.append(("Finished", format_created(d["finished_at"])))
        restarts = Text(str(d["restart_count"]),
                        style="yellow" if d["restart_count"] else "")
        policy = d["restart_policy"]
        if d["restart_policy_max"]:
            policy += f", max {d['restart_policy_max']}"
        restarts.append(f"  (policy: {policy})", style="dim")
        rows.append(("Restarts", restarts))
        if health:
            h_style = {"healthy": "green", "unhealthy": "red"}.get(
                health["status"], "yellow")
            h = Text(health["status"], style=h_style)
            if health["test"]:
                h.append(f"  ({health['test']})", style="dim")
            rows.append(("Health", h))
            if health["status"] == "unhealthy" and health["last_output"]:
                rows.append(("Last probe",
                             Text(health["last_output"], style="dim")))
        self._rows(rows)

        # --- Network ---
        if d["networks"] or d["ports"]:
            self._section("Network")
            rows = [(n["name"], n["ip"] or "-") for n in d["networks"]]
            rows.append(("Ports", d["ports"] or "-"))
            self._rows(rows)

        # --- Mounts ---
        if d["mounts"]:
            self._section("Mounts")
            rows = []
            for m in d["mounts"]:
                val = Text(m["source"])
                val.append(f" → {m['destination']}", style="dim")
                if not m["rw"]:
                    val.append("  (ro)", style="yellow")
                rows.append((m["type"], val))
            self._rows(rows)

        # --- Env ---
        if d["env"]:
            if self.show_env:
                self._section("Env")
                self._rows(mask_env(d["env"]))
            else:
                con.print()
                n = len(d["env"])
                con.print(Text(
                    f"  Env: {n} var{'s' if n != 1 else ''}  (use --env to show)",
                    style="dim",
                ))

        # --- Last logs (only when not running) ---
        if d["last_logs"]:
            self._section("Last logs")
            for line in d["last_logs"].splitlines():
                con.print(Text(f"  │ {line}", style="dim"))

    def render_json(self, d: dict) -> None:
        import json

        out = dict(d)
        if self.show_env:
            out["env"] = {k: v for k, v in mask_env(d["env"])}
        else:
            out.pop("env", None)
        self.console.print_json(json.dumps(out, default=str))
