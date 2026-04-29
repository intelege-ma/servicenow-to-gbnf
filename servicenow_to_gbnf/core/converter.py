"""Converts processed JSON Schema to GBNF grammar via the vendored llama.cpp script.

Writes three files alongside the grammar:
    <name>.gbnf       - the GBNF grammar itself
    <name>.json       - the processed JSON Schema (audit copy)
    <name>.meta.json  - generation metadata (timestamp, sha, source)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from servicenow_to_gbnf import __version__


class GBNFConversionError(RuntimeError):
    """Raised when the vendored llama.cpp script fails to convert a schema."""


class GBNFConverter:
    """Wrapper around llama.cpp's `json_schema_to_grammar.py`.

    The vendored script is invoked as a subprocess of the *current* Python
    interpreter (so a venv install always works), receiving the schema on
    stdin (so we don't need a temp file).

    Failures are surfaced as `GBNFConversionError` with the underlying stderr,
    rather than silently producing a stub grammar.
    """

    VENDOR_PATH: Path = Path(__file__).parent / "vendor" / "json_schema_to_grammar.py"
    SUBPROCESS_TIMEOUT_SECONDS: int = 30

    def convert(
        self,
        schema: dict[str, Any],
        output_dir: Path,
        name: str,
        *,
        source_path: Optional[str] = None,
        source_method: Optional[str] = None,
    ) -> Path:
        """Convert a processed JSON Schema to GBNF and write artifacts to disk."""
        output_dir.mkdir(parents=True, exist_ok=True)

        schema_text = json.dumps(schema, indent=2)
        schema_path = output_dir / f"{name}.json"
        schema_path.write_text(schema_text, encoding="utf-8")

        gbnf_text = self._invoke_vendor(schema)
        gbnf_path = output_dir / f"{name}.gbnf"
        gbnf_path.write_text(gbnf_text, encoding="utf-8")

        meta_path = output_dir / f"{name}.meta.json"
        meta_path.write_text(
            json.dumps(
                self._build_metadata(
                    schema_text=schema_text,
                    source_path=source_path,
                    source_method=source_method,
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        return gbnf_path

    def _invoke_vendor(self, schema: dict[str, Any]) -> str:
        """Run the vendored llama.cpp script and return its GBNF output."""
        if not self.VENDOR_PATH.exists():
            raise GBNFConversionError(
                f"Vendored llama.cpp script not found at {self.VENDOR_PATH}. "
                "Reinstall the package."
            )

        try:
            result = subprocess.run(
                [sys.executable, str(self.VENDOR_PATH), "-"],
                input=json.dumps(schema),
                capture_output=True,
                text=True,
                timeout=self.SUBPROCESS_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise GBNFConversionError(
                f"Could not start Python interpreter at {sys.executable}: {exc}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise GBNFConversionError(
                f"Vendored converter timed out after {self.SUBPROCESS_TIMEOUT_SECONDS}s "
                "(schema too large or too deeply nested?)."
            ) from exc

        if result.returncode != 0 or not result.stdout.strip():
            raise GBNFConversionError(
                "Vendored converter (json_schema_to_grammar.py) failed.\n"
                f"Return code: {result.returncode}\n"
                f"Stderr: {result.stderr.strip() or '(empty)'}"
            )

        return result.stdout

    def _build_metadata(
        self,
        *,
        schema_text: str,
        source_path: Optional[str],
        source_method: Optional[str],
    ) -> dict[str, Any]:
        """Assemble the `.meta.json` audit payload."""
        return {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "tool": "servicenow-to-gbnf",
            "tool_version": __version__,
            "source_path": source_path,
            "source_method": source_method,
            "schema_sha256": hashlib.sha256(schema_text.encode("utf-8")).hexdigest(),
        }
