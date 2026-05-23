# Migration Inventory: AgenticSeek → ecoseek-client

Generated: 2026-05-22
From: alrobles/AgenticSeek (commit: latest main)

## Inventory

Each file classified: **MOVE** (EcoSeek-owned, migrate), **KEEP** (stays in
AgenticSeek fork), **GLUE** (integration glue, review during Phase 6),
**SKIP** (upstream AgenticSeek, never copy).

### ecoseek/ package (MOVE — fully EcoSeek-owned)

| File | Target | License safe? | Notes |
|------|--------|---------------|-------|
| `ecoseek/__init__.py` | `src/ecoseek_client/__init__.py` | Yes — authored by alrobles | Empty, needs module docstring |
| `ecoseek/aar/__init__.py` | `src/ecoseek_client/aar/__init__.py` | Yes | Empty |
| `ecoseek/aar/decision_gate.py` | `src/ecoseek_client/aar/decision_gate.py` | Yes | Gate evaluation logic |
| `ecoseek/aar/intent_decomposer.py` | `src/ecoseek_client/aar/intent_decomposer.py` | Yes | Intent decomposition |
| `ecoseek/aar/orchestrator.py` | `src/ecoseek_client/aar/orchestrator.py` | Yes | Core AAR loop — imports other aar modules |
| `ecoseek/aar/quality_assessor.py` | `src/ecoseek_client/aar/quality_assessor.py` | Yes | Quality assessment |
| `ecoseek/aar/retrieval_router.py` | `src/ecoseek_client/aar/retrieval_router.py` | Yes | Retrieval routing |
| `ecoseek/aar/synthesizer.py` | `src/ecoseek_client/aar/synthesizer.py` | Yes | Final synthesis |
| `ecoseek/observability/__init__.py` | `src/ecoseek_client/observability/__init__.py` | Yes | Empty |
| `ecoseek/observability/phoenix_setup.py` | `src/ecoseek_client/observability/phoenix_setup.py` | Yes | Phoenix tracing — make optional |
| `ecoseek/providers/__init__.py` | `src/ecoseek_client/providers/__init__.py` | Yes | |
| `ecoseek/providers/nemotron.py` | `src/ecoseek_client/providers/nemotron.py` | Yes | Nemotron/DeepSeek/EcoCoder fallback |
| `ecoseek/prompts/intent_decompose.md` | `src/ecoseek_client/prompts/intent_decompose.md` | Yes | |
| `ecoseek/prompts/quality_assess.md` | `src/ecoseek_client/prompts/quality_assess.md` | Yes | |

### sources/ — EcoSeek-owned (MOVE)

| File | Target | License safe? | Notes |
|------|--------|---------------|-------|
| `sources/ecoseek_entrypoint.py` | `src/ecoseek_client/cli.py` | Yes | CLI entrypoint. Rename to cli.py. Remove dependency on `cli.main` — rewrite subcommand dispatcher. |
| `sources/agenticplug_session.py` | `src/ecoseek_client/session.py` | Yes | Session file loader. Drop-in ready. |
| `sources/agenticplug_ux.py` | `src/ecoseek_client/agenticplug_ux.py` | Yes | UX store. Depends on `sources.schemas` + `sources.logger` — needs adaptation. |
| `sources/connector_discovery.py` | `src/ecoseek_client/connector_discovery.py` | Yes | Connector discovery. Depends on `sources.utility.pretty_print` — inline or remove. |
| `sources/keystore.py` | `src/ecoseek_client/keystore.py` | Yes | BYOK key storage. Self-contained. |
| `sources/aar.py` | `src/ecoseek_client/aar_metrics.py` | Yes | AAR instrumentation (NOT the orchestrator). Rename to avoid confusion. |
| `sources/tools/agenticplug_connector.py` | `src/ecoseek_client/tools/agenticplug.py` | Yes | AgenticPlug connector tool. Depends on AgenticSeek tool framework — needs adapter or rewrite. |

### prompts/ecoseek/ (MOVE)

| File | Target | Notes |
|------|--------|-------|
| `prompts/ecoseek/browser_agent.txt` | `src/ecoseek_client/prompts/browser_agent.txt` | |
| `prompts/ecoseek/casual_agent.txt` | `src/ecoseek_client/prompts/casual_agent.txt` | |
| `prompts/ecoseek/coder_agent.txt` | `src/ecoseek_client/prompts/coder_agent.txt` | |
| `prompts/ecoseek/file_agent.txt` | `src/ecoseek_client/prompts/file_agent.txt` | |
| `prompts/ecoseek/planner_agent.txt` | `src/ecoseek_client/prompts/planner_agent.txt` | |

### tests/ — EcoSeek-specific (MOVE)

| File | Target | Notes |
|------|--------|-------|
| `tests/test_ecoseek_entrypoint.py` | `tests/test_cli.py` | CLI tests |
| `tests/test_agenticplug_session.py` | `tests/test_session.py` | Session tests |
| `tests/test_agenticplug_provider.py` | `tests/test_providers/test_agenticplug.py` | |
| `tests/test_agenticplug_ux.py` | `tests/test_agenticplug_ux.py` | |
| `tests/test_agenticplug_gateway_smoke.py` | `tests/test_smoke.py` | |
| `tests/test_connector_discovery.py` | `tests/test_connector_discovery.py` | |
| `tests/test_keystore.py` | `tests/test_keystore.py` | |
| `tests/test_ecocoder_provider.py` | `tests/test_providers/test_ecocoder.py` | |
| `tests/test_ecocoder_cluster.py` | `tests/test_providers/test_ecocoder_cluster.py` | |
| `tests/test_aar_core.py` | `tests/test_aar.py` | AAR orchestrator tests |

