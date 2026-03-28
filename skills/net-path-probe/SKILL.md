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

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_path_probe.py" --site-id "hq-1"
python3 "{baseDir}/net_path_probe.py" --site-id "hq-1" --include-raw
```

## Constraints

- Use the bundled helper.
- Do not guess latency, jitter, loss, or destination comparisons.
