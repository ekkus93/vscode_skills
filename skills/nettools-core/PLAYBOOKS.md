# NETTOOLS Troubleshooting Playbooks

This document collects operator-facing troubleshooting playbooks for the NETTOOLS skill suite.

These playbooks are meant for human-guided diagnosis. They align with the current NETTOOLS wrapper docs, finding-code registry, and the orchestrator playbook definitions under `skills/nettools-core/nettools/orchestrator/playbooks.py`.

## Single User Complaint

### When to Use

Use this playbook when:

- one user or one device is affected
- the complaint sounds local rather than site-wide
- there is no strong evidence yet that wired users or multiple floors are impacted

Typical examples:

- one laptop cannot connect to the primary SSID
- one phone shows poor Wi-Fi performance near a specific AP
- one user reports reconnects, roaming drops, or slow app access while others look normal

### Goal

Determine whether the problem is primarily caused by:

- client RF quality
- roaming behavior
- AP-side RF health
- AP wired uplink issues
- DNS or DHCP service degradation
- authentication or onboarding failure
- segmentation or policy placement errors

### Required Inputs

Collect as many of these as possible before starting:

- `client-id` or `client-mac`
- `site-id`
- `ssid`
- approximate incident time or time window
- whether reconnecting helps
- whether the user was stationary or moving
- whether the failure is “cannot connect”, “slow after connecting”, or “drops while moving”

If you do not have a usable client identifier yet, begin with `net.incident_intake` and capture the strongest scope hints you can.

### Fast Path

If you want the orchestrator to drive the sequence, start here:

```bash
python3 "{baseDir}/../net-diagnose-incident/net_diagnose_incident.py" \
  --site-id "hq-1" \
  --client-id "client-42" \
  --complaint "Laptop drops off CorpWiFi when moving between conference rooms"
```

Use the manual sequence below when you want tighter control over each branch or need to explain the reasoning step by step during live triage.

### Manual Sequence

#### Step 1. Normalize the complaint

Run `net.incident_intake` if the complaint is still freeform or incomplete.

```bash
python3 "{baseDir}/../net-incident-intake/net_incident_intake.py" \
  --site-id "hq-1" \
  --client-id "client-42" \
  --complaint "Laptop drops off CorpWiFi when moving between conference rooms"
```

What to look for:

- whether the complaint is clearly single-user and wireless
- whether movement is involved
- whether reconnecting helps
- whether the wording suggests onboarding or auth symptoms

Proceed when you have enough scope to target one client or one likely AP.

#### Step 2. Check client RF health first

Run `net.client_health` to establish whether the user’s current symptoms look RF-driven.

```bash
python3 "{baseDir}/../net-client-health/net_client_health.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `LOW_RSSI`
- `LOW_SNR`
- `HIGH_RETRY_RATE`
- `HIGH_PACKET_LOSS`
- `RAPID_RECONNECTS`
- `STICKY_CLIENT`

Interpretation:

- If RF findings dominate, continue to AP and roaming checks.
- If client health is clean but app access is still poor, move toward DNS, DHCP, or segmentation checks.

#### Step 3. Branch to roaming when movement matters

Run `net.roaming_analysis` if the user was moving, switching rooms, or reporting drops during handoff between APs.

```bash
python3 "{baseDir}/../net-roaming-analysis/net_roaming_analysis.py" \
  --site-id "hq-1" \
  --client-id "client-42" \
  --time-window-minutes 60
```

Primary signs to watch:

- `FAILED_ROAMS`
- `HIGH_ROAM_LATENCY`
- `EXCESSIVE_ROAM_COUNT`
- `STICKY_CLIENT_PATTERN`

Interpretation:

- Failed or slow roams push the investigation toward AP RF tuning, mobility configuration, or auth latency.
- Clean roaming results suggest the issue may be more local to one AP, one service, or one policy path.

#### Step 4. Check the serving AP’s RF health

Run `net.ap_rf_health` when the client symptoms implicate a specific AP or AP area.

```bash
python3 "{baseDir}/../net-ap-rf-health/net_ap_rf_health.py" \
  --site-id "hq-1" \
  --ap-name "AP-2F-EAST-03"
```

Primary signs to watch:

- `HIGH_CHANNEL_UTILIZATION`
- `HIGH_AP_CLIENT_LOAD`
- `UNSUITABLE_CHANNEL_WIDTH`
- `RADIO_RESETS`
- `POTENTIAL_CO_CHANNEL_INTERFERENCE`

Interpretation:

- RF degradation on the AP strengthens the case for a wireless-layer issue.
- Clean AP RF with bad client symptoms increases suspicion on uplink, policy, DNS, DHCP, or auth.

#### Step 5. Validate the AP uplink when AP-side issues remain ambiguous

Run `net.ap_uplink_health` when users on one AP look bad but RF alone does not fully explain the impact.

```bash
python3 "{baseDir}/../net-ap-uplink-health/net_ap_uplink_health.py" \
  --site-id "hq-1" \
  --ap-name "AP-2F-EAST-03"
