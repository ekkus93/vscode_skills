# NETTOOLS_SPECS.md

## 1. Purpose

This document defines a set of OpenClaw skills for diagnosing internal office Wi-Fi and LAN performance problems when Internet transit may still be healthy. The focus is on isolating whether user-visible slowness is caused by:

- Wi-Fi RF conditions
- AP health or AP configuration
- Client roaming behavior
- DHCP delays or failures
- DNS delays or failures
- 802.1X / RADIUS authentication issues
- AP wired uplink problems
- Switching loops or STP instability
- VLAN / segmentation / policy errors
- General latency, jitter, and packet loss inside the LAN

The target outcome is a toolbox of small, composable OpenClaw skills that can be chained together by an agent or manually invoked by an operator.

---

## 2. Goals

### 2.1 Primary goals

1. Detect whether the problem domain is:
   - wireless RF
   - wired LAN
   - shared network services
   - access control / authentication
   - topology instability

2. Provide structured evidence, not guesses.

3. Support both:
   - interactive troubleshooting of a single complaint
   - periodic health checks and baseline monitoring

4. Produce outputs that can be consumed by:
   - humans
   - other OpenClaw skills
   - higher-level orchestration logic

### 2.2 Non-goals

1. Full NMS replacement.
2. Full vendor-specific controller management UI.
3. Automatic remediation in v1.
4. Arbitrary packet dissection beyond narrow diagnostic captures.
5. Deep RF planning / predictive survey modeling.

### 2.3 Topology extension goals

The topology-oriented extension to NETTOOLS should answer the operator questions that the earlier diagnostic set could only imply:

1. What switch, port, or AP is this client currently attached to?
2. What is the likely client-to-gateway path, and which hops are inferred versus directly observed?
3. What VLAN, subnet, and local gateway appear to be in use?
4. What local hosts and mDNS-advertised services are visible within the requested subnet scope?
5. Where is evidence incomplete, stale, conflicting, or blocked by an unmanaged segment?

---

## 3. Design principles

1. **Narrow skills**
   - Each skill should have a small, clear responsibility.

2. **Evidence-first**
   - Every finding must include timestamps and metrics.

3. **Composable**
   - Skill outputs should be machine-readable and chainable.

4. **Vendor-adaptable**
   - Core logic should be independent of specific vendors.
   - Vendor-specific adapters should translate external APIs / CLI / SNMP into normalized internal models.

5. **Safe by default**
   - Read-only behavior for v1 unless explicitly marked otherwise.

6. **Operator-friendly**
   - Outputs must be understandable in plain English.
   - Include direct next steps.

7. **Threshold-aware**
   - Use configurable thresholds instead of hardcoded assumptions.

## 3.1 V1 implementation profile

The first implementation pass should align with the existing shared-skill layout in this repository.

1. NETTOOLS should live under `skills/` inside this repo, not as a separate top-level application.
2. Each user-facing capability should be packaged as an OpenClaw skill folder with a `SKILL.md` file and a corresponding Python helper script or approved Unix network-tool workflow.
3. `SKILL.md` files should explain when to use the skill, how to invoke the bundled script or tool, required dependencies, and failure behavior.
4. Shared reusable Python code may be factored into an internal support package under `skills/` as long as the public surface remains skill-first and OpenClaw-oriented.
5. The v1 target runtime is OpenClaw running on Debian on a Dell Chromebook, so dependencies should stay conservative and Unix-friendly.
6. Pydantic should be used for input models, output models, normalized data models, and configuration schemas in v1.
7. Observability should use standard-library logging with JSON-formatted output rather than a heavy external logging stack.
8. v1 should start interface-first with stub adapters and fixtures so the skills can be developed and tested without live vendor infrastructure.

---

## 4. High-level architecture

The implementation should be organized into five layers:

### 4.1 Skill layer

OpenClaw skills exposed to the bot. Each skill should have:
- a stable name
- input schema
- output schema
- deterministic behavior
- documented dependencies
- a `SKILL.md` wrapper inside its skill folder under `skills/`
- a corresponding Python helper script or documented Unix tool invocation path

