from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MountInfo:
    type: str  # "volume", "bind", "tmpfs"
    name: str | None  # Volume name (None for bind mounts)
    source: str
    destination: str


@dataclass(frozen=True)
class NetworkAttachment:
    network_name: str
    ip_address: str


@dataclass(frozen=True)
class ContainerInfo:
    id: str
    name: str
    status: str  # "running", "exited", "paused", "created", "restarting"
    image_id: str
    image_name: str
    command: str
    created: str  # ISO timestamp
    ports: str  # formatted port mappings
    project: str | None  # com.docker.compose.project
    service: str | None  # com.docker.compose.service
    working_dir: str | None  # com.docker.compose.project.working_dir
    started_at: str | None
    mounts: list[MountInfo] = field(default_factory=list)
    networks: list[NetworkAttachment] = field(default_factory=list)


@dataclass(frozen=True)
class ImageInfo:
    id: str
    tags: list[str]
    size: int  # bytes
    created: str


@dataclass(frozen=True)
class VolumeInfo:
    name: str
    driver: str
    mountpoint: str
    size: int | None = None  # bytes, from docker system df


@dataclass(frozen=True)
class NetworkInfo:
    id: str
    name: str
    driver: str
    scope: str