```

Primary signs to watch:

- `UPLINK_SPEED_MISMATCH`
- `UPLINK_ERROR_RATE`
- `UPLINK_FLAPPING`
- `UPLINK_VLAN_MISMATCH`
- `POE_INSTABILITY`

Interpretation:

- If uplink findings are present, treat the AP’s wired path as the primary failure domain.
- If uplink is clean, continue down the client-service path.

#### Step 6. Check DNS for slow-but-connected complaints

Run `net.dns_latency` when the user can connect but reports slow name resolution, app launch delay, or intermittent service slowness.

```bash
python3 "{baseDir}/../net-dns-latency/net_dns_latency.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `HIGH_DNS_LATENCY`
- `DNS_TIMEOUT_RATE`

Interpretation:

- DNS findings suggest service-path degradation rather than purely Wi-Fi RF.
- If DNS is clean, move to DHCP or segmentation when the complaint still sounds like onboarding or wrong-placement behavior.

#### Step 7. Check DHCP when reconnecting helps or address acquisition is suspect

Run `net.dhcp_path` when the complaint involves reconnects, delayed connectivity after association, or address-assignment symptoms.

```bash
python3 "{baseDir}/../net-dhcp-path/net_dhcp_path.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `HIGH_DHCP_OFFER_LATENCY`
- `HIGH_DHCP_ACK_LATENCY`
- `DHCP_TIMEOUTS`
- `MISSING_DHCP_ACK`
- `SCOPE_UTILIZATION_HIGH`
- `RELAY_PATH_MISMATCH`

Interpretation:

- DHCP findings explain slow onboarding and reconnect recovery loops well.
- If DHCP is clean, check auth or segmentation depending on the complaint shape.

#### Step 8. Check auth when connection attempts fail before the client is truly online

Run `net.auth_8021x_radius` when the complaint sounds like onboarding, repeated credential prompts, or long waits during connection establishment.

```bash
python3 "{baseDir}/../net-auth-8021x-radius/net_auth_8021x_radius.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `AUTH_TIMEOUTS`
- `RADIUS_UNREACHABLE`
- `RADIUS_HIGH_RTT`
- `AUTH_CREDENTIAL_FAILURES`
- `AUTH_CERTIFICATE_FAILURES`

Interpretation:

- Infrastructure auth failures point toward RADIUS reachability or latency.
- Credential or certificate failures point away from RF and toward identity or endpoint configuration.

#### Step 9. Validate segmentation and policy when the user lands in the wrong place

Run `net.segmentation_policy` when the user connects but gets the wrong access level, the wrong gateway, or the wrong VLAN behavior.

```bash
python3 "{baseDir}/../net-segmentation-policy/net_segmentation_policy.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `VLAN_MISMATCH`
- `POLICY_GROUP_MISMATCH`
- `GATEWAY_ALIGNMENT_MISMATCH`

Interpretation:

- These findings usually indicate role-mapping, NAC, or VLAN/policy placement problems rather than RF instability.

#### Step 10. Correlate with recent events when the direct path is unclear

Run `net.incident_correlation` when the previous steps suggest multiple weak signals or when timing may matter.

```bash
python3 "{baseDir}/../net-incident-correlation/net_incident_correlation.py" \
  --site-id "hq-1" \
  --incident-summary "Single user started seeing Wi-Fi drops around 9:15 AM"
```

Primary signs to watch:

- `CORRELATED_NETWORK_EVIDENCE`
- `CORRELATED_CHANGE_WINDOW`

Interpretation:

- Use this step to connect the single-user symptom to a change window or broader supporting evidence without prematurely escalating to site-wide diagnosis.

### Stop Conditions

You can usually stop this playbook when one of these is true:

- one failure domain has high-confidence supporting findings and contradictory domains look weak
- the relevant remediation owner is now clear, such as wireless, switching, DHCP, DNS, or identity
- you have ruled out the single-user path and the complaint now looks area-based or site-wide

Escalate out of this playbook when:

- multiple users report the same symptoms in the same area
- wired devices are also affected
- path or event evidence points to site-wide service degradation

### Recommended Final Summary

When handing off or closing the investigation, capture:

- user and device scope
- time window investigated
- top finding codes observed
- primary suspected domain
- skills run in order
- whether the issue appears isolated, area-based, or broader than one user

### Related References

- `single_client_wifi_issue` in `skills/nettools-core/nettools/orchestrator/playbooks.py`
- `16.1 Single user complaint flow` in `docs/NETTOOLS_SPECS.md`
- `9.1 Playbook: single_client_wifi_issue` in `docs/NETWORK_DIAGNOSIS_ORCHESTRATOR_SPECS.md`
- `docs/NETTOOLS_FINDING_CODES.md` for operator actions by finding code

## Area-Based Wireless Complaint

### When to Use

Use this playbook when:

- multiple users in one floor, wing, room cluster, or AP cell are affected
- the impact is broader than one client but not clearly site-wide
- the complaint still sounds primarily wireless rather than wired-core or WAN-wide

Typical examples:

- everyone near one conference suite reports poor Wi-Fi at the same time
- one floor shows repeated reconnects or slow app access while the rest of the site looks normal
- several users on one side of the building complain about the same AP cluster

### Goal

Determine whether the dominant failure domain is:

- overloaded or degraded AP RF in the affected area
- one or more AP uplink issues behind the area complaint
- representative client RF or roaming problems that only appear clustered because they share the same cell
- localized DHCP or DNS service issues that present as area-based symptoms

### Required Inputs

Collect as many of these as possible before starting:

- `site-id`
- `ssid`
- one or more affected areas, floors, or room labels
- one or more representative AP names or AP IDs from the affected area
- one or more representative client identifiers when available
- approximate incident time or time window
- whether movement matters, whether reconnecting helps, and whether the issue is slow, drops, or cannot-connect

If the area scope is still vague, begin with `net.incident_intake` and capture the strongest area, SSID, AP, or client hints you have.

### Fast Path

If you want the orchestrator to drive the sequence, start here:

```bash
python3 "{baseDir}/../net-diagnose-incident/net_diagnose_incident.py" \
  --site-id "hq-1" \
  --ssid "CorpWiFi" \
  --candidate-area "north-wing" \
  --candidate-ap-name "AP-2F-NORTH-03" \
  --comparison-ap-name "AP-2F-SOUTH-01" \
  --complaint "Several users in the north wing say Wi-Fi is slow and reconnecting only helps briefly"