### 4.2 Provider adapter layer

Adapters that gather raw data from external systems such as:
- wireless controller APIs
- switch APIs
- SSH / CLI
- SNMP
- syslog
- RADIUS server logs
- DHCP / DNS telemetry
- active probe nodes

### 4.3 Normalization layer

Converts raw vendor / source-specific payloads into normalized models such as:
- ClientSession
- AccessPointState
- SwitchPortState
- DhcpTransactionSummary
- DnsProbeSummary
- AuthEventSummary
- PathProbeSummary
- StpEventSummary

### 4.4 Analysis layer

Reusable logic that:
- scores health
- compares metrics against thresholds
- identifies anomalies
- correlates events across sources
- produces findings and recommendations

### 4.5 Storage / caching layer

Optional but strongly recommended.
Used for:
- short-term caching
- time-window comparisons
- baseline tracking
- event correlation
- “what changed” analysis

### 4.6 Topology discovery and graph reconstruction

Topology-oriented skills extend the existing adapter and analysis model with a graph-reconstruction workflow:

1. Collect neighbor evidence from LLDP, CDP, bridge tables, interface descriptions, controller uplink mappings, gateway neighbor caches, and local service discovery.
2. Normalize all records into reusable topology models such as `NetworkNode`, `NetworkEdge`, `NeighborRecord`, `MacLocationObservation`, and `GatewayPathSummary`.
3. Merge evidence into a `TopologyGraph` with explicit unresolved references and confidence scoring.
4. Prefer passive evidence by default and require explicit authorization for active subnet scans.
5. Keep inferred edges visible and downgrade confidence when evidence is partial or contradictory.

Topology outputs should support both a compact adjacency-list view for downstream agents and a richer graph JSON payload for operator tooling.

### 4.7 Active versus passive discovery

The topology layer is passive-first.

1. Passive discovery includes controller telemetry, switch neighbor state, bridge tables, gateway neighbor caches, inventory baselines, and service advertisements.
2. Active discovery is limited to explicitly authorized subnet probes such as ICMP sweep, ARP sweep, and narrow TCP banner checks.
3. Skills must record whether active discovery was used and degrade cleanly when only passive evidence is available.

---

## 5. Common skill contract

All OpenClaw network skills should use a shared output structure.

## 5.1 Required output fields

```json
{
  "status": "ok|warn|fail|unknown",
  "skill_name": "string",
  "scope_type": "client|ap|ssid|switch_port|vlan|site|service|path",
  "scope_id": "string",
  "summary": "short human-readable finding",
  "confidence": "low|medium|high",
  "observed_at": "ISO-8601 timestamp",
  "time_window": {
    "start": "ISO-8601 timestamp",
    "end": "ISO-8601 timestamp"
  },
  "evidence": {},
  "findings": [],
  "next_actions": [],
  "raw_refs": []
}
```

## 5.2 Output conventions

1. `status`
   - `ok`: no material issue detected
   - `warn`: suspicious condition detected
   - `fail`: clear problem or failed dependency
   - `unknown`: insufficient evidence

2. `summary`
   - One sentence, operator-readable

3. `confidence`
   - Based on evidence quality, not model confidence theater

4. `evidence`
   - Raw normalized metrics relevant to the skill

5. `findings`
   - Array of structured findings:
   ```json
   {
     "code": "HIGH_RETRY_RATE",
     "severity": "info|warn|critical",
     "message": "Client retry rate exceeded threshold",
     "metric": "retry_pct",
     "value": 28.4,
     "threshold": 15.0
   }
   ```

6. `next_actions`
   - Suggested follow-up skills, not vague prose
   ```json
   {
     "skill": "net.ap_rf_health",
     "reason": "High retry rate detected on AP and channel needs validation"
   }
   ```

---

## 6. Shared input conventions

All skills should support a consistent set of optional parameters where relevant:

