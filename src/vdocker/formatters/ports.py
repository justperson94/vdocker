from __future__ import annotations

from rich.table import Table
from rich.text import Text

from ..models import ContainerInfo
from .base import BaseFormatter


class PortsFormatter(BaseFormatter):
    def render_rich(self, data: list[dict]) -> None:
        if not data:
            self.console.print("[dim]No exposed ports found.[/dim]")
            return

        self.console.print(Text("Listening Ports (sorted by host port)", style="bold"))
        self.console.print()

        table = Table(
            show_header=True, box=None, padding=(0, 2), pad_edge=False,
            header_style="dim",
        )
        table.add_column("HOST PORT", no_wrap=True, style="cyan bold")
        table.add_column("BIND", no_wrap=True)
        table.add_column("CONTAINER PORT", no_wrap=True, style="dim")
        table.add_column("PROTO", no_wrap=True, style="dim")
        table.add_column("CONTAINER", no_wrap=True)
        table.add_column("IMAGE", no_wrap=True)
        table.add_column("NETWORK", no_wrap=True, style="dim")

        for row in data:
            container_cell = Text()
            container_cell.append(row["container_name"], style="green")
            if row["project"]:
                container_cell.append(f"  [{row['project']}]", style="dim")

            bind = row.get("bind", "0.0.0.0")
            # 0.0.0.0 (open to the world) is the unremarkable default;
            # a specific bind address is what deserves attention.
            bind_cell = Text(bind, style="dim" if bind == "0.0.0.0" else "yellow")

            table.add_row(
                str(row["host_port"]),
                bind_cell,
                str(row["container_port"]),
                row["protocol"],
                container_cell,
                row["image"],
                row["network"],
            )

        self.console.print(table)

        container_count = len({r["container_name"] for r in data})
        self.console.print()
        self.console.print(
            Text(f"{len(data)} ports in use by {container_count} containers", style="dim")
        )

    def render_json(self, data: list[dict]) -> None:
        import json
        self.console.print_json(json.dumps(data, default=str))
