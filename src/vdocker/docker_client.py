from __future__ import annotations

import docker

from .models import (
    ContainerInfo,
    ImageInfo,
    MountInfo,
    NetworkAttachment,
    NetworkInfo,
    PortBinding,
    VolumeInfo,
)


class DockerCollector:
    def __init__(self, show_all: bool = False):
        self._client = self._connect()
        self._show_all = show_all
        self._containers: list[ContainerInfo] | None = None
        self._volume_sizes: dict[str, int] | None = None
        self._df_thread = None

    @staticmethod
    def _connect() -> docker.DockerClient:
        """Connect to the daemon the docker CLI would talk to.

        docker-py's from_env() only reads DOCKER_HOST and ignores the CLI
        context store, so `docker context use remote` would silently leave
        vdocker looking at a different daemon than docker itself.
        """
        import os
        if not os.environ.get("DOCKER_HOST"):
            try:
                from docker.context import ContextAPI
                ctx = ContextAPI.get_current_context()
                if ctx and ctx.name != "default" and ctx.Host:
                    return docker.DockerClient(
                        base_url=ctx.Host,
                        use_ssh_client=ctx.Host.startswith("ssh://"),
                    )
            except Exception:
                pass  # fall back to the default resolution below
        return docker.from_env()

    @staticmethod
    def _parse_port_bindings(ports_dict: dict) -> list[PortBinding]:
        """Structured host-exposed port bindings, IPv6 duplicates dropped."""
        bindings = []
        for container_port_proto, raw in (ports_dict or {}).items():
            if not raw:
                continue
            port_str, _, proto = container_port_proto.rpartition("/")
            if not port_str.isdigit():
                continue
            for b in raw:
                host_ip = b.get("HostIp", "0.0.0.0") or "0.0.0.0"
                host_port = b.get("HostPort", "")
                if host_ip in ("::", "::1") or not host_port:
                    continue  # skip IPv6 duplicates
                bindings.append(PortBinding(
                    host_ip=host_ip,
                    host_port=int(host_port),
                    container_port=int(port_str),
                    protocol=proto,
                ))
        bindings.sort(key=lambda b: b.host_port)
        return bindings

    @staticmethod
    def _format_ports(bindings: list[PortBinding]) -> str:
        parts = []
        for b in bindings:
            proto = f"/{b.protocol}" if b.protocol else ""
            if b.host_ip == "0.0.0.0":
                parts.append(f"{b.host_port}->{b.container_port}{proto}")
            else:
                parts.append(f"{b.host_ip}:{b.host_port}->{b.container_port}{proto}")
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

        # Read image/command from attrs directly: the c.image property makes
        # an extra API call per container and raises ImageNotFound when the
        # image has been deleted out from under a container.
        config = c.attrs.get("Config", {})
        image_name = config.get("Image") or c.attrs.get("Image", "")[:19]

        # docker ps shows entrypoint + cmd combined; do the same
        parts = (config.get("Entrypoint") or []) + (config.get("Cmd") or [])
        command = " ".join(parts)

        # Ports
        port_bindings = DockerCollector._parse_port_bindings(
            c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
        )
        ports = DockerCollector._format_ports(port_bindings)

        return ContainerInfo(
            id=c.id,
            name=c.name,
            status=c.status,
            image_id=c.attrs.get("Image", ""),
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
            port_bindings=port_bindings,
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

        image_name = config.get("Image") or attrs.get("Image", "")[:19]

        parts = (config.get("Entrypoint") or []) + (config.get("Cmd") or [])
        command = " ".join(parts)

        networks = [
            {"name": name, "ip": data.get("IPAddress", "")}
            for name, data in (net_settings.get("Networks", {}) or {}).items()
        ]
        ports = self._format_ports(
            self._parse_port_bindings(net_settings.get("Ports", {}) or {})
        )

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
        if status in ("exited", "dead", "restarting"):
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
        # Use the raw list endpoint: images.list() inspects every image
        # individually, which costs hundreds of ms on image-heavy hosts.
        from datetime import datetime, timezone

        raw = self._client.api.images()
        images = []
        for img in raw:
            tags = [t for t in (img.get("RepoTags") or []) if t != "<none>:<none>"]
            created = img.get("Created", 0)
            if isinstance(created, (int, float)):
                created = datetime.fromtimestamp(
                    created, tz=timezone.utc).isoformat()
            images.append(ImageInfo(
                id=img.get("Id", ""),
                tags=tags,
                size=img.get("Size", 0),
                created=str(created),
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

    def prefetch_volume_sizes(self) -> None:
        """Start the slow `docker system df` call in the background.

        Uses its own client because requests sessions are not thread-safe.
        """
        import threading

        if self._volume_sizes is not None or self._df_thread is not None:
            return

        def work():
            self._prefetched_sizes = self._compute_volume_sizes(self._connect())

        self._df_thread = threading.Thread(target=work, daemon=True)
        self._df_thread.start()

    @staticmethod
    def _compute_volume_sizes(client: docker.DockerClient) -> dict[str, int]:
        sizes: dict[str, int] = {}
        try:
            df = client.df()
            for v in df.get("Volumes") or []:
                usage = v.get("UsageData") or {}
                size = usage.get("Size", -1)
                if size >= 0:
                    sizes[v["Name"]] = size
        except Exception:
            pass
        return sizes

    def _get_volume_sizes(self) -> dict[str, int]:
        if self._volume_sizes is not None:
            return self._volume_sizes
        if self._df_thread is not None:
            self._df_thread.join()
            self._volume_sizes = getattr(self, "_prefetched_sizes", {})
        else:
            self._volume_sizes = self._compute_volume_sizes(self._client)
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
            primary_net = c.networks[0].network_name if c.networks else ""
            for b in c.port_bindings:
                key = (b.host_ip, b.host_port, b.container_port, b.protocol, c.name)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "bind": b.host_ip,
                    "host_port": b.host_port,
                    "container_port": b.container_port,
                    "protocol": b.protocol,
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
