---
name: net-mac-path-trace
description: Trace a MAC address or client identity to its likely attachment point and surrounding local path.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net MAC Path Trace

Use this skill to answer where a client or host is attached right now.

## Inputs

- One of: `--mac-address`, `--client-id`, `--client-mac`, `--hostname`, `--ip-address`
- Optional scope hints: `--switch-id`, `--site-id`, `--subnet-cidr`

## Outputs

- JSON `SkillResult`
- MAC observations, candidate attachment locations, and follow-up recommendations

## Command

```bash
python3 "{baseDir}/net_mac_path_trace.py" --mac-address "aa:bb:cc:dd:ee:ff"
```