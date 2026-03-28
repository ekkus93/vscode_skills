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

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_change_detection.py" --site-id "hq-1" --time-window-minutes 60
```

## Constraints

- Use the bundled helper.
- Do not invent config changes or temporal correlation.
