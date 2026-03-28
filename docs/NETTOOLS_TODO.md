# NETTOOLS_TODO.md

## 1. Overview

This TODO list breaks NETTOOLS_SPECS.md into detailed implementation tasks and subtasks for Github Copilot. The tasks are ordered to reduce rework and establish the shared architecture before individual OpenClaw skills are implemented.

Implementation assumption for v1:

- NETTOOLS lives under `skills/` in this repo as OpenClaw skill folders.
- Each user-facing skill gets a `SKILL.md` plus a corresponding Python helper script or tightly scoped Unix tool workflow.
- Shared reusable code can live in an internal support package under `skills/`.
- Pydantic is the model and config layer.
- Logging uses standard-library logging with JSON formatting.

---

## 2. Phase 0 - Repository setup and scaffolding

### 2.1 Create project structure
- [x] Create skill-first package structure under `skills/`
  - [x] `skills/net-client-health/`
  - [x] `skills/net-ap-rf-health/`
  - [x] `skills/net-roaming-analysis/`
  - [x] `skills/net-dhcp-path/`
  - [x] `skills/net-dns-latency/`
  - [x] `skills/net-auth-8021x-radius/`
  - [x] `skills/net-ap-uplink-health/`
  - [x] `skills/net-stp-loop-anomaly/`
  - [x] `skills/net-path-probe/`
  - [x] `skills/net-segmentation-policy/`
  - [x] `skills/net-incident-intake/`
  - [x] `skills/net-incident-correlation/`
  - [x] `skills/net-change-detection/`
  - [x] `skills/net-capture-trigger/`
  - [x] `skills/nettools-core/`
  - [x] `skills/nettools-core/nettools/adapters/`
  - [x] `skills/nettools-core/nettools/models/`
  - [x] `skills/nettools-core/nettools/analysis/`
  - [x] `skills/nettools-core/nettools/config/`
  - [x] `tests/unit/`
  - [x] `tests/integration/`
  - [x] `tests/fixtures/`

### 2.2 Establish coding conventions
- [x] Define Python version target for Debian on the Dell Chromebook OpenClaw runtime
- [x] Add formatter / linter config
- [x] Add type-checking config
- [x] Add test runner config
- [x] Standardize on Pydantic for models and configuration
- [x] Add stdlib JSON logging config
- [x] Add `.env.example` or equivalent config template

### 2.3 Create package bootstrap
- [x] Add `SKILL.md` files for each NETTOOLS skill folder
- [x] Add corresponding Python helper script entrypoints for each NETTOOLS skill folder
- [x] Add package init files for the shared `nettools-core` support package
- [x] Add module export patterns if desired for shared support code
- [x] Add a minimal CLI or entrypoint for local testing if useful

### 2.4 Documentation bootstrap
- [x] Add `README.md`
- [x] Add `ARCHITECTURE.md` summary derived from specs
- [x] Add `CONFIGURATION.md`
- [x] Add `TESTING.md`

---

## 3. Phase 1 - Common contracts and shared infrastructure

### 3.1 Define common enums and constants
- [x] Create status enum
  - [x] `ok`
  - [x] `warn`
  - [x] `fail`
  - [x] `unknown`
- [x] Create confidence enum
  - [x] `low`
  - [x] `medium`
  - [x] `high`
- [x] Create scope type enum
  - [x] `client`
  - [x] `ap`
  - [x] `ssid`
  - [x] `switch_port`
  - [x] `vlan`
  - [x] `site`
  - [x] `service`
  - [x] `path`
- [x] Define stable finding code naming convention and registry location

### 3.2 Implement common output models
- [x] Create Pydantic `Finding` model
  - [x] code
  - [x] severity
  - [x] message
  - [x] metric
  - [x] value
  - [x] threshold
- [x] Create Pydantic `NextAction` model
  - [x] skill
  - [x] reason
- [x] Create Pydantic `TimeWindow` model
- [x] Create Pydantic `SkillResult` model
  - [x] status
  - [x] skill_name
  - [x] scope_type
  - [x] scope_id
  - [x] summary
  - [x] confidence
  - [x] observed_at
  - [x] time_window
  - [x] evidence
  - [x] findings
  - [x] next_actions
  - [x] raw_refs

