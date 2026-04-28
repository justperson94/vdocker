from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from rich.console import Console


class BaseFormatter:
    def __init__(self, console: Console, json_output: bool = False):
        self.console = console
        self.json_output = json_output

    def render(self, data: Any) -> None:
        if self.json_output:
            self.render_json(data)
        else:
            self.render_rich(data)

    def render_json(self, data: Any) -> None:
        if isinstance(data, list):
            output = [asdict(d) if hasattr(d, "__dataclass_fields__") else d for d in data]
        elif hasattr(data, "__dataclass_fields__"):
            output = asdict(data)
        else:
            output = data
        self.console.print_json(json.dumps(output, default=str))

    def render_rich(self, data: Any) -> None:
        raise NotImplementedError
