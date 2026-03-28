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

## Commands

```bash
python3 "{baseDir}/net_segmentation_policy.py" --client-id "client-123"
python3 "{baseDir}/net_segmentation_policy.py" --client-mac "aa:bb:cc:dd:ee:ff" --ssid "CorpWiFi"
python3 "{baseDir}/net_segmentation_policy.py" --client-id "client-123" --client-role "corp" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper.
- Do not guess VLAN mappings, NAC outcomes, or policy placement.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
