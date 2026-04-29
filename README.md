# servicenow-to-gbnf

**Open-source deterministic ServiceNow AI connector**  
Live GBNF grammar from ServiceNow OpenAPI → ready-to-use iii worker (zero hallucinations).

Works with iii + llama.cpp / Ollama.

## Installation

```bash
uv pip install git+https://github.com/intelege-ma/servicenow-to-gbnf.git

## Phase 2 – Generate iii Worker (NEW)

```bash
# After generating grammar

servicenow-to-gbnf generate-worker \
  --grammar ./grammars/incident-post.gbnf \
  --iii-function sn::incident-create \
  --instance https://dev12345.service-now.com \
  --table incident
  