---
name: net-diagnose-incident
description: Orchestrate NETTOOLS incident diagnosis across the lower-level network skills using the bundled helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Diagnose Incident

## Purpose

Use this skill to run the NETTOOLS state-machine orchestrator over a normalized complaint or incident scope and produce a structured diagnosis report.

## Status

Implemented first-pass orchestrator loop. The bundled helper now normalizes intake when needed, selects a playbook, runs lower-level NETTOOLS skills in a controlled sequence, scores diagnostic domains, evaluates stop conditions, and returns a final diagnosis report.

## Commands

```bash
python3 "{baseDir}/net_diagnose_incident.py" --site-id "hq-1" --client-id "client-42" --complaint "My laptop cannot connect to CorpWiFi and reconnect helps"
python3 "{baseDir}/net_diagnose_incident.py" --site-id "hq-1" --complaint "Everyone on the second floor says the office network is slow and wired is also affected"
```

## Constraints

- Use the bundled helper.
- Prefer passing the best available scope identifiers such as `client-id`, `site-id`, `ap-id`, or `ssid`.
- Return the helper's structured `SkillResult` output directly so the diagnosis report and investigation trace remain intact.
- This v1 orchestrator is read-only and should not imply that any remediation action was executed.