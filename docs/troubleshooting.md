# Troubleshooting Guide

Common issues and their fixes when setting up or using ecoseek-client.

## Installation issues

### "externally managed environment" (PEP 668)

```
error: externally-managed-environment
```

Ubuntu 24.04+ restricts system pip. Solutions:

**Option A**: Add `--break-system-packages`
```bash
pip install -e . --break-system-packages
```

**Option B**: Use a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### "No module named 'ecoseek_client'"

You installed the package but can't import it. Make sure you installed from the repo root:

```bash
cd ecoseek-client          # Must be in the repo root
pip install -e . --break-system-packages
ecoseek --version          # Should show 0.1.0
```

### Python version too old

```
ecoseek requires Python >= 3.10
```

```bash
python3 --version
# → Must be 3.10 or newer

# On Ubuntu 22.04, install newer Python:
sudo apt install python3.12 python3.12-venv
```

## AgenticPlug connection issues

### "No session token found"

```
ecoseek agenticplug whoami
→ No session token found.
```

You need either:
- A session file at `~/.config/agenticplug/session.json`
- Or `AGENTICPLUG_SESSION` env var with raw token

See [Connect to AgenticPlug guide](connect-agenticplug.md).

### "Connector: down"

```
ecoseek agenticplug health
→ Connector: down — Connection refused
```

The AgenticPlug connector isn't running. Check:

```bash
# Is the service running?
systemctl status agenticplug-connector

# Try a direct curl
curl http://localhost:3100/health

# Start it
sudo systemctl start agenticplug-connector
```

### "HTTP 401 Unauthorized"

Your session token has expired. Tokens typically last hours/days. Get a fresh one:

```bash
agenticplug login
# or update your AGENTICPLUG_SESSION env var
```

### Wrong URL or port

AgenticPlug runs on port 3100 by default. If yours is different:

```bash
export AGENTICPLUG_URL=http://localhost:3100   # or your custom port
ecoseek agenticplug health
```

## Hermes connection issues

### "Hermes unreachable"

```
ecoseek hermes whoami
→ status: unreachable
```

Hermes lives behind a Cloudflare tunnel. Check:

```bash
# Can you reach the tunnel?
curl https://hermes.ecoseek.org/health
# → {"status":"ok"}

# Is your DNS resolving?
nslookup hermes.ecoseek.org
```

If `hermes.ecoseek.org` doesn't resolve, the Cloudflare tunnel may be down. Check reumanlab server:

```bash
ssh reumanlab "systemctl status cloudflared"
```

### "Timeout" on orchestration

```
ecoseek hermes orchestrate "SDM..."
→ Timeout after 600s
```

SDMs can take minutes. Increase timeout:

```bash
export HERMES_TIMEOUT=1200
ecoseek hermes orchestrate "complex SDM"
```

## HPC issues

### "Auth required for HPC task"

```
ecoseek agenticplug task run hpc.status
→ Auth required for this task
```

HPC tasks need a valid AgenticPlug session with cluster access. Make sure you have a fresh session:

```bash
ecoseek agenticplug whoami
# Verify you see your identity
ecoseek agenticplug task run hpc.status
```

### "HPC host unreachable"

The connector can't reach the HPC cluster. Check:

```bash
# From reumanlab (the connector's host):
ssh $HPC_USER@$HPC_HOST "sinfo"
```

### HPC returns empty job list

This is normal if you have no active jobs. Try submitting a test:

```bash
# Not yet supported in v0.1 — coming in future phase
ecoseek agenticplug task run hpc.queue
```

## Package issues

### "No such file: /etc/agenticplug/session.json"

This is the AgenticPlug v1 path. v2 uses `~/.config/agenticplug/session.json`. Update your env:

```bash
export AGENTICPLUG_SESSION_FILE=~/.config/agenticplug/session.json
```

### Commands return empty JSON with no error

The response was sanitized (token removal is aggressive). This is normal security behavior. Check raw output:

```bash
ecoseek agenticplug whoami 2>&1
```

## Getting help

Still stuck? Open an issue on GitHub with:

1. `ecoseek doctor` output
2. The exact command you ran
3. The full error message
4. Your OS and Python version: `python3 --version && cat /etc/os-release | head -2`

Or tag `@alrobles` in the ecoSeek repo.
