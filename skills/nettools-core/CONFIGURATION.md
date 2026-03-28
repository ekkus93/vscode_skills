# NETTOOLS Configuration

This guide describes how to configure the current NETTOOLS runtime and how to reason about the environment variables reserved for later provider-backed deployments.

## Runtime Profile

Current assumptions:

- Python target: 3.10
- Runtime environment: OpenClaw on Debian on a Dell Chromebook
- Logging stack: standard-library logging with JSON formatting
- Shared config model direction: Pydantic models in `skills/nettools-core/nettools/config/`
- Current execution mode: fixture-backed by default unless live adapters are explicitly implemented and wired in code

## Configuration Sources

NETTOOLS currently draws configuration from three places:

1. Command-line flags on each helper script under `skills/net-*/`
2. Environment variables in the repo root `.env.example`
3. Code defaults in the shared support package under `skills/nettools-core/nettools/`

Precedence for commonly used settings is:

1. Explicit CLI flags
2. Supported environment variables
3. Hardcoded defaults in the shared package

Example:

- `--fixture-file` overrides `NETTOOLS_FIXTURE_FILE`
- `NETTOOLS_LOG_LEVEL` overrides the logger default of `INFO`
- Threshold values come from the shared threshold model because there is no environment override layer for them yet

## Supported Environment Variables Today

These environment variables are read by the current codebase:

| Variable | Current Effect | Notes |
| --- | --- | --- |
| `NETTOOLS_LOG_LEVEL` | Sets the JSON logger level in `nettools.logging.json_formatter.configure_logging()` | Defaults to `INFO` if unset or invalid |
| `NETTOOLS_FIXTURE_FILE` | Provides the default fixture file for helper scripts that accept `--fixture-file` | Used by the shared adapter-loading path in Priority 1 and the orchestrator helper |

### Logging

NETTOOLS emits JSON log lines to stderr through the shared formatter.

Supported values for `NETTOOLS_LOG_LEVEL` should match Python logging levels such as:

- `DEBUG`
- `INFO`
- `WARNING`
- `ERROR`

If an invalid value is supplied, NETTOOLS falls back to `INFO`.

### Fixture Mode

Fixture-backed execution is the current default operating model for deterministic local runs and tests.

You can supply fixture data in either of these ways:

- Per invocation: `--fixture-file /path/to/fixtures.json`
- Session-wide default: `export NETTOOLS_FIXTURE_FILE=/path/to/fixtures.json`

If neither a live provider implementation nor a fixture file is available, the runtime returns a dependency-unavailable result instead of fabricating data.

## Reserved Environment Variables

The repo root `.env.example` also contains variables that are documented for operator planning but are not yet consumed by the current code.

| Variable | Intended Role | Current State |
| --- | --- | --- |
| `NETTOOLS_OUTPUT_FORMAT` | Select output rendering mode | Reserved only; current helpers already emit JSON |
| `NETTOOLS_DEFAULT_TIME_WINDOW_MINUTES` | Set the default investigation window | Reserved only; current helpers use parser and model defaults |
| `NETTOOLS_ALLOW_ACTIVE_PROBES` | Gate active path probing | Reserved as policy documentation; not enforced through env lookup yet |
| `NETTOOLS_ALLOW_CAPTURE_TRIGGER` | Gate capture-plan or future capture execution flows | Reserved as policy documentation; not enforced through env lookup yet |
| `NETTOOLS_SITE_ID` | Provide a default site scope | Reserved only |
| `NETTOOLS_WIRELESS_PROVIDER` | Select the wireless provider implementation | Reserved only |
| `NETTOOLS_SWITCH_PROVIDER` | Select the switch provider implementation | Reserved only |
| `NETTOOLS_DHCP_PROVIDER` | Select the DHCP provider implementation | Reserved only |
| `NETTOOLS_DNS_PROVIDER` | Select the DNS provider implementation | Reserved only |
| `NETTOOLS_AUTH_PROVIDER` | Select the auth provider implementation | Reserved only |
| `NETTOOLS_SYSLOG_PROVIDER` | Select the syslog or event provider implementation | Reserved only |

Operator implication:

- Treat these reserved variables as documentation of intended control points, not as evidence that runtime selection logic already exists.
- If you set them today, they serve as local conventions for future wiring and team documentation, but they do not change NETTOOLS behavior unless the code explicitly reads them.

## Provider Configuration

