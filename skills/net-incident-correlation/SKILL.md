---
name: net-incident-correlation
description: Correlate incident timing with network telemetry and infrastructure events using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Incident Correlation

## Purpose

Use this skill to rank likely correlated network events or service anomalies around an incident time window.

## Status

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_incident_correlation.py" --site-id "hq-1" --time-window-minutes 30
```

## Constraints

- Use the bundled helper.
- Do not guess causal correlation without collected evidence.
