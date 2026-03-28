---
name: net-incident-intake
description: Collect user complaint details into a structured NETTOOLS incident record using the bundled helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Incident Intake

## Purpose

Use this skill to normalize a freeform user complaint into a structured incident record that can drive follow-up NETTOOLS skills.

## Status

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_incident_intake.py" --site-id "hq-1"
```

## Constraints

- Use the bundled helper.
- Do not fabricate details that were not provided by the user or a follow-up prompt.
