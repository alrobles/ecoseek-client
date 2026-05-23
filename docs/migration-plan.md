# EcoSeek Client — Migration Plan (Phase 0–7)

## Purpose

Extract EcoSeek-owned client code from the `alrobles/AgenticSeek` fork into
`alrobles/ecoseek-client`, keeping AgenticSeek as an optional shell/runtime
while `ecoseek-client` becomes the first-class local client for EcoSeek,
AgenticPlug, reumanlab, and KU-HPC workflows.

Key motivation: **licensing hygiene**. AgenticSeek is GPLv3. EcoSeek wants
`ecoseek-client` under MIT or Apache-2.0. All code in the AgenticSeek fork
was authored by alrobles/EcoSeek and can be relicensed, but we must track
provenance and avoid copying upstream AgenticSeek internals.

---

## Repository Map

```
alrobles/AgenticSeek   — GPLv3 fork. Has EcoSeek-specific code intermixed
                          with upstream AgenticSeek sources. After migration
                          it remains as an integration shell.

alrobles/ecoseek       — Product/website/docs/smoke orchestration.
                          Currently public-facing site. Keeps docs,
                          connector code, docker configs. Does NOT
                          get the client package.

alrobles/ecoseek-client — NEW. The pip-installable client package.
                           MIT or Apache-2.0 licensed.

alrobles/agenticplug   — Secure broker/connector layer. Unaffected
                          by this migration.
```

---

## Phase 0: Inventory

### Files identified in AgenticSeek fork

#### EcoSeek-owned — MOVE to ecoseek-client

| Source path (in AgenticSeek)         | Target path (in ecoseek-client)        | Notes |
|--------------------------------------|----------------------------------------|-------|
| `ecoseek/__init__.py`                | `src/ecoseek_client/__init__.py`       | Empty, needs content |
| `ecoseek/aar/__init__.py`            | `src/ecoseek_client/aar/__init__.py`   | Empty |
| `ecoseek/aar/decision_gate.py`       | `src/ecoseek_client/aar/decision_gate.py` | |
| `ecoseek/aar/intent_decomposer.py`   | `src/ecoseek_client/aar/intent_decomposer.py` | |
| `ecoseek/aar/orchestrator.py`        | `src/ecoseek_client/aar/orchestrator.py` | Core AAR loop |
| `ecoseek/aar/quality_assessor.py`    | `src/ecoseek_client/aar/quality_assessor.py` | |
| `ecoseek/aar/retrieval_router.py`    | `src/ecoseek_client/aar/retrieval_router.py` | |
| `ecoseek/aar/synthesizer.py`         | `src/ecoseek_client/aar/synthesizer.py` | |
| `ecoseek/observability/__init__.py`  | `src/ecoseek_client/observability/__init__.py` | Empty |
| `ecoseek/observability/phoenix_setup.py` | `src/ecoseek_client/observability/phoenix_setup.py` | Phoenix tracing |
| `ecoseek/providers/__init__.py`      | `src/ecoseek_client/providers/__init__.py` | |
| `ecoseek/providers/nemotron.py`      | `src/ecoseek_client/providers/nemotron.py` | Nemotron provider |
| `ecoseek/prompts/intent_decompose.md` | `src/ecoseek_client/prompts/intent_decompose.md` | |
| `ecoseek/prompts/quality_assess.md`  | `src/ecoseek_client/prompts/quality_assess.md` | |
| `sources/ecoseek_entrypoint.py`      | `src/ecoseek_client/cli.py`            | Renamed. Becomes main CLI entrypoint |
| `sources/agenticplug_session.py`     | `src/ecoseek_client/session.py`        | AgenticPlug session loading |
| `sources/agenticplug_ux.py`          | `src/ecoseek_client/agenticplug_ux.py` | UX store for tasks |
| `sources/connector_discovery.py`     | `src/ecoseek_client/connector_discovery.py` | Connector discovery |
| `sources/keystore.py`                | `src/ecoseek_client/keystore.py`       | BYOK key storage |
| `sources/aar.py`                     | `src/ecoseek_client/aar_metrics.py`    | AAR instrumentation/metrics. Renamed to avoid confusion with aar/ package |
| `sources/tools/agenticplug_connector.py` | `src/ecoseek_client/tools/agenticplug.py` | AgenticPlug tool |
| `prompts/ecoseek/*.txt`              | `src/ecoseek_client/prompts/`          | 5 prompt files (browser, casual, coder, file, planner agents) |
| `tests/test_ecoseek_entrypoint.py`   | `tests/test_cli.py`                    | |
| `tests/test_agenticplug_session.py`  | `tests/test_session.py`                | |
| `tests/test_agenticplug_provider.py` | `tests/test_providers/test_agenticplug.py` | |
| `tests/test_agenticplug_ux.py`       | `tests/test_agenticplug_ux.py`         | |
| `tests/test_agenticplug_gateway_smoke.py` | `tests/test_smoke.py`             | |
| `tests/test_connector_discovery.py`  | `tests/test_connector_discovery.py`    | |
| `tests/test_keystore.py`             | `tests/test_keystore.py`               | |
| `tests/test_ecocoder_provider.py`    | `tests/test_providers/test_ecocoder.py` | |
| `tests/test_ecocoder_cluster.py`     | `tests/test_providers/test_ecocoder_cluster.py` | |
| `tests/test_aar_core.py`             | `tests/test_aar.py`                    | AAR orchestrator tests |
| `docs/agenticplug*.md`               | `docs/`                                | AgenticPlug docs |
| `docs/ecocoder*.md`                  | `docs/`                                | EcoCoder docs |
| `docs/deepseek-byok.md`              | `docs/`                                | |
| `docs/connector-discovery.md`        | `docs/`                                | |
| `docs/ku-hpc-slurm-operations.md`    | `docs/`                                | |
| `docs/local-agenticseek-to-cluster.md` | `docs/`                              | |
| `scripts/agenticplug_smoke.py`       | `src/ecoseek_client/workflows/smoke.py` | Renamed |

