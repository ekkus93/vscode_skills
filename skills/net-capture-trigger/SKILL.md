---
name: net-capture-trigger
description: Prepare a gated packet-capture request or capture plan using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Capture Trigger

## Purpose

Use this skill to prepare a narrow packet-capture plan when telemetry suggests a specific protocol failure and authorization allows it.

## Status

Implemented first-pass Priority 3 skill. The bundled helper now produces a gated manual capture plan, derives a narrow capture filter from the stated reason, and refuses to imply execution without authorization and an approval ticket.

## Inputs

- Required: `--reason`
- Optional capture controls: `--protocol`, `--target-host`, `--interface-scope`, `--capture-duration-seconds`, `--packet-count-limit`
- Authorization controls: `--authorized`, `--approval-ticket`
- Optional scope selectors: `--site-id`, `--client-id`, `--client-mac`, `--ap-id`, `--ap-name`, `--ssid`, `--switch-id`, `--switch-port`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Returns a manual capture plan, not an executed capture
- Populates evidence with scope, derived filter hints, authorization state, and capture bounds
- Emits finding codes such as `CAPTURE_AUTHORIZATION_REQUIRED` and `CAPTURE_SCOPE_TOO_BROAD`
- Keeps `next_actions` focused on narrowing the scope or securing authorization

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- No packet-capture runtime dependency is required because this helper only plans a capture; fixture mode is optional for test flows

## Commands

```bash
python3 "{baseDir}/net_capture_trigger.py" --site-id "hq-1" --reason "Need to inspect DHCP failures during onboarding"
python3 "{baseDir}/net_capture_trigger.py" --client-id "client-123" --reason "Capture DNS failures" --authorized --approval-ticket "CHG-1234"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.capture_trigger",
	"scope_type": "site",
	"scope_id": "hq-1",
	"summary": "Capture plan is ready but authorization is still required.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"reason": "Need to inspect DHCP failures during onboarding",
		"capture_filter": "udp port 67 or udp port 68",
		"authorized": false
	},
	"findings": [
		{
			"code": "CAPTURE_AUTHORIZATION_REQUIRED",
			"severity": "warn",
			"message": "Packet-capture execution requires an approval ticket"
		}
	],
	"next_actions": [],
	"raw_refs": []
}
```

## Common Failure Cases

- Missing `--reason`: input validation fails before a plan is built
- Requested scope is too broad: the helper emits `CAPTURE_SCOPE_TOO_BROAD` and refuses to imply safe execution
- Authorization omitted for a plan that would otherwise be valid: the helper emits `CAPTURE_AUTHORIZATION_REQUIRED`
- Unsupported or ambiguous protocol hint: the helper falls back to a conservative manual plan instead of an unsafe filter guess

## Constraints

- Use the bundled helper.
- Do not start packet captures or claim authorization until the gated implementation exists.
- Return the capture plan only; do not imply that a capture was executed.
