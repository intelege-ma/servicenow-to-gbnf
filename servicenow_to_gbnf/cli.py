import typer
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

from servicenow_to_gbnf.core.extractor import OpenAPIExtractor
from servicenow_to_gbnf.core.schema_processor import SchemaProcessor
from servicenow_to_gbnf.core.converter import GBNFConverter
from servicenow_to_gbnf.core.iii_generator import IIIWorkerGenerator

app = typer.Typer(
    name="servicenow-to-gbnf",
    help="ServiceNow → GBNF grammar + iii worker generator",
    add_completion=False,
)

console = Console()
converter = GBNFConverter()

@app.command()
def from_openapi(
    file: Path = typer.Option(..., "--file", "-f", help="OpenAPI YAML/JSON file exported from ServiceNow REST API Explorer"),
    path: str = typer.Option(..., "--path", help="Example: /api/now/table/incident"),
    method: str = typer.Option("post", "--method", help="HTTP method (post/get/put etc.)"),
    output: Path = typer.Option("./grammars/", "--output", "-o"),
    simplify: bool = typer.Option(True, "--simplify/--no-simplify", help="Reduce schema to essential fields"),
):
    """Generate GBNF grammar from ServiceNow OpenAPI export."""
    console.print(Panel(f"[bold green]🚀 Processing {file} → {path} {method.upper()}[/]", title="servicenow-to-gbnf"))

    # Clean path (fixes Git Bash corruption)
    clean_path = path.strip().split("api/now")[-1]
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path
    clean_path = clean_path.split("Git/")[-1]  # remove Git Bash prefix if present

    extractor = OpenAPIExtractor(file)
    
    raw_schema = None
    for p in extractor.spec.get("paths", {}):
        if p.strip().rstrip('/') == clean_path.rstrip('/'):
            raw_schema = extractor.extract_request_schema(p, method)
            if raw_schema:
                break

    if not raw_schema:
        console.print("[bold red]❌ Could not find requestBody schema.[/]")
        console.print("Available paths in file:")
        for p in extractor.spec.get("paths", {}):
            console.print(f"  - {p}")
        raise typer.Exit(1)

    processor = SchemaProcessor(simplify=simplify)
    processed_schema = processor.process(raw_schema)

    name = f"{clean_path.strip('/').replace('/', '-')}-{method}"
    gbnf_path = converter.convert(processed_schema, output, name)

    console.print(f"[bold green]✅ Success![/] Grammar saved to {gbnf_path}")
    console.print(f"[bold]JSON Schema (audit):[/] {output / f'{name}.json'}")

@app.command()
def generate_worker(
    grammar: Path = typer.Option(..., "--grammar", "-g", help="Path to .gbnf file"),
    output: Path = typer.Option(None, "--output", "-o", help="Output path for worker.py"),
    iii_function_id: str = typer.Option("sn::incident-create", "--iii-function"),
    servicenow_instance: str = typer.Option("https://dev12345.service-now.com", "--instance"),
    table: str = typer.Option("incident", "--table"),
):
    """Generate a complete, ready-to-run iii worker from a GBNF grammar."""
    if output is None:
        output = Path("workers") / f"{iii_function_id.replace('::', '_')}.py"

    generator = IIIWorkerGenerator()
    worker_path = generator.generate(
        grammar_path=grammar,
        output_path=output,
        iii_function_id=iii_function_id,
        servicenow_instance=servicenow_instance,
        table=table,
    )

    console.print(f"[bold green]✅ iii Worker generated![/] {worker_path}")

@app.command()
def version():
    console.print("[bold]servicenow-to-gbnf v0.1.0[/] — open-source deterministic ServiceNow connector")

if __name__ == "__main__":
    app()