```

Use the manual sequence below when you need to choose the representative APs and clients yourself or explain each step during live triage.

### Manual Sequence

#### Step 1. Normalize the area-scoped complaint

Run `net.incident_intake` if the complaint is still freeform or incomplete.

```bash
python3 "{baseDir}/../net-incident-intake/net_incident_intake.py" \
  --site-id "hq-1" \
  --complaint "Several users in the north wing say Wi-Fi is slow and reconnecting only helps briefly"
```

What to look for:

- whether the complaint clearly stays inside one area instead of the whole site
- whether the issue sounds like RF degradation, roaming, slow access after connect, or onboarding failure
- whether you have enough scope to choose one or two representative APs and a small client sample

Proceed when the complaint is clearly broader than one client but still localized.

#### Step 2. Check representative AP RF health first

Run `net.ap_rf_health` on one or two representative APs from the affected area.

```bash
python3 "{baseDir}/../net-ap-rf-health/net_ap_rf_health.py" \
  --site-id "hq-1" \
  --ap-name "AP-2F-NORTH-03"
```

Primary signs to watch:

- `HIGH_CHANNEL_UTILIZATION`
- `HIGH_AP_CLIENT_LOAD`
- `UNSUITABLE_CHANNEL_WIDTH`
- `RADIO_RESETS`
- `POTENTIAL_CO_CHANNEL_INTERFERENCE`

Interpretation:

- If multiple representative APs show the same RF stress, the complaint is likely localized wireless capacity or interference.
- If sampled AP RF is clean, move quickly to uplink, representative client, or service-path checks.

#### Step 3. Validate AP uplinks for the affected area

Run `net.ap_uplink_health` on the same representative APs when the area symptoms remain ambiguous.

```bash
python3 "{baseDir}/../net-ap-uplink-health/net_ap_uplink_health.py" \
  --site-id "hq-1" \
  --ap-name "AP-2F-NORTH-03"
```

Primary signs to watch:

- `UPLINK_SPEED_MISMATCH`
- `UPLINK_ERROR_RATE`
- `UPLINK_FLAPPING`
- `UPLINK_VLAN_MISMATCH`
- `POE_INSTABILITY`

Interpretation:

- Uplink findings on multiple representative APs suggest the complaint is localized but wired rather than radio-only.
- Clean uplinks push the investigation back toward client, roaming, DNS, or DHCP branches.

#### Step 4. Sample representative client health

Run `net.client_health` for one or more representative affected clients from the area.

```bash
python3 "{baseDir}/../net-client-health/net_client_health.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `LOW_RSSI`
- `LOW_SNR`
- `HIGH_RETRY_RATE`
- `HIGH_PACKET_LOSS`
- `RAPID_RECONNECTS`
- `STICKY_CLIENT`

Interpretation:

- Consistent client findings across sampled users reinforce the area hypothesis.
- Divergent client results suggest the complaint may be mixing a local AP issue with individual endpoint conditions.

#### Step 5. Check roaming if movement matters inside the affected area

Run `net.roaming_analysis` when users are moving within the impacted floor or room cluster.

```bash
python3 "{baseDir}/../net-roaming-analysis/net_roaming_analysis.py" \
  --site-id "hq-1" \
  --client-id "client-42" \
  --time-window-minutes 60
```

Primary signs to watch:

- `FAILED_ROAMS`
- `HIGH_ROAM_LATENCY`
- `EXCESSIVE_ROAM_COUNT`
- `STICKY_CLIENT_PATTERN`

Interpretation:

- Roaming problems suggest mobility tuning, neighbor coverage, or auth latency in the area.
- Clean roaming results shift attention back to AP health or service-path issues.

#### Step 6. Check DNS or DHCP only if the area users are connected but still unusable

Run `net.dns_latency` when the complaint sounds like slow name-based access after connection.

```bash
python3 "{baseDir}/../net-dns-latency/net_dns_latency.py" \
  --site-id "hq-1"
```

Run `net.dhcp_path` when reconnecting helps briefly or address acquisition appears delayed.

```bash
python3 "{baseDir}/../net-dhcp-path/net_dhcp_path.py" \
  --site-id "hq-1"
```

Interpretation:

- If DNS or DHCP findings are present only for the affected area sample, the complaint may still be localized even though the failing domain is a shared service path.
- If service checks are clean, return to the strongest AP or client branch instead of expanding prematurely to site-wide triage.

#### Step 7. Correlate the area incident window before handoff

Run `net.incident_correlation` after the direct checks so the final handoff can tie the localized evidence back to recent events or change windows.

