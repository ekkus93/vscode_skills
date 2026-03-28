# NETTOOLS Fixtures

Use this directory for checked-in NETTOOLS sample payloads, normalized fixture inputs, and expected output artifacts used by deterministic tests.

`phase4_scenarios.json` is the shared canonical scenario corpus for the NETTOOLS tests. It now includes both normalized domain payloads and, where needed, small control sections for stub-adapter failure scenarios so later-phase tests can reuse the same checked-in cases.

`replay_scenarios.json` stores the canonical replay scenario specs used to build deterministic persisted-audit replay tests for `net.diagnose_incident` across single-client, area-based, site-wide, onboarding/auth, and ambiguous investigations.
