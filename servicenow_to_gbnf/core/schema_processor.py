"""Processes JSON Schema: resolves $ref, simplifies, adds ServiceNow-specific enums."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Optional


class SchemaProcessor:
    """Cleans and optimizes a JSON Schema for GBNF conversion."""

    DEFAULT_KEEP_FIELDS: set[str] = {
        "short_description",
        "description",
        "priority",
        "state",
        "impact",
        "urgency",
        "category",
        "assignment_group",
    }

    SERVICENOW_ENUMS: dict[str, list[str]] = {
        "priority": ["1", "2", "3", "4", "5"],
        "state": ["1", "2", "3", "6", "7", "8"],
        "impact": ["1", "2", "3"],
        "urgency": ["1", "2", "3"],
    }

    def __init__(
        self,
        simplify: bool = True,
        include_fields: Optional[Iterable[str]] = None,
        exclude_fields: Optional[Iterable[str]] = None,
    ) -> None:
        self.simplify = simplify
        self.include_fields: list[str] = list(include_fields or [])
        self.exclude_fields: set[str] = set(exclude_fields or [])

    def process(
        self,
        schema: dict[str, Any],
        defs: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run the full pipeline."""
        merged_defs: dict[str, Any] = {}
        merged_defs.update(schema.get("$defs", {}) or {})
        if defs:
            merged_defs.update(defs)

        schema = self._inline_refs(schema, merged_defs)
        if self.simplify:
            schema = self._simplify_schema(schema)
        schema = self._inject_enums(schema)
        return schema

    def _inline_refs(
        self,
        node: Any,
        defs: dict[str, Any],
        seen: Optional[set[str]] = None,
    ) -> Any:
        """Inline ``$ref`` references; tolerate missing/cyclic refs."""
        seen = seen or set()
        if isinstance(node, dict):
            if "$ref" in node:
                ref = str(node["$ref"]).split("/")[-1]
                if ref in seen:
                    return node
                if ref in defs:
                    return self._inline_refs(defs[ref], defs, seen | {ref})
                return node
            return {key: self._inline_refs(value, defs, seen) for key, value in node.items()}
        if isinstance(node, list):
            return [self._inline_refs(item, defs, seen) for item in node]
        return node

    def _simplify_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Keep only a curated subset of properties; honor include/exclude."""
        if "properties" not in schema:
            return schema

        props = schema["properties"]
        if self.include_fields:
            keep: set[str] = set(self.include_fields)
        else:
            keep = set(self.DEFAULT_KEEP_FIELDS)

        keep -= self.exclude_fields
        schema["properties"] = {k: v for k, v in props.items() if k in keep}

        if "required" in schema:
            schema["required"] = [r for r in schema["required"] if r in schema["properties"]]
            if not schema["required"]:
                schema.pop("required")

        return schema

    def _inject_enums(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Add ServiceNow enum values to known fields that lack them."""
        if "properties" in schema:
            for field, prop in schema["properties"].items():
                if (
                    isinstance(prop, dict)
                    and field in self.SERVICENOW_ENUMS
                    and "enum" not in prop
                ):
                    prop["enum"] = list(self.SERVICENOW_ENUMS[field])
        return schema
