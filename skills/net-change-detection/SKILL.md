---
name: net-change-detection
description: Detect likely relevant changes in network state or configuration using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Change Detection

## Purpose

Use this skill to identify recent changes in infrastructure state or configuration that align with a new complaint window.

## Status

Implemented first-pass Priority 3 skill. The bundled helper now ranks recent config and platform changes by time and scope relevance and highlights hardware, firmware, or switching changes that may explain the complaint.

## Inputs

- Primary selectors: `--site-id` plus a complaint window from `--time-window-minutes` or explicit times
- Optional correlation hints: `--device-id`, `--incident-summary`
- Optional scope selectors: `--client-id`, `--client-mac`, `--ap-id`, `--ap-name`, `--ssid`, `--switch-id`, `--switch-port`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses the strongest available site or device scope from the request
- Populates evidence with ranked recent changes, device context, and time-overlap relevance
- Emits finding codes such as `RECENT_RELEVANT_CHANGE`, `RECENT_HARDWARE_OR_FIRMWARE_CHANGE`, and `CORRELATED_CHANGE_WINDOW`
- Highlights which change should be reviewed or rolled back first

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- Configured inventory or syslog change sources, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_change_detection.py" --site-id "hq-1" --time-window-minutes 60
python3 "{baseDir}/net_change_detection.py" --site-id "hq-1" --incident-summary "Problems began after the switch refresh"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.change_detection",
	"scope_type": "site",
	"scope_id": "hq-1",
	"summary": "A recent infrastructure change appears relevant to the complaint window.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:00:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"ranked_changes": [
			{
				"change_id": "chg-2041",
				"category": "firmware",
				"score": 0.88
			}
		]
	},
	"findings": [
		{
			"code": "RECENT_HARDWARE_OR_FIRMWARE_CHANGE",
			"severity": "warn",
			"message": "A recent hardware or firmware event aligns with the incident window"
		}
	],
	"next_actions": [],
	"raw_refs": []
}
```

## Common Failure Cases

- No time-bounded complaint context: request validation can fail or the result can remain too weak to rank changes
- Change sources unavailable: returns a dependency-unavailable result
- No relevant changes in the requested window: returns insufficient evidence rather than overfitting a causal story
- Upstream timeout from inventory or event sources: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not invent config changes or temporal correlation.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
