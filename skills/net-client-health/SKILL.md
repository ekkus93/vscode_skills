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

Implemented first-pass Priority 1 skill. The bundled helper now evaluates client RF health, retries, reconnects, and sticky-client clues using the shared NETTOOLS models, adapters, and analysis utilities.

## Workflow

1. Accept `client_id` or `client_mac`, plus optional scope fields.
2. Run the bundled helper with `python3`.
3. If no live provider is configured yet, run in fixture-backed test mode with `--fixture-file`.
4. Return the helper's structured `SkillResult` output directly instead of paraphrasing away the findings.

## Commands

```bash
python3 "{baseDir}/net_client_health.py" --client-mac "aa:bb:cc:dd:ee:ff"
python3 "{baseDir}/net_client_health.py" --client-id "client-123" --time-window-minutes 30
python3 "{baseDir}/net_client_health.py" --client-id "client-123" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper instead of improvising a fresh workflow.
- Do not guess controller telemetry, findings, or thresholds.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
