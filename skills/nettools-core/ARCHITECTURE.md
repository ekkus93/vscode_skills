# NETTOOLS Architecture

NETTOOLS is organized as a skill-first shared library inside this repository.

Primary layers:

1. OpenClaw skill wrappers under `skills/net-*/`
2. shared support code under `skills/nettools-core/nettools/`
3. unit and integration coverage under `tests/`

Design constraints for v1:

- read-only by default
- evidence-first outputs
- vendor-adaptable adapters
- normalized models before skill-specific analysis logic
- deterministic tests using fixtures and stub adapters

Phase 0 intentionally stops short of full diagnostic logic. It establishes:

- repository structure
- shared Python package bootstrap
- placeholder helper entrypoints
- repo-level lint, type-check, and test configuration