```bash
python3 "{baseDir}/../net-incident-correlation/net_incident_correlation.py" \
  --site-id "hq-1" \
  --incident-summary "North wing users started seeing Wi-Fi degradation around 10:15 AM"
```

Primary signs to watch:

- `CORRELATED_NETWORK_EVIDENCE`
- `CORRELATED_CHANGE_WINDOW`

Interpretation:

- Use this final step to explain whether the area complaint lines up with a local AP cluster issue, uplink degradation, service slowdown, or a relevant change window.

### Stop Conditions

You can usually stop this playbook when one of these is true:

- one localized failure domain has clear supporting evidence across representative AP or client samples
- the likely remediation owner is clear, such as wireless operations, switching, DHCP, or DNS
- expanding from the area scope to the whole site is no longer justified by the evidence

Escalate or re-scope when:

- multiple additional areas begin showing the same symptoms
- wired users in other areas are also affected
- the strongest evidence now points to a site-wide path or topology issue

### Recommended Final Summary

When handing off or closing the investigation, capture:

- affected area or floor scope
- representative APs and clients sampled
- time window investigated
- top AP, client, roaming, DNS, or DHCP findings observed
- whether the complaint remained localized or started expanding site-wide
- the primary suspected domain and owning team

### Related References

- `area_based_wifi_issue` in `skills/nettools-core/nettools/orchestrator/playbooks.py`
- `docs/NETTOOLS_FINDING_CODES.md` for operator actions by finding code

## Site-Wide Slowdown

### When to Use

Use this playbook when:

- multiple users in different areas are affected
- the complaint sounds broader than a single AP cell or one endpoint
- wired users may also be affected
- internal services feel slow even when Internet transit is not the only suspect
- recent infrastructure changes may have contributed to the incident

Typical examples:

- multiple floors report slow internal apps at the same time
- both wired and wireless users say the office network is sluggish
- DNS, DHCP, or internal authentication feels slow across a large scope
- users report broad instability after switch, firmware, or maintenance work

### Goal

Determine whether the dominant failure domain is:

- recent infrastructure change impact
- site-wide path or service degradation
- switching-loop or L2 instability
- AP uplink degradation affecting representative areas
- DNS or DHCP service slowdown across the site
- localized RF issues that only look broad because a few representative APs are overloaded

### Required Inputs

Collect as many of these as possible before starting:

- `site-id`
- approximate incident start time or time window
- whether wired users are also affected
- one or more affected areas, floors, or rooms
- one or more representative AP names or AP IDs if available
- whether symptoms are slow access, packet loss, onboarding failure, or broad disconnects
- whether any recent network change window overlaps the complaint

If you have no reliable site scope, start with `net.incident_intake` and capture the broadest trustworthy description before moving to service or topology checks.

### Fast Path

If you want the orchestrator to drive the sequence, start here:

```bash
python3 "{baseDir}/../net-diagnose-incident/net_diagnose_incident.py" \
  --site-id "hq-1" \
  --complaint "Multiple teams across the office report slow internal apps and wired users are affected too"
```

Use the manual sequence below when you need explicit control over representative sampling, skill ordering, or operator narration during a live incident.

### Manual Sequence

#### Step 1. Normalize the site-wide complaint

Run `net.incident_intake` if the complaint is still freeform or if broad-impact details are incomplete.

```bash
python3 "{baseDir}/../net-incident-intake/net_incident_intake.py" \
  --site-id "hq-1" \
  --complaint "Users on multiple floors say internal apps are slow and wired desks are affected too"
```

What to look for:

- whether the complaint clearly spans multiple users or areas
- whether wired devices are also affected
- whether the symptom sounds like slowness, intermittent loss, or onboarding failure
- whether the complaint lines up with a shared time window rather than isolated user behavior

Proceed when the incident is clearly broader than one client.

#### Step 2. Check for recent relevant changes first

Run `net.change_detection` early so you know whether the incident window overlaps recent network work.

```bash
python3 "{baseDir}/../net-change-detection/net_change_detection.py" \
  --site-id "hq-1" \
  --time-window-minutes 60 \
  --incident-summary "Multiple areas report slow internal apps after morning maintenance"
```

Primary signs to watch:

- `RECENT_RELEVANT_CHANGE`
- `RECENT_HARDWARE_OR_FIRMWARE_CHANGE`
- `CORRELATED_CHANGE_WINDOW`

Interpretation:

- Strong change correlation should stay in view throughout the rest of the run.
- If a change aligns tightly with the incident, you may already have a leading hypothesis before deeper service checks.

#### Step 3. Measure broad internal path health

Run `net.path_probe` to determine whether the site shows shared latency, jitter, or loss toward key internal services.

```bash
python3 "{baseDir}/../net-path-probe/net_path_probe.py" \
  --site-id "hq-1" \
  --source-role "wireless" \
  --target "dns-service" \
  --target "radius-service" \
  --target "default-gateway"
```

Primary signs to watch:

- `SITE_WIDE_PATH_LOSS`
- `INTERNAL_SERVICE_DEGRADATION`
- `WAN_EXTERNAL_DEGRADATION`

Interpretation:

- If internal targets are broadly degraded, treat the issue as shared infrastructure or service impact.
- If only WAN or external targets are degraded, the incident may sit outside the LAN core.
- If path probes are clean, keep topology, AP uplink, and RF checks in play.