### 3.3 Implement common input models
- [x] Create shared Pydantic input base model
- [x] Add validators for:
  - [x] time window defaults
  - [x] start/end coherence
  - [x] mutually helpful identifier resolution hooks
- [x] Add optional fields for:
  - [x] site_id
  - [x] client_id
  - [x] client_mac
  - [x] ap_id
  - [x] ap_name
  - [x] ssid
  - [x] switch_id
  - [x] switch_port
  - [x] vlan_id
  - [x] include_raw

### 3.4 Implement error taxonomy
- [x] Create domain error classes
  - [x] bad input
  - [x] dependency timeout
  - [x] dependency unavailable
  - [x] insufficient evidence
  - [x] unsupported provider operation
- [x] Define error-to-result translation helpers

### 3.5 Implement logging helpers
- [x] Create invocation ID generator
- [x] Create structured logging wrapper around stdlib logging
- [x] Add JSON formatter for log output
- [x] Standardize log fields
- [x] Add redaction helpers for secrets / sensitive data

### 3.6 Implement threshold config framework
- [x] Create threshold config schema
- [x] Define default thresholds for:
  - [x] RSSI
  - [x] SNR
  - [x] retry rate
  - [x] channel utilization
  - [x] DHCP latency
  - [x] DNS latency
  - [x] auth timeout
  - [x] CRC errors
  - [x] topology change churn

---

## 4. Phase 2 - Normalized data models

### 4.1 Client and wireless models
- [x] Create `ClientSession`
  - [x] client identifiers
  - [x] AP association
  - [x] RSSI / SNR
  - [x] retry/loss
  - [x] PHY details
  - [x] timestamps
- [x] Create `AccessPointState`
- [x] Create `RadioState`
- [x] Create `RoamEvent`

### 4.2 Wired network models
- [x] Create `SwitchPortState`
- [x] Create `StpSummary`
- [x] Create `MacFlapEvent`

### 4.3 Service models
- [x] Create `DhcpSummary`
- [x] Create `DnsSummary`
- [x] Create `AuthSummary`
- [x] Create `SegmentationSummary`
- [x] Create `PathProbeResult`

### 4.4 Support models
- [x] Create `IncidentRecord`
- [x] Create `ChangeRecord`
- [x] Add source metadata fields to every normalized model
- [x] Add version field to every normalized model

### 4.5 Model tests
- [x] Add validation tests for each model
- [x] Add partial-data tolerance tests
- [x] Add serialization tests
- [x] Add contract tests confirming the Pydantic models serialize to the expected skill output shape

---

## 5. Phase 3 - Adapter interfaces

### 5.1 Wireless controller adapter interface
- [x] Define abstract interface for:
  - [x] get client session
  - [x] get client history
  - [x] get AP state
  - [x] get neighboring AP data
  - [x] get roam events
  - [x] get auth events if controller exposes them
- [x] Define normalized response expectations
- [x] Add timeout/error semantics

### 5.2 Switch adapter interface
- [x] Define abstract interface for:
  - [x] resolve AP to switch port
  - [x] get switch port state
  - [x] get interface counters
  - [x] get STP events
  - [x] get MAC flap events
  - [x] get topology change summaries

### 5.3 DHCP adapter interface
- [x] Define abstract interface for:
  - [x] get DHCP transaction summaries
  - [x] get scope utilization
  - [x] get relay path metadata

### 5.4 DNS adapter interface
- [x] Define abstract interface for:
  - [x] run DNS probes
  - [x] retrieve DNS telemetry if available
  - [x] compare resolver results

### 5.5 Auth adapter interface
- [x] Define abstract interface for:
  - [x] get auth event summaries
  - [x] get RADIUS reachability / timing
  - [x] retrieve categorized auth failures

### 5.6 Probe adapter interface
- [x] Define abstract interface for:
  - [x] run path probes
  - [x] define probe source
  - [x] define destination set
  - [x] capture latency/jitter/loss summaries

### 5.7 Inventory/config adapter interface
- [x] Define abstract interface for:
  - [x] expected VLAN by SSID/client role
  - [x] expected AP uplink characteristics
  - [x] expected policy mappings
  - [x] recent config changes

