---
name: net-site-baseline-compare
description: Compare current topology and host visibility against a saved NETTOOLS baseline snapshot for a site.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Site Baseline Compare

Use this skill to detect meaningful drift from a known-good topology baseline.

## Inputs

- Required: `--site-id`
- Optional: `--baseline-key`

## Outputs

- JSON `SkillResult`
- current summary, baseline summary, and regression findings

## Command

```bash
python3 "{baseDir}/net_site_baseline_compare.py" --site-id "site-1"
```