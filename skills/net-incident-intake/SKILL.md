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

Implemented first-pass Priority 3 skill. The bundled helper now normalizes a freeform complaint into a structured incident record, infers useful fields from the complaint text, and recommends likely follow-up NETTOOLS skills.

## Commands

```bash
python3 "{baseDir}/net_incident_intake.py" --site-id "hq-1" --complaint "Users in conference room B say Wi-Fi drops while walking between APs"
python3 "{baseDir}/net_incident_intake.py" --client-id "client-123" --complaint "Laptop cannot connect to SSID CorpWiFi and reconnect helps"
```

## Constraints

- Use the bundled helper.
- Do not fabricate details that were not provided by the user or a follow-up prompt.
- Return the helper's structured `SkillResult` output directly rather than paraphrasing away the normalized incident record.
