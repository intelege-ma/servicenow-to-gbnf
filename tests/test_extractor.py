"""Tests for OpenAPIExtractor."""
from __future__ import annotations

from pathlib import Path

import pytest

from servicenow_to_gbnf.core.extractor import Endpoint, OpenAPIExtractor


def test_loads_yaml(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    assert "paths" in extractor.spec
    assert "/api/now/table/incident" in extractor.spec["paths"]


def test_loads_json(tmp_path: Path) -> None:
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(
        '{"openapi":"3.0.0","paths":{"/x":{"get":{"summary":"hi"}}}}',
        encoding="utf-8",
    )
    extractor = OpenAPIExtractor(spec_file)
    assert extractor.available_paths() == ["/x"]


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OpenAPIExtractor(tmp_path / "nope.yaml")


def test_non_mapping_spec_raises(tmp_path: Path) -> None:
    spec_file = tmp_path / "bad.yaml"
    spec_file.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        OpenAPIExtractor(spec_file)


def test_extract_request_schema_post(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    schema = extractor.extract_request_schema("/api/now/table/incident", "post")
    assert schema is not None
    assert schema.get("$ref") == "#/components/schemas/IncidentRequest"


def test_extract_request_schema_put_with_path_param(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    schema = extractor.extract_request_schema(
        "/api/now/table/incident/{sys_id}", "put"
    )
    assert schema is not None
    assert schema.get("$ref") == "#/components/schemas/IncidentRequest"


def test_extract_request_schema_method_without_body(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    schema = extractor.extract_request_schema("/api/now/table/incident", "get")
    assert schema is None


def test_extract_request_schema_unknown_path(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    assert extractor.extract_request_schema("/nope", "post") is None


def test_extract_request_schema_trailing_slash_normalised(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    schema = extractor.extract_request_schema("/api/now/table/incident/", "post")
    assert schema is not None


def test_list_endpoints(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    endpoints = extractor.list_endpoints()
    assert all(isinstance(e, Endpoint) for e in endpoints)
    paths = {(e.path, e.method) for e in endpoints}
    assert ("/api/now/table/incident", "post") in paths
    assert ("/api/now/table/incident", "get") in paths
    assert ("/api/now/table/incident/{sys_id}", "put") in paths
    assert ("/api/now/table/change_request", "post") in paths


def test_list_endpoints_marks_request_body(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    by_key = {(e.path, e.method): e for e in extractor.list_endpoints()}
    assert by_key[("/api/now/table/incident", "post")].has_request_body is True
    assert by_key[("/api/now/table/incident", "get")].has_request_body is False


def test_components_schemas(incident_yaml_path: Path) -> None:
    extractor = OpenAPIExtractor(incident_yaml_path)
    schemas = extractor.components_schemas()
    assert "IncidentRequest" in schemas
    assert "ChangeRequest" in schemas
