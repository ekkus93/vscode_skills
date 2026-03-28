---
name: net-dhcp-path
description: Assess DHCP success rates, latency, relay behavior, and address-allocation symptoms using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net DHCP Path

## Purpose

Use this skill to determine whether DHCP is slow, failing, or unstable for a client, SSID, VLAN, or site scope.

## Status

Implemented first-pass Priority 1 skill. The helper now evaluates DHCP latency, timeouts, missing ACKs, scope pressure, and relay mismatches using the shared NETTOOLS contracts and analysis utilities.

## Inputs

- Primary selectors: `--client-id`, `--client-mac`, `--ssid`, `--vlan-id`, or `--site-id`
- Optional scope selectors: `--ap-id`, `--ap-name`, `--switch-id`, `--switch-port`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses the strongest available scope among client, VLAN, SSID, or site identifiers
- Populates evidence such as offer latency, ACK latency, timeout counts, scope utilization, and relay-path metadata
- Emits finding codes such as `HIGH_DHCP_OFFER_LATENCY`, `HIGH_DHCP_ACK_LATENCY`, `DHCP_TIMEOUTS`, `MISSING_DHCP_ACK`, `SCOPE_UTILIZATION_HIGH`, and `RELAY_PATH_MISMATCH`
- Suggests follow-up when segmentation or broader path validation is warranted

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- A configured DHCP adapter for live execution, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_dhcp_path.py" --client-id "client-123"
python3 "{baseDir}/net_dhcp_path.py" --ssid "CorpWiFi" --vlan-id "110" --site-id "hq-1"
python3 "{baseDir}/net_dhcp_path.py" --client-id "client-123" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.dhcp_path",
	"scope_type": "client",
	"scope_id": "client-123",
	"summary": "DHCP offer latency is elevated for the requested client scope.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"avg_offer_latency_ms": 1800.0,
		"avg_ack_latency_ms": 200.0,
		"timeout_count": 0
	},
	"findings": [
		{
			"code": "HIGH_DHCP_OFFER_LATENCY",
			"severity": "warn",
			"message": "DHCP discover-to-offer latency exceeded threshold",
			"metric": "avg_offer_latency_ms",
			"value": 1800.0,
			"threshold": 1000.0
		}
	],
	"next_actions": [
		{
			"skill": "net.path_probe",
			"reason": "DHCP is slow enough that shared service reachability should be validated."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- No client, SSID, VLAN, or site context supplied: the request can validate but may remain too broad to locate DHCP telemetry
- DHCP adapter unavailable: returns a dependency-unavailable result
- No transactions found in the requested window: returns insufficient evidence
- Upstream timeout from the DHCP provider: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not guess DHCP transaction data or relay-path findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