### docs/ — EcoSeek-specific (MOVE)

| File | Target | Notes |
|------|--------|-------|
| `docs/agenticplug-connector-design.md` | `docs/agenticplug-connector-design.md` | |
| `docs/agenticplug_device_flow.md` | `docs/agenticplug_device_flow.md` | |
| `docs/agenticplug_gpl_boundary.md` | `docs/agenticplug_gpl_boundary.md` | |
| `docs/agenticplug_provider.md` | `docs/agenticplug_provider.md` | |
| `docs/connector-discovery.md` | `docs/connector-discovery.md` | |
| `docs/deepseek-byok.md` | `docs/deepseek-byok.md` | |
| `docs/ecocoder-cluster.md` | `docs/ecocoder-cluster.md` | |
| `docs/ecocoder-local.md` | `docs/ecocoder-local.md` | |
| `docs/ku-hpc-slurm-operations.md` | `docs/ku-hpc-slurm-operations.md` | |
| `docs/local-agenticseek-to-cluster.md` | `docs/local-agenticseek-to-cluster.md` | |

### scripts/ (MOVE)

| File | Target | Notes |
|------|--------|-------|
| `scripts/agenticplug_smoke.py` | `src/ecoseek_client/workflows/smoke.py` | Rename, update imports |

### GLUE — stays in AgenticSeek, review in Phase 6

| File | Why |
|------|-----|
| `cli.py` | Main AgenticSeek CLI. Only the ecoseek entrypoint moved. |
| `config.ini` | Mixed config. EcoSeek sections may be referenced. |
| `api.py` | API server (upstream feature). |
| `sources/llm_provider.py` | Has AgenticPlug integration. Phase 6: refactor to import from ecoseek_client. |
| `pyproject.toml` | AgenticSeek package metadata. ecoseek-client gets its own. |

### SKIP — upstream AgenticSeek, never move

`setup.py`, `requirements.txt`, `uv.lock`, `Dockerfile.*`, `docker-compose.yml`,
`sources/agents/`, `sources/browser.py`, `sources/interaction.py`,
`sources/language.py`, `sources/local_security.py`, `sources/logger.py`,
`sources/memory.py`, `sources/router.py`, `sources/schemas.py`,
`sources/speech_to_text.py`, `sources/text_to_speech.py`, `sources/utility.py`,
`sources/web_scripts/`, `sources/tools/` (except agenticplug_connector.py),
`prompts/base/`, `prompts/jarvis/`, `llm_server/`, `llm_router/`,
`frontend/`, `searxng/`, `media/`, `crx/`, `.github/`, `.agents/`,
`tests/` (except EcoSeek-specific ones listed above),
`docs/` (except EcoSeek-specific ones listed above).

### From ecoseek repo — PORT

| File | Target | Notes |
|------|--------|-------|
| `scripts/remote-smoke.sh` | `src/ecoseek_client/workflows/remote_smoke.py` | Rewrite in Python. 395 lines of bash → ~200 lines Python. |
| `scripts/smoke.sh` | `src/ecoseek_client/workflows/local_smoke.py` | Rewrite in Python. |

---

## Dependency graph (moved modules)

```
session.py           — no internal deps (just stdlib + json)
keystore.py          — no internal deps (cryptography, keyring optional)
connector_discovery.py — depends on session.py
agenticplug_ux.py    — depends on schemas (needs adaptation)
agenticplug.py       — depends on tool framework (needs adaptation)
cli.py               — depends on all providers, workflows
aar/                 — self-contained package, depends on observability (optional)
providers/           — depends on session, keystore
workflows/           — depends on session, connector_discovery
```

## Adaptation notes

1. **agenticplug_ux.py**: Depends on `sources.schemas` (AgenticPlugTask, etc.) and
   `sources.logger`. These are upstream AgenticSeek code. Either:
   - Copy the schema dataclasses (small, ~30 lines of dataclass definitions)
   - Or write adapter that doesn't need AgenticSeek schemas

2. **agenticplug_connector.py**: Depends on AgenticSeek tool framework.
   Rewrite as a clean provider that calls AgenticPlug HTTP API directly.

3. **connector_discovery.py**: Uses `sources.utility.pretty_print`.
   Replace with `print` + `logging` or copy the small helper.

4. **cli.py (new)**: The current `ecoseek_entrypoint.py` just delegates to
   AgenticSeek's `cli.main`. The new cli.py needs its own subcommand dispatcher
   (argparse or click).

## File count summary

- **MOVE** (from AgenticSeek): 39 files
- **PORT** (from ecoseek): 2 files (both bash → Python rewrites)
- **NEW** (create from scratch): ~10 files (pyproject.toml, README, LICENSE, config.py, providers/base.py, providers/deepseek.py, providers/local.py, providers/agenticplug.py, workflows/local_smoke.py)
- **SKIP** (stay in AgenticSeek): ~50+ files
- **GLUE** (review later): 5 files
