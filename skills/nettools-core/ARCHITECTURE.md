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

Topology-oriented extensions add four more runtime responsibilities inside `skills/nettools-core/nettools/`.

1. Evidence-merging layer
	- Merge LLDP, CDP, bridge-table, controller, ARP, gateway, and service-discovery records into shared topology models.
2. Graph-building layer
	- Deduplicate nodes and edges, preserve evidence references, and emit adjacency and graph views.
3. Confidence and ambiguity layer
	- Mark inferred versus directly observed edges, surface unresolved references, and degrade confidence when evidence conflicts.
4. Path reconstruction layer
	- Summarize likely client, AP, subnet, or service paths to the local gateway and recommend follow-up skills when the graph is incomplete.

This keeps vendor-specific collection inside adapters while topology reasoning stays in reusable analysis helpers and skill evaluators.