### 5.8 Syslog/event adapter interface
- [x] Define abstract interface for:
  - [x] fetch events by time window
  - [x] fetch STP related events
  - [x] fetch AP/controller events
  - [x] fetch auth/DHCP/DNS related events

### 5.9 Stub implementations
- [x] Create local stub adapters for all interfaces
- [x] Ensure skills can run in test mode with fixtures only
- [x] Ensure stub-backed skills can run on Debian without vendor-specific dependencies installed

---

## 6. Phase 4 - Normalization and analysis utilities

### 6.1 Normalization helpers
- [x] Create converters from raw wireless data to normalized models
- [x] Create converters from switch data to normalized models
- [x] Create converters from DHCP/DNS/auth data to normalized models
- [x] Create converters for path probe results
- [x] Preserve raw source references

### 6.2 Analysis helper library
- [x] Create threshold comparison helpers
- [x] Create severity scoring helpers
- [x] Create confidence scoring helpers
- [x] Create baseline comparison helpers
- [x] Create recommendation builder helpers

### 6.3 Correlation helpers
- [x] Implement time-window overlap logic
- [x] Implement event correlation scoring
- [x] Implement multi-source evidence aggregation
- [x] Implement ranking of suspected causes

### 6.4 Cache/baseline utilities
- [x] Create cache abstraction
- [x] Add TTL support
- [x] Add optional persistent baseline storage
- [x] Add current vs baseline comparison helpers

### 6.5 Shared test fixtures
- [x] Create representative fixture data for:
  - [x] weak signal client
  - [x] overloaded AP
  - [x] DHCP slowness
  - [x] DNS slowness
  - [x] auth timeout
  - [x] bad AP uplink
  - [x] STP loop symptoms
  - [x] wrong VLAN/policy

---

## 7. Phase 5 - Implement Priority 1 skills

## 7.1 Implement `net.client_health`

### 7.1.1 Input/output plumbing
- [x] Create `skills/net-client-health/SKILL.md`
- [x] Create `skills/net-client-health/net_client_health.py`
- [x] Create client health input model
- [x] Wire shared result model
- [x] Validate client identifier resolution path

### 7.1.2 Data collection
- [x] Query wireless adapter for current client session
- [x] Query historical session data if available
- [x] Resolve associated AP and channel details

### 7.1.3 Analysis logic
- [x] Evaluate RSSI against threshold
- [x] Evaluate SNR against threshold
- [x] Evaluate retry rate
- [x] Evaluate packet loss
- [x] Evaluate disconnect/reconnect frequency
- [x] Evaluate possible sticky-client clues if neighbor/roam context exists

### 7.1.4 Findings and recommendations
- [x] Emit finding codes for each issue type
- [x] Recommend `net.ap_rf_health` for AP/channel issues
- [x] Recommend `net.roaming_analysis` for movement-related issues
- [x] Recommend `net.ap_uplink_health` if AP-side pattern suspected

### 7.1.5 Tests
- [x] Healthy client test
- [x] Weak signal test
- [x] High retry test
- [x] Missing client test
- [x] Adapter timeout test

## 7.2 Implement `net.ap_rf_health`

### 7.2.1 Input/output plumbing
- [x] Create `skills/net-ap-rf-health/SKILL.md`
- [x] Create `skills/net-ap-rf-health/net_ap_rf_health.py`
- [x] Create AP RF health input model

### 7.2.2 Data collection
- [x] Query AP state
- [x] Query radio state
- [x] Query neighbor overlap / surrounding AP data if available
- [x] Query AP event history for radio resets

### 7.2.3 Analysis logic
- [x] Check channel utilization
- [x] Check radio client load
- [x] Check channel width suitability
- [x] Check radio reset frequency
- [x] Check overlap/interference indicators if data exists

### 7.2.4 Findings and recommendations
- [x] Emit channel utilization findings
- [x] Emit overload findings
- [x] Emit radio instability findings
- [x] Recommend client follow-up or site-wide RF follow-up

### 7.2.5 Tests
- [x] Healthy AP test
- [x] High utilization test
- [x] Radio reset test
- [x] Missing AP test

