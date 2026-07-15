from __future__ import annotations

import sys

import click
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def common_options(f):
    f = click.option("-a", "--all", "show_all", is_flag=True, help="Include stopped containers")(f)
    f = click.option("--json", "json_output", is_flag=True, help="Output as JSON")(f)
    return f


def get_collector(show_all: bool):
    try:
        from vdocker.docker_client import DockerCollector
        return DockerCollector(show_all=show_all)
    except Exception as e:
        err_console.print(f"[red]Error:[/red] Cannot connect to Docker. Is Docker running?\n{e}")
        sys.exit(1)


@click.group()
@click.version_option(package_name="vdocker", prog_name="vdocker")
def cli():
    """vdocker — Visualize Docker objects and their relationships."""


@cli.command()
@common_options
def ps(show_all: bool, json_output: bool):
    """Show containers grouped by compose project."""
    collector = get_collector(show_all)
    data = collector.containers_by_project()

    if not data:
        console.print("[dim]No containers found.[/dim]")
        return

    from vdocker.formatters.ps import PsFormatter
    PsFormatter(console, json_output).render(data)


@cli.command()
@common_options
@click.option("--unused", is_flag=True, help="Show images without containers too")
def images(show_all: bool, json_output: bool, unused: bool):
    """Show images with dependent containers."""
    collector = get_collector(show_all)
    all_images = collector.get_images()
    containers_by_image = collector.containers_by_image()

    if not all_images:
        console.print("[dim]No images found.[/dim]")
        return

    from vdocker.formatters.images import ImagesFormatter
    ImagesFormatter(console, json_output, show_unused=unused).render((all_images, containers_by_image))


@cli.command()
@common_options
def volumes(show_all: bool, json_output: bool):
    """Show volumes with mounted containers."""
    collector = get_collector(show_all)
    all_volumes = collector.get_volumes()
    containers_by_volume = collector.containers_by_volume()

    if not all_volumes:
        console.print("[dim]No volumes found.[/dim]")
        return

    from vdocker.formatters.volumes import VolumesFormatter
    VolumesFormatter(console, json_output).render((all_volumes, containers_by_volume))


@cli.command()
@common_options
def networks(show_all: bool, json_output: bool):
    """Show networks with connected containers."""
    collector = get_collector(show_all)
    all_networks = collector.get_networks()
    containers_by_network = collector.containers_by_network()

    if not all_networks:
        console.print("[dim]No networks found.[/dim]")
        return

    from vdocker.formatters.networks import NetworksFormatter
    NetworksFormatter(console, json_output).render((all_networks, containers_by_network))


@cli.command()
@common_options
def ports(show_all: bool, json_output: bool):
    """Show all exposed port mappings."""
    collector = get_collector(show_all)
    data = collector.port_mappings()

    from vdocker.formatters.ports import PortsFormatter
    PortsFormatter(console, json_output).render(data)


@cli.command()
@common_options
def tree(show_all: bool, json_output: bool):
    """Show full relationship tree."""
    collector = get_collector(show_all)
    data = {
        "containers": collector.get_containers(),
        "images": collector.get_images(),
        "volumes": collector.get_volumes(),
        "networks": collector.get_networks(),
    }

    from vdocker.formatters.tree import TreeFormatter
    TreeFormatter(console, json_output).render(data)


def complete_container(ctx, param, incomplete):
    """Shell completion: running container names starting with `incomplete`."""
    try:
        from vdocker.docker_client import DockerCollector
        names = [c.name for c in DockerCollector().get_containers()]
    except Exception:
        return []
    return [n for n in names if n.startswith(incomplete)]


@cli.command(name="exec")
@click.argument("container", shell_complete=complete_container)
@click.argument("shell", required=False)
def exec_(container: str, shell: str | None):
    """Open an interactive shell inside a running container.

    With no SHELL argument, tries bash and falls back to sh.
    If a SHELL is given explicitly, it must exist in the container.
    """
    import shutil

    if shutil.which("docker") is None:
        err_console.print("[red]Error:[/red] 'docker' CLI not found in PATH.")
        sys.exit(1)

    def shell_exists(name: str) -> bool:
        import subprocess
        result = subprocess.run(
            ["docker", "exec", container, "sh", "-c",
             f"command -v {shlex_quote(name)}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0

    if shell:
        if not shell_exists(shell):
            err_console.print(
                f"[red]Error:[/red] '{shell}' not found in container "
                f"'{container}'."
            )
            sys.exit(1)
        chosen = shell
    else:
        chosen = "bash" if shell_exists("bash") else "sh"

    import os
    os.execvp("docker", ["docker", "exec", "-it", container, chosen])


def shlex_quote(s: str) -> str:
    import shlex
    return shlex.quote(s)


if __name__ == "__main__":
    cli()
