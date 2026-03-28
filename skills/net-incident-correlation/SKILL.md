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

Implemented first-pass Priority 3 skill. The bundled helper now correlates the requested incident window against recent syslog-style events and config changes, ranks the strongest evidence, and recommends targeted follow-up skills.

## Commands

```bash
python3 "{baseDir}/net_incident_correlation.py" --site-id "hq-1" --time-window-minutes 30
python3 "{baseDir}/net_incident_correlation.py" --site-id "hq-1" --incident-summary "Zoom calls started failing right after the switch work"
```

## Constraints

- Use the bundled helper.
- Do not guess causal correlation without collected evidence.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
