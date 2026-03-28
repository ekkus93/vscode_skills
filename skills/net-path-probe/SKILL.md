---
name: net-path-probe
description: Measure internal path latency, jitter, and packet loss using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Path Probe

## Purpose

Use this skill to compare path quality between key internal targets so LAN, service, or site-wide degradation can be isolated.

## Status

Implemented first-pass Priority 2 skill. The bundled helper now runs deterministic internal and optional external path probes, classifies degraded targets, and recommends follow-up service or wireless checks.

## Inputs

- Primary selectors: `--site-id` or `--source-probe-id`
- Probe controls: `--source-role`, `--target`, `--external-target`, `--sample-count`, `--probe-timeout-seconds`
- Optional scope selectors: `--client-id`, `--client-mac`, `--ap-id`, `--ap-name`, `--ssid`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses `scope_type=site` unless a narrower source scope is provided
- Populates evidence such as per-target latency, jitter, loss, and degraded target classification
- Emits finding codes such as `SITE_WIDE_PATH_LOSS`, `INTERNAL_SERVICE_DEGRADATION`, and `WAN_EXTERNAL_DEGRADATION`
- Recommends service-specific or wireless follow-up depending on which targets degrade

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured probe adapter for live execution, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_path_probe.py" --site-id "hq-1" --source-role "wireless"
python3 "{baseDir}/net_path_probe.py" --site-id "hq-1" --target "dns-service" --target "radius-service" --external-target "internet-edge"
python3 "{baseDir}/net_path_probe.py" --site-id "hq-1" --target "dns-service" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.path_probe",
	"scope_type": "site",
	"scope_id": "hq-1",
	"summary": "Internal service reachability is degraded while the local gateway remains healthy.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"source_role": "wireless",
		"degraded_targets": ["dns-service"],
		"gateway_latency_ms": 5.0
	},
	"findings": [
		{
			"code": "INTERNAL_SERVICE_DEGRADATION",
			"severity": "warn",
			"message": "One or more internal service targets show degradation",
			"metric": "degraded_target_count",
			"value": 1,
			"threshold": 0
		}
	],
	"next_actions": [],
	"raw_refs": []
}
```

## Common Failure Cases

- No source scope or targets supplied for custom probing: the helper may fall back to defaults, but unsupported probe plans can still fail validation
- Probe adapter unavailable: returns a dependency-unavailable result
- No probe results returned for the requested window: returns insufficient evidence
- Upstream timeout from the probe system: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not guess latency, jitter, loss, or destination comparisons.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
