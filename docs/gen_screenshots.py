"""Generate SVG screenshots for README using mock data."""

from datetime import datetime, timedelta, timezone

from rich.console import Console

from vdocker.formatters.images import ImagesFormatter
from vdocker.formatters.info import InfoFormatter
from vdocker.formatters.networks import NetworksFormatter
from vdocker.formatters.ports import PortsFormatter
from vdocker.formatters.ps import PsFormatter
from vdocker.formatters.tree import TreeFormatter
from vdocker.formatters.volumes import VolumesFormatter


from vdocker.models import (
    ContainerInfo,
    ImageInfo,
    MountInfo,
    NetworkAttachment,
    NetworkInfo,
    VolumeInfo,
)


def ago(days: int = 0, hours: int = 0) -> str:
    """Timestamp relative to now, so screenshots don't age on regeneration."""
    return (datetime.now(timezone.utc) - timedelta(days=days, hours=hours)).isoformat()

# Custom SVG template — no external @font-face, uses universally available monospace fonts
CUSTOM_SVG_FORMAT = """\
<svg class="rich-terminal" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Generated with Rich https://www.textualize.io -->
    <style>

    .{unique_id}-matrix {{
        font-family: "SFMono-Regular", "Menlo", "Consolas", "Liberation Mono", "Courier New", monospace;
        font-size: {char_height}px;
        line-height: {line_height}px;
        font-variant-east-asian: full-width;
    }}

    .{unique_id}-title {{
        font-size: 18px;
        font-weight: bold;
        font-family: arial;
    }}

    {styles}
    </style>

    <defs>
    <clipPath id="{unique_id}-clip-terminal">
      <rect x="0" y="0" width="{terminal_width}" height="{terminal_height}" />
    </clipPath>
    {lines}
    </defs>

    {chrome}
    <g transform="translate({terminal_x}, {terminal_y})" clip-path="url(#{unique_id}-clip-terminal)">
    {backgrounds}
    <g class="{unique_id}-matrix">
    {matrix}
    </g>
    </g>
</svg>
"""

# ──────────────────────────────────────────────
#  Mock data — edit this section freely
# ──────────────────────────────────────────────

CONTAINERS = [
    # [myapp] project
    ContainerInfo(
        id="a1b2c3d4e5f6a1b2c3d4e5f6",
        name="myapp-web-1",
        status="running",
        image_id="img_nginx",
        image_name="nginx:latest",
        command="nginx -g 'daemon off;'",
        created=ago(days=1),
        ports="80->80/tcp, :::80->80/tcp",
        project="myapp",
        service="web",
        working_dir="/home/user/projects/myapp",
        started_at=ago(days=1),
        mounts=[MountInfo("volume", "myapp_static", "", "/usr/share/nginx/html")],
        networks=[NetworkAttachment("myapp_default", "172.18.0.2")],
    ),
    ContainerInfo(
        id="b2c3d4e5f6a7b2c3d4e5f6a7",
        name="myapp-api-1",
        status="running",
        image_id="img_node",
        image_name="node:18",
        command="node server.js",
        created=ago(days=1),
        ports="3000->3000/tcp",
        project="myapp",
        service="api",
        working_dir="/home/user/projects/myapp",
        started_at=ago(days=1),
        mounts=[],
        networks=[NetworkAttachment("myapp_default", "172.18.0.3")],
    ),
    ContainerInfo(
        id="c3d4e5f6a7b8c3d4e5f6a7b8",
        name="myapp-db-1",
        status="running",
        image_id="img_postgres",
        image_name="postgres:15",
        command="postgres",
        created=ago(days=1),
        ports="5432->5432/tcp",
        project="myapp",
        service="db",
        working_dir="/home/user/projects/myapp",
        started_at=ago(days=1),
        mounts=[MountInfo("volume", "myapp_db-data", "", "/var/lib/postgresql/data")],
        networks=[NetworkAttachment("myapp_default", "172.18.0.4")],
    ),
    # [monitoring] project
    ContainerInfo(
        id="d4e5f6a7b8c9d4e5f6a7b8c9",
        name="monitoring-grafana-1",
        status="running",
        image_id="img_grafana",
        image_name="grafana/grafana:10.2",
        command="/run.sh",
        created=ago(days=4),
        ports="3001->3000/tcp",
        project="monitoring",
        service="grafana",
        working_dir="/opt/monitoring",
        started_at=ago(days=4),
        mounts=[MountInfo("volume", "monitoring_grafana-data", "", "/var/lib/grafana")],
        networks=[NetworkAttachment("monitoring_default", "172.19.0.2")],
    ),
    ContainerInfo(
        id="e5f6a7b8c9d0e5f6a7b8c9d0",
        name="monitoring-prometheus-1",
        status="running",
        image_id="img_prometheus",
        image_name="prom/prometheus:latest",
        command="/bin/prometheus",
        created=ago(days=4),
        ports="9090->9090/tcp",
        project="monitoring",
        service="prometheus",
        working_dir="/opt/monitoring",
        started_at=ago(days=4),
        mounts=[],
        networks=[NetworkAttachment("monitoring_default", "172.19.0.3")],
    ),
    # [standalone]
    ContainerInfo(
        id="f6a7b8c9d0e1f6a7b8c9d0e1",
        name="redis-test",
        status="running",
        image_id="img_redis",
        image_name="redis:7",
        command="redis-server",
        created=ago(hours=19),
        ports="6379->6379/tcp",
        project=None,
        service=None,
        working_dir=None,
        started_at=ago(hours=19),
        mounts=[MountInfo("volume", "redis-data", "", "/data")],
        networks=[NetworkAttachment("bridge", "172.17.0.2")],
    ),
    # Stopped container
    ContainerInfo(
        id="a7b8c9d0e1f2a7b8c9d0e1f2",
        name="myapp-worker-1",
        status="exited",
        image_id="img_node",
        image_name="node:18",
        command="node worker.js",
        created=ago(days=3),
        ports="",
        project="myapp",
        service="worker",
        working_dir="/home/user/projects/myapp",
        started_at=None,
        mounts=[],
        networks=[NetworkAttachment("myapp_default", "")],
    ),
]

