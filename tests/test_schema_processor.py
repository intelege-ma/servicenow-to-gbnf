"""Tests for SchemaProcessor."""
from __future__ import annotations

from servicenow_to_gbnf.core.schema_processor import SchemaProcessor


def _basic_schema() -> dict:
    return {
        "type": "object",
        "required": ["short_description"],
        "properties": {
            "short_description": {"type": "string"},
            "description": {"type": "string"},
            "priority": {"type": "string"},
            "state": {"type": "string"},
            "impact": {"type": "string"},
            "category": {"type": "string"},
            "sys_mod_count": {"type": "integer"},
            "u_custom_field": {"type": "string"},
        },
    }


def test_simplify_keeps_default_set() -> None:
    processed = SchemaProcessor(simplify=True).process(_basic_schema())
    keys = set(processed["properties"].keys())
    assert "short_description" in keys
    assert "description" in keys
    assert "sys_mod_count" not in keys
    assert "u_custom_field" not in keys


def test_simplify_drops_required_for_filtered_fields() -> None:
    schema = {
        "type": "object",
        "required": ["short_description", "u_custom_field"],
        "properties": {
            "short_description": {"type": "string"},
            "u_custom_field": {"type": "string"},
        },
    }
    processed = SchemaProcessor(simplify=True).process(schema)
    assert processed["required"] == ["short_description"]


def test_no_simplify_passes_everything_through() -> None:
    processed = SchemaProcessor(simplify=False).process(_basic_schema())
    keys = set(processed["properties"].keys())
    assert "sys_mod_count" in keys
    assert "u_custom_field" in keys


def test_include_fields_overrides_default() -> None:
    processed = SchemaProcessor(
        simplify=True,
        include_fields=["short_description", "u_custom_field"],
    ).process(_basic_schema())
    assert set(processed["properties"].keys()) == {"short_description", "u_custom_field"}


def test_exclude_fields_removes_from_default() -> None:
    processed = SchemaProcessor(
        simplify=True,
        exclude_fields=["priority", "state"],
    ).process(_basic_schema())
    keys = set(processed["properties"].keys())
    assert "priority" not in keys
    assert "state" not in keys
    assert "short_description" in keys


def test_inject_servicenow_enums() -> None:
    processed = SchemaProcessor(simplify=True).process(_basic_schema())
    assert processed["properties"]["priority"]["enum"] == ["1", "2", "3", "4", "5"]
    assert processed["properties"]["state"]["enum"] == ["1", "2", "3", "6", "7", "8"]
    assert processed["properties"]["impact"]["enum"] == ["1", "2", "3"]


def test_existing_enum_is_preserved() -> None:
    schema = {
        "type": "object",
        "properties": {
            "priority": {"type": "string", "enum": ["LOW", "HIGH"]},
        },
    }
    processed = SchemaProcessor(simplify=False).process(schema)
    assert processed["properties"]["priority"]["enum"] == ["LOW", "HIGH"]


def test_inline_refs_with_external_defs() -> None:
    schema = {"$ref": "#/components/schemas/Body"}
    defs = {
        "Body": {
            "type": "object",
            "properties": {
                "short_description": {"type": "string"},
            },
        }
    }
    processed = SchemaProcessor(simplify=False).process(schema, defs=defs)
    assert processed["type"] == "object"
    assert "short_description" in processed["properties"]


def test_inline_refs_handles_cycles() -> None:
    defs = {
        "Tree": {
            "type": "object",
            "properties": {
                "child": {"$ref": "#/$defs/Tree"},
            },
        }
    }
    schema = {"$ref": "#/$defs/Tree", "$defs": defs}
    processed = SchemaProcessor(simplify=False).process(schema)
    assert processed.get("type") == "object" or "$ref" in processed


def test_unknown_ref_left_intact() -> None:
    schema = {"$ref": "#/components/schemas/Missing"}
    processed = SchemaProcessor(simplify=False).process(schema, defs={})
    assert "$ref" in processed
