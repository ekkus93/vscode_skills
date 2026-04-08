---
name: net-topology-map
description: Build a merged local-network topology graph and likely client-to-gateway path from NETTOOLS evidence sources.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Topology Map

Use this skill to answer what is connected to what and what the likely local path looks like.

## Inputs

- Any supported scope: `--client-id`, `--client-mac`, `--ap-id`, `--switch-id`, `--vlan-id`, `--subnet-cidr`, `--site-id`
- Output controls: `--output-mode summary|adjacency|graph|path`, `--include-active-discovery`
- Optional controls: `--time-window-minutes`, `--include-raw`, `--fixture-file`

## Outputs

- JSON `SkillResult`
- graph counts, adjacency list or graph payload, and gateway path summary

## Command

```bash
python3 "{baseDir}/net_topology_map.py" --client-id "client-1" --site-id "site-1" --output-mode graph
```