```json
{
  "site_id": "optional string",
  "client_id": "optional string",
  "client_mac": "optional string",
  "ap_id": "optional string",
  "ap_name": "optional string",
  "ssid": "optional string",
  "switch_id": "optional string",
  "switch_port": "optional string",
  "vlan_id": "optional string or integer",
  "time_window_minutes": "optional integer",
  "start_time": "optional ISO-8601 timestamp",
  "end_time": "optional ISO-8601 timestamp",
  "include_raw": "optional boolean"
}
```

Rules:
1. If both `time_window_minutes` and explicit start/end are absent, default to 15 minutes.
2. If only one of `client_id` or `client_mac` is provided, resolver logic should try to map to the other.
3. Inputs must be validated before any external call is made.

---

## 7. Required skills

## 7.1 net.client_health

### Purpose
Assess the health of a specific Wi-Fi client session or a set of client sessions.

### What it checks
- RSSI
- SNR
- PHY rate / MCS if available
- retry rate
- packet loss
- current AP
- current channel / band
- connection duration
- recent roam events
- disconnect / reassociation frequency

### Inputs
- `client_id` or `client_mac` preferred
- optional `ssid`
- optional `time_window_minutes`

### Evidence examples
```json
{
  "rssi_dbm": -77,
  "snr_db": 18,
  "retry_pct": 24.2,
  "packet_loss_pct": 3.8,
  "connected_ap": "AP-2F-EAST-03",
  "channel": 149,
  "band": "5GHz",
  "recent_roams": 4
}
```

### Analysis rules
- Warn on low RSSI, low SNR, elevated retries, abnormal loss
- Warn on excessive roaming or rapid reconnect cycles
- Flag sticky-client behavior when a client remains on a poor AP while stronger alternatives exist, if data is available

### Success criteria
- Can diagnose whether the user complaint is likely local to the client’s RF session
- Produces concrete next actions:
  - RF health
  - roaming analysis
  - uplink validation

---

## 7.2 net.ap_rf_health

### Purpose
Evaluate radio conditions and AP-level wireless health.

### What it checks
- channel utilization
- channel / band assignments
- channel width
- transmit power
- neighboring AP overlap
- interference indicators
- radio reset / crash events
- client load by radio

### Inputs
- `ap_id` or `ap_name`
- optional `site_id`
- optional `ssid`
- optional time range

### Evidence examples
```json
{
  "radio_2g": {
    "channel": 11,
    "width_mhz": 20,
    "utilization_pct": 82,
    "client_count": 19
  },
  "radio_5g": {
    "channel": 36,
    "width_mhz": 80,
    "utilization_pct": 76,
    "client_count": 31
  },
  "radio_resets_last_24h": 3
}
```

### Analysis rules
- Warn on high channel utilization
- Warn on overloaded APs
- Warn on suspicious channel width in dense office deployment
- Warn on repeated radio resets
- Highlight probable co-channel interference or poor AP plan if neighboring overlap data supports it

### Success criteria
- Can identify whether the AP/radio environment is likely causing slowness
- Suggest client-level, site-level, or channel-plan follow-up

---

## 7.3 net.roaming_analysis

### Purpose
Analyze roaming behavior for a specific client over a time window.

### What it checks
- roam count
- roam latency if available
- failed roam attempts
- AP-to-AP transitions
- sticky-client patterns
- disconnect-to-reconnect sequences that masquerade as roams

### Inputs
- `client_id` or `client_mac`
- optional `time_window_minutes`
- optional `site_id`

### Evidence examples
```json
{
  "roam_count": 7,
  "failed_roam_count": 2,
  "avg_roam_latency_ms": 480,
  "transitions": [
    {"from": "AP-A", "to": "AP-B", "latency_ms": 510}
  ]
}
```

### Analysis rules
- Warn on high roam latency
- Warn on repeated failed roam attempts
- Warn on sticky roaming if client remains attached to weak AP despite movement
- Correlate with low RSSI or poor AP conditions where possible

### Success criteria
- Explains whether mobility is part of the problem
- Suggests AP RF health or client health follow-up where appropriate

---

