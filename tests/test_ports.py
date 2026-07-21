from vdocker.docker_client import DockerCollector
from vdocker.models import PortBinding


def parse(ports_dict):
    return DockerCollector._parse_port_bindings(ports_dict)


class TestParsePortBindings:
    def test_empty(self):
        assert parse({}) == []
        assert parse(None) == []

    def test_unpublished_port(self):
        assert parse({"80/tcp": None}) == []

    def test_basic_mapping(self):
        result = parse({"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]})
        assert result == [PortBinding("0.0.0.0", 8080, 80, "tcp")]

    def test_ipv6_duplicates_dropped(self):
        result = parse({"80/tcp": [
            {"HostIp": "0.0.0.0", "HostPort": "8080"},
            {"HostIp": "::", "HostPort": "8080"},
        ]})
        assert len(result) == 1
        assert result[0].host_ip == "0.0.0.0"

    def test_localhost_bind_kept(self):
        result = parse({"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "5432"}]})
        assert result[0].host_ip == "127.0.0.1"

    def test_missing_host_ip_defaults(self):
        result = parse({"80/tcp": [{"HostPort": "80"}]})
        assert result[0].host_ip == "0.0.0.0"

    def test_sorted_by_host_port(self):
        result = parse({
            "9090/tcp": [{"HostIp": "0.0.0.0", "HostPort": "9090"}],
            "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "80"}],
        })
        assert [b.host_port for b in result] == [80, 9090]

    def test_udp_protocol(self):
        result = parse({"53/udp": [{"HostIp": "0.0.0.0", "HostPort": "53"}]})
        assert result[0].protocol == "udp"


class TestFormatPorts:
    def test_empty(self):
        assert DockerCollector._format_ports([]) == ""

    def test_default_bind_hides_ip(self):
        s = DockerCollector._format_ports([PortBinding("0.0.0.0", 8080, 80, "tcp")])
        assert s == "8080->80/tcp"

    def test_specific_bind_shows_ip(self):
        s = DockerCollector._format_ports([PortBinding("127.0.0.1", 5432, 5432, "tcp")])
        assert s == "127.0.0.1:5432->5432/tcp"

    def test_multiple_joined(self):
        s = DockerCollector._format_ports([
            PortBinding("0.0.0.0", 80, 80, "tcp"),
            PortBinding("0.0.0.0", 443, 443, "tcp"),
        ])
        assert s == "80->80/tcp, 443->443/tcp"


class TestIPv6OnlyBindings:
    def test_ipv6_only_publish_is_kept(self):
        # docker run -p '[::1]:8080:80' — no IPv4 twin exists
        result = parse({"80/tcp": [{"HostIp": "::1", "HostPort": "8080"}]})
        assert len(result) == 1
        assert result[0].host_ip == "::1"

    def test_dual_stack_still_deduplicated(self):
        result = parse({"80/tcp": [
            {"HostIp": "0.0.0.0", "HostPort": "8080"},
            {"HostIp": "::", "HostPort": "8080"},
        ]})
        assert [b.host_ip for b in result] == ["0.0.0.0"]
