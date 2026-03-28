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

Implemented first-pass Priority 3 skill. The bundled helper now produces a gated manual capture plan, derives a narrow capture filter from the stated reason, and refuses to imply execution without authorization and an approval ticket.

## Commands

```bash
python3 "{baseDir}/net_capture_trigger.py" --site-id "hq-1" --reason "Need to inspect DHCP failures during onboarding"
python3 "{baseDir}/net_capture_trigger.py" --client-id "client-123" --reason "Capture DNS failures" --authorized --approval-ticket "CHG-1234"
```

## Constraints

- Use the bundled helper.
- Do not start packet captures or claim authorization until the gated implementation exists.
- Return the capture plan only; do not imply that a capture was executed.