#### Step 4. Check for topology instability or loops

Run `net.stp_loop_anomaly` when the symptoms are broad, bursty, or consistent with switching churn.

```bash
python3 "{baseDir}/../net-stp-loop-anomaly/net_stp_loop_anomaly.py" \
  --site-id "hq-1" \
  --time-window-minutes 60
```

Primary signs to watch:

- `TOPOLOGY_CHURN`
- `ROOT_BRIDGE_CHANGES`
- `MAC_FLAP_LOOP_SIGNATURE`
- `STORM_INDICATORS`

Interpretation:

- Strong L2 findings can explain wide-area slowness or intermittent outages faster than service-by-service checks.
- If topology is stable, continue toward uplink and service-specific branches.

#### Step 5. Sample representative AP uplinks

Run `net.ap_uplink_health` against representative APs or switch ports from impacted areas.

```bash
python3 "{baseDir}/../net-ap-uplink-health/net_ap_uplink_health.py" \
  --site-id "hq-1" \
  --ap-name "AP-2F-EAST-03"
```

Repeat for a small set of representative APs rather than every AP.

Primary signs to watch:

- `UPLINK_SPEED_MISMATCH`
- `UPLINK_ERROR_RATE`
- `UPLINK_FLAPPING`
- `UPLINK_VLAN_MISMATCH`
- `POE_INSTABILITY`

Interpretation:

- Multiple AP uplink problems across different areas suggest a broader wired distribution issue.
- Clean uplinks across representative APs shift attention back toward shared services or core path health.

#### Step 6. Check DNS across the affected site scope

Run `net.dns_latency` when users are connected but internal or name-based services feel slow across the site.

```bash
python3 "{baseDir}/../net-dns-latency/net_dns_latency.py" \
  --site-id "hq-1"
```

Primary signs to watch:

- `HIGH_DNS_LATENCY`
- `DNS_TIMEOUT_RATE`

Interpretation:

- Site-wide DNS findings suggest a shared resolver or service-path issue.
- If DNS is clean, move toward DHCP or sampled RF/client checks depending on the complaint shape.

#### Step 7. Check DHCP when onboarding or reconnect delays are widespread

Run `net.dhcp_path` when users across the site are slow to obtain working access, reconnecting helps briefly, or onboarding is broadly degraded.

```bash
python3 "{baseDir}/../net-dhcp-path/net_dhcp_path.py" \
  --site-id "hq-1"
```

Primary signs to watch:

- `HIGH_DHCP_OFFER_LATENCY`
- `HIGH_DHCP_ACK_LATENCY`
- `DHCP_TIMEOUTS`
- `MISSING_DHCP_ACK`
- `SCOPE_UTILIZATION_HIGH`
- `RELAY_PATH_MISMATCH`

Interpretation:

- Shared DHCP problems explain broad onboarding and recovery failures well.
- If DHCP is clean, the issue is more likely path, topology, or sampled wireless capacity.

#### Step 8. Sample AP RF health instead of querying the whole site blindly

Run `net.ap_rf_health` on representative APs from the most affected areas rather than attempting full-site RF diagnosis in one jump.

```bash
python3 "{baseDir}/../net-ap-rf-health/net_ap_rf_health.py" \
  --site-id "hq-1" \
  --ap-name "AP-2F-EAST-03"
```

Primary signs to watch:

- `HIGH_CHANNEL_UTILIZATION`
- `HIGH_AP_CLIENT_LOAD`
- `UNSUITABLE_CHANNEL_WIDTH`
- `RADIO_RESETS`
- `POTENTIAL_CO_CHANNEL_INTERFERENCE`

Interpretation:

- If multiple sampled APs show the same RF stress, localized wireless capacity may be contributing to the broader complaint.
- If sampled AP RF is clean, site-wide symptoms are more likely upstream of the radio layer.

#### Step 9. Sample representative client health only if needed

Run `net.client_health` for one or more representative affected clients when you need to verify how a broad complaint appears at the edge.

```bash
python3 "{baseDir}/../net-client-health/net_client_health.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- whether multiple representative clients show the same RF or retry pattern
- whether edge symptoms match the broader service or topology hypothesis

Interpretation:

- Consistent client symptoms across different areas strengthen the case for a shared cause.
- Divergent client symptoms may indicate the complaint is partly site-wide and partly local to certain cells.

#### Step 10. Correlate the broad incident window before handoff

Run `net.incident_correlation` after the main site-wide checks so you can tie the strongest evidence back to time, change windows, and supporting events.

```bash
python3 "{baseDir}/../net-incident-correlation/net_incident_correlation.py" \
  --site-id "hq-1" \
  --incident-summary "Multiple teams reported broad slowdown starting around 9:15 AM"
