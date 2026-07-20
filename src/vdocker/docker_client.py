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
                    if host_ip == "::" or host_ip == "::1":
                        continue  # skip IPv6 duplicates
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
            working_dir=c.labels.get("com.docker.compose.project.working_dir"),
            started_at=c.attrs.get("State", {}).get("StartedAt"),
            mounts=mounts,
            networks=networks,
        )

    @staticmethod
    def _clean_ts(ts: str | None) -> str | None:
        """Docker uses 0001-01-01 as 'never'; treat it as absent."""
        if not ts or ts.startswith("0001-"):
            return None
        return ts

    def get_container_detail(self, name_or_id: str) -> dict:
        """Full one-container summary for `vdocker info`."""
        c = self._client.containers.get(name_or_id)
        attrs = c.attrs
        state = attrs.get("State", {}) or {}
        config = attrs.get("Config", {}) or {}
        host = attrs.get("HostConfig", {}) or {}
        labels = config.get("Labels", {}) or {}
        net_settings = attrs.get("NetworkSettings", {}) or {}

        image_tags = c.image.tags or []
        image_name = image_tags[0] if image_tags else c.image.short_id

        cmd = config.get("Cmd")
        command = " ".join(cmd) if cmd else ""

        networks = [
            {"name": name, "ip": data.get("IPAddress", "")}
            for name, data in (net_settings.get("Networks", {}) or {}).items()
        ]
        ports = self._format_ports(net_settings.get("Ports", {}) or {})

        mounts = []
        for m in attrs.get("Mounts", []):
            mounts.append({
                "type": m.get("Type", ""),
                "source": m.get("Name") or m.get("Source", ""),
                "destination": m.get("Destination", ""),
                "rw": m.get("RW", True),
            })

        policy = host.get("RestartPolicy", {}) or {}

        health = state.get("Health")
        health_info = None
        if health:
            probes = health.get("Log") or []
            last_output = (probes[-1].get("Output") or "").strip() if probes else ""
            test = (config.get("Healthcheck", {}) or {}).get("Test") or []
            test_str = " ".join(t for t in test if t not in ("CMD-SHELL", "CMD", "NONE"))
            health_info = {
                "status": health.get("Status", ""),
                "failing_streak": health.get("FailingStreak", 0),
                "test": test_str,
                "last_output": last_output,
            }

        status = state.get("Status", "")
        last_logs = None
        if status != "running":
            try:
                last_logs = c.logs(tail=10).decode("utf-8", errors="replace").rstrip()
            except Exception:
                last_logs = None

        return {
            "name": c.name,
            "id": c.id,
            "status": status,
            "image": image_name,
            "command": command,
            "created": attrs.get("Created", ""),
            "started_at": self._clean_ts(state.get("StartedAt")),
            "finished_at": self._clean_ts(state.get("FinishedAt")),
            "exit_code": state.get("ExitCode"),
            "oom_killed": state.get("OOMKilled", False),
            "error": state.get("Error", ""),
            "restart_count": attrs.get("RestartCount", 0),
            "restart_policy": policy.get("Name") or "no",
            "restart_policy_max": policy.get("MaximumRetryCount", 0),
            "memory_limit": host.get("Memory", 0),
            "project": labels.get("com.docker.compose.project"),
            "service": labels.get("com.docker.compose.service"),
            "working_dir": labels.get("com.docker.compose.project.working_dir"),
            "networks": networks,
            "ports": ports,
            "mounts": mounts,
            "health": health_info,
            "env": config.get("Env") or [],
            "last_logs": last_logs,
        }

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

    def port_mappings(self) -> list[dict]:
        """Return all host-exposed port mappings sorted by host port."""
        seen: set[tuple] = set()
        rows = []
        for c in self.get_containers():
            raw = self._client.containers.get(c.id)
            raw_ports = raw.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            net_names = [n.network_name for n in c.networks]
            primary_net = net_names[0] if net_names else ""

            for container_port_proto, bindings in raw_ports.items():
                if not bindings:
                    continue
                port_str, proto = container_port_proto.rsplit("/", 1)
                for b in bindings:
                    host_port = b.get("HostPort", "")
                    if not host_port:
                        continue
                    key = (int(host_port), int(port_str), proto, c.name)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append({
                        "host_port": int(host_port),
                        "container_port": int(port_str),
                        "protocol": proto,
                        "container_name": c.name,
                        "project": c.project,
                        "image": c.image_name,
                        "network": primary_net,
                    })
        rows.sort(key=lambda r: r["host_port"])
        return rows

    def containers_by_network(self) -> dict[str, list[tuple[ContainerInfo, str]]]:
        all_containers = self.get_all_containers()
        groups: dict[str, list[tuple[ContainerInfo, str]]] = {}
        for c in all_containers:
            for n in c.networks:
                groups.setdefault(n.network_name, []).append((c, n.ip_address))
        return groups
