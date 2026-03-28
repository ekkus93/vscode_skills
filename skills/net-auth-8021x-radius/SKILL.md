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

## Commands

```bash
python3 "{baseDir}/net_auth_8021x_radius.py" --client-id "client-123"
python3 "{baseDir}/net_auth_8021x_radius.py" --ssid "CorpWiFi" --site-id "hq-1"
python3 "{baseDir}/net_auth_8021x_radius.py" --client-id "client-123" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper.
- Do not guess RADIUS reachability, EAP failures, or auth-success metrics.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
