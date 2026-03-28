---
name: net-ap-uplink-health
description: Validate the switch-port and uplink health behind an access point using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net AP Uplink Health

## Purpose

Use this skill to verify whether an AP’s wired uplink, switch port, or PoE state is causing apparent wireless problems.

## Status

Implemented first-pass Priority 1 skill. The helper now evaluates AP-to-switch resolution, negotiated speed, error counters, flap history, and expected uplink configuration mismatches.

## Inputs

- Primary identifiers: `--ap-id`, `--ap-name`, or an explicit `--switch-id` plus `--switch-port`
- Optional scope selectors: `--site-id`, `--ssid`, `--client-id`, `--client-mac`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses `scope_type=ap` or `scope_type=switch_port` depending on the supplied identifiers
- Populates evidence such as resolved switch port, negotiated speed, port counters, flap history, PoE state, and expected uplink configuration
- Emits finding codes such as `UPLINK_SPEED_MISMATCH`, `UPLINK_ERROR_RATE`, `UPLINK_FLAPPING`, `UPLINK_VLAN_MISMATCH`, and `POE_INSTABILITY`
- Recommends RF follow-up only when the wired side looks clean but symptoms persist

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured switch adapter and, for expectation checks, inventory data; or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_ap_uplink_health.py" --ap-name "AP-2F-EAST-03"
python3 "{baseDir}/net_ap_uplink_health.py" --switch-id "sw-idf-3-01" --switch-port "Gi1/0/18"
python3 "{baseDir}/net_ap_uplink_health.py" --ap-id "ap-123" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.ap_uplink_health",
	"scope_type": "ap",
	"scope_id": "ap-123",
	"summary": "AP uplink negotiated below the expected speed.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"switch_id": "sw-idf-3-01",
		"switch_port": "Gi1/0/18",
		"speed_mbps": 100,
		"expected_speed_mbps": 1000
	},
	"findings": [
		{
			"code": "UPLINK_SPEED_MISMATCH",
			"severity": "warn",
			"message": "AP uplink negotiated below expected speed",
			"metric": "speed_mbps",
			"value": 100,
			"threshold": 1000
		}
	],
	"next_actions": [],
	"raw_refs": []
}
```

## Common Failure Cases

- No AP-to-port mapping and no explicit switch port supplied: returns insufficient evidence
- Switch adapter unavailable: returns a dependency-unavailable result
- Inventory expectations unavailable: the skill still runs, but VLAN or speed mismatch checks may be limited
- Upstream timeout from the switch provider: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not guess switch-port counters, PoE state, or VLAN mismatch findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
