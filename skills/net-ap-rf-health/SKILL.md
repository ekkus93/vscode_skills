---
name: net-ap-rf-health
description: Evaluate AP radio conditions, utilization, resets, and client load using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net AP RF Health

## Purpose

Use this skill to inspect AP-level wireless health, including channel utilization, radio load, and RF instability indicators.

## Status

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_ap_rf_health.py" --ap-name "AP-2F-EAST-03"
python3 "{baseDir}/net_ap_rf_health.py" --ap-id "ap-123" --site-id "hq-1"
```

## Constraints

- Use the bundled helper instead of ad hoc controller queries.
- Do not guess AP telemetry or channel-plan findings.