### Current State

Provider selection is not yet driven by environment variables or a central settings object.

Current behavior:

- Tests and local runs use stub adapters populated from checked-in or local fixture JSON
- Helper scripts load those fixtures through `--fixture-file` or `NETTOOLS_FIXTURE_FILE`
- If a skill requires live telemetry and no live adapter has been wired, it returns a dependency-unavailable result rather than silently falling back to empty data

### Expected Provider Domains

The skill suite is structured around these provider categories:

- Wireless controller
- Switch or wired infrastructure
- DHCP telemetry
- DNS telemetry or probing
- Auth or RADIUS telemetry
- Active probe nodes
- Inventory or configuration data
- Syslog or event data

These correspond to the adapter interfaces under `skills/nettools-core/nettools/adapters/`.

### Operator Guidance Until Live Wiring Exists

For now, configure NETTOOLS like this:

1. Keep a fixture file per scenario or site
2. Set `NETTOOLS_FIXTURE_FILE` in your shell if you want a reusable default
3. Override with `--fixture-file` when testing a different scenario
4. Treat any provider selection variable in `.env.example` as preparatory documentation only

## Thresholds

Thresholds are implemented in code today through the shared Pydantic models in `skills/nettools-core/nettools/config/thresholds.py`.

Current defaults:

### Wireless thresholds

- `low_rssi_dbm = -70`
- `low_snr_db = 20`
- `high_retry_pct = 15.0`
- `high_channel_utilization_pct = 75.0`

### Service thresholds

- `high_dhcp_latency_ms = 1500`
- `high_dns_latency_ms = 250`
- `auth_timeout_ms = 3000`

### Wired thresholds

- `high_crc_errors = 100`
- `topology_change_churn = 10`

### Threshold Override Model

There is currently no environment-based or file-based threshold override path. To change thresholds today, edit the shared threshold model in code and rerun validation.

Operator guidance:

- Treat threshold changes as code changes, not runtime toggles
- Re-run unit tests and contract tests after changing thresholds
- Record the operational reason for non-default thresholds in a change record or deployment note

## Secrets Handling

NETTOOLS does not currently ship a live credential-loading path for provider adapters, but the logging layer is already written to avoid leaking common secret fields.

The shared logger redacts values whose keys match names such as:

- `api_key`
- `authorization`
- `certificate`
- `cert_pem`
- `key`
- `password`
- `secret`
- `token`

Operator guidance for future live-provider deployments:

1. Do not hardcode credentials into fixture files committed to the repo
2. Do not place real provider secrets into `SKILL.md` examples or test fixtures
3. Prefer environment injection or external secret stores once live adapters are introduced
4. Assume any field not matching the built-in redaction list may still need manual review before logs are shared externally

## Active-Probe Restrictions

NETTOOLS is read-only by default.

Current state of active behavior:

- `net.path_probe` performs probe-style analysis through its adapter interface, but environment gating for probes is not yet wired through `NETTOOLS_ALLOW_ACTIVE_PROBES`
- `net.capture_trigger` produces a capture plan only and does not execute packet capture
- The wrapper docs already describe authorization and scope narrowing requirements for capture planning

Operator policy guidance:

1. Treat active probing as opt-in and site-policy controlled even if the current env flag is not enforced yet
2. Use narrow scopes for path probes and avoid ad hoc target sprawl
3. Treat `net.capture_trigger` as planning-only until an explicitly authorized execution path exists
4. Require a change or approval ticket before acting on any capture plan in a live environment

## Recommended Local Setup

For current local operation, a practical shell setup looks like this:

```bash
export NETTOOLS_LOG_LEVEL=INFO
export NETTOOLS_FIXTURE_FILE="$PWD/tests/fixtures/nettools/example.json"
```

Then invoke helpers directly, for example:

```bash
python3 skills/net-client-health/net_client_health.py --client-id client-123
python3 skills/net-diagnose-incident/net_diagnose_incident.py --site-id hq-1 --complaint "Users say Wi-Fi is slow"
```

## Validation After Configuration Changes

If you change configuration-related code or operational defaults, run:

```bash
ruff check .
mypy --python-executable /home/phil/work/vscode_skills/.venv/bin/python .
/home/phil/work/vscode_skills/.venv/bin/python -m pytest
```

For documentation-only changes, validate at least the affected documentation contract tests if the edit touches a tested doc surface.
