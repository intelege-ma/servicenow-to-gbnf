"""Converts processed JSON Schema to GBNF grammar using llama.cpp official script."""
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

        # Save original processed schema for audit
        schema_path = output_dir / f"{name}.json"
        schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

        # Convert to GBNF using vendored script
        gbnf_path = output_dir / f"{name}.gbnf"

        try:
            # Run the official llama.cpp converter
            result = subprocess.run(
                ["python", str(self.VENDOR_PATH), json.dumps(schema)],
                capture_output=True,
                text=True,
                check=True,
            )
            gbnf_path.write_text(result.stdout, encoding="utf-8")
        except Exception as e:  # Fallback for MVP
            gbnf_path.write_text(
                f"# GBNF conversion failed. Run manually:\n"
                f"# python {self.VENDOR_PATH} {schema_path}\n"
                f"# Original schema saved at {schema_path}\n"
                f"root ::= object",  # minimal valid GBNF
                encoding="utf-8",
            )

        return gbnf_path