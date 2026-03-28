---
name: net-stp-loop-anomaly
description: Detect switching-loop, STP, and MAC-flap symptoms using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net STP Loop Anomaly

## Purpose

Use this skill to detect L2 instability such as topology churn, root changes, or MAC flapping that can cause widespread slowness.

## Status

Implemented first-pass Priority 1 skill. The helper now evaluates topology churn, root changes, MAC flaps, and loop-like switching symptoms using the shared NETTOOLS analysis utilities.

## Commands

```bash
python3 "{baseDir}/net_stp_loop_anomaly.py" --site-id "hq-1"
python3 "{baseDir}/net_stp_loop_anomaly.py" --switch-id "sw-core-1" --time-window-minutes 60
python3 "{baseDir}/net_stp_loop_anomaly.py" --site-id "hq-1" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper.
- Do not guess topology-change counters, flap events, or suspect ports.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
