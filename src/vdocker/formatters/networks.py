from __future__ import annotations

from rich.text import Text
from rich.tree import Tree

from ..models import ContainerInfo, NetworkInfo
from ..utils import status_style
from .base import BaseFormatter


class NetworksFormatter(BaseFormatter):
    def render_rich(
        self,
        data: tuple[list[NetworkInfo], dict[str, list[tuple[ContainerInfo, str]]]],
    ) -> None:
        networks, containers_by_network = data

        # Sort: networks with containers first, then by name
        def sort_key(n: NetworkInfo) -> tuple[bool, str]:
            has_containers = n.name in containers_by_network
            return (not has_containers, n.name)

        for i, network in enumerate(sorted(networks, key=sort_key)):
            label = Text()
            label.append(network.name, style="bold")
            label.append(f" ({network.driver})", style="dim")

            tree = Tree(label)
            containers = containers_by_network.get(network.name, [])
            if containers:
                for c, ip in sorted(containers, key=lambda x: x[0].name):
                    node_text = Text()
                    node_text.append(c.name, style=status_style(c.status))
                    if ip:
                        node_text.append(f"  {ip}", style="dim")
                    tree.add(node_text)
            else:
                tree.add(Text("(no containers)", style="dim"))

            self.console.print(tree)
            if i < len(networks) - 1:
                self.console.print()

    def render_json(
        self,
        data: tuple[list[NetworkInfo], dict[str, list[tuple[ContainerInfo, str]]]],
    ) -> None:
        import json
        from dataclasses import asdict

        networks, containers_by_network = data
        output = []
        for n in networks:
            entry = asdict(n)
            entry["containers"] = [
                {"container": asdict(c), "ip_address": ip}
                for c, ip in containers_by_network.get(n.name, [])
            ]
            output.append(entry)
        self.console.print_json(json.dumps(output, default=str))
