# First Hello World from Cluster

Once ecoseek-client is installed and connected to AgenticPlug, here's your first end-to-end task: dispatch a simple remote health check and see the full diagnostic path.

## Prerequisites

- ecoseek-client installed ([install guide](install-wsl.md))
- AgenticPlug connected ([connect guide](connect-agenticplug.md))

## Run your first diagnostic

```bash
ecoseek smoke remote
```

This runs the full stack health check:
1. AgenticPlug broker health
2. Cluster/connector discovery
3. Remote task dispatch (remote.health)
4. HPC status check (if configured)

Expected output:
```
Connector health: OK (12ms)
Cluster discovery: 2 clusters found
  ✓ reumanlab (local)
  ✓ ku-hpc (hpc) [rw]
Task dispatch: remote.health → OK (45ms)
HPC status: 3 jobs in queue

Remote smoke: all clear.
```

## What's actually happening

```
ecoseek smoke remote
  │
  ├── GET localhost:3100/health           → broker check
  ├── GET localhost:3100/api/clusters     → connector discovery
  ├── POST localhost:3100/v1/tasks/run    → task dispatch
  │     └── cloudflared tunnel → reumanlab → Hermes
  │           └── Hermes responds
  └── POST localhost:3100/api/hpc/status → HPC check (if auth)
```

## Your first scientific task

Now something ecological:

```bash
ecoseek hermes orchestrate "SDM for monarch butterfly in central Mexico"
```

This sends the task to Hermes, which:
1. Plans the SDM workflow
2. Selects appropriate skills (SDM, niche, climate)
3. Dispatches worker agents in parallel
4. Reviews and synthesizes the report
5. Returns the complete result

Expected output:
```
Hermes Orchestration
  task: SDM for monarch butterfly in central Mexico
  mode: ecoSeek

Completed (2340ms)
  task_id: task-abc123
  Workers: 2 deployed
    ✓ EcoCoder: success
    ✓ EcoAgent: success
  Report:
    SDM complete for Danaus plexippus. MaxEnt model fit with AUC=0.89...
```

## Working with parameters

Instead of free-text, use structured parameters:

```bash
ecoseek hermes orchestrate \
  --species "Panthera onca" \
  --region "Yucatan Peninsula" \
  --method "MaxEnt"
```

## Check Hermes connectivity directly

```bash
ecoseek hermes whoami
```

Expected:
```
Hermes Provider
  connector: hermes.ecoseek.org
  status: connected (42ms)
```

## Run an AAR (autonomous) loop

```bash
ecoseek aar run "Check all connectors, report health status"
```

This runs the full observe→reason→act→evaluate→update cycle.

## Check HPC jobs

```bash
ecoseek agenticplug task run hpc.status
```

Expected:
```
Running: hpc.status — Check HPC job queue
  GET /api/hpc/status
  OK (120ms)

{
  "jobs": [
    {"id": 12345, "name": "maxent_sdm", "state": "RUNNING", ...}
  ],
  "total": 3
}
```

## Available ecological skills

```bash
ecoseek skill list
```

```
SDM         — Species distribution modeling
connectivity — Landscape connectivity analysis
niche       — Ecological niche modeling
climate     — Climate envelope analysis
system      — EcoSeek system diagnostics
```

## Next steps

- [Troubleshooting guide](troubleshooting.md) — when things go wrong
- See the [CLI reference](../README.md#commands) for all commands
- Contribute: see [CONTRIBUTING.md](../CONTRIBUTING.md)