#### EcoSeek-owned — KEEP in AgenticSeek (integration glue)

| Path                        | Why it stays                                   |
|-----------------------------|------------------------------------------------|
| `cli.py`                    | Main AgenticSeek CLI (not EcoSeek-specific)    |
| `config.ini`                | AgenticSeek config (mixed, review later)       |
| `api.py`                    | API server (upstream AgenticSeek)              |
| `sources/llm_provider.py`   | Has AgenticPlug import — needs refactor, not move |

#### Upstream AgenticSeek — DO NOT MOVE

All `sources/agents/`, `sources/router.py`, `sources/interaction.py`,
`sources/memory.py`, `sources/browser.py`, `sources/tools/` (except
agenticplug_connector.py), `prompts/base/`, `prompts/jarvis/`,
`llm_server/`, `llm_router/`, `frontend/`, `searxng/`.

#### From ecoseek repo — PORT to ecoseek-client

| Source path (ecoseek)              | Target path (ecoseek-client)          | Notes |
|------------------------------------|---------------------------------------|-------|
| `scripts/remote-smoke.sh`          | Ported to `workflows/remote_smoke.py` | Rewrite shell → Python |
| `scripts/smoke.sh`                 | Ported to `workflows/local_smoke.py`  | Rewrite shell → Python |

### Licensing boundary notes

- All EcoSeek code in AgenticSeek was authored by alrobles — safe to relicense
- AgenticSeek upstream (Fosowl/agenticSeek) is GPLv3 — never copy upstream internals
- `sources/llm_provider.py` imports `agenticplug_session` — this is a GPL boundary.
  After migration, AgenticSeek's llm_provider should import from the ecoseek-client
  package instead.
- Prefer clean-room wrappers over copying: write new `base.py` provider interface,
  implement providers against it

---

## Phase 1: Package skeleton

Create minimal installable Python package.

### Tasks

1. Create `pyproject.toml` with package name `ecoseek-client`, CLI entrypoint `ecoseek`
2. Create `README.md`
3. Create `LICENSE` (MIT)
4. Create package skeleton under `src/ecoseek_client/`
5. Create `src/ecoseek_client/cli.py` with `--help`, `--version`, `doctor`
6. Create `src/ecoseek_client/config.py` (env loading, defaults)
7. Create `.gitignore`, `.env.example`
8. Set up tests with pytest

### Acceptance

- `pip install -e .` works
- `ecoseek --help` prints usage
- `ecoseek --version` prints version
- `ecoseek doctor` checks Python version, deps, AgenticPlug session file

---

## Phase 2: Session + AgenticPlug provider

### Tasks

1. Port `agenticplug_session.py` → `src/ecoseek_client/session.py`
   - Rename `AgenticPlugSession` → `Session`, keep compat aliases
   - Same file paths, env vars (`AGENTICPLUG_SESSION_FILE`, etc.)
2. Port `connector_discovery.py` → `src/ecoseek_client/connector_discovery.py`
   - Remove dependency on `sources.utility.pretty_print` (inline or skip)
   - Use `ecoseek_client.session` instead of `sources.agenticplug_session`
3. Add CLI commands to `cli.py`:
   - `ecoseek agenticplug whoami` — prints identity from session
   - `ecoseek agenticplug clusters` — lists connectors
   - `ecoseek agenticplug task remote.health` — dispatches task
   - `ecoseek agenticplug task hpc.status` — HPC status