## 7.4 net.dhcp_path

### Purpose
Determine whether DHCP is slow, failing, or unstable for a client, SSID, VLAN, or site.

### What it checks
- DHCP success rate
- discover→offer latency
- request→ack latency
- relay path if available
- scope utilization if accessible
- duplicate offers or missing ACKs
- transaction failure reasons

### Inputs
- `client_id` or `client_mac` optional
- `ssid` optional
- `vlan_id` optional
- `site_id` optional

### Evidence examples
```json
{
  "success_rate_pct": 84,
  "avg_offer_latency_ms": 1800,
  "avg_ack_latency_ms": 2400,
  "timeouts": 9,
  "dhcp_server": "10.10.20.5",
  "relay_ip": "10.10.1.1"
}
```

### Analysis rules
- Warn on excessive DHCP latency
- Fail on repeated missing offers or ACKs
- Warn on scope exhaustion or near exhaustion if data exists
- Flag VLAN / relay mismatch if observed

### Success criteria
- Distinguishes onboarding/addressing problems from RF problems

---

## 7.5 net.dns_latency

### Purpose
Measure whether DNS performance is contributing to “slow network” complaints.

### What it checks
- resolver reachability
- average lookup latency
- timeout rate
- NXDOMAIN rate if useful
- differences between wired and wireless probe points
- variance by resolver

### Inputs
- `site_id` optional
- `ssid` optional
- `client_id` optional
- probe target names list optional

### Evidence examples
```json
{
  "resolver_results": [
    {
      "resolver": "10.10.0.53",
      "avg_latency_ms": 340,
      "timeout_pct": 12
    }
  ],
  "sample_queries": ["example.com", "microsoft.com", "internal.service.local"]
}
```

### Analysis rules
- Warn on elevated average lookup latency
- Fail on timeouts above threshold
- Warn when DNS is slow internally but raw IP probes are fine
- Compare internal resolver vs public resolver only if explicitly allowed by policy

### Success criteria
- Identifies DNS as a source of perceived slowness

---

## 7.6 net.auth_8021x_radius

### Purpose
Check whether authentication delays or failures are affecting Wi-Fi access.

### What it checks
- 802.1X auth success rate
- EAP phase failures if available
- RADIUS server reachability
- timeout frequency
- certificate-related failures where visible
- AP/controller to RADIUS round-trip timing

### Inputs
- `client_id` or `client_mac` optional
- `ssid` optional
- `site_id` optional
- `time_window_minutes` optional

### Evidence examples
```json
{
  "auth_success_rate_pct": 71,
  "timeouts": 14,
  "invalid_credentials": 2,
  "cert_failures": 4,
  "radius_servers": [
    {"server": "10.10.30.8", "avg_rtt_ms": 420}
  ]
}
```

### Analysis rules
- Warn on elevated auth latency
- Fail on repeated timeouts
- Differentiate user credential issues from infrastructure issues
- Suggest dependency checks if RADIUS servers are unreachable or unstable

### Success criteria
- Distinguishes auth issues from general RF / LAN issues

---

## 7.7 net.ap_uplink_health

### Purpose
Validate the wired path between APs and the switching infrastructure.

### What it checks
- link up/down state
- negotiated speed / duplex
- PoE state and power budget
- CRC / frame / input errors
- output drops
- link flaps
- native / access VLAN state
- trunk status if relevant
- uplink utilization / congestion if available

### Inputs
- `ap_id` or `ap_name`
- optional `switch_id`
- optional `switch_port`

### Evidence examples
```json
{
  "switch_id": "SW-IDF-3-01",
  "port": "Gi1/0/18",
  "link_state": "up",
  "speed_mbps": 100,
  "duplex": "full",
  "crc_errors": 944,
  "input_drops": 183,
  "poe_watts": 11.7,
  "flaps_last_24h": 6
}
```

### Analysis rules
- Warn on 100 Mbps link where gigabit is expected
- Warn or fail on CRC errors, drops, or frequent flaps
- Warn on unstable PoE or insufficient power class
- Warn on VLAN mismatch or missing expected trunk/access config