IMAGES = [
    ImageInfo(id="img_nginx", tags=["nginx:latest"], size=47_000_000, created="2026-04-20T00:00:00Z"),
    ImageInfo(id="img_node", tags=["node:18"], size=350_000_000, created="2026-04-18T00:00:00Z"),
    ImageInfo(id="img_postgres", tags=["postgres:15"], size=380_000_000, created="2026-04-15T00:00:00Z"),
    ImageInfo(id="img_grafana", tags=["grafana/grafana:10.2"], size=420_000_000, created="2026-04-10T00:00:00Z"),
    ImageInfo(id="img_prometheus", tags=["prom/prometheus:latest"], size=260_000_000, created="2026-04-10T00:00:00Z"),
    ImageInfo(id="img_redis", tags=["redis:7"], size=30_000_000, created="2026-04-12T00:00:00Z"),
    ImageInfo(id="img_alpine", tags=["alpine:3.18"], size=7_000_000, created="2026-03-01T00:00:00Z"),
]

VOLUMES = [
    VolumeInfo(name="myapp_static", driver="local", mountpoint="/var/lib/docker/volumes/myapp_static", size=12_000_000),
    VolumeInfo(name="myapp_db-data", driver="local", mountpoint="/var/lib/docker/volumes/myapp_db-data", size=524_000_000),
    VolumeInfo(name="monitoring_grafana-data", driver="local", mountpoint="/var/lib/docker/volumes/monitoring_grafana-data", size=85_000_000),
    VolumeInfo(name="redis-data", driver="local", mountpoint="/var/lib/docker/volumes/redis-data", size=10_000_000),
    VolumeInfo(name="old-backup", driver="local", mountpoint="/var/lib/docker/volumes/old-backup", size=0),
]

PORT_ROWS = [
    {"host_port": 80, "bind": "0.0.0.0", "container_port": 80, "protocol": "tcp",
     "container_name": "myapp-web-1", "project": "myapp", "image": "nginx:latest",
     "network": "myapp_default"},
    {"host_port": 3000, "bind": "0.0.0.0", "container_port": 3000, "protocol": "tcp",
     "container_name": "myapp-api-1", "project": "myapp", "image": "node:18",
     "network": "myapp_default"},
    {"host_port": 3001, "bind": "0.0.0.0", "container_port": 3000, "protocol": "tcp",
     "container_name": "monitoring-grafana-1", "project": "monitoring",
     "image": "grafana/grafana:10.2", "network": "monitoring_default"},
    {"host_port": 5432, "bind": "127.0.0.1", "container_port": 5432, "protocol": "tcp",
     "container_name": "myapp-db-1", "project": "myapp", "image": "postgres:15",
     "network": "myapp_default"},
    {"host_port": 6379, "bind": "0.0.0.0", "container_port": 6379, "protocol": "tcp",
     "container_name": "redis-test", "project": None, "image": "redis:7",
     "network": "bridge"},
    {"host_port": 9090, "bind": "127.0.0.1", "container_port": 9090, "protocol": "tcp",
     "container_name": "monitoring-prometheus-1", "project": "monitoring",
     "image": "prom/prometheus:latest", "network": "monitoring_default"},
]

