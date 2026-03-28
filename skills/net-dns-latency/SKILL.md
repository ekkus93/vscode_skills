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

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_dns_latency.py" --site-id "hq-1"
python3 "{baseDir}/net_dns_latency.py" --ssid "CorpWiFi" --client-id "client-123"
```

## Constraints

- Use the bundled helper.
- Do not guess resolver telemetry or service-health findings.
