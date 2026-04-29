"""Tests for IIIWorkerGenerator."""
from __future__ import annotations

import py_compile
from pathlib import Path

import pytest

from servicenow_to_gbnf.core.iii_generator import IIIWorkerGenerator


@pytest.fixture()
def grammar_file(tmp_path: Path) -> Path:
    p = tmp_path / "grammars" / "incident-post.gbnf"
    p.parent.mkdir(parents=True)
    p.write_text("# fake grammar\nroot ::= \"x\"\n", encoding="utf-8")
    return p


def test_generated_worker_compiles(tmp_path: Path, grammar_file: Path) -> None:
    gen = IIIWorkerGenerator()
    worker_path = gen.generate(
        grammar_path=grammar_file,
        output_path=tmp_path / "workers" / "incident.py",
        iii_function_id="sn::incident-create",
        servicenow_instance="https://dev12345.service-now.com",
        table="incident",
    )
    py_compile.compile(str(worker_path), doraise=True)


def test_function_name_replaces_hyphens_and_colons(tmp_path: Path, grammar_file: Path) -> None:
    gen = IIIWorkerGenerator()
    worker_path = gen.generate(
        grammar_path=grammar_file,
        output_path=tmp_path / "w.py",
        iii_function_id="sn::incident-create",
        servicenow_instance="https://x",
    )
    src = worker_path.read_text(encoding="utf-8")
    assert "async def sn_incident_create(" in src
    assert 'iii.register_function("sn::incident-create"' in src


def test_no_hardcoded_credentials(tmp_path: Path, grammar_file: Path) -> None:
    gen = IIIWorkerGenerator()
    worker_path = gen.generate(
        grammar_path=grammar_file,
        output_path=tmp_path / "w.py",
        iii_function_id="sn::incident-create",
        servicenow_instance="https://x",
    )
    src = worker_path.read_text(encoding="utf-8")
    assert "your_password" not in src
    assert 'os.getenv("SERVICENOW_USERNAME")' in src
    assert 'os.getenv("SERVICENOW_PASSWORD")' in src


def test_grammar_path_is_relative_to_worker(tmp_path: Path, grammar_file: Path) -> None:
    gen = IIIWorkerGenerator()
    worker_path = gen.generate(
        grammar_path=grammar_file,
        output_path=tmp_path / "workers" / "w.py",
        iii_function_id="sn::incident-create",
        servicenow_instance="https://x",
    )
    src = worker_path.read_text(encoding="utf-8")
    assert 'Path(__file__).parent / "incident-post.gbnf"' in src


def test_system_prompt_is_populated(tmp_path: Path, grammar_file: Path) -> None:
    gen = IIIWorkerGenerator()
    worker_path = gen.generate(
        grammar_path=grammar_file,
        output_path=tmp_path / "workers" / "w.py",
        iii_function_id="sn::incident-create",
        servicenow_instance="https://x",
        table="incident",
    )
    prompt = (worker_path.parent / "system_prompt.txt").read_text(encoding="utf-8")
    assert "Field guidance for Incident:" in prompt
    assert "short_description" in prompt
    assert "Required fields for :" not in prompt


def test_python_identifier_helper() -> None:
    f = IIIWorkerGenerator._python_identifier
    assert f("sn::incident-create") == "sn_incident_create"
    assert f("plain") == "plain"
    assert f("123leading") == "fn_123leading"
    assert f("only::::dots") == "only_dots"


def test_http_api_path_helper() -> None:
    f = IIIWorkerGenerator._http_api_path
    assert f("sn::incident-create") == "sn/incident-create"
