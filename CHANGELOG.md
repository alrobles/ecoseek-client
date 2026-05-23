# Changelog

All notable changes to ecoseek-client will be documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] — Unreleased

### Added

- **Phase 1**: Package skeleton — pyproject.toml, CLI entrypoint (`ecoseek`), `doctor` command, tests with pytest
- **Phase 2**: AgenticPlug session and provider — `session.py`, `providers/agenticplug.py`, CLI commands (`agenticplug whoami`, `clusters`, `health`, `task list`, `task run`)
- **Phase 3**: Remote smoke workflow — `ecoseek smoke remote` with failure classification (auth, broker, connector, HPC, capability)
- **Phase 4**: Provider architecture — `HermesProvider` connecting to `hermes.ecoseek.org`, abstract provider interface
- **Phase 5**: Hermes as provider via AgenticPlug — orchestration, chat, scientific task dispatch, ecological skills
- **Phase 6**: AgenticSeek integration — `AgenticSeekProvider`, integration guide, hybrid AAR mode
- **Phase 7**: Product packaging — README, install guides, CI/CD, PyPI publish workflow, CHANGELOG, CONTRIBUTING

### CLI Commands

- `ecoseek doctor` — Full environment diagnostics
- `ecoseek agenticplug {whoami,health,status,clusters,task}` — AgenticPlug broker commands
- `ecoseek hermes {whoami,orchestrate,chat}` — Hermes scientific agent
- `ecoseek smoke remote` — Full-stack diagnostic smoke test
- `ecoseek aar {run,status}` — AAR (observe→reason→act→evaluate→update) loop
- `ecoseek skill {list,show}` — Scientific ecological skills

### Infrastructure

- MIT License
- GitHub Actions CI (tests on push/PR, PyPI publish on release)
- Python 3.10, 3.11, 3.12 support
- WSL2 / Ubuntu compatible