```

Primary signs to watch:

- `CORRELATED_NETWORK_EVIDENCE`
- `CORRELATED_CHANGE_WINDOW`

Interpretation:

- Use this final step to explain whether the site-wide evidence points to change impact, service degradation, topology instability, or a combination.

### Stop Conditions

You can usually stop this playbook when one of these is true:

- one broad-impact domain has strong supporting evidence, such as path degradation, topology instability, or a tightly correlated change window
- the likely remediation owner is clear, such as switching, core services, wireless operations, or infrastructure change management
- sampled AP and client evidence is consistent enough that additional spot checks are no longer changing the conclusion

Escalate or re-scope when:

- the incident narrows down to one floor, room, or AP cluster instead of the whole site
- evidence points to onboarding or authentication specifically rather than general slowdown
- the issue appears upstream of the internal LAN, such as a WAN or external dependency problem

### Recommended Final Summary

When handing off or closing the investigation, capture:

- site scope and affected areas
- whether wired users were also affected
- time window investigated
- the strongest path, topology, service, or change findings
- which representative APs or clients were sampled
- the primary suspected domain and the owning team

### Related References

- `site_wide_internal_slowdown` in `skills/nettools-core/nettools/orchestrator/playbooks.py`
- `16.2 Site-wide slowdown flow` in `docs/NETTOOLS_SPECS.md`
- `9.3 Playbook: site_wide_internal_slowdown` in `docs/NETWORK_DIAGNOSIS_ORCHESTRATOR_SPECS.md`
- `docs/NETTOOLS_FINDING_CODES.md` for operator actions by finding code

## Auth Issue

### When to Use

Use this playbook when:

- users cannot complete Wi-Fi onboarding or authentication
- users connect to the SSID but do not get working access afterward
- reconnecting helps temporarily but the issue returns
- the complaint sounds like 802.1X, RADIUS, DHCP, or policy placement rather than pure RF degradation

Typical examples:

- users hang on “connecting” or fail to finish SSID authentication
- a device authenticates inconsistently and only works after repeated reconnects
- users join the SSID but land in the wrong VLAN or lack expected access
- onboarding fails for multiple users after an identity, certificate, or NAC change

### Goal

Determine whether the dominant failure domain is:

- RADIUS or authentication latency
- credential or certificate failure
- DHCP lease acquisition problems after successful association
- segmentation or policy assignment errors
- DNS or client-side symptoms that only appear after onboarding completes

### Required Inputs

Collect as many of these as possible before starting:

- `client-id` or `client-mac`
- `site-id`
- `ssid`
- approximate incident time or time window
- whether the user fails before getting online or connects with limited access
- whether reconnecting helps temporarily
- any visible credential, certificate, or supplicant error wording from the client

If scope is incomplete, begin with `net.incident_intake` so the onboarding complaint is normalized before you branch into auth, DHCP, or policy checks.

### Fast Path

If you want the orchestrator to drive the sequence, start here:

```bash
python3 "{baseDir}/../net-diagnose-incident/net_diagnose_incident.py" \
  --site-id "hq-1" \
  --client-id "client-42" \
  --complaint "Laptop keeps failing to join CorpWiFi and reconnect helps for a minute"
```

Use the manual sequence below when you need to narrate the access path explicitly or verify each dependency hop in order.

### Manual Sequence

#### Step 1. Normalize the onboarding complaint

Run `net.incident_intake` if the complaint is still freeform or missing important scope details.

```bash
python3 "{baseDir}/../net-incident-intake/net_incident_intake.py" \
  --site-id "hq-1" \
  --client-id "client-42" \
  --complaint "Laptop keeps failing to join CorpWiFi and reconnect helps for a minute"
```

What to look for:

- whether the complaint clearly sounds like onboarding or auth failure
- whether reconnecting helps
- whether movement is irrelevant and the failure happens before stable access is established
- whether the user reports limited access after connecting rather than complete failure

Proceed when you have enough scope to target one client or one SSID path.

#### Step 2. Check authentication and RADIUS first

Run `net.auth_8021x_radius` as the primary branch for onboarding and access-failure complaints.

```bash
python3 "{baseDir}/../net-auth-8021x-radius/net_auth_8021x_radius.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `AUTH_TIMEOUTS`
- `RADIUS_UNREACHABLE`
- `RADIUS_HIGH_RTT`
- `AUTH_CREDENTIAL_FAILURES`
- `AUTH_CERTIFICATE_FAILURES`
- `LOW_AUTH_SUCCESS_RATE`

Interpretation:

- Timeout, reachability, or RTT findings point toward infrastructure auth problems.
- Credential and certificate findings point toward identity, endpoint, or supplicant configuration.
- If auth looks clean, continue immediately to DHCP and segmentation because the user may be failing after authentication completes.

#### Step 3. Check DHCP after association succeeds but access still fails

Run `net.dhcp_path` when the user authenticates inconsistently, gets partial access, or only recovers after reconnecting.

```bash
python3 "{baseDir}/../net-dhcp-path/net_dhcp_path.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `HIGH_DHCP_OFFER_LATENCY`
- `HIGH_DHCP_ACK_LATENCY`
- `DHCP_TIMEOUTS`
- `MISSING_DHCP_ACK`
- `SCOPE_UTILIZATION_HIGH`
- `RELAY_PATH_MISMATCH`

Interpretation:

- DHCP findings explain why users appear to authenticate but still fail to become usable.
- If DHCP is clean, move toward segmentation or DNS depending on whether the user gets the wrong access or simply poor service.

#### Step 4. Validate segmentation and policy placement

Run `net.segmentation_policy` when the user joins the SSID but lands in the wrong VLAN, wrong policy group, or wrong gateway path.

```bash
python3 "{baseDir}/../net-segmentation-policy/net_segmentation_policy.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `VLAN_MISMATCH`
- `POLICY_GROUP_MISMATCH`
- `GATEWAY_ALIGNMENT_MISMATCH`