### Success criteria
- Detects the common “wireless problem that is really a switch-port problem”

---

## 7.8 net.stp_loop_anomaly

### Purpose
Detect signs of switching loops, STP instability, or MAC flapping affecting internal network health.

### What it checks
- recent topology changes
- blocked/unblocked port churn
- root bridge changes
- MAC move / MAC flap events
- broadcast / multicast storm indicators if available
- interface utilization spikes associated with loops

### Inputs
- `site_id` optional
- `switch_id` optional
- `time_window_minutes` optional

### Evidence examples
```json
{
  "topology_changes_last_hour": 37,
  "root_bridge_changes": 2,
  "mac_flap_events": 54,
  "suspect_ports": ["Gi1/0/11", "Gi1/0/23"]
}
```

### Analysis rules
- Warn on unusual topology churn
- Fail on clear MAC flapping / loop signatures
- Surface suspect ports and switches
- Recommend operator review before any automated action

### Success criteria
- Explains random widespread slowness caused by L2 instability

---

## 7.9 net.path_probe

### Purpose
Measure latency, jitter, and loss between key internal points to isolate the failing segment.

### What it checks
- probe from one or more nodes to:
  - default gateway
  - controller
  - DHCP server
  - DNS server
  - RADIUS server
  - optional external IP or host
- latency
- jitter
- packet loss
- comparative path quality

### Inputs
- source probe ID or source role
- destination set
- protocol type if configurable
- sample count
- timeouts

### Evidence examples
```json
{
  "results": [
    {
      "target": "10.10.0.1",
      "avg_latency_ms": 5.2,
      "jitter_ms": 1.8,
      "loss_pct": 0.0
    },
    {
      "target": "10.10.0.53",
      "avg_latency_ms": 186,
      "jitter_ms": 44,
      "loss_pct": 8.0
    }
  ]
}
```

### Analysis rules
- Identify whether failures are:
  - local to Wi-Fi
  - local to LAN services
  - site-wide
  - external/WAN-related
- Warn on high internal loss or jitter even if Internet probes succeed

### Success criteria
- Provides segment-isolation evidence, not just endpoint anecdotes

---

## 7.10 net.segmentation_policy

### Purpose
Verify whether clients are being placed into the correct network segment and policy set.

### What it checks
- SSID to VLAN mapping
- dynamic VLAN assignment
- ACL/policy group
- DHCP scope alignment
- default gateway alignment
- captive portal / NAC state if applicable

### Inputs
- `client_id` or `client_mac`
- optional `ssid`
- optional `vlan_id`

### Evidence examples
```json
{
  "observed_ssid": "CorpWiFi",
  "observed_vlan": 120,
  "expected_vlan": 110,
  "policy_group": "guest_restricted",
  "dhcp_scope": "10.10.120.0/24"
}
```

### Analysis rules
- Fail on clear mismatch between expected and observed placement
- Warn on unexpected restrictive policy
- Suggest auth / NAC follow-up if policy is derived dynamically

### Success criteria
- Detects “the user is on the wrong network” class of issues

---

## 8. Supporting skills

## 8.1 net.incident_intake

### Purpose
Collect complaint details in a structured format.

### Inputs
User freeform text plus optional follow-up prompts.

### Outputs
Normalized incident record:
- who
- where
- when
- device type
- movement vs stationary
- SSID
- whether wired is affected
- whether reconnect helps
- impacted apps or workflows

### Notes
This skill is intentionally simple but important for routing subsequent skills.

---

## 8.2 net.incident_correlation

### Purpose
Correlate complaint timing with telemetry and infrastructure events.

### What it checks
- AP events
- switch events
- DHCP/DNS/auth anomalies
- recent config changes
- site-level alarms

### Inputs
- incident record
- time window

### Outputs
A ranked list of likely correlated factors and recommended follow-up skills.

---

## 8.3 net.change_detection

### Purpose
Detect changes in network state or configuration that align with new issues.

