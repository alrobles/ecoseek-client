# Connect to AgenticPlug

AgenticPlug is the secure broker that connects ecoseek-client to remote resources: the reumanlab server, KU-HPC, and any other agent connectors.

This guide covers getting your first session and verifying the connection.

## What you need

1. An AgenticPlug connector running (local or remote)
2. A session token (from `agenticplug login`)
3. ecoseek-client installed (see [WSL install guide](install-wsl.md))

## Step 1: Verify the connector is running

```bash
ecoseek agenticplug health
```

Expected:
```
Connector: healthy
```

If you see "Connector: down", make sure the agenticplug connector is running:
```bash
systemctl status agenticplug-connector   # if running as systemd
# or
curl http://localhost:3100/health
```

## Step 2: Get a session token

### If you already have the agenticplug CLI:

```bash
agenticplug login
```
This produces `~/.config/agenticplug/session.json`.

### If you have a raw session token:

Set it as an environment variable:
```bash
export AGENTICPLUG_SESSION="your-session-token-here"
```

### If someone shared a session file with you:

```bash
cp /path/to/shared/session.json ~/.config/agenticplug/session.json
chmod 600 ~/.config/agenticplug/session.json  # protect your token
```

## Step 3: Configure ecoseek-client

### Option A: Environment variables (recommended)

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export AGENTICPLUG_URL=http://localhost:3100
export AGENTICPLUG_SESSION_FILE=~/.config/agenticplug/session.json
```

Reload your shell:
```bash
source ~/.bashrc
```

### Option B: .env file

```bash
cd ~/ecoseek-client
cp .env.example .env
# Edit .env with your values
```

## Step 4: Verify your connection

```bash
ecoseek agenticplug whoami
```

Expected output:
```
Connected as: your-github-username

{
  "user": "your-github-username",
  "connector_id": "reumanlab-agentic",
  ...
}
```

## Step 5: List available clusters

```bash
ecoseek agenticplug clusters
```

Expected:
```
Clusters (2):
  ✓ reumanlab (local)
  ✓ ku-hpc (hpc) [rw]
```

## Troubleshooting

### "No session token found"

Check your env vars:
```bash
echo $AGENTICPLUG_SESSION_FILE
ls -la ~/.config/agenticplug/session.json
```

### "Session is expired"

Tokens expire after a set period. Run `agenticplug login` again.

### "Connector: down"

The agenticplug-connector service is not running:
```bash
# Check logs
journalctl -u agenticplug-connector -n 50

# Restart
sudo systemctl restart agenticplug-connector
```

### "HTTP 401 / Unauthorized"

Your session token is invalid. Get a fresh one:
```bash
agenticplug login
```

## Security notes

- Never commit `.env` or `session.json` to git
- Session tokens are bearer tokens — treat them like passwords
- ecoseek-client NEVER prints tokens in output (sanitized by default)
- Use file permissions: `chmod 600` on session files
