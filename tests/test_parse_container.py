from vdocker.docker_client import DockerCollector


class StubContainer:
    """Mimics the docker-py Container surface _parse_container touches."""

    def __init__(self, attrs):
        self.attrs = attrs
        self.id = attrs.get("Id", "c" * 64)
        self.name = attrs.get("Name", "/test").lstrip("/")
        self.status = (attrs.get("State") or {}).get("Status", "running")
        self.labels = ((attrs.get("Config") or {}).get("Labels")) or {}


def parse(**overrides):
    attrs = {
        "Id": "c" * 64,
        "Name": "/web-1",
        "Image": "sha256:" + "a" * 64,
        "Created": "2026-01-01T00:00:00Z",
        "State": {"Status": "running", "StartedAt": "2026-01-01T00:00:00Z"},
        "Config": {"Image": "nginx:latest", "Cmd": None, "Entrypoint": None,
                   "Labels": {}},
        "NetworkSettings": {"Ports": {}, "Networks": {}},
        "Mounts": [],
    }
    attrs.update(overrides)
    return DockerCollector._parse_container(StubContainer(attrs))


class TestParseContainer:
    def test_image_name_from_config(self):
        assert parse().image_name == "nginx:latest"

    def test_orphaned_image_falls_back_to_id(self):
        # image deleted out from under the container: Config.Image missing
        c = parse(Config={"Image": None, "Labels": {}})
        assert c.image_name.startswith("sha256:aaaaaaaaaaaa")
        # regression: this used to raise ImageNotFound via the c.image property

    def test_command_combines_entrypoint_and_cmd(self):
        c = parse(Config={"Image": "x", "Entrypoint": ["/entry.sh"],
                          "Cmd": ["serve", "--port", "80"], "Labels": {}})
        assert c.command == "/entry.sh serve --port 80"

    def test_entrypoint_only_command(self):
        c = parse(Config={"Image": "x", "Entrypoint": ["/kong-entrypoint.sh"],
                          "Cmd": None, "Labels": {}})
        assert c.command == "/kong-entrypoint.sh"

    def test_compose_labels(self):
        c = parse(Config={"Image": "x", "Labels": {
            "com.docker.compose.project": "myapp",
            "com.docker.compose.service": "web",
            "com.docker.compose.project.working_dir": "/srv/myapp",
        }})
        assert (c.project, c.service, c.working_dir) == \
            ("myapp", "web", "/srv/myapp")

    def test_port_bindings_wired(self):
        c = parse(NetworkSettings={
            "Ports": {"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]},
            "Networks": {},
        })
        assert c.ports == "8080->80/tcp"
        assert c.port_bindings[0].host_port == 8080
