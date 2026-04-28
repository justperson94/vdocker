from __future__ import annotations

from rich.text import Text
from rich.tree import Tree

from ..models import ContainerInfo, ImageInfo
from ..utils import format_size, status_style, status_text
from .base import BaseFormatter


class ImagesFormatter(BaseFormatter):
    def __init__(self, *args, show_unused: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_unused = show_unused

    def render_rich(
        self,
        data: tuple[list[ImageInfo], dict[str, list[ContainerInfo]]],
    ) -> None:
        images, containers_by_image = data

        # Filter: only images with containers, unless show_unused
        if not self.show_unused:
            images = [img for img in images if img.id in containers_by_image]

        if not images:
            self.console.print("[dim]No images with containers found. Use --unused to show all.[/dim]")
            return

        def sort_key(img: ImageInfo) -> tuple[bool, str]:
            has_containers = img.id in containers_by_image
            tag = img.tags[0] if img.tags else "~" + img.id[:12]
            return (not has_containers, tag)

        for i, image in enumerate(sorted(images, key=sort_key)):
            if not image.tags and image.id not in containers_by_image:
                continue

            tag = image.tags[0] if image.tags else image.id[:12]
            label = Text()
            label.append(tag, style="bold")
            label.append(f" ({format_size(image.size)})", style="dim")

            tree = Tree(label)
            containers = containers_by_image.get(image.id, [])
            if containers:
                for c in sorted(containers, key=lambda x: x.name):
                    node_text = Text()
                    node_text.append(c.name, style=status_style(c.status))
                    node_text.append("  ")
                    node_text.append_text(status_text(c.status, c.started_at))
                    tree.add(node_text)
            else:
                tree.add(Text("(no containers)", style="dim"))

            self.console.print(tree)
            if i < len(images) - 1:
                self.console.print()

    def render_json(
        self,
        data: tuple[list[ImageInfo], dict[str, list[ContainerInfo]]],
    ) -> None:
        import json
        from dataclasses import asdict

        images, containers_by_image = data
        if not self.show_unused:
            images = [img for img in images if img.id in containers_by_image]
        output = []
        for img in images:
            entry = asdict(img)
            entry["containers"] = [
                asdict(c) for c in containers_by_image.get(img.id, [])
            ]
            output.append(entry)
        self.console.print_json(json.dumps(output, default=str))
