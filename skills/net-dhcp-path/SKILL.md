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

## Commands

```bash
python3 "{baseDir}/net_dhcp_path.py" --client-id "client-123"
python3 "{baseDir}/net_dhcp_path.py" --ssid "CorpWiFi" --vlan-id "110" --site-id "hq-1"
python3 "{baseDir}/net_dhcp_path.py" --client-id "client-123" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper.
- Do not guess DHCP transaction data or relay-path findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
