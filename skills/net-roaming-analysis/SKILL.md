---
name: net-roaming-analysis
description: Analyze roaming behavior for a Wi-Fi client, including failed roams, latency, and sticky-client symptoms, using the bundled NETTOOLS helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Roaming Analysis

## Purpose

Use this skill to analyze client roaming patterns, roam failures, and sticky-client symptoms across a time window.

## Status

Implemented first-pass Priority 2 skill. The bundled helper now evaluates roam history, failed roam attempts, roam latency, and sticky-client patterns using the shared NETTOOLS contracts, adapters, and analysis helpers.

## Workflow

1. Accept `client_id` or `client_mac`, plus optional scope fields.
2. Run the bundled helper with `python3`.
3. If no live provider is configured yet, run in fixture-backed test mode with `--fixture-file`.
4. Return the helper's structured `SkillResult` output directly instead of paraphrasing away the findings.

## Commands

```bash
python3 "{baseDir}/net_roaming_analysis.py" --client-id "client-123"
python3 "{baseDir}/net_roaming_analysis.py" --client-mac "aa:bb:cc:dd:ee:ff" --time-window-minutes 60
python3 "{baseDir}/net_roaming_analysis.py" --client-id "client-123" --fixture-file "/path/to/fixtures.json"
```

## Constraints

- Use the bundled helper.
- Do not invent roam history, AP transitions, or mobility findings.
- If no provider implementation is configured, use fixture-backed test mode rather than inventing data.