### What it checks
- AP firmware changes
- controller config changes
- channel / power changes
- switch config changes
- VLAN / ACL changes
- DHCP / DNS changes
- STP root changes
- hardware replacement or port reassignment metadata if available

### Outputs
Change report with timestamps and possible relevance score.

---

## 8.4 net.capture_trigger

### Purpose
Trigger a narrowly scoped packet capture when telemetry suggests a specific protocol failure.

### Scope
Read-only orchestration until explicitly authorized to start captures in a given environment.

### Triggers
- DHCP timeouts
- DNS latency spikes
- 802.1X failures
- excessive retransmissions

### Output
Capture request plan or capture artifact reference.

---

## 9. Data model requirements

At minimum, implement normalized models for:

- `ClientSession`
- `AccessPointState`
- `RadioState`
- `SwitchPortState`
- `DhcpSummary`
- `DnsSummary`
- `AuthSummary`
- `PathProbeResult`
- `SegmentationSummary`
- `StpSummary`
- `IncidentRecord`
- `ChangeRecord`

Each model should:
- be versioned
- have source metadata
- include timestamps
- tolerate partial vendor data without crashing

For v1, these models should be implemented as Pydantic models so validation, serialization, and contract testing are consistent across skills and shared helpers.

---

## 10. Provider adapter requirements

Adapters should be swappable. Define interfaces for:

- wireless controller adapter
- switch adapter
- syslog adapter
- auth adapter
- DHCP adapter
- DNS adapter
- probe adapter
- config / inventory adapter

### Adapter requirements

1. Return normalized structures or raw payloads convertible by normalization layer.
2. Support timeout handling and partial failures.
3. Never silently swallow source errors.
4. Attach source references to outputs.
5. Prefer read-only operations in v1.

---

## 11. Configuration requirements

A central config system should define:

- source credentials and endpoints
- enabled providers
- per-skill thresholds
- site/AP/client resolution settings
- cache TTLs
- feature flags
- allowed active probes
- capture authorization flags

Threshold examples:
- low RSSI threshold
- high retry threshold
- high channel utilization threshold
- high DHCP offer latency
- high DNS latency
- auth timeout threshold
- excessive CRC errors
- STP topology change threshold

---

## 12. Observability requirements

The implementation should include:

- structured logs for every skill invocation
- latency metrics per skill
- source dependency metrics
- error classification
- optional audit log of bot-triggered investigations

In v1, implement this with standard-library logging plus JSON-formatted log records.
Avoid introducing a heavier logging framework unless the minimal approach proves insufficient.

Minimum logging fields:
- skill_name
- invocation_id
- scope
- inputs summary
- start/end time
- result status
- source calls made
- source failures
- final finding codes

---

## 13. Caching and baseline behavior

Recommended behavior:
1. Cache short-lived source lookups where safe.
2. Store rolling baselines for:
   - AP utilization
   - DNS latency
   - DHCP latency
   - auth success rate
   - path probe latency/loss
3. Support “current vs baseline” comparison in outputs.

Example:
- “Current DNS latency 340 ms vs 7-day baseline 18 ms”

---

## 14. Error-handling requirements

Every skill must distinguish between:
- no issue found
- source unavailable
- insufficient evidence
- bad input
- dependency failure

Do not collapse all failures into a generic error string.

Example output:
```json
{
  "status": "unknown",
  "summary": "Unable to assess AP uplink health because switch adapter timed out",
  "findings": [
    {
      "code": "DEPENDENCY_TIMEOUT",
      "severity": "warn",
      "message": "Switch adapter timed out during port lookup"
    }
  ]
}
```

---

## 15. Security and safety requirements

1. Secrets must not be hardcoded.
2. Skills should redact sensitive values in logs.
3. v1 should be read-only by default.
4. Active probes must be rate-limited.
5. Packet capture triggers must be explicitly gated by config and authorization.
6. Outputs should avoid exposing unnecessary credentials, certificate material, or internal secrets.

---

## 16. Suggested execution flows

## 16.1 Single user complaint flow

