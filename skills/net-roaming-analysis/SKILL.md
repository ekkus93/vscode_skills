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

Phase 0 scaffold. The wrapper and helper entrypoint exist, but the diagnostic implementation is not complete yet.

## Commands

```bash
python3 "{baseDir}/net_roaming_analysis.py" --client-id "client-123"
python3 "{baseDir}/net_roaming_analysis.py" --client-mac "aa:bb:cc:dd:ee:ff" --time-window-minutes 60
```

## Constraints

- Use the bundled helper.
- Do not invent roam history or mobility findings.
