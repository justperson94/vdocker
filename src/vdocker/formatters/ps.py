from __future__ import annotations

from rich.table import Table
from rich.text import Text

from ..models import ContainerInfo
from ..utils import format_created, status_style, status_text
from .base import BaseFormatter


class PsFormatter(BaseFormatter):
    def render_rich(self, data: dict[str | None, list[ContainerInfo]]) -> None:
        projects = sorted(data.keys(), key=lambda k: (k is None, k or ""))

        for i, project in enumerate(projects):
            containers = data[project]
            label = project or "standalone"
            self.console.print(Text(f"[{label}]", style="bold cyan"))

            table = Table(
                show_header=True, box=None, padding=(0, 2), pad_edge=False,
                header_style="dim",
            )
            table.add_column("  ID", no_wrap=True, style="dim", max_width=14)
            table.add_column("NAME", no_wrap=True)
            table.add_column("IMAGE", no_wrap=True)
            table.add_column("COMMAND", no_wrap=True, max_width=20, style="dim")
            table.add_column("CREATED", no_wrap=True, style="dim")
            table.add_column("STATUS", no_wrap=True)
            table.add_column("PORTS", style="cyan", overflow="fold")

            for c in sorted(containers, key=lambda x: x.name):
                cmd = c.command
                if len(cmd) > 18:
                    cmd = cmd[:18] + "��"

                table.add_row(
                    f"  {c.id[:12]}",
                    Text(c.name, style=status_style(c.status)),
                    c.image_name,
                    f'"{cmd}"',
                    format_created(c.created),
                    status_text(c.status, c.started_at),
                    c.ports or "",
                )

            self.console.print(table)
            if i < len(projects) - 1:
                self.console.print()

    def render_json(self, data: dict[str | None, list[ContainerInfo]]) -> None:
        import json
        from dataclasses import asdict

        output = {}
        for project, containers in data.items():
            key = project or "standalone"
            output[key] = [asdict(c) for c in containers]
        self.console.print_json(json.dumps(output, default=str))
