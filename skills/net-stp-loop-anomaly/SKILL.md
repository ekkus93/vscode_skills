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

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_stp_loop_anomaly.py" --site-id "hq-1"
python3 "{baseDir}/net_stp_loop_anomaly.py" --switch-id "sw-core-1" --time-window-minutes 60
```

## Constraints

- Use the bundled helper.
- Do not guess topology-change counters, flap events, or suspect ports.
