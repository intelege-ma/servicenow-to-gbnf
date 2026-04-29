"""Generates ready-to-use iii Python workers from a GBNF grammar."""
from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from servicenow_to_gbnf import __version__


class IIIWorkerGenerator:
    """Renders Jinja2 templates for an iii worker + system prompt."""

    TEMPLATE_DIR: Path = Path(__file__).parent.parent / "templates"

    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(self.TEMPLATE_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def generate(
        self,
        grammar_path: Path,
        output_path: Path,
        iii_function_id: str,
        servicenow_instance: str,
        table: str = "incident",
        fields: Optional[Iterable[str]] = None,
    ) -> Path:
        """Render and write a complete iii worker + system prompt."""
        grammar_path = Path(grammar_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        context: dict[str, Any] = {
            "iii_function_id": iii_function_id,
            "python_function_name": self._python_identifier(iii_function_id),
            "grammar_filename": grammar_path.name,
            "servicenow_instance": servicenow_instance.rstrip("/"),
            "table": table,
            "fields": list(fields) if fields else self._default_fields(),
            "http_api_path": self._http_api_path(iii_function_id),
            "tool_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }

        worker_template = self.env.get_template("worker.py.j2")
        output_path.write_text(worker_template.render(**context), encoding="utf-8")

        prompt_template = self.env.get_template("prompt.txt.j2")
        prompt_path = output_path.parent / "system_prompt.txt"
        prompt_path.write_text(prompt_template.render(**context), encoding="utf-8")

        return output_path

    @staticmethod
    def _python_identifier(iii_function_id: str) -> str:
        """Turn an iii function id into a valid Python identifier.

        ``sn::incident-create`` -> ``sn_incident_create``.
        """
        cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", iii_function_id)
        cleaned = cleaned.strip("_")
        if not cleaned or cleaned[0].isdigit():
            cleaned = "fn_" + cleaned
        return cleaned

    @staticmethod
    def _http_api_path(iii_function_id: str) -> str:
        return iii_function_id.replace("::", "/").replace(":", "/")

    @staticmethod
    def _default_fields() -> list[str]:
        return [
            "short_description (string, required) - one-line title",
            "description (string, required) - full incident description",
            "priority (enum '1'..'5')",
            "state (enum '1','2','3','6','7','8')",
            "impact (enum '1','2','3')",
            "urgency (enum '1','2','3')",
            "category (string)",
            "assignment_group (string, sys_id of group)",
        ]
