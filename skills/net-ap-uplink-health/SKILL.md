---
name: net-ap-uplink-health
description: Validate the switch-port and uplink health behind an access point using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net AP Uplink Health

## Purpose

Use this skill to verify whether an AP’s wired uplink, switch port, or PoE state is causing apparent wireless problems.

## Status

Implemented first-pass Priority 1 skill. The helper now evaluates AP-to-switch resolution, negotiated speed, error counters, flap history, and expected uplink configuration mismatches.

## Commands

```bash
python3 "{baseDir}/net_ap_uplink_health.py" --ap-name "AP-2F-EAST-03"
python3 "{baseDir}/net_ap_uplink_health.py" --switch-id "sw-idf-3-01" --switch-port "Gi1/0/18"
python3 "{baseDir}/net_ap_uplink_health.py" --ap-id "ap-123" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper.
- Do not guess switch-port counters, PoE state, or VLAN mismatch findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
