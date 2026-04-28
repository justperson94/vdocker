from __future__ import annotations

from rich.text import Text
from rich.tree import Tree

from ..models import ContainerInfo, VolumeInfo
from ..utils import format_size, status_style
from .base import BaseFormatter


class VolumesFormatter(BaseFormatter):
    def render_rich(
        self,
        data: tuple[list[VolumeInfo], dict[str, list[tuple[ContainerInfo, str]]]],
    ) -> None:
        volumes, containers_by_volume = data

        # Sort: volumes with containers first, then by name
        def sort_key(v: VolumeInfo) -> tuple[bool, str]:
            has_containers = v.name in containers_by_volume
            return (not has_containers, v.name)

        for i, volume in enumerate(sorted(volumes, key=sort_key)):
            label = Text()
            label.append(volume.name, style="bold")
            label.append(f" ({format_size(volume.size)})", style="dim")

            tree = Tree(label)
            containers = containers_by_volume.get(volume.name, [])
            if containers:
                for c, mount_dest in sorted(containers, key=lambda x: x[0].name):
                    node_text = Text()
                    node_text.append(c.name, style=status_style(c.status))
                    node_text.append(f"  {mount_dest}", style="dim")
                    tree.add(node_text)
            else:
                tree.add(Text("(no containers)", style="dim"))

            self.console.print(tree)
            if i < len(volumes) - 1:
                self.console.print()

    def render_json(
        self,
        data: tuple[list[VolumeInfo], dict[str, list[tuple[ContainerInfo, str]]]],
    ) -> None:
        import json
        from dataclasses import asdict

        volumes, containers_by_volume = data
        output = []
        for v in volumes:
            entry = asdict(v)
            entry["containers"] = [
                {"container": asdict(c), "mount_destination": dest}
                for c, dest in containers_by_volume.get(v.name, [])
            ]
            output.append(entry)
        self.console.print_json(json.dumps(output, default=str))
