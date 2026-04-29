# Changelog

All notable changes to **servicenow-to-gbnf** are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-29

The Phase-2 hardening release. **Every public path in v0.1.0 was broken on a
clean install** - this release fixes them and adds a real test suite + CI so
that doesn't happen again.

### Fixed
- **CLI: `from-openapi` is now actually usable.** Removed the `split("api/now")`
  path-mangling that turned `/api/now/table/incident` into `/table/incident`
  and then guaranteed a "could not find requestBody schema" failure. Paths are
  now matched exactly (modulo a single trailing slash). _Was: CLI-1._
- **Converter: real GBNF instead of a silent stub.** Two stacked bugs in the
  subprocess invocation made every previous user receive a generic-JSON
  fallback grammar with zero schema enforcement:
    - hard-coded `python` command (missing on most modern Linux distros) -
      now uses `sys.executable`;
    - the schema was passed as a positional arg where the vendored llama.cpp
      script expected a file path - now piped through stdin via `"-"`.
  Failures are surfaced as `GBNFConversionError` with the underlying stderr,
  not silently swallowed. _Was: CONVERTER-1._
- **Generated worker.py is now valid Python.** The Jinja substitution didn't
  replace hyphens, so the default `sn::incident-create` rendered as
  `sn_incident-create` - invalid identifier. The generator now derives a safe
  Python name via regex while keeping the original iii function id intact in
  `register_function(...)`. _Was: WORKER-1._
- **No more hard-coded credentials in the worker template.** `auth=("admin",
  "your_password")` is gone; the generated worker reads `SERVICENOW_USERNAME` /
  `SERVICENOW_PASSWORD` from the environment and refuses to run without them.
  _Was: WORKER-2._
- **System prompt is no longer empty.** `prompt.txt.j2` now receives the same
  context as `worker.py.j2` so `Field guidance for table:` actually
  describes fields. _Was: WORKER-3._
- **Package paths work after `pip install`.** `converter.VENDOR_PATH` and the
  template loader were both relative to the current working directory; both
  now resolve relative to `__file__`. _Was: PACKAGE-1._
- **Wheel actually contains templates + vendor script.** Added `__init__.py`
  to every subpackage and declared `[tool.setuptools.package-data]` in
  `pyproject.toml`. _Was: PACKAGE-2 + PACKAGE-3._

### Added
- New `list-endpoints` command with `--filter <regex>` and `--method <m>`
  filters, rendered as a Rich table.
- `--include-fields` and `--exclude-fields` flags on `from-openapi` for
  property-level grammar shaping.
- `<name>.meta.json` audit sidecar emitted alongside every grammar:
  `{ generated_at, tool_version, source_path, source_method, schema_sha256 }`.
- `tests/fixtures/servicenow-incident.yaml` - a hand-crafted but realistic
  ServiceNow Table API subset usable as a self-contained playground.
- Full `pytest` suite: 47 tests, 93% line coverage on `core/` + `cli`.
- GitHub Actions CI (`.github/workflows/ci.yml`) running `ruff`, `mypy`, and
  the test suite on Python 3.11 and 3.12 plus a CLI smoke-test job.
- Project metadata polish: PyPI classifiers, project URLs, ruff + pytest
  configuration in `pyproject.toml`.

### Changed
- Schema processor now accepts external `$defs` (e.g. `components.schemas`)
  via a second argument to `process()`, tolerates missing/cyclic refs, and
  prunes orphaned entries from `required` after simplification.
- Default keep-set extended to include `assignment_group`.
- Generated worker resolves the grammar via `Path(__file__).parent / "<file>"`
  so the worker is portable across machines.
- Generated worker file name is now `re.sub(r"[^A-Za-z0-9]+", "_", ...)`-derived
  rather than a naive `replace("::", "_")`, so multi-colon ids don't break.

### Internal
- `from __future__ import annotations` everywhere; modern type hints (`list`,
  `dict`, `X | None`) wherever ruff's `UP` rules apply.
- `_python_identifier` and `_http_api_path` extracted into staticmethods on
  `IIIWorkerGenerator`, both unit-tested in isolation.

## [0.1.0] - 2026-04-29

Initial public release. Wireframe-level MVP - see
[v0.2.0](#020--2026-04-29) above for the full list of bugs that this release
shipped with.
