# WSL / Ubuntu Install Guide

This guide covers installing ecoseek-client on WSL2 (Windows Subsystem for Linux) or native Ubuntu.

## Prerequisites

- WSL2 with Ubuntu 22.04+ (or native Ubuntu 22.04+)
- Python 3.10 or newer
- Git

### Check your setup

```bash
python3 --version   # Should be 3.10+
git --version        # Any recent version
```

## Install ecoseek-client

### Option 1: From source (recommended for development)

```bash
# Clone the repo
git clone https://github.com/alrobles/ecoseek-client.git
cd ecoseek-client

# Install in editable mode
# Ubuntu 24.04+ requires --break-system-packages due to PEP 668
pip install -e . --break-system-packages

# Verify
ecoseek --version   # → 0.1.0
ecoseek doctor      # → diagnostic output
```

### Option 2: From PyPI (when published)

```bash
pip install ecoseek-client --break-system-packages
```

### Option 3: With a virtual environment (no pip restrictions)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ecoseek-client
```

## First verification

```bash
ecoseek doctor
```

Expected output:
```
ecoseek doctor
  Python 3.12.x
  OS: Linux (WSL2)
  git: /usr/bin/git
  AgenticPlug: http://localhost:3100 (configured)
  HPC: not configured (ok for now)
Done.
```

## Connect to AgenticPlug

If you have an AgenticPlug session file, link it:

```bash
export AGENTICPLUG_SESSION_FILE=~/.config/agenticplug/session.json
ecoseek agenticplug whoami
```

No session yet? See [Connect to AgenticPlug](connect-agenticplug.md).

## Optional: HPC access

If you have KU-HPC credentials:

```bash
export HPC_HOST=your-cluster-hostname
export HPC_USER=your_username
ecoseek agenticplug task run hpc.status
```

## Next steps

- Run your first task: [First hello world from cluster](first-task.md)
- Troubleshooting: [Troubleshooting guide](troubleshooting.md)
