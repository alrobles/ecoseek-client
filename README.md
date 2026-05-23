# ecoseek-client

First-class local client for EcoSeek — scientific agent environment for ecology.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-green.svg)](https://www.python.org/)
[![Status: Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)]()

ecoseek-client connects your laptop to the EcoSeek ecosystem: Hermes scientific agent (on reumanlab), AgenticPlug secure broker, and KU-HPC compute. One CLI, one Python package.

```
ecoseek hermes orchestrate "SDM de jaguar en Yucatan con MaxEnt"
ecoseek smoke remote
ecoseek agenticplug task run hpc.status
```

---

## Quickstart

### Install

```bash
git clone https://github.com/alrobles/ecoseek-client
cd ecoseek-client
pip install -e .
```

### Verify

```bash
ecoseek --version
ecoseek doctor
```

Expected output:

```
ecoseek doctor
  version: 0.1.0

Python
  3.11.15 (CPython)
Platform
  Linux 6.17.0-29-generic
  WSL2: yes
Git
  git: /usr/bin/git
AgenticPlug
  connector: http://127.0.0.1:3100 (healthy, 41ms)
  auth: configured
  session file: /home/reumanlab/.config/agenticplug/session.json (found)
Hermes
  provider: hermes (connected)

Done.
```

### Connect to AgenticPlug

```bash
export AGENTICPLUG_SESSION_FILE=~/.config/agenticplug/session.json
ecoseek agenticplug whoami
# → Connected as: reumanlab
```

### First task

```bash
ecoseek smoke remote
ecoseek hermes orchestrate "Run SDM for monarch butterfly in Mexico"
```

---

## Architecture

```
ecoseek-client (MIT, pip-installable)
│
├── CLI (click) ─────────────────────────────────────────────
│   ecoseek doctor | agenticplug | hermes | smoke | aar | skill
│
├── Providers ───────────────────────────────────────────────
│   ├── AgenticPlugClient  → AgenticPlug (:3100, auth, tasks)
│   └── HermesProvider     → AgenticPlug → Hermes (:8642)
│
├── AAR Loop ────────────────────────────────────────────────
│   observe → reason → act → evaluate → update
│
├── Skills ──────────────────────────────────────────────────
│   SDM, connectivity, niche, climate, ecoseek-system
│
└── Workflows ───────────────────────────────────────────────
    remote_smoke: broker → connector → HPC health check
```

### Full ecosystem

```
[Your laptop]
  ecoseek-client (CLI)
  │
  ├── AgenticPlugClient ──HTTP──→ AgenticPlug (:3100, auth)
  │                                │
  └── HermesProvider ─────────────┘
                                     │
                                     ▼
                               [reumanlab server]
                               Hermes Agent (:8642)
                               ├── DeepSeek v4 Pro (primary)
                               ├── OpenCode Go (fallback)
                               ├── Skills (ecoseek-orchestrator, ecocoder, ecoagent, reviewer)
                               └── Memory (persistent ecosystem knowledge)
```

---

## Commands

### `ecoseek doctor`
Full environment diagnostics: Python, WSL, git, AgenticPlug, Hermes, HPC.

### `ecoseek agenticplug`

| Subcommand | Description |
|------------|-------------|
| `whoami` | Show connected user and connector identity |
| `health` | Check connector health |
| `status` | Full status: health + auth + HPC |
| `clusters` | List all available clusters/connectors |
| `task list` | Show all known tasks |
| `task run NAME` | Dispatch a named task (remote.health, hpc.status, hpc.queue) |

### `ecoseek hermes`

| Subcommand | Description |
|------------|-------------|
| `whoami` | Check Hermes connectivity |
| `orchestrate TASK` | Full agent orchestration (plan → workers → review) |
| `orchestrate -s SPECIES -r REGION -m METHOD` | Scientific SDM task |
| `chat MESSAGE` | Direct chat with Hermes |

### `ecoseek smoke`

| Subcommand | Description |
|------------|-------------|
| `remote` | Full remote smoke: connector → clusters → dispatch → HPC |

### `ecoseek aar`

| Subcommand | Description |
|------------|-------------|
| `run GOAL` | Run observe→reason→act→evaluate→update loop |
| `status` | Show AAR loop capabilities |

### `ecoseek skill`

| Subcommand | Description |
|------------|-------------|
| `list` | List available ecological skills |
| `show NAME` | Show a skill's complete pipeline |

---

## Providers

ecoseek-client can use multiple backends:

### Hermes (via AgenticPlug) — default, recommended

Hermes is the scientific agent running on reumanlab. It handles orchestration, reasoning, tool calling, and has persistent memory.

```bash
ecoseek hermes orchestrate "SDM de Panthera onca en Yucatan"
```

Why through AgenticPlug? Security: GitHub Device Flow auth, scoped sessions, audit log, rate limiting. Hermes is never exposed directly.

### AgenticPlug — direct task dispatch

For simple tasks that don't need reasoning:

```bash
ecoseek agenticplug task run remote.health
ecoseek agenticplug task run hpc.status
```

### Local (coming soon)

For offline work with local models when in the field.

---

## Configuration

All via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTICPLUG_URL` | `http://localhost:3100` | AgenticPlug connector URL |
| `AGENTICPLUG_SESSION` | (none) | Raw session token string |
| `AGENTICPLUG_SESSION_FILE` | `~/.config/agenticplug/session.json` | Path to session JSON file |
| `HERMES_GATEWAY_URL` | `https://hermes.ecoseek.org` | Hermes gateway URL |
| `HERMES_TIMEOUT` | `600` | Hermes orchestration timeout (seconds) |

Copy `.env.example` to `.env` and fill in your values.

---

## Documentation

- [WSL / Ubuntu install](docs/install-wsl.md)
- [Connect to AgenticPlug](docs/connect-agenticplug.md)
- [First task from cluster](docs/first-task.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Migration inventory](docs/migration-inventory.md)
- [Migration plan](docs/migration-plan.md)

---

## Development

```bash
pip install -e ".[dev]"
pytest -v
```

12 tests, 11 passing (1 pre-existing mock mismatch in test_task_remote_health). See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Requirements

- Python 3.10+
- Click 8+
- HTTPX 0.24+
- Git

Optional: AgenticPlug session file, HPC credentials.

---

## License

MIT — see [LICENSE](LICENSE).

No GPL code. Fully independent from AgenticSeek (GPLv3 fork). AgenticSeek can consume ecoseek-client as a package; ecoseek-client does not depend on AgenticSeek.

---

## Status

Pre-Alpha (v0.1.0). Actively developed.

Phases 0-6 complete. Backend (Hermes, AgenticPlug connector) in pre-alpha. Client is testable end-to-end: Hermes connectivity from laptop → AgenticPlug → reumanlab confirmed working.
