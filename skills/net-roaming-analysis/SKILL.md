---
name: net-roaming-analysis
description: Analyze roaming behavior for a Wi-Fi client, including failed roams, latency, and sticky-client symptoms, using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Roaming Analysis

## Purpose

Use this skill to analyze client roaming patterns, roam failures, and sticky-client symptoms across a time window.

## Status

Implemented first-pass Priority 2 skill. The bundled helper now evaluates roam history, failed roam attempts, roam latency, and sticky-client patterns using the shared NETTOOLS contracts, adapters, and analysis helpers.

## Inputs

- Primary identifiers: `--client-id` or `--client-mac`
- Optional scope selectors: `--site-id`, `--ap-id`, `--ap-name`, `--ssid`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses `scope_type=client` when a client identifier is supplied
- Populates evidence such as roam counts, failed roam attempts, latency summaries, and AP transition details
- Emits finding codes such as `EXCESSIVE_ROAM_COUNT`, `HIGH_ROAM_LATENCY`, `FAILED_ROAMS`, and `STICKY_CLIENT_PATTERN`
- Suggests AP RF or client-health follow-up when roaming symptoms overlap with RF conditions

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured wireless-controller adapter for live execution, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_roaming_analysis.py" --client-id "client-123"
python3 "{baseDir}/net_roaming_analysis.py" --client-mac "aa:bb:cc:dd:ee:ff" --time-window-minutes 60
python3 "{baseDir}/net_roaming_analysis.py" --client-id "client-123" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "fail",
	"skill_name": "net.roaming_analysis",
	"scope_type": "client",
	"scope_id": "client-123",
	"summary": "Roam history shows failed transitions and excessive roam latency.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:00:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"roam_count": 1,
		"failed_roams": 1,
		"average_roam_latency_ms": 410.0
	},
	"findings": [
		{
			"code": "FAILED_ROAMS",
			"severity": "critical",
			"message": "One or more roam attempts failed",
			"metric": "failed_roams",
			"value": 1,
			"threshold": 0
		}
	],
	"next_actions": [
		{
			"skill": "net.ap_rf_health",
			"reason": "Roam failures should be compared with AP-side RF conditions."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- Missing client identifier: input validation fails or the request remains too broad to resolve roam history
- Wireless adapter unavailable: returns a dependency-unavailable result
- No roam telemetry in the requested window: returns insufficient evidence rather than fabricated mobility conclusions
- Upstream timeout from the wireless provider: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not invent roam history, AP transitions, or mobility findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
