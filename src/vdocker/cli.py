from __future__ import annotations

import sys

import click
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


json_option = click.option("--json", "json_output", is_flag=True, help="Output as JSON")


def common_options(f):
    f = click.option("-a", "--all", "show_all", is_flag=True, help="Include stopped containers")(f)
    return json_option(f)


def friendly_errors(f):
    """Surface daemon/API failures mid-command as clean errors, not tracebacks."""
    import functools

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            import docker as _docker
            from rich.markup import escape
            transient = isinstance(e, _docker.errors.DockerException) or \
                e.__class__.__module__.startswith(("requests", "urllib3"))
            if not transient:
                raise
            err_console.print(f"[red]Error:[/red] {escape(str(e))}")
            sys.exit(1)
    return wrapper


def get_collector(show_all: bool):
    try:
        from vdocker.docker_client import DockerCollector
        return DockerCollector(show_all=show_all)
    except Exception as e:
        from rich.markup import escape
        err_console.print(
            f"[red]Error:[/red] Cannot connect to Docker. "
            f"Is Docker running?\n{escape(str(e))}")
        sys.exit(1)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="vdocker", prog_name="vdocker")
def cli():
    """vdocker — Visualize Docker objects and their relationships."""


@cli.command()
@common_options
@friendly_errors
def ps(show_all: bool, json_output: bool):
    """Show containers grouped by compose project."""
    collector = get_collector(show_all)
    data = collector.containers_by_project()

    if not data and not json_output:
        console.print("[dim]No containers found.[/dim]")
        return

    from vdocker.formatters.ps import PsFormatter
    PsFormatter(console, json_output).render(data)


@cli.command()
@json_option
@click.option("--unused", is_flag=True, help="Show images without containers too")
@friendly_errors
def images(json_output: bool, unused: bool):
    """Show images with dependent containers."""
    collector = get_collector(False)
    all_images = collector.get_images()
    containers_by_image = collector.containers_by_image()

    if not all_images and not json_output:
        console.print("[dim]No images found.[/dim]")
        return

    from vdocker.formatters.images import ImagesFormatter
    ImagesFormatter(console, json_output, show_unused=unused).render((all_images, containers_by_image))


@cli.command()
@json_option
@friendly_errors
def volumes(json_output: bool):
    """Show volumes with mounted containers."""
    collector = get_collector(False)
    collector.prefetch_volume_sizes()  # `docker system df` is slow — overlap it
    containers_by_volume = collector.containers_by_volume()
    all_volumes = collector.get_volumes()  # joins the df prefetch

    if not all_volumes and not json_output:
        console.print("[dim]No volumes found.[/dim]")
        return

    from vdocker.formatters.volumes import VolumesFormatter
    VolumesFormatter(console, json_output).render((all_volumes, containers_by_volume))


@cli.command()
@json_option
@friendly_errors
def networks(json_output: bool):
    """Show networks with connected containers."""
    collector = get_collector(False)
    all_networks = collector.get_networks()
    containers_by_network = collector.containers_by_network()

    if not all_networks and not json_output:
        console.print("[dim]No networks found.[/dim]")
        return

    from vdocker.formatters.networks import NetworksFormatter
    NetworksFormatter(console, json_output).render((all_networks, containers_by_network))


@cli.command()
@json_option
@friendly_errors
def ports(json_output: bool):
    """Show all exposed port mappings."""
    collector = get_collector(False)
    data = collector.port_mappings()

    from vdocker.formatters.ports import PortsFormatter
    PortsFormatter(console, json_output).render(data)


@cli.command()
@common_options
@friendly_errors
def tree(show_all: bool, json_output: bool):
    """Show full relationship tree."""
    collector = get_collector(show_all)
    collector.prefetch_volume_sizes()  # `docker system df` is slow — overlap it
    data = {
        "containers": collector.get_containers(),
        # usage must consider stopped containers too, or a stopped
        # container's image/volume shows up under "Unused Resources"
        "usage_containers": collector.get_all_containers(),
        "images": collector.get_images(),
        "volumes": collector.get_volumes(),
        "networks": collector.get_networks(),
    }

    from vdocker.formatters.tree import TreeFormatter
    TreeFormatter(console, json_output).render(data)


