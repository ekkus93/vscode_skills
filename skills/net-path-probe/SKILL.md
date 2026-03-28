---
name: net-path-probe
description: Measure internal path latency, jitter, and packet loss using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Path Probe

## Purpose

Use this skill to compare path quality between key internal targets so LAN, service, or site-wide degradation can be isolated.

## Status

Implemented first-pass Priority 2 skill. The bundled helper now runs deterministic internal and optional external path probes, classifies degraded targets, and recommends follow-up service or wireless checks.

## Commands

```bash
python3 "{baseDir}/net_path_probe.py" --site-id "hq-1" --source-role "wireless"
python3 "{baseDir}/net_path_probe.py" --site-id "hq-1" --target "dns-service" --target "radius-service" --external-target "internet-edge"
python3 "{baseDir}/net_path_probe.py" --site-id "hq-1" --target "dns-service" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper.
- Do not guess latency, jitter, loss, or destination comparisons.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
