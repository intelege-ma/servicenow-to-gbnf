"""Extracts OpenAPI specification and target operation schema from a ServiceNow export."""
from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class Endpoint:
    """A single ``(path, method)`` entry from an OpenAPI spec."""

    path: str
    method: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    has_request_body: bool = False


class OpenAPIExtractor:
    """Loads and extracts schemas from ServiceNow OpenAPI YAML/JSON exports."""

    HTTP_METHODS: tuple = ("get", "post", "put", "patch", "delete", "head", "options")

    def __init__(self, openapi_path: Path) -> None:
        self.openapi_path = Path(openapi_path)
        self.spec: dict[str, Any] = self._load_spec()

    def list_endpoints(self) -> list[Endpoint]:
        """Return every ``(path, method)`` in the spec as an :class:`Endpoint`."""
        endpoints: list[Endpoint] = []
        for path, methods in self._iter_paths():
            if not isinstance(methods, dict):
                continue
            for method, operation in methods.items():
                if method.lower() not in self.HTTP_METHODS or not isinstance(operation, dict):
                    continue
                endpoints.append(
                    Endpoint(
                        path=path,
                        method=method.lower(),
                        operation_id=operation.get("operationId"),
                        summary=operation.get("summary"),
                        has_request_body="requestBody" in operation,
                    )
                )
        return endpoints

    def available_paths(self) -> list[str]:
        """Sorted list of paths in this spec (helper for error messages)."""
        return sorted(self.spec.get("paths", {}).keys())

    def extract_request_schema(self, path: str, method: str = "post") -> Optional[dict[str, Any]]:
        """Return the JSON Schema for ``requestBody`` of a given path/method."""
        method = method.lower()
        target = path.strip().rstrip("/")

        for p, methods in self._iter_paths():
            if p.strip().rstrip("/") != target:
                continue
            operation = (methods or {}).get(method)
            if not operation:
                return None
            request_body = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
            )
            return request_body.get("schema")
        return None

    def components_schemas(self) -> dict[str, Any]:
        """Return ``components.schemas`` (used for $ref resolution)."""
        return self.spec.get("components", {}).get("schemas", {}) or {}

    def _load_spec(self) -> dict[str, Any]:
        if not self.openapi_path.exists():
            raise FileNotFoundError(f"OpenAPI file not found: {self.openapi_path}")
        content = self.openapi_path.read_text(encoding="utf-8")
        if self.openapi_path.suffix.lower() in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError(
                f"OpenAPI file {self.openapi_path} did not parse as a mapping; got {type(data).__name__}."
            )
        return data

    def _iter_paths(self) -> Iterator[tuple]:
        yield from (self.spec.get("paths", {}) or {}).items()