## 7.3 Implement `net.dhcp_path`

### 7.3.1 Input/output plumbing
- [x] Create `skills/net-dhcp-path/SKILL.md`
- [x] Create `skills/net-dhcp-path/net_dhcp_path.py`
- [x] Create DHCP path input model

### 7.3.2 Data collection
- [x] Query DHCP adapter for transaction summaries
- [x] Query scope utilization if available
- [x] Query relay metadata if available

### 7.3.3 Analysis logic
- [x] Evaluate success rate
- [x] Evaluate discover→offer latency
- [x] Evaluate request→ack latency
- [x] Detect missing offer / missing ACK patterns
- [x] Detect scope exhaustion / relay mismatch if data allows

### 7.3.4 Findings and recommendations
- [x] Emit latency findings
- [x] Emit timeout findings
- [x] Emit scope exhaustion findings
- [x] Recommend segmentation or service follow-up as needed

### 7.3.5 Tests
- [x] Healthy DHCP path test
- [x] Slow offer test
- [x] Missing ACK test
- [x] Scope exhaustion warning test

## 7.4 Implement `net.dns_latency`

### 7.4.1 Input/output plumbing
- [x] Create `skills/net-dns-latency/SKILL.md`
- [x] Create `skills/net-dns-latency/net_dns_latency.py`
- [x] Create DNS latency input model

### 7.4.2 Data collection
- [x] Query DNS adapter or run probe-based lookups
- [x] Support resolver-by-resolver results
- [x] Support optional comparison across source locations

### 7.4.3 Analysis logic
- [x] Compute average latency
- [x] Compute timeout rate
- [x] Distinguish slow DNS from general IP reachability issues
- [x] Support sample query set

### 7.4.4 Findings and recommendations
- [x] Emit slow resolver findings
- [x] Emit timeout findings
- [x] Recommend path probe if service reachability is suspect

### 7.4.5 Tests
- [x] Healthy DNS test
- [x] Slow DNS test
- [x] Timeout-heavy DNS test
- [x] Resolver unavailable test

## 7.5 Implement `net.ap_uplink_health`

### 7.5.1 Input/output plumbing
- [x] Create `skills/net-ap-uplink-health/SKILL.md`
- [x] Create `skills/net-ap-uplink-health/net_ap_uplink_health.py`
- [x] Create AP uplink input model

### 7.5.2 Data collection
- [x] Resolve AP to switch and port
- [x] Query port operational status
- [x] Query speed / duplex
- [x] Query error counters
- [x] Query PoE status
- [x] Query flap history
- [x] Query VLAN/trunk/access state

### 7.5.3 Analysis logic
- [x] Detect under-speed link
- [x] Detect CRC or input/output errors
- [x] Detect flapping
- [x] Detect PoE instability
- [x] Detect VLAN mismatch

### 7.5.4 Findings and recommendations
- [x] Emit switch-port problem findings
- [x] Recommend AP RF follow-up if uplink looks clean but user symptoms persist

### 7.5.5 Tests
- [x] Healthy uplink test
- [x] 100 Mbps mismatch test
- [x] CRC-heavy test
- [x] flapping test
- [x] AP-to-port resolution failure test

## 7.6 Implement `net.stp_loop_anomaly`

### 7.6.1 Input/output plumbing
- [x] Create `skills/net-stp-loop-anomaly/SKILL.md`
- [x] Create `skills/net-stp-loop-anomaly/net_stp_loop_anomaly.py`
- [x] Create STP anomaly input model

### 7.6.2 Data collection
- [x] Query STP/topology event summaries
- [x] Query MAC flap events
- [x] Query suspect interface data if available

### 7.6.3 Analysis logic
- [x] Detect unusual topology churn
- [x] Detect root changes
- [x] Detect MAC flap severity
- [x] Surface suspect ports
- [x] Score likely loop severity

### 7.6.4 Findings and recommendations
- [x] Emit topology churn findings
- [x] Emit probable loop findings
- [x] Recommend operator review and targeted switch investigation

### 7.6.5 Tests
- [x] Stable topology test
- [x] topology churn warning test
- [x] MAC flap failure test
- [x] missing switch data test

---

## 8. Phase 6 - Implement Priority 2 skills

