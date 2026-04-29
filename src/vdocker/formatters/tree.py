from __future__ import annotations

from rich.text import Text
from rich.tree import Tree

from ..models import ContainerInfo, ImageInfo, NetworkInfo, VolumeInfo
from ..utils import format_size, status_style, status_text
from .base import BaseFormatter


class TreeFormatter(BaseFormatter):
    def render_rich(self, data: dict) -> None:
        containers: list[ContainerInfo] = data["containers"]
        images: list[ImageInfo] = data["images"]
        volumes: list[VolumeInfo] = data["volumes"]
        networks: list[NetworkInfo] = data["networks"]

        # Build lookup maps
        image_map = {img.id: img for img in images}
        used_image_ids: set[str] = set()
        used_volume_names: set[str] = set()
        used_network_names: set[str] = set()

        # Group containers by project, then by service
        projects: dict[str | None, dict[str | None, list[ContainerInfo]]] = {}
        for c in containers:
            proj = projects.setdefault(c.project, {})
            proj.setdefault(c.service, []).append(c)
            used_image_ids.add(c.image_id)
            for m in c.mounts:
                if m.type == "volume" and m.name:
                    used_volume_names.add(m.name)
            for n in c.networks:
                used_network_names.add(n.network_name)

        root = Tree(Text("Docker Environment", style="bold white"))

        # Project trees
        sorted_projects = sorted(
            projects.keys(), key=lambda k: (k is None, k or "")
        )
        for project in sorted_projects:
            services = projects[project]
            proj_label = project or "standalone"
            # Get working_dir from any container in this project
            all_containers_in_proj = [
                c for svc in services.values() for c in svc
            ]
            working_dir = next(
                (c.working_dir for c in all_containers_in_proj if c.working_dir),
                None,
            )
            proj_header = Text(f"[{proj_label}]", style="bold cyan")
            if working_dir:
                proj_header.append(f"  {working_dir}", style="dim")
            proj_node = root.add(proj_header)

            sorted_services = sorted(
                services.keys(), key=lambda k: (k is None, k or "")
            )
            for service in sorted_services:
                svc_containers = services[service]
                if service:
                    svc_node = proj_node.add(
                        Text(f"{service} (service)", style="bold")
                    )
                else:
                    svc_node = proj_node

                for c in sorted(svc_containers, key=lambda x: x.name):
                    c_label = Text()
                    c_label.append(c.name, style=status_style(c.status))
                    c_label.append("  ")
                    c_label.append_text(status_text(c.status, c.started_at))
                    c_node = svc_node.add(c_label)

                    # Image
                    img = image_map.get(c.image_id)
                    img_label = c.image_name
                    if img:
                        img_label += f" ({format_size(img.size)})"
                    c_node.add(Text(f"Image: {img_label}", style="dim"))

                    # Volumes
                    vol_mounts = [m for m in c.mounts if m.type == "volume" and m.name]
                    if vol_mounts:
                        vol_node = c_node.add(Text("Volumes:", style="dim"))
                        for m in vol_mounts:
                            vol_node.add(
                                Text(f"{m.name} \u2192 {m.destination}", style="dim")
                            )

                    # Networks
                    if c.networks:
                        net_node = c_node.add(Text("Networks:", style="dim"))
                        for n in c.networks:
                            ip_part = f" ({n.ip_address})" if n.ip_address else ""
                            net_node.add(
                                Text(f"{n.network_name}{ip_part}", style="dim")
                            )

        # Unused resources
        unused_images = [
            img for img in images
            if img.id not in used_image_ids and img.tags
        ]
        unused_volumes = [
            v for v in volumes if v.name not in used_volume_names
        ]
        # Skip default Docker networks from unused
        default_nets = {"bridge", "host", "none"}
        unused_networks = [
            n for n in networks
            if n.name not in used_network_names and n.name not in default_nets
        ]

        if unused_images or unused_volumes or unused_networks:
            unused_node = root.add(Text("Unused Resources", style="bold red"))

            if unused_images:
                img_node = unused_node.add(Text("Images:", style="dim"))
                for img in sorted(unused_images, key=lambda x: x.tags[0]):
                    img_node.add(
                        Text(
                            f"{img.tags[0]} ({format_size(img.size)})",
                            style="dim",
                        )
                    )

            if unused_volumes:
                vol_node = unused_node.add(Text("Volumes:", style="dim"))
                for v in sorted(unused_volumes, key=lambda x: x.name):
                    vol_node.add(
                        Text(
                            f"{v.name} ({format_size(v.size)})",
                            style="dim",
                        )
                    )

            if unused_networks:
                net_node = unused_node.add(Text("Networks:", style="dim"))
                for n in sorted(unused_networks, key=lambda x: x.name):
                    net_node.add(Text(f"{n.name} ({n.driver})", style="dim"))

        self.console.print(root)

    def render_json(self, data: dict) -> None:
        import json
        from dataclasses import asdict

        output = {
            "containers": [asdict(c) for c in data["containers"]],
            "images": [asdict(i) for i in data["images"]],
            "volumes": [asdict(v) for v in data["volumes"]],
            "networks": [asdict(n) for n in data["networks"]],
        }
        self.console.print_json(json.dumps(output, default=str))
