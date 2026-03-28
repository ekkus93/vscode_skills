---
name: net-segmentation-policy
description: Verify SSID, VLAN, DHCP-scope, and policy alignment for a client using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Segmentation Policy

## Purpose

Use this skill to verify whether a client has been placed into the correct VLAN and policy set for its expected network segment.

## Status

Implemented first-pass Priority 2 skill. The bundled helper now compares observed client placement from wireless and DHCP telemetry against expected VLAN and policy mappings from inventory data.

## Inputs

- Primary identifiers: `--client-id` or `--client-mac`
- Optional scope selectors: `--site-id`, `--ssid`, `--ap-id`, `--ap-name`, `--vlan-id`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Uses `scope_type=client` when a client identifier is supplied
- Populates evidence such as observed VLAN, DHCP scope, gateway or relay alignment, and expected policy mapping
- Emits finding codes such as `VLAN_MISMATCH`, `POLICY_GROUP_MISMATCH`, and `GATEWAY_ALIGNMENT_MISMATCH`
- Recommends auth or DHCP follow-up when policy placement looks incorrect

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- Configured wireless, DHCP, and inventory adapters for live execution, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_segmentation_policy.py" --client-id "client-123"
python3 "{baseDir}/net_segmentation_policy.py" --client-mac "aa:bb:cc:dd:ee:ff" --ssid "CorpWiFi"
python3 "{baseDir}/net_segmentation_policy.py" --client-id "client-123" --site-id "hq-1" --fixture-file "/path/to/fixtures.json"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.segmentation_policy",
	"scope_type": "client",
	"scope_id": "client-123",
	"summary": "Observed client placement does not match the expected segmentation policy.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"observed_vlan": 220,
		"expected_vlan": 120,
		"expected_policy_group": "corp"
	},
	"findings": [
		{
			"code": "VLAN_MISMATCH",
			"severity": "warn",
			"message": "Observed VLAN does not match the expected policy mapping",
			"metric": "observed_vlan",
			"value": 220,
			"threshold": 120
		}
	],
	"next_actions": [
		{
			"skill": "net.auth_8021x_radius",
			"reason": "Incorrect placement may be driven by role or policy assignment errors."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- Missing client context: the request may validate but remain too broad to compare observed and expected placement
- Inventory adapter unavailable: returns a dependency-unavailable result when expected mapping data cannot be loaded
- Only partial observed data is available: the skill may return `ok` or `unknown` with limited evidence instead of fabricating a mismatch
- Upstream timeout from wireless, DHCP, or inventory sources: returns a dependency-timeout result

## Constraints

- Use the bundled helper.
- Do not guess VLAN mappings, NAC outcomes, or policy placement.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
