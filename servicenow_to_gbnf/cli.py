"""Typer CLI for servicenow-to-gbnf."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from servicenow_to_gbnf import __version__
from servicenow_to_gbnf.core.converter import GBNFConversionError, GBNFConverter
from servicenow_to_gbnf.core.extractor import OpenAPIExtractor
from servicenow_to_gbnf.core.iii_generator import IIIWorkerGenerator
from servicenow_to_gbnf.core.schema_processor import SchemaProcessor

app = typer.Typer(
    name="servicenow-to-gbnf",
    help="ServiceNow → GBNF grammar + iii worker generator",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


def _parse_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,\s]+", value) if item.strip()]


def _normalize_path(raw: str) -> str:
    if not raw:
        return raw
    cleaned = raw.strip()
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return cleaned.rstrip("/") or "/"


def _safe_name(path: str, method: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-")
    return f"{slug}-{method.lower()}"


@app.command()
def from_openapi(
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="OpenAPI YAML/JSON file exported from the ServiceNow REST API Explorer."),
    path: str = typer.Option(..., "--path", help="API path to extract, e.g. /api/now/table/incident"),
    method: str = typer.Option("post", "--method", help="HTTP method (post/put/patch/get/delete)."),
    output: Path = typer.Option(Path("./grammars/"), "--output", "-o", help="Directory to write the .gbnf, .json, and .meta.json files into."),
    simplify: bool = typer.Option(True, "--simplify/--no-simplify", help="Reduce the schema to a curated set of essential fields before conversion."),
    include_fields: Optional[str] = typer.Option(None, "--include-fields", help="Comma-separated allow-list of property names to keep (overrides default)."),
    exclude_fields: Optional[str] = typer.Option(None, "--exclude-fields", help="Comma-separated deny-list of property names to drop."),
) -> None:
    """Generate a GBNF grammar from a ServiceNow OpenAPI export."""
    target_path = _normalize_path(path)
    target_method = method.lower()

    console.print(Panel(f"[bold green]\U0001f680 Processing[/] {file} \u2192 {target_path} {target_method.upper()}", title="servicenow-to-gbnf"))

    extractor = OpenAPIExtractor(file)
    raw_schema = extractor.extract_request_schema(target_path, target_method)
    if not raw_schema:
        console.print(f"[bold red]\u274c Could not find requestBody schema for {target_method.upper()} {target_path}.[/]")
        console.print("Available paths in file:")
        for available in extractor.available_paths():
            console.print(f"  - {available}")
        raise typer.Exit(1)

    processor = SchemaProcessor(simplify=simplify, include_fields=_parse_csv(include_fields), exclude_fields=_parse_csv(exclude_fields))
    processed_schema = processor.process(raw_schema, defs=extractor.components_schemas())

    if "properties" in processed_schema and not processed_schema["properties"]:
        console.print("[bold red]\u274c All properties were filtered out.[/] Check --include-fields / --exclude-fields.")
        raise typer.Exit(1)

    name = _safe_name(target_path, target_method)
    converter = GBNFConverter()

    try:
        gbnf_path = converter.convert(processed_schema, output, name, source_path=target_path, source_method=target_method)
    except GBNFConversionError as exc:
        console.print(f"[bold red]\u274c GBNF conversion failed:[/] {exc}")
        raise typer.Exit(2) from exc

    console.print(f"[bold green]\u2705 Success![/] Grammar saved to {gbnf_path}")
    console.print(f"[bold]JSON Schema (audit):[/] {output / f'{name}.json'}")
    console.print(f"[bold]Metadata:[/]            {output / f'{name}.meta.json'}")


@app.command("list-endpoints")
def list_endpoints(
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="OpenAPI YAML/JSON file to inspect."),
    filter_pattern: Optional[str] = typer.Option(None, "--filter", help="Optional regex applied to the path to filter rows."),
    method: Optional[str] = typer.Option(None, "--method", help="Optional HTTP method filter (post/get/put/...)"),
) -> None:
    """List every (path, method) operation in an OpenAPI file."""
    extractor = OpenAPIExtractor(file)
    endpoints = extractor.list_endpoints()

    pattern = re.compile(filter_pattern) if filter_pattern else None
    target_method = method.lower() if method else None

    table = Table(title=f"Endpoints in {file.name}", show_lines=False)
    table.add_column("Method", style="bold cyan", width=6)
    table.add_column("Path", style="white")
    table.add_column("Operation", style="dim")
    table.add_column("Body?", style="bold magenta", width=5)

    rows = 0
    for ep in endpoints:
        if target_method and ep.method != target_method:
            continue
        if pattern and not pattern.search(ep.path):
            continue
        table.add_row(ep.method.upper(), ep.path, ep.operation_id or ep.summary or "", "yes" if ep.has_request_body else "no")
        rows += 1

    console.print(table)
    console.print(f"[dim]{rows} endpoint(s) shown[/]")


@app.command("generate-worker")
def generate_worker(
    grammar: Path = typer.Option(..., "--grammar", "-g", exists=True, readable=True, help="Path to a .gbnf file produced by `from-openapi`."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path for the generated worker.py (default: ./workers/<id>.py)"),
    iii_function_id: str = typer.Option("sn::incident-create", "--iii-function", help="iii function id to register (e.g. sn::incident-create)."),
    servicenow_instance: str = typer.Option("https://dev12345.service-now.com", "--instance", help="Default ServiceNow instance URL (env var SERVICENOW_INSTANCE overrides at runtime)."),
    table: str = typer.Option("incident", "--table", help="ServiceNow table name (e.g. incident, change_request, problem)."),
) -> None:
    """Generate a complete, ready-to-run iii worker from a GBNF grammar."""
    if output is None:
        safe_id = re.sub(r"[^A-Za-z0-9]+", "_", iii_function_id).strip("_") or "worker"
        output = Path("workers") / f"{safe_id}.py"

    generator = IIIWorkerGenerator()
    worker_path = generator.generate(grammar_path=grammar, output_path=output, iii_function_id=iii_function_id, servicenow_instance=servicenow_instance, table=table)

    console.print(f"[bold green]\u2705 iii Worker generated![/] {worker_path}")
    console.print(f"[bold]System prompt:[/] {worker_path.parent / 'system_prompt.txt'}")
    console.print("[dim]Set SERVICENOW_USERNAME / SERVICENOW_PASSWORD env vars before running.[/]")


@app.command()
def version() -> None:
    """Print the installed servicenow-to-gbnf version."""
    console.print(f"[bold]servicenow-to-gbnf v{__version__}[/] \u2014 open-source deterministic ServiceNow connector")


if __name__ == "__main__":
    app()