1. `net.incident_intake`
2. `net.client_health`
3. `net.roaming_analysis` if mobility suspected
4. `net.ap_rf_health`
5. `net.ap_uplink_health`
6. `net.dhcp_path`
7. `net.dns_latency`
8. `net.auth_8021x_radius` if auth symptoms exist
9. `net.segmentation_policy`
10. `net.incident_correlation`

## 16.2 Site-wide slowdown flow

1. `net.path_probe`
2. `net.ap_rf_health` across suspect APs
3. `net.ap_uplink_health`
4. `net.stp_loop_anomaly`
5. `net.dhcp_path`
6. `net.dns_latency`
7. `net.change_detection`
8. `net.incident_correlation`

---

## 17. Implementation priorities

## Priority 1
- `net.client_health`
- `net.ap_rf_health`
- `net.dhcp_path`
- `net.dns_latency`
- `net.ap_uplink_health`
- `net.stp_loop_anomaly`

## Priority 2
- `net.roaming_analysis`
- `net.auth_8021x_radius`
- `net.path_probe`
- `net.segmentation_policy`

## Priority 3
- `net.incident_intake`
- `net.incident_correlation`
- `net.change_detection`
- `net.capture_trigger`

---

## 18. Acceptance criteria

The project is considered successful when:

1. Each required skill has:
   - defined input schema
   - defined output schema
   - working provider integration points
   - deterministic analysis logic
   - tests

2. The system can correctly distinguish at least these scenarios:
   - poor Wi-Fi signal / retries
   - overloaded AP / bad RF
   - slow DHCP
   - slow DNS
   - auth timeout
   - bad AP switch uplink
   - L2 instability / loop symptoms
   - wrong VLAN / wrong policy

3. Skills can be chained using `next_actions` without brittle manual glue.

4. Failures in one data source do not crash unrelated skills.

---

## 19. Suggested repository layout

```text
skills/
  net-client-health/
    SKILL.md
    net_client_health.py
  net-ap-rf-health/
    SKILL.md
    net_ap_rf_health.py
  net-roaming-analysis/
    SKILL.md
    net_roaming_analysis.py
  net-dhcp-path/
    SKILL.md
    net_dhcp_path.py
  net-dns-latency/
    SKILL.md
    net_dns_latency.py
  net-auth-8021x-radius/
    SKILL.md
    net_auth_8021x_radius.py
  net-ap-uplink-health/
    SKILL.md
    net_ap_uplink_health.py
  net-stp-loop-anomaly/
    SKILL.md
    net_stp_loop_anomaly.py
  net-path-probe/
    SKILL.md
    net_path_probe.py
  net-segmentation-policy/
    SKILL.md
    net_segmentation_policy.py
  net-incident-intake/
    SKILL.md
    net_incident_intake.py
  net-incident-correlation/
    SKILL.md
    net_incident_correlation.py
  net-change-detection/
    SKILL.md
    net_change_detection.py
  net-capture-trigger/
    SKILL.md
    net_capture_trigger.py
  nettools-core/
    SKILL.md
    nettools/
      adapters/
      analysis/
      config/
      findings/
      logging/
      models/

tests/
  unit/
    nettools/
    skills/
  integration/
    nettools/
  fixtures/
    nettools/
```

Notes:

1. `nettools-core` is an internal support skill or support folder for shared Python code, not the primary operator entrypoint.
2. The user-facing surface should remain the individual OpenClaw skills under `skills/`.
3. Each `SKILL.md` should instruct OpenClaw to use its bundled helper script or a narrowly scoped Unix tool sequence rather than improvising a fresh workflow at runtime.

---

## 20. Copilot implementation notes

1. Start with the normalized models and common output contract first.
2. Implement one provider adapter interface per data source, even if the initial adapter is a stub or mockable local implementation.
3. Implement the six Priority 1 skills before adding orchestration-heavy supporting skills.
4. Keep analysis logic pure and testable.
5. Avoid vendor lock-in in the analysis layer.
6. Do not implement auto-remediation in the first pass.