Interpretation:

- These findings usually indicate NAC, role-mapping, VLAN assignment, or policy logic problems after the auth step.
- If segmentation is correct, continue to DNS or client-edge validation.

#### Step 5. Check DNS when onboarding succeeds but service still feels broken

Run `net.dns_latency` when the user appears online but internal names, captive dependencies, or app startup remain slow after joining.

```bash
python3 "{baseDir}/../net-dns-latency/net_dns_latency.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `HIGH_DNS_LATENCY`
- `DNS_TIMEOUT_RATE`

Interpretation:

- DNS degradation can make onboarding look broken even after auth and DHCP succeed.
- If DNS is clean, use client-health data to determine whether the remaining issue is endpoint-local or RF-adjacent.

#### Step 6. Check client health when the access path is clean but the user still reports failure

Run `net.client_health` only after the auth, DHCP, and segmentation path looks mostly healthy, or when you need to confirm edge symptoms.

```bash
python3 "{baseDir}/../net-client-health/net_client_health.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Primary signs to watch:

- `LOW_RSSI`
- `LOW_SNR`
- `HIGH_RETRY_RATE`
- `HIGH_PACKET_LOSS`
- `RAPID_RECONNECTS`

Interpretation:

- If client RF findings dominate only after the access path checks are clean, the original complaint may have mixed causes.
- If client health is also clean, finish with time-window correlation before escalating further.

#### Step 7. Correlate the incident with recent events before handoff

Run `net.incident_correlation` to connect the access-failure path with recent events or changes.

```bash
python3 "{baseDir}/../net-incident-correlation/net_incident_correlation.py" \
  --site-id "hq-1" \
  --incident-summary "Users started failing onboarding after the morning identity maintenance window"
```

Primary signs to watch:

- `CORRELATED_NETWORK_EVIDENCE`
- `CORRELATED_CHANGE_WINDOW`

Interpretation:

- Use this final step to explain whether the access failure lines up with infrastructure auth issues, DHCP path trouble, or a recent policy or change event.

### Stop Conditions

You can usually stop this playbook when one of these is true:

- one access-path domain has clear supporting evidence, such as RADIUS timeout, DHCP failure, or policy mismatch
- the owning team is clear, such as identity, DHCP, NAC, or wireless operations
- later steps are only confirming a conclusion that is already high-confidence

Escalate or re-scope when:

- the complaint turns out to be broad site-wide slowdown rather than onboarding failure
- multiple users in one area show RF symptoms that point to localized wireless health instead of access control
- the evidence suggests recent infrastructure change impact that should be handled through change review

### Recommended Final Summary

When handing off or closing the investigation, capture:

- user and device scope
- SSID and site scope
- time window investigated
- whether failure occurred before or after the client obtained working access
- top auth, DHCP, segmentation, or DNS finding codes observed
- the primary suspected domain and the owning team

### Related References

- `auth_or_onboarding_issue` in `skills/nettools-core/nettools/orchestrator/playbooks.py`
- `9.4 Playbook: auth_or_onboarding_issue` in `docs/NETWORK_DIAGNOSIS_ORCHESTRATOR_SPECS.md`
- `docs/NETTOOLS_FINDING_CODES.md` for operator actions by finding code

## Recent Hardware Change

### When to Use

Use this playbook when:

- symptoms began soon after hardware replacement, firmware rollout, controller upgrade, or switch maintenance
- operators already suspect a recent change window is relevant
- the problem may be local or site-wide, but a recent infrastructure event is the strongest early clue

Typical examples:

- Wi-Fi instability started after an AP firmware push
- users in one area began failing after a switch replacement or uplink move
- site-wide slowdown began shortly after core or controller maintenance
- onboarding failures appeared after NAC, controller, or access-switch changes

### Goal

Determine whether a recent hardware, firmware, or infrastructure change is:

- tightly correlated with the complaint window
- the most plausible primary cause
- only one contributing factor among RF, service, topology, or policy symptoms
- severe enough to justify rollback, containment, or direct owner escalation

### Required Inputs

Collect as many of these as possible before starting:

- `site-id`
- approximate incident start time or time window
- known change window or maintenance window
- affected device IDs, AP names, switch IDs, or areas if known
- whether the issue is isolated, area-based, or site-wide
- whether wired users are also affected
- the type of recent change if already known, such as firmware, hardware swap, VLAN change, or controller maintenance

If the complaint is still vague, begin with `net.incident_intake` so the scope is normalized before you evaluate the change window.

### Fast Path

If you already know the issue started after maintenance and want a guided run, start here:

```bash
python3 "{baseDir}/../net-diagnose-incident/net_diagnose_incident.py" \
  --site-id "hq-1" \
  --complaint "Users started dropping from Wi-Fi right after the AP firmware rollout" \
  --playbook-override "site_wide_internal_slowdown"
```

There is no dedicated orchestrator playbook named `recent_hardware_change` in the current code. Use the manual sequence below when the change window itself is the main hypothesis and you want to validate it directly.

### Manual Sequence

#### Step 1. Normalize the complaint and scope

Run `net.incident_intake` if the report is still freeform or missing scope information.

```bash
python3 "{baseDir}/../net-incident-intake/net_incident_intake.py" \
  --site-id "hq-1" \
  --complaint "Users started dropping from Wi-Fi right after the AP firmware rollout"
```

What to look for:

