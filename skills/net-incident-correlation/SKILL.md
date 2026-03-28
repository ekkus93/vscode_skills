---
name: net-incident-correlation
description: Correlate incident timing with network telemetry and infrastructure events using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Incident Correlation

## Purpose

Use this skill to rank likely correlated network events or service anomalies around an incident time window.

## Status

Implemented first-pass Priority 3 skill. The bundled helper now correlates the requested incident window against recent syslog-style events and config changes, ranks the strongest evidence, and recommends targeted follow-up skills.

## Inputs

- Primary selectors: `--site-id` and an incident window from `--time-window-minutes` or explicit times
- Optional incident context: `--incident-summary`, `--reporter`
- Optional scope selectors: `--client-id`, `--client-mac`, `--ap-id`, `--ap-name`, `--ssid`, `--switch-id`, `--switch-port`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses the strongest available site, AP, or client scope from the request
- Populates evidence with correlated event records, ranked anomalies, and recent change context
- Emits finding codes such as `CORRELATED_NETWORK_EVIDENCE` and `CORRELATED_CHANGE_WINDOW`
- Suggests follow-up skills that best match the strongest correlation cluster

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- Configured syslog or event data and recent change data, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_incident_correlation.py" --site-id "hq-1" --time-window-minutes 30
python3 "{baseDir}/net_incident_correlation.py" --site-id "hq-1" --incident-summary "Zoom calls started failing right after the switch work"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.incident_correlation",
	"scope_type": "site",
	"scope_id": "hq-1",
	"summary": "Incident timing correlates with recent network evidence and a change window.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:30:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"correlated_events": 3,
		"top_correlation_domain": "change_window"
	},
	"findings": [
		{
			"code": "CORRELATED_CHANGE_WINDOW",
			"severity": "warn",
			"message": "A recent change aligns with the incident timing"
		}
	],
	"next_actions": [
		{
			"skill": "net.change_detection",
			"reason": "Recent changes appear temporally aligned with the incident."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- No usable time window supplied: validation fails or the scope is too broad to correlate meaningfully
- Event or change providers unavailable: returns a dependency-unavailable result
- No events match the incident window: returns insufficient evidence instead of invented correlation
- Upstream timeout from event or change sources: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not guess causal correlation without collected evidence.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