## 8.1 Implement `net.roaming_analysis`

### 8.1.1 Data collection
- [x] Create `skills/net-roaming-analysis/SKILL.md`
- [x] Create `skills/net-roaming-analysis/net_roaming_analysis.py`
- [x] Query roam event history
- [x] Query associated client metrics over same window
- [x] Resolve AP transitions

### 8.1.2 Analysis
- [x] Detect excessive roam count
- [x] Detect high roam latency
- [x] Detect failed roams
- [x] Detect sticky-client patterns

### 8.1.3 Recommendations
- [x] Recommend AP RF health
- [x] Recommend client health review
- [x] Recommend site tuning review

### 8.1.4 Tests
- [x] healthy roaming test
- [x] failed roam test
- [x] sticky client test

## 8.2 Implement `net.auth_8021x_radius`

### 8.2.1 Data collection
- [x] Create `skills/net-auth-8021x-radius/SKILL.md`
- [x] Create `skills/net-auth-8021x-radius/net_auth_8021x_radius.py`
- [x] Query auth events
- [x] Query RADIUS RTT/reachability
- [x] Categorize failure causes

### 8.2.2 Analysis
- [x] Compute auth success rate
- [x] Detect timeouts
- [x] Separate credential issues from infra issues
- [x] Detect certificate-related recurring failures if visible

### 8.2.3 Recommendations
- [x] Recommend service path checks
- [x] Recommend credential/policy review
- [x] Recommend segmentation/policy checks

### 8.2.4 Tests
- [x] healthy auth test
- [x] timeout-heavy auth test
- [x] credential failure test
- [x] RADIUS unreachable test

## 8.3 Implement `net.path_probe`

### 8.3.1 Data collection
- [x] Create `skills/net-path-probe/SKILL.md`
- [x] Create `skills/net-path-probe/net_path_probe.py`
- [x] Define probe request model
- [x] Select destinations
- [x] Invoke probe adapter
- [x] Collect latency/jitter/loss summaries

### 8.3.2 Analysis
- [x] Compare internal targets
- [x] Compare optional external target
- [x] Identify failing segment category

### 8.3.3 Recommendations
- [x] Recommend DNS/DHCP/auth follow-up based on failing service
- [x] Recommend AP/client follow-up if only Wi-Fi probe nodes degrade

### 8.3.4 Tests
- [x] clean path test
- [x] internal service degradation test
- [x] site-wide loss test

## 8.4 Implement `net.segmentation_policy`

### 8.4.1 Data collection
- [x] Create `skills/net-segmentation-policy/SKILL.md`
- [x] Create `skills/net-segmentation-policy/net_segmentation_policy.py`
- [x] Query observed client placement
- [x] Query expected VLAN/policy mapping
- [x] Query DHCP scope/gateway alignment

### 8.4.2 Analysis
- [x] Detect expected vs actual VLAN mismatch
- [x] Detect policy mismatch
- [x] Detect wrong gateway/scope alignment

### 8.4.3 Recommendations
- [x] Recommend auth/NAC review
- [x] Recommend DHCP / SSID mapping review

### 8.4.4 Tests
- [x] correct placement test
- [x] wrong VLAN test
- [x] wrong policy group test

---

## 9. Phase 7 - Implement Priority 3 supporting skills

## 9.1 Implement `net.incident_intake`
- [x] Create `skills/net-incident-intake/SKILL.md`
- [x] Create `skills/net-incident-intake/net_incident_intake.py`
- [x] Define incident schema
- [x] Define prompt/parse logic for structured intake
- [ ] Normalize:
  - [x] location
  - [x] time
  - [x] device type
  - [x] affected SSID
  - [x] stationary vs moving
  - [x] wired vs wireless comparison
  - [x] reconnect behavior
- [x] Add tests for common complaint formats

## 9.2 Implement `net.incident_correlation`
- [x] Create `skills/net-incident-correlation/SKILL.md`
- [x] Create `skills/net-incident-correlation/net_incident_correlation.py`
- [x] Accept incident record and time window
- [x] Pull relevant data from prior skills or source adapters
- [x] Rank correlated anomalies
- [x] Emit likely cause clusters
- [x] Add tests for multi-source correlation

