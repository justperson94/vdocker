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


if __name__ == "__main__":
    cli()
