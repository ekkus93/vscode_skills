---
name: net-dns-latency
description: Measure internal DNS latency, timeout rate, and resolver quality using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net DNS Latency

## Purpose

Use this skill to determine whether DNS lookup latency or resolver timeouts are contributing to perceived network slowness.

## Status

Implemented first-pass Priority 1 skill. The helper now evaluates resolver latency and timeout behavior, compares current latency against the shared baseline utility, and recommends path probing when DNS looks suspect.

## Inputs

- Primary selectors: `--client-id`, `--client-mac`, `--site-id`, or `--ssid`
- Optional query override: `--query`
- Optional scope selectors: `--ap-id`, `--ap-name`, `--switch-id`, `--switch-port`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses the best available scope from the request and DNS telemetry returned by the adapter
- Populates evidence such as resolver latency, timeout percentage, and per-resolver results
- Emits finding codes such as `HIGH_DNS_LATENCY` and `DNS_TIMEOUT_RATE`
- Suggests `net.path_probe` when DNS symptoms may reflect a broader service-path issue

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured DNS adapter for live execution, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_dns_latency.py" --site-id "hq-1"
python3 "{baseDir}/net_dns_latency.py" --ssid "CorpWiFi" --client-id "client-123"
python3 "{baseDir}/net_dns_latency.py" --client-id "client-123" --query "internal.service.local" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.dns_latency",
	"scope_type": "client",
	"scope_id": "client-123",
	"summary": "DNS latency and timeout rate are elevated for the requested scope.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"overall_avg_latency_ms": 320.0,
		"overall_timeout_pct": 12.0,
		"resolver_count": 1
	},
	"findings": [
		{
			"code": "DNS_TIMEOUT_RATE",
			"severity": "critical",
			"message": "DNS timeout rate exceeded threshold",
			"metric": "overall_timeout_pct",
			"value": 12.0,
			"threshold": 5.0
		}
	],
	"next_actions": [
		{
			"skill": "net.path_probe",
			"reason": "Resolver symptoms should be compared against general path quality."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- Scope too broad to map to DNS telemetry: returns insufficient evidence instead of synthesizing resolver health
- DNS adapter unavailable: returns a dependency-unavailable result
- No resolver telemetry for the requested window: returns insufficient evidence
- Upstream timeout from the DNS provider: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not guess resolver telemetry or service-health findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
