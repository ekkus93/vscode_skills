---
name: net-incident-intake
description: Collect user complaint details into a structured NETTOOLS incident record using the bundled helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Incident Intake

## Purpose

Use this skill to normalize a freeform user complaint into a structured incident record that can drive follow-up NETTOOLS skills.

## Status

Implemented first-pass Priority 3 skill. The bundled helper now normalizes a freeform complaint into a structured incident record, infers useful fields from the complaint text, and recommends likely follow-up NETTOOLS skills.

## Inputs

- Required: `--complaint`
- Optional incident context: `--reporter`, `--incident-id`, `--location`, `--device-type`, `--movement-state`, `--occurred-at`
- Optional impact hints: `--wired-also-affected`, `--reconnect-helps`, `--impacted-app`, `--note`
- Optional scope selectors: `--site-id`, `--client-id`, `--client-mac`, `--ap-id`, `--ap-name`, `--ssid`, `--switch-id`, `--switch-port`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses a structured incident scope derived from the supplied identifiers and complaint text
- Populates evidence with a normalized incident record, extracted scope hints, and recommended next-step skills
- Emits `INTAKE_INCOMPLETE_SCOPE` when the complaint still lacks enough detail for targeted follow-up
- Suggests downstream skills such as `net.client_health`, `net.roaming_analysis`, or `net.dhcp_path` when the complaint implies a likely branch

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- No live provider is required for normalization; fixture mode is optional when testing bundled flows

## Commands

```bash
python3 "{baseDir}/net_incident_intake.py" --site-id "hq-1" --complaint "Users in conference room B say Wi-Fi drops while walking between APs"
python3 "{baseDir}/net_incident_intake.py" --client-id "client-123" --complaint "Laptop cannot connect to SSID CorpWiFi and reconnect helps"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.incident_intake",
	"scope_type": "site",
	"scope_id": "hq-1",
	"summary": "Complaint was normalized into an incident record with wireless mobility symptoms.",
	"confidence": "medium",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"incident_record": {
			"site_id": "hq-1",
			"movement_state": "moving",
			"wired_also_affected": false
		}
	},
	"findings": [
		{
			"code": "INTAKE_INCOMPLETE_SCOPE",
			"severity": "warn",
			"message": "Incident intake still lacks some targeting detail"
		}
	],
	"next_actions": [
		{
			"skill": "net.roaming_analysis",
			"reason": "Complaint mentions drops while moving between APs."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- Missing `--complaint`: input validation fails before normalization begins
- Complaint text lacks enough scope details: the skill returns a partial incident record and may emit `INTAKE_INCOMPLETE_SCOPE`
- Invalid timestamps or conflicting time inputs: request validation fails
- Freeform text is too vague to route confidently: the skill avoids over-committing and returns conservative next actions

## Constraints

- Use the bundled helper.
- Do not fabricate details that were not provided by the user or a follow-up prompt.
- Return the helper's structured `SkillResult` output directly rather than paraphrasing away the normalized incident record.
