from rich.console import Console

from vdocker.formatters.ports import PortsFormatter
from vdocker.formatters.ps import PsFormatter
from vdocker.models import ContainerInfo


def recording_console(width=300):
    return Console(record=True, force_terminal=True, color_system=None, width=width)


class TestRichMarkupEscaping:
    def test_ps_escapes_rich_markup_in_untrusted_fields(self):
        console = recording_console()
        container = ContainerInfo(
            id="c" * 64,
            name="web",
            status="running",
            image_id="sha256:" + "a" * 64,
            image_name="[red]evil[/red]",
            command="echo [blink]owned[/blink]",
            created="",
            ports="[link=https://example.test]80->80/tcp[/link]",
            project=None,
            service=None,
            working_dir=None,
            started_at=None,
        )

        PsFormatter(console).render({"[blue]project[/blue]": [container]})

        output = console.export_text(styles=False)
        assert "[red]evil[/red]" in output
        assert '"echo [blink]owned' in output
        assert "[link=https://example.test]80->80/tcp[/link]" in output

    def test_ports_escapes_rich_markup_in_untrusted_fields(self):
        console = recording_console()
        PortsFormatter(console).render([
            {
                "host_port": 8080,
                "bind": "[yellow]127.0.0.1[/yellow]",
                "container_port": 80,
                "protocol": "[red]tcp[/red]",
                "container_name": "[green]web[/green]",
                "image": "[blue]nginx[/blue]",
                "network": "[magenta]bridge[/magenta]",
                "project": "[cyan]demo[/cyan]",
            }
        ])

        output = console.export_text(styles=False)
        assert "[red]tcp[/red]" in output
        assert "[green]web[/green]" in output
        assert "[blue]nginx[/blue]" in output
        assert "[magenta]bridge[/magenta]" in output
        assert "[[cyan]demo[/cyan]]" in output
