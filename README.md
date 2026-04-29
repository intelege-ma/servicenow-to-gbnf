# servicenow-to-gbnf

**Open-source deterministic ServiceNow AI connector**  
Live GBNF grammar from ServiceNow OpenAPI → ready-to-use iii worker (zero hallucinations).

Works with [iii-hq/iii](https://github.com/iii-hq/iii) + llama.cpp / Ollama.

## Installation

```bash
uv pip install git+https://github.com/intelege-ma/servicenow-to-gbnf.git

## 30-second Quick Start

```bash
1. Generate grammar (from your ServiceNow OpenAPI export)
servicenow-to-gbnf from-openapi \
  --file ./servicenow-openapi.yaml \
  --path /api/now/table/incident \
  --method post \
  --output ./grammars/

# 2. Generate iii worker
servicenow-to-gbnf generate-worker \
  --grammar ./grammars/incident-post.gbnf

Pre-generated example grammars are available in grammars/examples/.
Features (Free forever)

Full CLI for JSON Schema → GBNF conversion
Automatic ServiceNow enum injection
Ready-to-run iii Python workers
Works with local LLMs (Ollama / llama.cpp)

Free and open-source forever. Built for the ServiceNow + iii community.

## Next Steps
Try it on your ServiceNow PDI instance
Star the repo if it helps you!

Made with ❤️ by intelege-ma