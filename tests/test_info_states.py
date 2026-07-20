from rich.console import Console

from vdocker.formatters.info import InfoFormatter


def render(**overrides):
    detail = {
        "name": "c1", "id": "a" * 64, "status": "running",
        "image": "img:latest", "command": "run", "created": "",
        "started_at": None, "finished_at": None, "exit_code": 0,
        "oom_killed": False, "error": "", "restart_count": 0,
        "restart_policy": "no", "restart_policy_max": 0, "memory_limit": 0,
        "project": None, "service": None, "working_dir": None,
        "networks": [], "ports": "", "mounts": [], "health": None,
        "env": [], "last_logs": None,
    }
    detail.update(overrides)
    console = Console(record=True, width=100)
    InfoFormatter(console).render_rich(detail)
    return console.export_text()


class TestInfoStates:
    def test_paused_never_shows_exit_code(self):
        # regression: paused containers displayed "Exit code 0 — success"
        out = render(status="paused", exit_code=0)
        assert "Exit code" not in out
        assert "Started" in out
        assert "Paused" in out

    def test_restarting_shows_last_exit_code(self):
        out = render(status="restarting", exit_code=7, restart_count=10)
        assert "Restarting (7)" in out
        assert "Exit code" in out

    def test_exited_oom_death(self):
        out = render(status="exited", exit_code=137, oom_killed=True,
                     memory_limit=512 * 1024 * 1024)
        assert "OOM" in out
        assert "OOMKilled" in out
        assert "512.0MB" in out

    def test_created_is_clean(self):
        out = render(status="created", exit_code=0)
        assert "Exit code" not in out

    def test_env_hidden_by_default(self):
        out = render(env=["SECRET_KEY=abc"])
        assert "abc" not in out
        assert "--env" in out
