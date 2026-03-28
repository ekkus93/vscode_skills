# NETTOOLS Core

This folder contains the shared support code and bootstrap documentation for the NETTOOLS skill suite.

Phase 0 scope in this folder:

- create the package skeleton under `nettools/`
- add a minimal CLI used by scaffolded skill helper scripts
- add stdlib JSON logging support
- document architecture, configuration, and testing expectations

Operator documentation in this folder now includes:

- `CONFIGURATION.md` for runtime and policy configuration guidance
- `TESTING.md` for validation guidance
- `PLAYBOOKS.md` for human-driven troubleshooting playbooks aligned with the current orchestrator and wrapper docs

Current status:

- the public NETTOOLS skill folders exist under `skills/`
- each skill has a `SKILL.md` wrapper and a Python entrypoint
- the entrypoints currently return scaffold output until the Phase 1 and Phase 5 implementations are completed

Quick local check:

```bash
python3 "{baseDir}/nettools/cli.py" --skill-name net.client_health --scope-type client --client-id demo-client
```
