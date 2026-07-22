import io
import json

from rich.console import Console

from vdocker import update_check


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def response_for(tag):
    return FakeResponse(json.dumps({"tag_name": tag}).encode())


class TestVersionComparison:
    def test_newer_release(self):
        assert update_check._is_newer("v0.5.1", "0.5.0")

    def test_equal_release_with_shorter_version(self):
        assert not update_check._is_newer("v0.5", "0.5.0")

    def test_older_and_invalid_releases(self):
        assert not update_check._is_newer("v0.4.9", "0.5.0")
        assert not update_check._is_newer("not-a-version", "0.5.0")


class TestUpdateCheck:
    def test_new_release_is_returned_and_cached(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "update-check.json"
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request, timeout))
            return response_for("v0.5.1")

        monkeypatch.setattr(update_check, "urlopen", fake_urlopen)

        assert update_check.check_for_update(
            "0.5.0", cache_file=cache_file, now=100,
        ) == "0.5.1"
        assert len(calls) == 1
        assert json.loads(cache_file.read_text())["latest"] == "v0.5.1"

        assert update_check.check_for_update(
            "0.5.0", cache_file=cache_file, now=101,
        ) is None
        assert len(calls) == 1

    def test_expired_cache_checks_again(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "update-check.json"
        cache_file.write_text(json.dumps({"checked_at": 10, "latest": "v0.5.1"}))
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(1)
            return response_for("v0.5.1")

        monkeypatch.setattr(update_check, "urlopen", fake_urlopen)
        now = 10 + update_check.CHECK_INTERVAL

        assert update_check.check_for_update(
            "0.5.0", cache_file=cache_file, now=now,
        ) == "0.5.1"
        assert len(calls) == 1

    def test_network_failure_is_silent_and_cached(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "update-check.json"

        def fail(request, timeout):
            raise OSError("offline")

        monkeypatch.setattr(update_check, "urlopen", fail)

        assert update_check.check_for_update(
            "0.5.0", cache_file=cache_file, now=100,
        ) is None
        assert json.loads(cache_file.read_text()) == {
            "checked_at": 100,
            "latest": None,
        }

    def test_unknown_development_version_skips_network(self, tmp_path, monkeypatch):
        def unexpected(request, timeout):
            raise AssertionError("network should not be used")

        monkeypatch.setattr(update_check, "urlopen", unexpected)
        assert update_check.check_for_update(
            "0+unknown", cache_file=tmp_path / "cache", now=100,
        ) is None


class TestUpdateNotification:
    def test_colored_notification_contains_upgrade_command(self, monkeypatch):
        output = io.StringIO()
        console = Console(
            file=output,
            force_terminal=True,
            color_system="standard",
            record=True,
            width=80,
        )
        monkeypatch.setattr(update_check, "check_for_update", lambda: "0.5.1")

        update_check.notify_if_update_available(console)

        rendered = output.getvalue()
        plain = console.export_text(styles=False)
        assert "\x1b[" in rendered
        assert "Update available:" in plain
        assert "0.5.1" in plain
        assert update_check.UPGRADE_COMMAND in plain

    def test_environment_variable_disables_notification(self, monkeypatch):
        monkeypatch.setenv("VDOCKER_NO_UPDATE_CHECK", "1")
        monkeypatch.setattr(
            update_check,
            "check_for_update",
            lambda: (_ for _ in ()).throw(AssertionError("should be disabled")),
        )

        update_check.notify_if_update_available(Console(file=io.StringIO()))
