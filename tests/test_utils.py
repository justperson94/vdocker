from datetime import datetime, timedelta, timezone

from vdocker.utils import (
    describe_exit_code,
    format_created,
    format_size,
    format_uptime,
    status_style,
)


class TestFormatSize:
    def test_zero(self):
        assert format_size(0) == "0B"

    def test_none(self):
        assert format_size(None) == "N/A"

    def test_negative(self):
        assert format_size(-1) == "N/A"

    def test_bytes(self):
        assert format_size(512) == "512B"

    def test_megabytes(self):
        assert format_size(44_800_000) == "42.7MB"

    def test_gigabytes(self):
        assert format_size(9_200_000_000) == "8.6GB"


class TestFormatCreated:
    def test_empty(self):
        assert format_created("") == ""

    def test_invalid(self):
        assert format_created("not-a-date") == ""

    def test_days_ago(self):
        ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        assert format_created(ts) == "3d ago"

    def test_docker_z_suffix(self):
        ts = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        assert format_created(ts) == "2h ago"


class TestFormatUptime:
    def test_not_running(self):
        assert format_uptime(None, "exited") == "Exited"

    def test_running(self):
        ts = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        assert format_uptime(ts, "running") == "Up 2d"


class TestDescribeExitCode:
    def test_success(self):
        assert describe_exit_code(0) == "success"

    def test_app_error(self):
        assert describe_exit_code(1) == "application error"

    def test_command_not_found(self):
        assert describe_exit_code(127) == "command not found"

    def test_sigkill(self):
        assert "SIGKILL" in describe_exit_code(137)

    def test_sigterm(self):
        assert "SIGTERM" in describe_exit_code(143)

    def test_sigsegv(self):
        assert "SIGSEGV" in describe_exit_code(139)

    def test_oom_overrides(self):
        assert "OOM" in describe_exit_code(137, oom_killed=True)

    def test_unknown_plain_code(self):
        assert describe_exit_code(42) == ""


class TestStatusStyle:
    def test_known(self):
        assert status_style("running") == "green"
        assert status_style("exited") == "red"

    def test_unknown(self):
        assert status_style("whatever") == "white"
