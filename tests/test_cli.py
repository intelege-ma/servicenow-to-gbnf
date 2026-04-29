"""Integration tests for the Typer CLI."""
from __future__ import annotations

import json
import py_compile
from pathlib import Path

from typer.testing import CliRunner

from servicenow_to_gbnf import __version__
from servicenow_to_gbnf.cli import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("from-openapi", "list-endpoints", "generate-worker", "version"):
        assert cmd in result.stdout


def test_list_endpoints(incident_yaml_path: Path) -> None:
    result = runner.invoke(app, ["list-endpoints", "--file", str(incident_yaml_path)])
    assert result.exit_code == 0
    assert "/api/now/table/incident" in result.stdout
    assert "/api/now/table/change_request" in result.stdout


def test_list_endpoints_filter(incident_yaml_path: Path) -> None:
    result = runner.invoke(
        app,
        ["list-endpoints", "--file", str(incident_yaml_path), "--filter", "change"],
    )
    assert result.exit_code == 0
    assert "change_request" in result.stdout
    assert "/api/now/table/incident " not in result.stdout


def test_from_openapi_full_path(tmp_path: Path, incident_yaml_path: Path) -> None:
    result = runner.invoke(
        app,
        ["from-openapi", "--file", str(incident_yaml_path), "--path", "/api/now/table/incident", "--method", "post", "--output", str(tmp_path / "grammars")],
    )
    assert result.exit_code == 0, result.stdout
    out = tmp_path / "grammars" / "api-now-table-incident-post.gbnf"
    assert out.exists()
    text = out.read_text()
    assert "short-description-kv" in text or "short_description" in text
    assert "priority" in text


def test_from_openapi_unknown_path_exits_nonzero(tmp_path: Path, incident_yaml_path: Path) -> None:
    result = runner.invoke(
        app,
        ["from-openapi", "--file", str(incident_yaml_path), "--path", "/no/such/path", "--output", str(tmp_path)],
    )
    assert result.exit_code != 0
    assert "Available paths" in result.stdout


def test_from_openapi_include_fields(tmp_path: Path, incident_yaml_path: Path) -> None:
    result = runner.invoke(
        app,
        ["from-openapi", "--file", str(incident_yaml_path), "--path", "/api/now/table/incident", "--method", "post", "--include-fields", "short_description,description", "--output", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout
    schema = json.loads((tmp_path / "api-now-table-incident-post.json").read_text())
    assert set(schema["properties"].keys()) == {"short_description", "description"}


def test_from_openapi_exclude_fields(tmp_path: Path, incident_yaml_path: Path) -> None:
    result = runner.invoke(
        app,
        ["from-openapi", "--file", str(incident_yaml_path), "--path", "/api/now/table/incident", "--method", "post", "--exclude-fields", "category,impact,urgency,assignment_group", "--output", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout
    schema = json.loads((tmp_path / "api-now-table-incident-post.json").read_text())
    keys = set(schema["properties"].keys())
    assert "category" not in keys
    assert "impact" not in keys
    assert "short_description" in keys


def test_from_openapi_put_method(tmp_path: Path, incident_yaml_path: Path) -> None:
    result = runner.invoke(
        app,
        ["from-openapi", "--file", str(incident_yaml_path), "--path", "/api/now/table/incident/{sys_id}", "--method", "put", "--output", str(tmp_path)],
    )
    assert result.exit_code == 0, result.stdout
    files = sorted(p.name for p in tmp_path.glob("*"))
    assert any("put" in f and f.endswith(".gbnf") for f in files)


def test_full_pipeline_from_openapi_then_generate_worker(tmp_path: Path, incident_yaml_path: Path) -> None:
    grammars = tmp_path / "grammars"
    workers = tmp_path / "workers"
    r1 = runner.invoke(app, ["from-openapi", "--file", str(incident_yaml_path), "--path", "/api/now/table/incident", "--method", "post", "--output", str(grammars)])
    assert r1.exit_code == 0, r1.stdout
    grammar = grammars / "api-now-table-incident-post.gbnf"
    r2 = runner.invoke(app, ["generate-worker", "--grammar", str(grammar), "--output", str(workers / "incident_create.py"), "--iii-function", "sn::incident-create", "--instance", "https://example.service-now.com"])
    assert r2.exit_code == 0, r2.stdout
    worker = workers / "incident_create.py"
    assert worker.exists()
    py_compile.compile(str(worker), doraise=True)
    assert (workers / "system_prompt.txt").exists()
