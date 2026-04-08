---
name: net-rf-interference-scan
description: Estimate RF interference risk from neighboring AP overlap and utilization data.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net RF Interference Scan

Use this skill to estimate whether same-channel overlap or utilization points toward interference.

## Inputs

- Scope: `--ap-id`, `--ap-name`, or `--site-id`

## Outputs

- JSON `SkillResult`
- interference score, neighboring AP overlap, and follow-up recommendations

## Command

```bash
python3 "{baseDir}/net_rf_interference_scan.py" --ap-id "ap-42"
```