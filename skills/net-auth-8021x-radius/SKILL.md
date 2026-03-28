---
name: net-auth-8021x-radius
description: Assess 802.1X and RADIUS authentication delays or failures using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Auth 802.1X Radius

## Purpose

Use this skill to evaluate whether authentication latency, timeouts, or repeated failures are affecting Wi-Fi access.

## Status

Implemented first-pass Priority 2 skill. The bundled helper now evaluates 802.1X success rate, RADIUS reachability, timeout patterns, credential failures, and certificate-related auth symptoms.

## Inputs

- Primary selectors: `--client-id`, `--client-mac`, `--ssid`, or `--site-id`
- Optional scope selectors: `--ap-id`, `--ap-name`, `--switch-id`, `--switch-port`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses the best available scope from the request and authentication telemetry returned by the adapter
- Populates evidence such as auth success rate, timeout counts, categorized failure reasons, and RADIUS RTT or reachability
- Emits finding codes such as `LOW_AUTH_SUCCESS_RATE`, `AUTH_TIMEOUTS`, `RADIUS_UNREACHABLE`, `RADIUS_HIGH_RTT`, `AUTH_CREDENTIAL_FAILURES`, and `AUTH_CERTIFICATE_FAILURES`
- Suggests path or policy follow-up when auth symptoms point beyond end-user credentials

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured auth adapter for live execution, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_auth_8021x_radius.py" --client-id "client-123"
python3 "{baseDir}/net_auth_8021x_radius.py" --ssid "CorpWiFi" --site-id "hq-1"
python3 "{baseDir}/net_auth_8021x_radius.py" --client-id "client-123" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "fail",
	"skill_name": "net.auth_8021x_radius",
	"scope_type": "client",
	"scope_id": "client-123",
	"summary": "Authentication timeouts and high RADIUS latency are impacting access.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"auth_success_rate_pct": 73.0,
		"timeout_count": 8,
		"radius_avg_rtt_ms": 3400.0
	},
	"findings": [
		{
			"code": "AUTH_TIMEOUTS",
			"severity": "critical",
			"message": "Authentication attempts are timing out",
			"metric": "timeouts",
			"value": 8,
			"threshold": 0
		}
	],
	"next_actions": [
		{
			"skill": "net.path_probe",
			"reason": "RADIUS latency should be compared to broader service-path quality."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- Scope too broad to map to recent auth telemetry: returns insufficient evidence
- Auth adapter unavailable: returns a dependency-unavailable result
- No recent auth events or reachability data: returns insufficient evidence
- Upstream timeout from the auth provider: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not guess RADIUS reachability, EAP failures, or auth-success metrics.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
