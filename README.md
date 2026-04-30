# servicenow-to-gbnf

[![CI](https://github.com/intelege-ma/servicenow-to-gbnf/actions/workflows/ci.yml/badge.svg)](https://github.com/intelege-ma/servicenow-to-gbnf/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

**The open-source deterministic ServiceNow AI connector.**
Turn any ServiceNow OpenAPI export into a live GBNF grammar + a ready-to-run
[iii](https://github.com/iii-hq/iii) worker so a local LLM (llama.cpp /
Ollama) **physically cannot** (more or less lol) generate an invalid ServiceNow payload.

> Grammar-as-contract. Documentation, validation, and audit trail in a single artifact.

---

## Why

Classic agentic-AI integrations halucinate field names, enum values, and JSON
shapes and you only find out when ServiceNow rejects the payload (or worse,
silently accepts garbage). With **constrained decoding** via GBNF, the LLM can
only produce tokens that fit the grammar. Combined with the
[iii](https://github.com/iii-hq/iii) orchestrator's polyglot workers and
built-in observability, you get:

- **Zero schema-shaped hallucinations** - `priority` can only be `1`..`5`, etc.
- **Live contract** - re-run the tool when ServiceNow updates an endpoint; the
  grammar (and worker) update with it.
- **Local-first** - your data never leaves the perimeter. No cloud LLM required.
- **Audit-ready** - every grammar ships with a `.meta.json` sidecar
  containing the source path, method, schema SHA-256, and tool version.

## Installation

```bash
# With pip
pip install git+https://github.com/intelege-ma/servicenow-to-gbnf.git

# With uv
uv pip install git+https://github.com/intelege-ma/servicenow-to-gbnf.git
```

Requires Python 3.11+.

## 30-second quickstart

```bash
# 1. Inspect what's in your OpenAPI export.
servicenow-to-gbnf list-endpoints --file ./servicenow-openapi.yaml

# 2. Generate a GBNF grammar for one endpoint.
servicenow-to-gbnf from-openapi \
  --file ./servicenow-openapi.yaml \
  --path /api/now/table/incident \
  --method post \
  --output ./grammars/

# 3. Generate a ready-to-run iii worker.
servicenow-to-gbnf generate-worker \
  --grammar ./grammars/api-now-table-incident-post.gbnf \
  --iii-function sn::incident-create \
  --instance https://dev12345.service-now.com \
  --table incident

# 4. Run the worker (after `iii` engine + Ollama are running locally).
export SERVICENOW_USERNAME=admin
export SERVICENOW_PASSWORD=...
python workers/sn_incident_create.py
```

Want to try it without a real ServiceNow instance?
The repo ships a hand-crafted fixture at
[`tests/fixtures/servicenow-incident.yaml`](tests/fixtures/servicenow-incident.yaml) -
point step 2 at it and the whole pipeline runs end-to-end.

## CLI reference

### `from-openapi`

Generate a GBNF grammar (plus a JSON-schema audit copy and a `.meta.json`
sidecar) from an OpenAPI export.

```bash
servicenow-to-gbnf from-openapi \
  --file <openapi.yaml> \
  --path /api/now/table/<table> \
  --method post \
  --output ./grammars/ \
  [--simplify | --no-simplify] \
  [--include-fields short_description,description,priority] \
  [--exclude-fields category,impact]
```

| Flag | Default | Notes |
|---|---|---|
| `--simplify` | `True` | Trim the schema down to a curated set of useful ServiceNow fields. |
| `--include-fields` | _(none)_ | Comma-separated allow-list (overrides the curated default). |
| `--exclude-fields` | _(none)_ | Comma-separated deny-list applied after the allow-list. |

Outputs in `--output`:
- `<slug>.gbnf` - the grammar itself
- `<slug>.json` - the processed JSON Schema (audit copy)
- `<slug>.meta.json` - `{ generated_at, tool_version, source_path, source_method, schema_sha256 }`

### `list-endpoints`

```bash
servicenow-to-gbnf list-endpoints \
  --file <openapi.yaml> \
  [--filter <regex>] \
  [--method post]
```

Renders every `(method, path, operationId, has_body)` row in a table.
Great for figuring out exactly which `--path` to feed into `from-openapi`.

### `generate-worker`

Render a complete iii Python worker + system prompt from a grammar.

```bash
servicenow-to-gbnf generate-worker \
  --grammar ./grammars/<slug>.gbnf \
  --iii-function sn::incident-create \
  --instance https://dev12345.service-now.com \
  --table incident \
  [--output ./workers/sn_incident_create.py]
```

The generated worker reads credentials from environment variables -
**no secrets are ever written into the worker file**:

| Env var | Purpose |
|---|---|
| `SERVICENOW_USERNAME` | Basic-auth username (required) |
| `SERVICENOW_PASSWORD` | Basic-auth password (required) |
| `SERVICENOW_INSTANCE` | Override the instance baked in at generation time |
| `III_ENGINE_URL` | iii engine URL (defaults to `ws://localhost:49134`) |
| `OLLAMA_MODEL` | Ollama model name (defaults to `llama3.2`) |

### `version`

```bash
servicenow-to-gbnf version
```

## Architecture

```
servicenow_to_gbnf/
|-- cli.py                       # Typer CLI: from-openapi, list-endpoints, generate-worker
|-- core/
|   |-- extractor.py             # Loads YAML/JSON OpenAPI, extracts requestBody schemas
|   |-- schema_processor.py      # $ref inlining, simplification, ServiceNow enum injection
|   |-- converter.py             # Wraps the vendored llama.cpp converter, emits .gbnf+.json+.meta.json
|   |-- iii_generator.py         # Renders worker.py.j2 + prompt.txt.j2 into a runnable iii worker
|   `-- vendor/
|       `-- json_schema_to_grammar.py   # Verbatim copy of llama.cpp's converter (MIT)
|-- templates/
|   |-- worker.py.j2
|   `-- prompt.txt.j2
`-- grammars/examples/           # Hand-crafted reference grammars
```

The pipeline is intentionally linear - there's almost nothing to configure.
That's the point.

## Development

```bash
git clone https://github.com/intelege-ma/servicenow-to-gbnf.git
cd servicenow-to-gbnf
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                # 47 tests, ~1s
ruff check .
```

CI runs `ruff`, `mypy`, and `pytest` on Python 3.11 and 3.12 plus a smoke-test
that exercises the full CLI end-to-end (see `.github/workflows/ci.yml`).

## Roadmap

- [x] **Phase 1** - CLI scaffolding, vendor-script integration, worker template
- [x] **Phase 2** - Robust pipeline, audit metadata, include/exclude flags, `list-endpoints`, full pytest suite, CI
- [ ] **Phase 3** - Live ServiceNow connection (basic + OAuth), pre-built grammars for common tables, optional Streamlit UI

The free OSS tier in this repo is the foundation. Phase 3 will keep
everything here working - additions are opt-in.

## Contributing

PRs and issues are welcome. Please:
1. Open an issue first if you're proposing a non-trivial change.
2. Match the existing style (`ruff check` must pass).
3. Add a test for any new behavior.

## License

[Apache-2.0](LICENSE). Vendored `json_schema_to_grammar.py` from
[ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) (MIT).

---

Made with love by [intelege-ma](https://github.com/intelege-ma).
