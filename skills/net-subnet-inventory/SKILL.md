---
name: net-subnet-inventory
description: Enumerate hosts, gateways, and local service visibility within a subnet or VLAN scope.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Subnet Inventory

Use this skill to build a passive-first inventory of the local subnet.

## Inputs

- Scope: `--subnet-cidr`, `--vlan-id`, `--ssid`, `--site-id`, or `--gateway-ip`
- Active scan controls: `--active-scan-authorized`, `--enable-icmp-sweep`, `--enable-arp-sweep`, `--tcp-port`

## Outputs

- JSON `SkillResult`
- merged host list, gateways, discovered services, and active-scan metadata

## Command

```bash
python3 "{baseDir}/net_subnet_inventory.py" --subnet-cidr "10.0.120.0/24" --active-scan-authorized --enable-icmp-sweep
```