def _container_names(all_states: bool, running_only: bool) -> list[str]:
    """Container names via one raw list call — completion runs per keystroke,
    so avoid docker-py's per-container inspects."""
    from vdocker.docker_client import DockerCollector
    client = DockerCollector._connect()
    try:
        rows = client.api.containers(all=all_states)
    finally:
        try:
            client.close()
        except Exception:
            pass
    names = []
    for r in rows:
        if running_only and r.get("State") != "running":
            continue
        for n in r.get("Names") or []:
            names.append(n.lstrip("/"))
    return names


def complete_container(ctx, param, incomplete):
    """Shell completion: exec-able (running, not paused) container names."""
    try:
        names = _container_names(all_states=False, running_only=True)
    except Exception:
        return []
    return [n for n in names if n.startswith(incomplete)]


def complete_any_container(ctx, param, incomplete):
    """Shell completion: all container names, including stopped ones."""
    try:
        names = _container_names(all_states=True, running_only=False)
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
        from docker.errors import APIError, NotFound
        from rich.markup import escape
        if isinstance(e, NotFound):
            err_console.print(
                f"[red]Error:[/red] No such container: '{escape(container)}'")
        elif isinstance(e, APIError) and "multiple" in str(e).lower():
            err_console.print(
                f"[red]Error:[/red] '{escape(container)}' matches multiple "
                f"containers — use more of the ID or the full name.")
        else:
            err_console.print(f"[red]Error:[/red] {escape(str(e))}")
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

    from rich.markup import escape

    if shutil.which("docker") is None:
        err_console.print("[red]Error:[/red] 'docker' CLI not found in PATH.")
        sys.exit(1)

    # A stopped container makes every shell probe fail with a misleading
    # "shell not found" — check the container state first. --type container
    # keeps a same-named image/network from matching (or clashing).
    state = subprocess.run(
        ["docker", "inspect", "--type", "container",
         "-f", "{{.State.Status}}", "--", container],
        capture_output=True, text=True,
    )
    if state.returncode != 0:
        stderr = state.stderr.strip()
        # "no such object/container" = bad name; anything else (e.g. a
        # dial error, whose text also contains "no such file") = daemon issue
        low = stderr.lower()
        if "no such object" in low or "no such container" in low:
            err_console.print(
                f"[red]Error:[/red] No such container: '{escape(container)}'")
        else:
            # e.g. the daemon is unreachable — don't blame the container
            detail = stderr.splitlines()[-1] if stderr else "unknown docker error"
            err_console.print(f"[red]Error:[/red] {escape(detail)}")
        sys.exit(1)
    status = state.stdout.strip()
    if status != "running":
        name = escape(container)
        hints = {
            "paused": f"Unpause it first: docker unpause {name}",
            "restarting": f"It is crash-looping — check: vdocker info {name}",
        }
        hint = hints.get(status, f"Start it first: docker start {name}")
        err_console.print(
            f"[red]Error:[/red] Container '{name}' is not running "
            f"(status: {escape(status)}). {hint}"
        )
        sys.exit(1)

    if shell:
        probe = subprocess.run(
            ["docker", "exec", "--", container, "sh", "-c",
             f"command -v {shlex.quote(shell)}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if probe.returncode != 0:
            err_console.print(
                f"[red]Error:[/red] '{escape(shell)}' not found in container "
                f"'{escape(container)}'."
            )
            sys.exit(1)
        argv = [shell]
    else:
        # Single round-trip: pick bash inside the container, fall back to sh
        argv = ["sh", "-c",
                "command -v bash >/dev/null 2>&1 && exec bash || exec sh"]

    import os

    # Without a real TTY, docker's -t fails ("the input device is not a TTY")
    tty = sys.stdin.isatty() and sys.stdout.isatty()
    docker_argv = ["docker", "exec", "-it" if tty else "-i",
                   "--", container, *argv]
    if os.name == "nt":
        # execvp on Windows is spawn-emulated and garbles the console
        sys.exit(subprocess.run(docker_argv).returncode)
    os.execvp("docker", docker_argv)


if __name__ == "__main__":
    cli()
