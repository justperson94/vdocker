from vdocker.docker_client import DockerCollector
from vdocker.models import ContainerInfo


def make_container(name, project=None, service=None):
    return ContainerInfo(
        id=f"id-{name}", name=name, status="running",
        image_id="img", image_name="img:latest", command="cmd",
        created="2026-01-01T00:00:00Z", ports="",
        project=project, service=service, working_dir=None,
        started_at="2026-01-01T00:00:00Z",
    )


def collector_with(containers):
    """A DockerCollector with a pre-seeded cache — no daemon needed."""
    c = DockerCollector.__new__(DockerCollector)
    c._show_all = False
    c._containers = containers
    c._volume_sizes = {}
    return c


class TestContainersByProject:
    def test_grouped_by_compose_project(self):
        col = collector_with([
            make_container("web-1", project="myapp", service="web"),
            make_container("db-1", project="myapp", service="db"),
            make_container("grafana-1", project="mon", service="grafana"),
        ])
        groups = col.containers_by_project()
        assert {c.name for c in groups["myapp"]} == {"web-1", "db-1"}
        assert [c.name for c in groups["mon"]] == ["grafana-1"]

    def test_standalone_grouped_under_none(self):
        col = collector_with([make_container("redis-test")])
        groups = col.containers_by_project()
        assert [c.name for c in groups[None]] == ["redis-test"]

    def test_empty(self):
        assert collector_with([]).containers_by_project() == {}
