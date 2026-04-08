---
name: net-local-route-anomaly
description: Detect duplicate ARP ownership, interface-to-subnet mismatches, and local route-selection anomalies.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Local Route Anomaly

Use this skill to investigate suspicious local routing and ARP behavior.

## Inputs

- Scope: `--site-id`, `--gateway-ip`, or `--subnet-cidr`

## Outputs

- JSON `SkillResult`
- route counts, neighbor-cache analysis, and anomaly findings

## Command

```bash
python3 "{baseDir}/net_local_route_anomaly.py" --gateway-ip "10.0.120.1" --subnet-cidr "10.0.120.0/24"
```