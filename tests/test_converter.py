"""Tests for GBNFConverter."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from servicenow_to_gbnf.core.converter import GBNFConversionError, GBNFConverter

SAMPLE_SCHEMA = {
    "type": "object",
    "required": ["short_description", "description"],
    "properties": {
        "short_description": {"type": "string"},
        "description": {"type": "string"},
        "priority": {"type": "string", "enum": ["1", "2", "3", "4", "5"]},
    },
}


def test_convert_writes_three_artifacts(tmp_path: Path) -> None:
    converter = GBNFConverter()
    gbnf_path = converter.convert(
        SAMPLE_SCHEMA,
        tmp_path,
        "sample",
        source_path="/api/now/table/incident",
        source_method="post",
    )
    assert gbnf_path == tmp_path / "sample.gbnf"
    assert gbnf_path.exists()
    assert (tmp_path / "sample.json").exists()
    assert (tmp_path / "sample.meta.json").exists()


def test_gbnf_contains_priority_enum(tmp_path: Path) -> None:
    converter = GBNFConverter()
    gbnf_path = converter.convert(SAMPLE_SCHEMA, tmp_path, "incident-post")
    text = gbnf_path.read_text(encoding="utf-8")
    assert '"\\"1\\""' in text
    assert '"\\"5\\""' in text
    assert "short-description-kv" in text or "short_description-kv" in text or "short-description" in text


def test_gbnf_does_not_contain_dropped_fields(tmp_path: Path) -> None:
    converter = GBNFConverter()
    gbnf_path = converter.convert(SAMPLE_SCHEMA, tmp_path, "incident-post")
    text = gbnf_path.read_text(encoding="utf-8")
    assert "u_custom_field" not in text
    assert "sys_mod_count" not in text


def test_meta_contains_audit_fields(tmp_path: Path) -> None:
    converter = GBNFConverter()
    converter.convert(
        SAMPLE_SCHEMA,
        tmp_path,
        "audit",
        source_path="/api/now/table/incident",
        source_method="post",
    )
    meta = json.loads((tmp_path / "audit.meta.json").read_text(encoding="utf-8"))
    assert meta["tool"] == "servicenow-to-gbnf"
    assert meta["source_path"] == "/api/now/table/incident"
    assert meta["source_method"] == "post"
    assert isinstance(meta["schema_sha256"], str) and len(meta["schema_sha256"]) == 64
    assert meta["tool_version"]


def test_meta_sha_changes_when_schema_changes(tmp_path: Path) -> None:
    converter = GBNFConverter()
    converter.convert(SAMPLE_SCHEMA, tmp_path / "a", "x")
    altered = {**SAMPLE_SCHEMA, "properties": {**SAMPLE_SCHEMA["properties"], "extra": {"type": "string"}}}
    converter.convert(altered, tmp_path / "b", "x")
    meta_a = json.loads((tmp_path / "a" / "x.meta.json").read_text())
    meta_b = json.loads((tmp_path / "b" / "x.meta.json").read_text())
    assert meta_a["schema_sha256"] != meta_b["schema_sha256"]


def test_vendor_failure_raises_loud_error(tmp_path: Path) -> None:
    converter = GBNFConverter()

    class _FakeResult:
        returncode = 1
        stdout = ""
        stderr = "boom: simulated vendor failure"

    with patch("servicenow_to_gbnf.core.converter.subprocess.run", return_value=_FakeResult()):
        with pytest.raises(GBNFConversionError) as excinfo:
            converter.convert(SAMPLE_SCHEMA, tmp_path, "fail")
    assert "boom" in str(excinfo.value)
    assert not (tmp_path / "fail.gbnf").exists()


def test_vendor_path_resolves_relative_to_module(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    converter = GBNFConverter()
    assert converter.VENDOR_PATH.exists(), (
        f"VENDOR_PATH {converter.VENDOR_PATH} should exist regardless of cwd"
    )
    out = converter.convert(SAMPLE_SCHEMA, tmp_path / "out", "x")
    assert out.exists()


def test_missing_vendor_raises(tmp_path: Path) -> None:
    converter = GBNFConverter()
    with patch.object(GBNFConverter, "VENDOR_PATH", tmp_path / "does-not-exist.py"):
        with pytest.raises(GBNFConversionError) as excinfo:
            converter.convert(SAMPLE_SCHEMA, tmp_path, "x")
    assert "not found" in str(excinfo.value)
