---
name: net-gateway-health
description: Validate local gateway latency, packet loss, and ARP stability from NETTOOLS gateway telemetry.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Gateway Health

Use this skill to isolate first-hop or gateway-local degradation.

## Inputs

- Scope: `--gateway-ip`, `--site-id`, or `--subnet-cidr`
- Optional probe hints: `--source-probe-id`, `--source-role`

## Outputs

- JSON `SkillResult`
- gateway snapshot, route summary, interface summary, and follow-up recommendations

## Command

```bash
python3 "{baseDir}/net_gateway_health.py" --gateway-ip "10.0.120.1"
```