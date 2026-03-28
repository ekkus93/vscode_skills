---
name: net-capture-trigger
description: Prepare a gated packet-capture request or capture plan using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Capture Trigger

## Purpose

Use this skill to prepare a narrow packet-capture plan when telemetry suggests a specific protocol failure and authorization allows it.

## Status

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_capture_trigger.py" --site-id "hq-1" --include-raw
```

## Constraints

- Use the bundled helper.
- Do not start packet captures or claim authorization until the gated implementation exists.
