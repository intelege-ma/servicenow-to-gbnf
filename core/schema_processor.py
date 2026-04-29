"""Processes JSON Schema: resolves $ref, simplifies, adds ServiceNow-specific enums."""
from typing import Any, Dict, List, Optional


class SchemaProcessor:
    """Cleans and optimizes JSON Schema for GBNF conversion."""

    # ServiceNow common enums (extend as needed)
    SERVICENOW_ENUMS: Dict[str, List[str]] = {
        "priority": ["1", "2", "3", "4", "5"],
        "state": ["1", "2", "3", "6", "7", "8"],
        "impact": ["1", "2", "3"],
        "urgency": ["1", "2", "3"],
        # Add more per table in config later
    }

    def __init__(self, simplify: bool = True, include_fields: Optional[List[str]] = None):
        self.simplify = simplify
        self.include_fields = include_fields or []

    def process(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing pipeline."""
        # Simple $ref inlining (recursive for MVP)
        schema = self._inline_refs(schema, schema.get("$defs", {}))
        # Simplify if requested
        if self.simplify:
            schema = self._simplify_schema(schema)
        # Inject ServiceNow enums where field names match
        schema = self._inject_enums(schema)
        return schema

    def _inline_refs(self, schema: Dict[str, Any], defs: Dict[str, Any]) -> Dict[str, Any]:
        """Basic $ref resolver for MVP (handles common ServiceNow patterns)."""
        if isinstance(schema, dict):
            if "$ref" in schema:
                ref = schema["$ref"].split("/")[-1]
                if ref in defs:
                    return self._inline_refs(defs[ref], defs)
            for key, value in list(schema.items()):
                schema[key] = self._inline_refs(value, defs)
        elif isinstance(schema, list):
            schema = [self._inline_refs(item, defs) for item in schema]
        return schema

    def _simplify_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Keep only essential fields to reduce grammar size."""
        if "properties" in schema:
            props = schema["properties"]
            if self.include_fields:
                schema["properties"] = {k: v for k, v in props.items() if k in self.include_fields}
            else:
                # Default: keep common ServiceNow fields
                keep = {"short_description", "description", "priority", "state", "impact", "urgency", "category"}
                schema["properties"] = {k: v for k, v in props.items() if k in keep}
        return schema

    def _inject_enums(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Add real ServiceNow enum values where field name matches."""
        if "properties" in schema:
            for field, prop in schema["properties"].items():
                if field in self.SERVICENOW_ENUMS and "enum" not in prop:
                    prop["enum"] = self.SERVICENOW_ENUMS[field]
        return schema