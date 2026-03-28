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

## Commands

```bash
python3 "{baseDir}/net_dns_latency.py" --site-id "hq-1"
python3 "{baseDir}/net_dns_latency.py" --ssid "CorpWiFi" --client-id "client-123"
python3 "{baseDir}/net_dns_latency.py" --client-id "client-123" --query "internal.service.local" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper.
- Do not guess resolver telemetry or service-health findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