INFO_DETAIL = {
    "name": "myapp-worker-1",
    "id": "a7b8c9d0e1f2a7b8c9d0e1f2",
    "status": "exited",
    "image": "node:18",
    "command": "node worker.js",
    "created": ago(days=3),
    "started_at": None,
    "finished_at": ago(hours=2),
    "exit_code": 137,
    "oom_killed": True,
    "error": "",
    "restart_count": 14,
    "restart_policy": "on-failure",
    "restart_policy_max": 5,
    "memory_limit": 512 * 1024 * 1024,
    "project": "myapp",
    "service": "worker",
    "working_dir": "/home/user/projects/myapp",
    "networks": [{"name": "myapp_default", "ip": ""}],
    "ports": "",
    "mounts": [],
    "health": None,
    "env": ["NODE_ENV=production", "QUEUE_URL=redis://redis:6379"],
    "last_logs": (
        "<--- Last few GCs --->\n"
        "[1:0x5f2a8c0]  4382919 ms: Mark-sweep 505.2 (515.4) -> 504.8 (515.6) MB\n"
        "FATAL ERROR: Reached heap limit Allocation failed - "
        "JavaScript heap out of memory\n"
        " 1: 0xb85bc0 node::Abort() [node]"
    ),
}

NETWORKS = [
    NetworkInfo(id="net1", name="myapp_default", driver="bridge", scope="local"),
    NetworkInfo(id="net2", name="monitoring_default", driver="bridge", scope="local"),
    NetworkInfo(id="net3", name="bridge", driver="bridge", scope="local"),
]


# ──────────────────────────────────────────────
#  Screenshot generation
# ──────────────────────────────────────────────

def capture(name: str, render_fn, width: int = 110, title: str = ""):
    console = Console(record=True, width=width, force_terminal=True)
    render_fn(console)
    svg = console.export_svg(
        title=title,
        code_format=CUSTOM_SVG_FORMAT,
        font_aspect_ratio=0.65,
    )
    path = f"docs/{name}.svg"
    with open(path, "w") as f:
        f.write(svg)
    print(f"  saved {path}")


def build_containers_by_project(containers):
    groups = {}
    for c in containers:
        groups.setdefault(c.project, []).append(c)
    return groups


def build_containers_by_image(containers):
    groups = {}
    for c in containers:
        groups.setdefault(c.image_id, []).append(c)
    return groups


def build_containers_by_volume(containers):
    groups = {}
    for c in containers:
        for m in c.mounts:
            if m.type == "volume" and m.name:
                groups.setdefault(m.name, []).append((c, m.destination))
    return groups


def build_containers_by_network(containers):
    groups = {}
    for c in containers:
        for n in c.networks:
            groups.setdefault(n.network_name, []).append((c, n.ip_address))
    return groups


def main():
    print("Generating screenshots with mock data...")

    # ps drops columns below width 130, so capture wide to show the full set
    capture("ps", lambda c: PsFormatter(c, False).render(
        build_containers_by_project(CONTAINERS)
    ), width=140, title="vdocker ps -a")

    running = [c for c in CONTAINERS if c.status == "running"]

    capture("images", lambda c: ImagesFormatter(c, False).render(
        (IMAGES, build_containers_by_image(running))
    ), title="vdocker images")

    capture("volumes", lambda c: VolumesFormatter(c, False).render(
        (VOLUMES, build_containers_by_volume(running))
    ), title="vdocker volumes")

    capture("networks", lambda c: NetworksFormatter(c, False).render(
        (NETWORKS, build_containers_by_network(running))
    ), title="vdocker networks")

    capture("tree", lambda c: TreeFormatter(c, False).render({
        "containers": running,
        "images": IMAGES,
        "volumes": VOLUMES,
        "networks": NETWORKS,
    }), title="vdocker tree")

    capture("ports", lambda c: PortsFormatter(c, False).render(PORT_ROWS),
            width=140, title="vdocker ports")

    capture("info", lambda c: InfoFormatter(c, False).render(INFO_DETAIL),
            width=100, title="vdocker info myapp-worker-1")

    print("Done!")


if __name__ == "__main__":
    main()
