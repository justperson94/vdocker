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

        # Group volumes by project (via their mounted containers)
        groups: dict[str | None, list[tuple[VolumeInfo, list[tuple[ContainerInfo, str]]]]] = {}
        unmounted: list[VolumeInfo] = []

        for volume in volumes:
            containers = containers_by_volume.get(volume.name, [])
            if not containers:
                unmounted.append(volume)
                continue
            # Determine project from the first container
            project = containers[0][0].project
            groups.setdefault(project, []).append((volume, containers))

        # Sort project keys: named projects first, then None (standalone)
        sorted_projects = sorted(groups.keys(), key=lambda k: (k is None, k or ""))

        for i, project in enumerate(sorted_projects):
            items = groups[project]
            label = project or "standalone"

            header = Text(f"[{label}]", style="bold cyan")
            # Show working_dir from any container
            working_dir = next(
                (c.working_dir for vol, conts in items for c, _ in conts if c.working_dir),
                None,
            )
            if working_dir and self.console.width >= 80:
                header.append(f"  {working_dir}", style="dim")

            proj_tree = Tree(header)

            for volume, containers in sorted(items, key=lambda x: x[0].name):
                vol_label = Text()
                vol_label.append(volume.name, style="bold")
                vol_label.append(f" ({format_size(volume.size)})", style="dim")
                vol_node = proj_tree.add(vol_label)

                for c, mount_dest in sorted(containers, key=lambda x: x[0].name):
                    node_text = Text()
                    node_text.append(c.name, style=status_style(c.status))
                    node_text.append(f"  {mount_dest}", style="dim")
                    vol_node.add(node_text)

            self.console.print(proj_tree)
            if i < len(sorted_projects) - 1 or unmounted:
                self.console.print()

        # Unmounted volumes
        if unmounted:
            unmounted_tree = Tree(Text("[no containers]", style="dim"))
            for volume in sorted(unmounted, key=lambda v: v.name):
                vol_label = Text()
                vol_label.append(volume.name, style="dim")
                vol_label.append(f" ({format_size(volume.size)})", style="dim")
                vol_node = unmounted_tree.add(vol_label)
                vol_node.add(Text("(not mounted)", style="dim"))
            self.console.print(unmounted_tree)

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