4. Never print tokens. Store no secrets in repo.

### Acceptance

- With valid `AGENTICPLUG_SESSION`, `ecoseek agenticplug clusters` lists reumanlab
- Missing session produces clear error with login instructions
- Tests mock HTTP and prove no token leakage

---

## Phase 3: Remote smoke workflow

### Tasks

1. Port `scripts/remote-smoke.sh` (from ecoseek repo) to Python
   - `ecoseek smoke remote`
2. Steps: broker /healthz → edge health → task dispatch (remote.health, hpc.status, hpc.queue)
3. Classify failures: auth, broker down, connector offline, HPC unavailable, capability disabled
4. Same exit codes as shell version (0–6)

### Acceptance

- `ecoseek smoke remote` gives actionable diagnostics
- No token leakage
- Exits non-zero on real failures
- Can run without AgenticSeek installed

---

## Phase 4: Model providers

### Tasks

1. Create `src/ecoseek_client/providers/base.py` — abstract Provider interface
2. Create `src/ecoseek_client/providers/deepseek.py` — BYOK DeepSeek
   - Read API key from env or keystore (port `keystore.py`)
   - Simple `ecoseek provider deepseek smoke` command
3. Port `ecoseek/providers/nemotron.py` → `src/ecoseek_client/providers/nemotron.py`
4. Create `src/ecoseek_client/providers/local.py` — local EcoAgent/EcoCoder
   - OpenAI-compatible endpoint
   - Graceful degradation when no local model
5. Create `src/ecoseek_client/providers/agenticplug.py` — AgenticPlug as LLM provider
   - Wraps session + task dispatch
   - Optional: not required for basic install

### Acceptance

- Provider interface is stable
- DeepSeek provider works with user-owned key
- Local provider has smoke path
- AgenticPlug provider is isolated and optional

---

## Phase 5: AAR / ReAct loop

### Tasks

1. Port `ecoseek/aar/` → `src/ecoseek_client/aar/` (already inventoried in Phase 0)
   - Update imports: `ecoseek.aar.*` → `ecoseek_client.aar.*`
   - Remove Phoenix dependency or make it optional
2. Port `sources/aar.py` → `src/ecoseek_client/aar_metrics.py`
3. Create minimal loop: observe → reason → act → evaluate → update
4. Support provider selection (DeepSeek, local, AgenticPlug)
5. Support AgenticPlug tool calls

### Acceptance

- Minimal local task runs end-to-end
- Remote task can call `remote.health` or `hpc.status`
- Loop runs without AgenticSeek
- Unit tests cover loop transitions

---

## Phase 6: AgenticSeek integration

### Tasks

1. Add `ecoseek-client` as dependency to `alrobles/AgenticSeek`
2. Update `sources/llm_provider.py` to import from ecoseek_client
3. Update `sources/ecoseek_entrypoint.py` to re-export from ecoseek_client
4. Document editable install for both repos
5. Keep AgenticSeek-specific glue minimal

### Acceptance

- AgenticSeek fork runs existing workflows
- EcoSeek logic lives in ecoseek-client
- No unnecessary duplication

---

## Phase 7: Packaging + docs

### Tasks

1. Write WSL install guide
2. Write "connect to AgenticPlug" guide
3. Write "first hello world from cluster" guide
4. Add `.env.example`
5. Add troubleshooting docs
6. Add `ecoseek doctor` full implementation (check env, deps, network, session)

### Acceptance

New user can:
```
pip install -e .
ecoseek doctor
ecoseek agenticplug clusters
ecoseek smoke remote
```

---

## Execution Order

1. Phase 0 — inventory (this document)
2. Phase 1 — package skeleton + `ecoseek doctor`
3. Phase 2 — AgenticPlug session + provider
4. Phase 3 — remote smoke workflow
5. Phase 4 — model providers (DeepSeek + local + AgenticPlug)
6. Phase 5 — AAR / ReAct loop
7. Phase 6 — AgenticSeek reintegration
8. Phase 7 — packaging + docs

---

## Definition of Done (MVP)

- `alrobles/ecoseek-client` repo has working code
- `pip install -e .` works
- `ecoseek --help`, `ecoseek doctor` work
- `ecoseek agenticplug clusters` lists reumanlab
- `ecoseek smoke remote` runs diagnostics
- AgenticSeek fork no longer owns core EcoSeek client logic

---

## Deferred (post-MVP)

- Full approval workflow for write/HPC mutation ops
- Managed SaaS auth
- Multi-cluster UI
- Public product website (stays in ecoseek repo)
- Full upstream AgenticSeek PR
- Complete EcoCoder/EcoAgent local model serving
