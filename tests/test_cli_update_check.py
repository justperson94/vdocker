from click.testing import CliRunner

import vdocker.cli as cli_module
import vdocker.update_check as update_check


class EmptyCollector:
    def port_mappings(self):
        return []


def test_successful_command_checks_for_updates(monkeypatch):
    calls = []
    monkeypatch.setattr(cli_module, "get_collector", lambda show_all: EmptyCollector())
    monkeypatch.setattr(
        update_check,
        "notify_if_update_available",
        lambda console: calls.append(console),
    )

    result = CliRunner().invoke(cli_module.cli, ["ports"])

    assert result.exit_code == 0
    assert calls == [cli_module.err_console]


def test_json_output_skips_update_check(monkeypatch):
    calls = []
    monkeypatch.setattr(cli_module, "get_collector", lambda show_all: EmptyCollector())
    monkeypatch.setattr(
        update_check,
        "notify_if_update_available",
        lambda console: calls.append(console),
    )

    result = CliRunner().invoke(cli_module.cli, ["ports", "--json"])

    assert result.exit_code == 0
    assert calls == []
