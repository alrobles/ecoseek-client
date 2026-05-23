# ecoseek-client

First-class local client for EcoSeek — the scientific agent environment for ecology.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-green.svg)](https://www.python.org/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

**ecoseek-client** connects your laptop to the EcoSeek ecosystem: Hermes scientific agent, AgenticPlug secure broker, and KU-HPC compute. One CLI for everything.

```
ecoseek hermes orchestrate "SDM de jaguar en Yucatan con MaxEnt"
ecoseek smoke remote
ecoseek agenticplug task run hpc.status
```

---

## Why ecoseek-client?

You're an ecologist with a laptop. You need to:
- Talk to Hermes (scientific reasoning agent) for SDM, connectivity, niche analysis
- Reach HPC clusters (KU's Slurm) to run compute jobs
- Check system health across connectors, Cloudflare tunnels, and agents
- Work offline with local models when in the field

ecoseek-client is the single Python package that does all of this. It replaces scattered shell scripts, curl commands, and SSH aliases with a consistent CLI.

**No AgenticSeek required.** ecoseek-client is fully independent (MIT licensed). AgenticSeek can consume it as an integration shell, but you don't need it.

---

## Quickstart

### Install

```bash
# From PyPI (coming soon)
pip install ecoseek-client

# From source (development)
git clone https://github.com/alrobles/ecoseek-client
cd ecoseek-client
pip install -e . --break-system-packages
```

### Verify

```bash
ecoseek --version     # 0.1.0
ecoseek doctor        # Full environment diagnostic
```

### Connect to AgenticPlug

```bash
# If you already have an AgenticPlug session file:
export AGENTICPLUG_SESSION_FILE=~/.config/agenticplug/session.json
ecoseek agenticplug whoami  # → "Connected as: alrobles"

# List available connectors:
ecoseek agenticplug clusters
# → ✓ reumanlab (local)  ✓ ku-hpc (hpc) [rw]
```

### First task

```bash
# Health check: local connector → Cloudflare tunnel → Hermes
ecoseek smoke remote

# Check HPC jobs
ecoseek agenticplug task run hpc.status

# Run an SDM through Hermes
ecoseek hermes orchestrate "Species distribution model for monarch butterfly in Mexico"
```

---

## Architecture

```
ecoseek-client (MIT, pip-installable)
│
├── CLI (click) ──────────────────────────────────────────────
│   ecoseek doctor | agenticplug | hermes | smoke | aar | skill
│
├── Providers ────────────────────────────────────────────────
│   ├── AgenticPlugClient  → agenticplug (port 3100, auth, tasks)
│   └── HermesProvider     → hermes.ecoseek.org (orchestration)
│
├── AAR Loop ─────────────────────────────────────────────────
│   observe → reason → act → evaluate → update
│   Scientific autonomy measurement
│
├── Skills ───────────────────────────────────────────────────
│   SDM, connectivity, niche, climate analysis pipelines
│
└── Workflows ────────────────────────────────────────────────
    remote_smoke: full-stack health check (broker → connector → HPC)
```

### The full ecosystem

```
[Your laptop]
  ecoseek-client (CLI)
  │
  ├── AgenticPlugClient ──HTTP────────→ AgenticPlug (port 3100, auth)
  │                                      │
  └── HermesProvider ────HTTP────────→ Cloudflare Tunnel
                                        hermes.ecoseek.org:443
                                          │
                                          ▼
                                     [reumanlab server]
                                       Hermes Agent (:8642)
                                       ├── DeepSeek v4 Pro (primary)
                                       ├── OpenCode Go (fallback)
                                       ├── Skills (SDM, niche, climate)
                                       └── Memory (persistent knowledge)
```

---

## Commands

### `ecoseek doctor`
Full environment diagnostics: Python, WSL, git, SSH, AgenticPlug, HPC, Docker.

### `ecoseek agenticplug`
AgenticPlug broker commands:

| Subcommand | Description |
|------------|-------------|
| `whoami` | Show connected user and connector identity |
| `health` | Check connector health |
| `status` | Full status: health + auth + HPC |
| `clusters` | List all available clusters/connectors |
| `task list` | Show all known tasks |
| `task run NAME` | Dispatch a named task (remote.health, hpc.status, hpc.queue) |

### `ecoseek hermes`
Hermes scientific agent commands:

| Subcommand | Description |
|------------|-------------|
| `whoami` | Check Hermes connectivity |
| `orchestrate TASK` | Full agent orchestration (plan → workers → review) |
| `orchestrate -s SPECIES -r REGION -m METHOD` | Scientific SDM task |
| `chat MESSAGE` | Direct chat with Hermes |

### `ecoseek smoke`
Diagnostic smoke tests:

| Subcommand | Description |
|------------|-------------|
| `remote` | Full remote smoke: connector → clusters → dispatch → HPC |

### `ecoseek aar`
AAR (After Action Review) ReAct loop:

| Subcommand | Description |
|------------|-------------|
| `run GOAL` | Run observe→reason→act→evaluate→update loop |
| `status` | Show AAR capabilities |

### `ecoseek skill`
Scientific skills:

| Subcommand | Description |
|------------|-------------|
| `list` | List available ecological skills |
| `show NAME` | Show a skill's complete pipeline |

---

## Configuration

All configuration via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTICPLUG_URL` | `http://localhost:3100` | AgenticPlug connector URL |
| `AGENTICPLUG_SESSION` | (none) | Raw session token string |
| `AGENTICPLUG_SESSION_FILE` | `~/.config/agenticplug/session.json` | Path to session JSON file |
| `HERMES_GATEWAY_URL` | `https://hermes.ecoseek.org` | Hermes gateway URL |
| `HERMES_TIMEOUT` | `600` | Hermes orchestration timeout (seconds) |

See `.env.example` for a complete template.

---

## Installation guides

- [WSL / Ubuntu install](docs/install-wsl.md)
- [Connect to AgenticPlug](docs/connect-agenticplug.md)
- [First hello world from cluster](docs/first-task.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## Development

```bash
pip install -e ".[dev]" --break-system-packages
pytest -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Requirements

- Python 3.10+  
- Click 8+  
- HTTPX 0.24+  
- Git (for version detection)  

**Optional:** Docker, HPC credentials, AgenticPlug session file.

---

## License

MIT — see [LICENSE](LICENSE).

## Status

Alpha (v0.1.0). Actively developed. Breaking changes possible before v1.0.

Phases complete: 0–6. Phase 7 (packaging) in progress.
