"""Generate SVG screenshots for README using mock data."""

from rich.console import Console

from vdocker.formatters.images import ImagesFormatter
from vdocker.formatters.networks import NetworksFormatter
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
        created="2026-04-26T10:00:00Z",
        ports="80->80/tcp, :::80->80/tcp",
        project="myapp",
        service="web",
        started_at="2026-04-26T10:00:00Z",
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
        created="2026-04-26T10:00:00Z",
        ports="3000->3000/tcp",
        project="myapp",
        service="api",
        started_at="2026-04-26T10:00:00Z",
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
        created="2026-04-26T10:00:00Z",
        ports="5432->5432/tcp",
        project="myapp",
        service="db",
        started_at="2026-04-26T10:00:00Z",
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
        created="2026-04-23T08:00:00Z",
        ports="3001->3000/tcp",
        project="monitoring",
        service="grafana",
        started_at="2026-04-23T08:00:00Z",
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
        created="2026-04-23T08:00:00Z",
        ports="9090->9090/tcp",
        project="monitoring",
        service="prometheus",
        started_at="2026-04-23T08:00:00Z",
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
        created="2026-04-27T12:00:00Z",
        ports="6379->6379/tcp",
        project=None,
        service=None,
        started_at="2026-04-27T12:00:00Z",
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
        created="2026-04-25T06:00:00Z",
        ports="",
        project="myapp",
        service="worker",
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
    svg = console.export_svg(title=title)
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

    capture("ps", lambda c: PsFormatter(c, False).render(
        build_containers_by_project(CONTAINERS)
    ), title="vdocker ps -a")

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

    print("Done!")


if __name__ == "__main__":
    main()
