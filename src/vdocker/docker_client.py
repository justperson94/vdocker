from __future__ import annotations

import docker

from .models import (
    ContainerInfo,
    ImageInfo,
    MountInfo,
    NetworkAttachment,
    NetworkInfo,
    VolumeInfo,
)


class DockerCollector:
    def __init__(self, show_all: bool = False):
        self._client = docker.from_env()
        self._show_all = show_all
        self._containers: list[ContainerInfo] | None = None
        self._volume_sizes: dict[str, int] | None = None

    @staticmethod
    def _format_ports(ports_dict: dict) -> str:
        if not ports_dict:
            return ""
        parts = []
        for container_port, bindings in ports_dict.items():
            if bindings:
                for b in bindings:
                    host_ip = b.get("HostIp", "0.0.0.0")
                    host_port = b.get("HostPort", "")
                    if host_ip == "0.0.0.0":
                        parts.append(f"{host_port}->{container_port}")
                    else:
                        parts.append(f"{host_ip}:{host_port}->{container_port}")
        return ", ".join(parts)

    @staticmethod
    def _parse_container(c) -> ContainerInfo:
        mounts = []
        for m in c.attrs.get("Mounts", []):
            mounts.append(MountInfo(
                type=m.get("Type", ""),
                name=m.get("Name"),
                source=m.get("Source", ""),
                destination=m.get("Destination", ""),
            ))

        networks = []
        for net_name, net_data in (
            c.attrs.get("NetworkSettings", {}).get("Networks", {}).items()
        ):
            networks.append(NetworkAttachment(
                network_name=net_name,
                ip_address=net_data.get("IPAddress", ""),
            ))

        image_tags = c.image.tags if c.image.tags else []
        image_name = image_tags[0] if image_tags else c.image.short_id

        # Command: from Config.Cmd or Config.Entrypoint
        config = c.attrs.get("Config", {})
        cmd = config.get("Cmd")
        command = " ".join(cmd) if cmd else ""

        # Ports
        ports_dict = c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
        ports = DockerCollector._format_ports(ports_dict)

        return ContainerInfo(
            id=c.id,
            name=c.name,
            status=c.status,
            image_id=c.image.id,
            image_name=image_name,
            command=command,
            created=c.attrs.get("Created", ""),
            ports=ports,
            project=c.labels.get("com.docker.compose.project"),
            service=c.labels.get("com.docker.compose.service"),
            started_at=c.attrs.get("State", {}).get("StartedAt"),
            mounts=mounts,
            networks=networks,
        )

    def get_containers(self) -> list[ContainerInfo]:
        if self._containers is not None:
            return self._containers
        raw = self._client.containers.list(all=self._show_all)
        self._containers = [self._parse_container(c) for c in raw]
        return self._containers

    def get_all_containers(self) -> list[ContainerInfo]:
        """Always fetch all containers regardless of show_all flag."""
        raw = self._client.containers.list(all=True)
        return [self._parse_container(c) for c in raw]

    def get_images(self) -> list[ImageInfo]:
        raw = self._client.images.list()
        images = []
        for img in raw:
            images.append(ImageInfo(
                id=img.id,
                tags=img.tags or [],
                size=img.attrs.get("Size", 0),
                created=img.attrs.get("Created", ""),
            ))
        return images

    def get_volumes(self) -> list[VolumeInfo]:
        raw = self._client.volumes.list()
        sizes = self._get_volume_sizes()
        volumes = []
        for v in raw:
            volumes.append(VolumeInfo(
                name=v.name,
                driver=v.attrs.get("Driver", ""),
                mountpoint=v.attrs.get("Mountpoint", ""),
                size=sizes.get(v.name),
            ))
        return volumes

    def _get_volume_sizes(self) -> dict[str, int]:
        if self._volume_sizes is not None:
            return self._volume_sizes
        try:
            df = self._client.df()
            self._volume_sizes = {}
            for v in df.get("Volumes", []):
                usage = v.get("UsageData", {})
                size = usage.get("Size", -1)
                if size >= 0:
                    self._volume_sizes[v["Name"]] = size
        except Exception:
            self._volume_sizes = {}
        return self._volume_sizes

    def get_networks(self) -> list[NetworkInfo]:
        raw = self._client.networks.list()
        networks = []
        for n in raw:
            networks.append(NetworkInfo(
                id=n.id,
                name=n.name,
                driver=n.attrs.get("Driver", ""),
                scope=n.attrs.get("Scope", ""),
            ))
        return networks

    # --- Relationship builders ---

    def containers_by_project(self) -> dict[str | None, list[ContainerInfo]]:
        groups: dict[str | None, list[ContainerInfo]] = {}
        for c in self.get_containers():
            groups.setdefault(c.project, []).append(c)
        return groups

    def containers_by_image(self) -> dict[str, list[ContainerInfo]]:
        all_containers = self.get_all_containers()
        groups: dict[str, list[ContainerInfo]] = {}
        for c in all_containers:
            groups.setdefault(c.image_id, []).append(c)
        return groups

    def containers_by_volume(self) -> dict[str, list[tuple[ContainerInfo, str]]]:
        all_containers = self.get_all_containers()
        groups: dict[str, list[tuple[ContainerInfo, str]]] = {}
        for c in all_containers:
            for m in c.mounts:
                if m.type == "volume" and m.name:
                    groups.setdefault(m.name, []).append((c, m.destination))
        return groups

    def containers_by_network(self) -> dict[str, list[tuple[ContainerInfo, str]]]:
        all_containers = self.get_all_containers()
        groups: dict[str, list[tuple[ContainerInfo, str]]] = {}
        for c in all_containers:
            for n in c.networks:
                groups.setdefault(n.network_name, []).append((c, n.ip_address))
        return groups
