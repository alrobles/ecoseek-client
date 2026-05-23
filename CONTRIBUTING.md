# Contributing to ecoseek-client

Welcome. ecoseek-client is the first-class local client for EcoSeek — the scientific agent environment for ecology.

## Development setup

```bash
# Clone
git clone https://github.com/alrobles/ecoseek-client.git
cd ecoseek-client

# Install editable with dev deps
pip install -e ".[dev]" --break-system-packages

# Verify
ecoseek --version
pytest -v
```

## Architecture

```
src/ecoseek_client/
├── __init__.py        # Version string
├── cli.py             # Click CLI (all commands)
├── config.py          # Environment variables, defaults
├── session.py         # AgenticPlugSession (v2 JSON format)
├── doctor.py          # Environment diagnostics
├── providers/
│   ├── __init__.py    # Re-exports: AgenticPlugClient, HermesProvider
│   ├── agenticplug.py # HTTP client for AgenticPlug broker
│   └── hermes.py      # Hermes scientific agent provider
├── aar/
│   ├── __init__.py    # AAR loop (observe→reason→act→evaluate→update)
│   └── scoring.py     # AAR autonomy scoring
├── skills/
│   └── definitions/   # Ecological skill pipelines (SDM, niche, etc.)
└── workflows/
    └── remote_smoke.py # Full-stack health check
```

## Code style

- Python 3.10+ with type hints
- Click for CLI, HTTPX for HTTP
- Tests use pytest
- Session tokens are NEVER printed (sanitize before output)

## Before submitting

```bash
# Run tests
pytest -v

# Check no import errors
python -c "from ecoseek_client.cli import main; print('OK')"

# Verify CLI
ecoseek --help
ecoseek doctor
```

## Commit style

- Short subject line (50 chars)
- Detailed body for complex changes
- Reference phases when relevant: "Phase 6: AgenticSeekProvider"
- No secrets in commits

## License

ecoseek-client is MIT licensed. All contributions are assumed to be MIT unless explicitly stated otherwise.

## Need help?

- See [troubleshooting](docs/troubleshooting.md) for common issues
- Open an issue on GitHub with the `bug` or `enhancement` label
