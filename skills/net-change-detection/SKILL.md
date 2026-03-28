---
name: net-change-detection
description: Detect likely relevant changes in network state or configuration using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Change Detection

## Purpose

Use this skill to identify recent changes in infrastructure state or configuration that align with a new complaint window.

## Status

Implemented first-pass Priority 3 skill. The bundled helper now ranks recent config and platform changes by time and scope relevance and highlights hardware, firmware, or switching changes that may explain the complaint.

## Commands

```bash
python3 "{baseDir}/net_change_detection.py" --site-id "hq-1" --time-window-minutes 60
python3 "{baseDir}/net_change_detection.py" --site-id "hq-1" --incident-summary "Problems began after the switch refresh"
```

## Constraints

- Use the bundled helper.
- Do not invent config changes or temporal correlation.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
