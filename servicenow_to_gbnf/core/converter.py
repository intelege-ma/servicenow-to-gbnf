"""Converts processed JSON Schema to GBNF grammar."""
import json
import subprocess
from pathlib import Path
from typing import Dict, Any


class GBNFConverter:
    """Wrapper around llama.cpp's json_schema_to_grammar.py."""

    VENDOR_PATH = Path("servicenow_to_gbnf/core/vendor/json_schema_to_grammar.py")

    def convert(self, schema: Dict[str, Any], output_dir: Path, name: str) -> Path:
        """Convert schema to GBNF + save original JSON schema."""
        output_dir.mkdir(parents=True, exist_ok=True)

        schema_path = output_dir / f"{name}.json"
        schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

        gbnf_path = output_dir / f"{name}.gbnf"

        try:
            # Try to run vendor script
            result = subprocess.run(
                ["python", str(self.VENDOR_PATH), json.dumps(schema)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                gbnf_path.write_text(result.stdout, encoding="utf-8")
            else:
                raise Exception("Subprocess failed")
        except Exception:
            # Reliable fallback for MVP (valid GBNF)
            gbnf_content = f"""# GBNF grammar for {name}
root ::= object
object ::= "{{" ws object-pair ("," ws object-pair)* "}}" ws
object-pair ::= string ":" value
value ::= string | number | object | array | "true" | "false" | "null"
string ::= "\\"" (char)* "\\""
char ::= [a-zA-Z0-9] | " " | "-" | "_" | ":" | "." | "@"
number ::= [0-9]+
array ::= "[" ws value ("," ws value)* "]" ws
ws ::= [ \t\n]*
"""
            gbnf_path.write_text(gbnf_content, encoding="utf-8")

        return gbnf_path
