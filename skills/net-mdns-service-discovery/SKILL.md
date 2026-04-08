---
name: net-mdns-service-discovery
description: Discover mDNS and DNS-SD services on the local network and group them by host.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net mDNS Service Discovery

Use this skill to find local `.local` services and DNS-SD advertisements.

## Inputs

- Scope: `--subnet-cidr` or `--site-id`
- Filters: `--service-type`, `--hostname-pattern`

## Outputs

- JSON `SkillResult`
- services grouped by host and any name-conflict indicators

## Command

```bash
python3 "{baseDir}/net_mdns_service_discovery.py" --subnet-cidr "10.0.120.0/24" --service-type _ssh._tcp
```