- when the symptoms started relative to the change window
- whether the issue is single-user, area-based, or site-wide
- whether wired devices are also affected
- which devices, APs, floors, or services seem most affected

Proceed when the complaint has enough structure to compare against recent changes.

#### Step 2. Check for recent relevant changes immediately

Run `net.change_detection` first. This is the anchor step for this playbook.

```bash
python3 "{baseDir}/../net-change-detection/net_change_detection.py" \
  --site-id "hq-1" \
  --time-window-minutes 120 \
  --incident-summary "Users started dropping from Wi-Fi right after the AP firmware rollout"
```

Primary signs to watch:

- `RECENT_RELEVANT_CHANGE`
- `RECENT_HARDWARE_OR_FIRMWARE_CHANGE`
- `CORRELATED_CHANGE_WINDOW`

Interpretation:

- If a hardware or firmware event ranks highly and aligns tightly with the incident start, it becomes the working hypothesis.
- If no relevant change appears, keep the change theory in reserve but validate the normal failure domains before escalating on that basis.

#### Step 3. Correlate the change window with recent events

Run `net.incident_correlation` to see whether the same window also contains supportive network evidence.

```bash
python3 "{baseDir}/../net-incident-correlation/net_incident_correlation.py" \
  --site-id "hq-1" \
  --incident-summary "Symptoms started immediately after controller and AP maintenance"
```

Primary signs to watch:

- `CORRELATED_NETWORK_EVIDENCE`
- `CORRELATED_CHANGE_WINDOW`

Interpretation:

- If change data and network evidence line up, the rollback or validation case is much stronger.
- If change correlation is weak, move quickly into direct technical validation of the suspected domain.

#### Step 4. Validate the most likely affected technical domain

Choose the next validation skill based on what changed.

Use `net.ap_uplink_health` when the change involved AP cabling, switching, PoE, or access-port work:

```bash
python3 "{baseDir}/../net-ap-uplink-health/net_ap_uplink_health.py" \
  --site-id "hq-1" \
  --ap-name "AP-2F-EAST-03"
```

Use `net.ap_rf_health` when the change involved AP firmware, radio settings, channel plan, or AP replacement:

```bash
python3 "{baseDir}/../net-ap-rf-health/net_ap_rf_health.py" \
  --site-id "hq-1" \
  --ap-name "AP-2F-EAST-03"
```

Use `net.stp_loop_anomaly` when the change involved switching, topology, or L2 reconvergence risk:

```bash
python3 "{baseDir}/../net-stp-loop-anomaly/net_stp_loop_anomaly.py" \
  --site-id "hq-1" \
  --time-window-minutes 60
```

Use `net.dhcp_path` or `net.dns_latency` when the change affected shared services or server paths:

```bash
python3 "{baseDir}/../net-dhcp-path/net_dhcp_path.py" --site-id "hq-1"
python3 "{baseDir}/../net-dns-latency/net_dns_latency.py" --site-id "hq-1"
```

Interpretation:

- The purpose of this step is to prove or disprove that the changed component now shows the expected failure signature.
- If the changed component looks clean, the timeline may still be coincidental and you should continue with the broader symptom-led playbook instead.

#### Step 5. Sample representative edge impact if needed

If the changed component suggests wireless-user impact but the symptom scope is still unclear, sample one or more representative clients.

```bash
python3 "{baseDir}/../net-client-health/net_client_health.py" \
  --site-id "hq-1" \
  --client-id "client-42"
```

Use this step to determine whether the change impact is actually visible at the client edge or only in infrastructure telemetry.

#### Step 6. Decide whether to continue, contain, or escalate

At this point, one of three outcomes should usually be clear:

- the recent hardware or firmware event is the leading cause and needs rollback, validation, or owner escalation
- the change window is correlated but not yet proven, so broader symptom-led investigation should continue
- the change appears unrelated and normal domain triage should take over instead

### Stop Conditions

You can usually stop this playbook when one of these is true:

- a recent hardware or firmware event aligns with the incident and the directly affected technical domain now shows supporting findings
- the relevant remediation owner is clear, such as wireless operations, switching, DHCP, DNS, or change management
- the evidence is strong enough to justify rollback review, targeted validation, or escalation to the team that performed the change

Escalate or re-scope when:

- the complaint turns out not to align cleanly with the change window
- the changed component validates as healthy and another failure domain becomes stronger
- the impact is broader than expected and should be handled through the site-wide slowdown playbook instead

### Recommended Final Summary

When handing off or closing the investigation, capture:

- the complaint scope and time window
- the specific hardware, firmware, or infrastructure change under review
- the strongest related finding codes
- which validation skills were run against the changed domain
- whether the change appears causal, contributory, or coincidental
- the recommended next action, such as rollback review, targeted validation, or owner escalation

### Related References

- [skills/net-change-detection/SKILL.md](skills/net-change-detection/SKILL.md) for the primary change-detection helper
- `9.3 Playbook: site_wide_internal_slowdown` in `docs/NETWORK_DIAGNOSIS_ORCHESTRATOR_SPECS.md` for the closest current orchestrator path
- `docs/NETTOOLS_FINDING_CODES.md` for operator actions tied to `RECENT_RELEVANT_CHANGE`, `RECENT_HARDWARE_OR_FIRMWARE_CHANGE`, and `CORRELATED_CHANGE_WINDOW`