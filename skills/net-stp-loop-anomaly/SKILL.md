---
name: net-stp-loop-anomaly
description: Detect switching-loop, STP, and MAC-flap symptoms using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net STP Loop Anomaly

## Purpose

Use this skill to detect L2 instability such as topology churn, root changes, or MAC flapping that can cause widespread slowness.

## Status

Implemented first-pass Priority 1 skill. The helper now evaluates topology churn, root changes, MAC flaps, and loop-like switching symptoms using the shared NETTOOLS analysis utilities.

## Inputs

- Primary selectors: `--site-id` or `--switch-id`
- Optional scope selectors: `--switch-port`, `--vlan-id`, `--ap-id`, `--ap-name`, `--ssid`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses `scope_type=site` or `scope_type=switch_port` depending on the request
- Populates evidence such as topology-change counts, root-bridge changes, MAC-flap counts, and suspect ports
- Emits finding codes such as `TOPOLOGY_CHURN`, `ROOT_BRIDGE_CHANGES`, `MAC_FLAP_LOOP_SIGNATURE`, and `STORM_INDICATORS`
- Surfaces L2 instability clearly enough to drive operator containment or targeted switch follow-up

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured switch adapter and optional syslog event source, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_stp_loop_anomaly.py" --site-id "hq-1"
python3 "{baseDir}/net_stp_loop_anomaly.py" --switch-id "sw-core-1" --time-window-minutes 60
python3 "{baseDir}/net_stp_loop_anomaly.py" --site-id "hq-1" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "fail",
	"skill_name": "net.stp_loop_anomaly",
	"scope_type": "site",
	"scope_id": "hq-1",
	"summary": "Topology churn and MAC flaps suggest L2 instability.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:00:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"topology_changes": 22,
		"root_bridge_changes": 2,
		"mac_flap_events": 6,
		"suspect_ports": ["Gi1/0/11", "Gi1/0/23"]
	},
	"findings": [
		{
			"code": "MAC_FLAP_LOOP_SIGNATURE",
			"severity": "critical",
			"message": "MAC flap pattern strongly suggests a loop signature",
			"metric": "mac_flap_events",
			"value": 6,
			"threshold": 1
		}
	],
	"next_actions": [],
	"raw_refs": []
}
```

## Common Failure Cases

- No site or switch scope provided for broad L2 symptoms: the request may validate but remain too ambiguous to correlate topology data
- Switch adapter unavailable: returns a dependency-unavailable result
- No topology or flap telemetry in the requested window: returns insufficient evidence
- Upstream timeout from switch or event sources: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not guess topology-change counters, flap events, or suspect ports.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
