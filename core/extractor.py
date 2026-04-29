"""Extracts OpenAPI specification and target operation schema from ServiceNow export."""
import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel


class OpenAPIExtractor:
    """Loads and extracts requestBody schema from ServiceNow OpenAPI YAML/JSON."""

    def __init__(self, openapi_path: Path):
        self.openapi_path = openapi_path
        self.spec: Dict[str, Any] = self._load_spec()

    def _load_spec(self) -> Dict[str, Any]:
        """Load YAML or JSON OpenAPI spec."""
        content = self.openapi_path.read_text(encoding="utf-8")
        if self.openapi_path.suffix.lower() in (".yaml", ".yml"):
            return yaml.safe_load(content)
        return json.loads(content)

    def extract_request_schema(
        self, path: str, method: str = "post"
    ) -> Optional[Dict[str, Any]]:
        """Extract requestBody schema for a specific path + method."""
        method = method.lower()
        paths = self.spec.get("paths", {})
        if path not in paths:
            return None

        operation = paths[path].get(method)
        if not operation:
            return None

        request_body = operation.get("requestBody", {}).get("content", {}).get("application/json", {})
        schema = request_body.get("schema")
        if not schema:
            return None

        return schema