## 9.3 Implement `net.change_detection`
- [x] Create `skills/net-change-detection/SKILL.md`
- [x] Create `skills/net-change-detection/net_change_detection.py`
- [x] Query config/inventory change sources
- [x] Query firmware/event changes
- [x] Rank changes by temporal correlation and scope overlap
- [x] Add tests for “recent hardware change likely relevant” scenarios

## 9.4 Implement `net.capture_trigger`
- [x] Create `skills/net-capture-trigger/SKILL.md`
- [x] Create `skills/net-capture-trigger/net_capture_trigger.py`
- [x] Define capture request schema
- [x] Define authorization gating
- [x] Define safe trigger rules
- [x] Emit capture plan output
- [x] Optionally integrate capture execution later
- [x] Add tests for unauthorized vs authorized behavior

---

## 10. Phase 8 - Orchestration and chaining

### 10.1 Shared skill execution wrapper
- [x] Implement common invocation wrapper
- [x] Add logging, timing, and standardized error handling
- [x] Ensure every skill emits `next_actions`

### 10.2 Skill chaining examples
- [x] Implement single-user complaint chain helper
- [x] Implement site-wide slowdown chain helper
- [x] Ensure follow-up suggestions are deterministic and testable

### 10.3 Identifier resolution
- [x] Build helper to resolve:
  - [x] client MAC ↔ client ID
  - [x] AP name ↔ AP ID
  - [x] AP ↔ switch port
- [x] Add caching for common lookups

---

## 11. Phase 9 - Testing and validation

### 11.1 Unit testing
- [x] Add unit tests for all analysis helpers
- [x] Add unit tests for threshold boundaries
- [x] Add unit tests for recommendation builders
- [x] Add unit tests for error translation

### 11.2 Integration testing
- [x] Create end-to-end tests for:
  - [x] weak client RF case
  - [x] overloaded AP case
  - [x] slow DHCP case
  - [x] slow DNS case
  - [x] auth timeout case
  - [x] AP uplink issue case
  - [x] STP loop symptom case
  - [x] wrong VLAN case

### 11.3 Failure mode testing
- [x] Test source adapter timeouts
- [x] Test partial data returns
- [x] Test missing identifiers
- [x] Test contradictory data from multiple sources

### 11.4 Output contract testing
- [x] Verify every skill returns valid `SkillResult`
- [x] Verify every finding code is stable and documented
- [x] Verify all timestamps are ISO-8601
- [x] Verify `next_actions` reference valid skill names

---

## 12. Phase 10 - Documentation and operator usability

### 12.1 Skill docs
- [ ] Document each skill:
  - [ ] purpose
  - [ ] inputs
  - [ ] outputs
  - [ ] dependencies
  - [ ] example invocation
  - [ ] example result
  - [ ] common failure cases

### 12.2 Configuration docs
- [ ] Document provider configuration
- [ ] Document thresholds
- [ ] Document secrets handling
- [ ] Document active-probe restrictions

### 12.3 Troubleshooting playbooks
- [ ] Add “single user complaint” playbook
- [ ] Add “site-wide slowdown” playbook
- [ ] Add “auth issue” playbook
- [ ] Add “recent hardware change” playbook

### 12.4 Findings code registry
- [ ] Create registry of finding codes
- [ ] Document severity semantics
- [ ] Document expected operator actions per code

---

## 13. Nice-to-have enhancements after v1

- [ ] Historical baseline anomaly scoring
- [ ] Dashboard or summary report rendering
- [ ] Multi-site comparative health summary
- [ ] Suggested remediation text generation
- [ ] Controlled auto-remediation hooks behind strict gates
- [ ] Vendor-specific optimization modules
- [ ] Deeper packet-capture workflow integration

---

## 14. Definition of done

The implementation is done when:

- [ ] All Priority 1 skills are fully implemented and tested
- [ ] Priority 2 skills are implemented and tested
- [ ] Shared schemas and adapters are stable
- [ ] All skills emit standardized results
- [ ] Failure modes are handled cleanly
- [ ] Example playbooks are documented
- [ ] Copilot can execute work item by work item without needing the architecture reinvented midstream
