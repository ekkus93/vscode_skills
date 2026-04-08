---
name: net-l2-neighbor-discovery
description: Collect LLDP, CDP, bridge-FDB, and interface neighbor evidence for local network topology reconstruction.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net L2 Neighbor Discovery

Use this skill to gather adjacency evidence before building a topology map.

## Inputs

- Scope: `--site-id`, `--device-id`, `--device-name`, `--ap-id`, `--ap-name`, or `--switch-id`
- Optional filters: `--protocol`, `--include-stale`
- Optional controls: `--time-window-minutes`, `--include-raw`, `--fixture-file`

## Outputs

- JSON `SkillResult`
- protocol counts, merged adjacencies, and follow-up recommendations

## Command

```bash
python3 "{baseDir}/net_l2_neighbor_discovery.py" --site-id "site-1" --protocol lldp --protocol cdp
```