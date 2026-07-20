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


json_option = click.option("--json", "json_output", is_flag=True, help="Output as JSON")


def get_collector(show_all: bool):
    try:
        from vdocker.docker_client import DockerCollector
        return DockerCollector(show_all=show_all)
    except Exception as e:
        err_console.print(f"[red]Error:[/red] Cannot connect to Docker. Is Docker running?\n{e}")
        sys.exit(1)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
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
@json_option
@click.option("--unused", is_flag=True, help="Show images without containers too")
def images(json_output: bool, unused: bool):
    """Show images with dependent containers."""
    collector = get_collector(False)
    all_images = collector.get_images()
    containers_by_image = collector.containers_by_image()

    if not all_images:
        console.print("[dim]No images found.[/dim]")
        return

    from vdocker.formatters.images import ImagesFormatter
    ImagesFormatter(console, json_output, show_unused=unused).render((all_images, containers_by_image))


@cli.command()
@json_option
def volumes(json_output: bool):
    """Show volumes with mounted containers."""
    collector = get_collector(False)
    collector.prefetch_volume_sizes()  # `docker system df` is slow — overlap it
    containers_by_volume = collector.containers_by_volume()
    all_volumes = collector.get_volumes()  # joins the df prefetch

    if not all_volumes:
        console.print("[dim]No volumes found.[/dim]")
        return

    from vdocker.formatters.volumes import VolumesFormatter
    VolumesFormatter(console, json_output).render((all_volumes, containers_by_volume))


@cli.command()
@json_option
def networks(json_output: bool):
    """Show networks with connected containers."""
    collector = get_collector(False)
    all_networks = collector.get_networks()
    containers_by_network = collector.containers_by_network()

    if not all_networks:
        console.print("[dim]No networks found.[/dim]")
        return

    from vdocker.formatters.networks import NetworksFormatter
    NetworksFormatter(console, json_output).render((all_networks, containers_by_network))


@cli.command()
@json_option
def ports(json_output: bool):
    """Show all exposed port mappings."""
    collector = get_collector(False)
    data = collector.port_mappings()

    from vdocker.formatters.ports import PortsFormatter
    PortsFormatter(console, json_output).render(data)


@cli.command()
@common_options
def tree(show_all: bool, json_output: bool):
    """Show full relationship tree."""
    collector = get_collector(show_all)
    collector.prefetch_volume_sizes()  # `docker system df` is slow — overlap it
    data = {
        "containers": collector.get_containers(),
        "images": collector.get_images(),
        "volumes": collector.get_volumes(),
        "networks": collector.get_networks(),
    }

    from vdocker.formatters.tree import TreeFormatter
    TreeFormatter(console, json_output).render(data)


def complete_container(ctx, param, incomplete):
    """Shell completion: exec-able (running, not paused) container names."""
    try:
        from vdocker.docker_client import DockerCollector
        names = [c.name for c in DockerCollector().get_containers()
                 if c.status == "running"]
    except Exception:
        return []
    return [n for n in names if n.startswith(incomplete)]


def complete_any_container(ctx, param, incomplete):
    """Shell completion: all container names, including stopped ones."""
    try:
        from vdocker.docker_client import DockerCollector
        names = [c.name for c in DockerCollector(show_all=True).get_containers()]
    except Exception:
        return []
    return [n for n in names if n.startswith(incomplete)]


@cli.command()
@click.argument("container", shell_complete=complete_any_container)
@click.option("--env", "show_env", is_flag=True,
              help="Show environment variables (sensitive values masked)")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def info(container: str, show_env: bool, json_output: bool):
    """Show a one-screen summary of a container.

    Includes state, network, mounts — and for dead containers, the decoded
    exit code, OOM status, and last log lines so you can see why it died.
    """
    collector = get_collector(False)
    try:
        detail = collector.get_container_detail(container)
    except Exception as e:
        from docker.errors import NotFound
        if isinstance(e, NotFound):
            err_console.print(f"[red]Error:[/red] No such container: '{container}'")
        else:
            err_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    from vdocker.formatters.info import InfoFormatter
    InfoFormatter(console, json_output, show_env=show_env).render(detail)


@cli.command(name="exec")
@click.argument("container", shell_complete=complete_container)
@click.argument("shell", required=False)
def exec_(container: str, shell: str | None):
    """Open an interactive shell inside a running container.

    With no SHELL argument, tries bash and falls back to sh.
    If a SHELL is given explicitly, it must exist in the container.
    """
    import shlex
    import shutil
    import subprocess

    if shutil.which("docker") is None:
        err_console.print("[red]Error:[/red] 'docker' CLI not found in PATH.")
        sys.exit(1)

    # A stopped container makes every shell probe fail with a misleading
    # "shell not found" — check the container state first.
    state = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Status}}", container],
        capture_output=True, text=True,
    )
    if state.returncode != 0:
        err_console.print(f"[red]Error:[/red] No such container: '{container}'")
        sys.exit(1)
    status = state.stdout.strip()
    if status != "running":
        hints = {
            "paused": f"Unpause it first: docker unpause {container}",
            "restarting": f"It is crash-looping — check: vdocker info {container}",
        }
        hint = hints.get(status, f"Start it first: docker start {container}")
        err_console.print(
            f"[red]Error:[/red] Container '{container}' is not running "
            f"(status: {status}). {hint}"
        )
        sys.exit(1)

    if shell:
        probe = subprocess.run(
            ["docker", "exec", container, "sh", "-c",
             f"command -v {shlex.quote(shell)}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if probe.returncode != 0:
            err_console.print(
                f"[red]Error:[/red] '{shell}' not found in container "
                f"'{container}'."
            )
            sys.exit(1)
        argv = [shell]
    else:
        # Single round-trip: pick bash inside the container, fall back to sh
        argv = ["sh", "-c",
                "command -v bash >/dev/null 2>&1 && exec bash || exec sh"]

    import os
    os.execvp("docker", ["docker", "exec", "-it", container, *argv])


if __name__ == "__main__":
    cli()
