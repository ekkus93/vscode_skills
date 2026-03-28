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

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_segmentation_policy.py" --client-id "client-123"
python3 "{baseDir}/net_segmentation_policy.py" --client-mac "aa:bb:cc:dd:ee:ff" --ssid "CorpWiFi"
```

## Constraints

- Use the bundled helper.
- Do not guess VLAN mappings, NAC outcomes, or policy placement.
