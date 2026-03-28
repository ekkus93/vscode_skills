---
name: net-client-health
description: Assess one Wi-Fi client session for RF quality, retries, disconnects, and roam symptoms using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Client Health

## Purpose

Use this skill to assess whether one client session looks unhealthy because of weak RF conditions, elevated retries, disconnects, or roam-related symptoms.

## Status

Implemented first-pass Priority 1 skill. The bundled helper now evaluates client RF health, retries, reconnects, and sticky-client clues using the shared NETTOOLS models, adapters, and analysis utilities.

## Inputs

- Primary identifiers: `--client-id` or `--client-mac`
- Optional scope selectors: `--site-id`, `--ap-id`, `--ap-name`, `--ssid`, `--switch-id`, `--switch-port`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses `scope_type=client` when a client identifier is supplied
- Populates evidence such as current session metrics, connected AP, roam counts, and threshold comparisons
- Emits finding codes such as `LOW_RSSI`, `LOW_SNR`, `HIGH_RETRY_RATE`, `HIGH_PACKET_LOSS`, `EXCESSIVE_ROAMING`, `RAPID_RECONNECTS`, and `STICKY_CLIENT`
- Suggests follow-up skills when the symptom points toward AP RF, roaming, or uplink issues

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured wireless-controller adapter for live execution, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_client_health.py" --client-mac "aa:bb:cc:dd:ee:ff"
python3 "{baseDir}/net_client_health.py" --client-id "client-123" --time-window-minutes 30
python3 "{baseDir}/net_client_health.py" --client-id "client-123" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.client_health",
	"scope_type": "client",
	"scope_id": "client-123",
	"summary": "Client session shows elevated retries and weak RF symptoms.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"connected_ap": "AP-2F-EAST-03",
		"retry_pct": 28.0,
		"packet_loss_pct": 0.4,
		"recent_roams": 0
	},
	"findings": [
		{
			"code": "HIGH_RETRY_RATE",
			"severity": "warn",
			"message": "Client retry rate exceeded threshold",
			"metric": "retry_pct",
			"value": 28.0,
			"threshold": 15.0
		}
	],
	"next_actions": [
		{
			"skill": "net.ap_rf_health",
			"reason": "High retries suggest AP-side RF conditions need validation."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- Missing `--client-id` and `--client-mac`: input validation fails before collection starts
- Wireless adapter unavailable: returns a dependency-unavailable result instead of guessing client telemetry
- Client not found in the requested window: returns insufficient evidence or a scoped unknown result
- Upstream timeout from the wireless provider: returns a dependency-timeout result

## Constraints

- Use the bundled helper instead of improvising a fresh workflow.
- Do not guess controller telemetry, findings, or thresholds.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
