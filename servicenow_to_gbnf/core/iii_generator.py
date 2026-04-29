"""Generates ready-to-use iii Python workers from GBNF grammars."""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any


class IIIWorkerGenerator:
    """Renders Jinja templates for iii workers."""

    def __init__(self):
        self.template_dir = Path("servicenow_to_gbnf/templates")
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        grammar_path: Path,
        output_path: Path,
        iii_function_id: str,
        servicenow_instance: str,
        table: str = "incident",
    ) -> Path:
        """Generate full iii worker Python file."""
        template = self.env.get_template("worker.py.j2")

        context: Dict[str, Any] = {
            "iii_function_id": iii_function_id,
            "grammar_path": str(grammar_path.absolute()),
            "servicenow_instance": servicenow_instance.rstrip("/"),
            "table": table,
        }

        rendered = template.render(**context)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")

        # Also copy prompt template
        prompt_template = self.env.get_template("prompt.txt.j2")
        prompt_path = output_path.parent / "system_prompt.txt"
        prompt_path.write_text(prompt_template.render(), encoding="utf-8")

        return output_path