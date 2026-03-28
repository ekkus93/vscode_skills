# NETTOOLS Core

This folder contains the shared support code and bootstrap documentation for the NETTOOLS skill suite.

Phase 0 scope in this folder:

- create the package skeleton under `nettools/`
- add a minimal CLI used by scaffolded skill helper scripts
- add stdlib JSON logging support
- document architecture, configuration, and testing expectations

Current status:

- the public NETTOOLS skill folders exist under `skills/`
- each skill has a `SKILL.md` wrapper and a Python entrypoint
- the entrypoints currently return scaffold output until the Phase 1 and Phase 5 implementations are completed

Quick local check:

```bash
python3 "{baseDir}/nettools/cli.py" --skill-name net.client_health --scope-type client --client-id demo-client
```
