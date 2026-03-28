---
name: net-client-health
description: Assess one Wi-Fi client session for RF quality, retries, disconnects, and roam symptoms using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Client Health

## Purpose

Use this skill to assess whether one client session looks unhealthy because of weak RF conditions, elevated retries, disconnects, or roam-related symptoms.

## Status

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Workflow

1. Accept `client_id` or `client_mac`, plus optional scope fields.
2. Run the bundled helper with `python3`.
3. If the helper still returns scaffold output, report that the implementation is not complete instead of inventing telemetry.

## Commands

```bash
python3 "{baseDir}/net_client_health.py" --client-mac "aa:bb:cc:dd:ee:ff"
python3 "{baseDir}/net_client_health.py" --client-id "client-123" --time-window-minutes 30
```

## Constraints

- Use the bundled helper instead of improvising a fresh workflow.
- Do not guess controller telemetry, findings, or thresholds.
