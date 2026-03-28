---
name: net-ap-rf-health
description: Evaluate AP radio conditions, utilization, resets, and client load using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net AP RF Health

## Purpose

Use this skill to inspect AP-level wireless health, including channel utilization, radio load, and RF instability indicators.

## Status

Implemented first-pass Priority 1 skill. The helper now evaluates AP utilization, client load, reset indicators, and likely RF overlap using the shared NETTOOLS analysis utilities.

## Inputs

- Primary identifiers: `--ap-id` or `--ap-name`
- Optional scope selectors: `--site-id`, `--ssid`, `--client-id`, `--client-mac`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses `scope_type=ap` when an AP identifier is supplied
- Populates evidence such as radio utilization, client load, channel width, reset indicators, and neighboring AP context
- Emits finding codes such as `HIGH_CHANNEL_UTILIZATION`, `HIGH_AP_CLIENT_LOAD`, `UNSUITABLE_CHANNEL_WIDTH`, `RADIO_RESETS`, and `POTENTIAL_CO_CHANNEL_INTERFERENCE`
- Suggests RF or client-side follow-up when the AP looks degraded

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured wireless-controller adapter for live execution, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_ap_rf_health.py" --ap-name "AP-2F-EAST-03"
python3 "{baseDir}/net_ap_rf_health.py" --ap-id "ap-123" --site-id "hq-1"
python3 "{baseDir}/net_ap_rf_health.py" --ap-id "ap-123" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.ap_rf_health",
	"scope_type": "ap",
	"scope_id": "ap-123",
	"summary": "AP radio utilization and client load are above threshold.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"ap_name": "AP-2F-EAST-03",
		"channel_utilization_pct": 88.0,
		"client_count": 37,
		"neighboring_ap_count": 2
	},
	"findings": [
		{
			"code": "HIGH_CHANNEL_UTILIZATION",
			"severity": "warn",
			"message": "AP radio channel utilization exceeded threshold",
			"metric": "utilization_pct",
			"value": 88.0,
			"threshold": 75.0
		}
	],
	"next_actions": [],
	"raw_refs": []
}
```

## Common Failure Cases

- Missing AP identifier for an AP-focused investigation: the request may validate but return insufficient evidence if no AP can be resolved
- Wireless adapter unavailable: returns a dependency-unavailable result
- AP state absent in the requested window: returns insufficient evidence rather than inferred RF state
- Upstream timeout from the wireless provider: returns a dependency-timeout result

## Constraints

- Use the bundled helper instead of ad hoc controller queries.
- Do not guess AP telemetry or channel-plan findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
