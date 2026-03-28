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
- [ ] Create converters from raw wireless data to normalized models
- [ ] Create converters from switch data to normalized models
- [ ] Create converters from DHCP/DNS/auth data to normalized models
- [ ] Create converters for path probe results
- [ ] Preserve raw source references

### 6.2 Analysis helper library
- [ ] Create threshold comparison helpers
- [ ] Create severity scoring helpers
- [ ] Create confidence scoring helpers
- [ ] Create baseline comparison helpers
- [ ] Create recommendation builder helpers

### 6.3 Correlation helpers
- [ ] Implement time-window overlap logic
- [ ] Implement event correlation scoring
- [ ] Implement multi-source evidence aggregation
- [ ] Implement ranking of suspected causes

### 6.4 Cache/baseline utilities
- [ ] Create cache abstraction
- [ ] Add TTL support
- [ ] Add optional persistent baseline storage
- [ ] Add current vs baseline comparison helpers

### 6.5 Shared test fixtures
- [ ] Create representative fixture data for:
  - [ ] weak signal client
  - [ ] overloaded AP
  - [ ] DHCP slowness
  - [ ] DNS slowness
  - [ ] auth timeout
  - [ ] bad AP uplink
  - [ ] STP loop symptoms
  - [ ] wrong VLAN/policy

---

## 7. Phase 5 - Implement Priority 1 skills

## 7.1 Implement `net.client_health`

### 7.1.1 Input/output plumbing
- [ ] Create `skills/net-client-health/SKILL.md`
- [ ] Create `skills/net-client-health/net_client_health.py`
- [ ] Create client health input model
- [ ] Wire shared result model
- [ ] Validate client identifier resolution path

### 7.1.2 Data collection
- [ ] Query wireless adapter for current client session
- [ ] Query historical session data if available
- [ ] Resolve associated AP and channel details

### 7.1.3 Analysis logic
- [ ] Evaluate RSSI against threshold
- [ ] Evaluate SNR against threshold
- [ ] Evaluate retry rate
- [ ] Evaluate packet loss
- [ ] Evaluate disconnect/reconnect frequency
- [ ] Evaluate possible sticky-client clues if neighbor/roam context exists

### 7.1.4 Findings and recommendations
- [ ] Emit finding codes for each issue type
- [ ] Recommend `net.ap_rf_health` for AP/channel issues
- [ ] Recommend `net.roaming_analysis` for movement-related issues
- [ ] Recommend `net.ap_uplink_health` if AP-side pattern suspected

### 7.1.5 Tests
- [ ] Healthy client test
- [ ] Weak signal test
- [ ] High retry test
- [ ] Missing client test
- [ ] Adapter timeout test

## 7.2 Implement `net.ap_rf_health`

### 7.2.1 Input/output plumbing
- [ ] Create `skills/net-ap-rf-health/SKILL.md`
- [ ] Create `skills/net-ap-rf-health/net_ap_rf_health.py`
- [ ] Create AP RF health input model

### 7.2.2 Data collection
- [ ] Query AP state
- [ ] Query radio state
- [ ] Query neighbor overlap / surrounding AP data if available
- [ ] Query AP event history for radio resets

### 7.2.3 Analysis logic
- [ ] Check channel utilization
- [ ] Check radio client load
- [ ] Check channel width suitability
- [ ] Check radio reset frequency
- [ ] Check overlap/interference indicators if data exists

### 7.2.4 Findings and recommendations
- [ ] Emit channel utilization findings
- [ ] Emit overload findings
- [ ] Emit radio instability findings
- [ ] Recommend client follow-up or site-wide RF follow-up

### 7.2.5 Tests
- [ ] Healthy AP test
- [ ] High utilization test
- [ ] Radio reset test
- [ ] Missing AP test

## 7.3 Implement `net.dhcp_path`

### 7.3.1 Input/output plumbing
- [ ] Create `skills/net-dhcp-path/SKILL.md`
- [ ] Create `skills/net-dhcp-path/net_dhcp_path.py`
- [ ] Create DHCP path input model

### 7.3.2 Data collection
- [ ] Query DHCP adapter for transaction summaries
- [ ] Query scope utilization if available
- [ ] Query relay metadata if available

### 7.3.3 Analysis logic
- [ ] Evaluate success rate
- [ ] Evaluate discover→offer latency
- [ ] Evaluate request→ack latency
- [ ] Detect missing offer / missing ACK patterns
- [ ] Detect scope exhaustion / relay mismatch if data allows

### 7.3.4 Findings and recommendations
- [ ] Emit latency findings
- [ ] Emit timeout findings
- [ ] Emit scope exhaustion findings
- [ ] Recommend segmentation or service follow-up as needed

### 7.3.5 Tests
- [ ] Healthy DHCP path test
- [ ] Slow offer test
- [ ] Missing ACK test
- [ ] Scope exhaustion warning test

## 7.4 Implement `net.dns_latency`

### 7.4.1 Input/output plumbing
- [ ] Create `skills/net-dns-latency/SKILL.md`
- [ ] Create `skills/net-dns-latency/net_dns_latency.py`
- [ ] Create DNS latency input model

### 7.4.2 Data collection
- [ ] Query DNS adapter or run probe-based lookups
- [ ] Support resolver-by-resolver results
- [ ] Support optional comparison across source locations

### 7.4.3 Analysis logic
- [ ] Compute average latency
- [ ] Compute timeout rate
- [ ] Distinguish slow DNS from general IP reachability issues
- [ ] Support sample query set

### 7.4.4 Findings and recommendations
- [ ] Emit slow resolver findings
- [ ] Emit timeout findings
- [ ] Recommend path probe if service reachability is suspect

### 7.4.5 Tests
- [ ] Healthy DNS test
- [ ] Slow DNS test
- [ ] Timeout-heavy DNS test
- [ ] Resolver unavailable test

## 7.5 Implement `net.ap_uplink_health`

### 7.5.1 Input/output plumbing
- [ ] Create `skills/net-ap-uplink-health/SKILL.md`
- [ ] Create `skills/net-ap-uplink-health/net_ap_uplink_health.py`
- [ ] Create AP uplink input model

### 7.5.2 Data collection
- [ ] Resolve AP to switch and port
- [ ] Query port operational status
- [ ] Query speed / duplex
- [ ] Query error counters
- [ ] Query PoE status
- [ ] Query flap history
- [ ] Query VLAN/trunk/access state

### 7.5.3 Analysis logic
- [ ] Detect under-speed link
- [ ] Detect CRC or input/output errors
- [ ] Detect flapping
- [ ] Detect PoE instability
- [ ] Detect VLAN mismatch

### 7.5.4 Findings and recommendations
- [ ] Emit switch-port problem findings
- [ ] Recommend AP RF follow-up if uplink looks clean but user symptoms persist

### 7.5.5 Tests
- [ ] Healthy uplink test
- [ ] 100 Mbps mismatch test
- [ ] CRC-heavy test
- [ ] flapping test
- [ ] AP-to-port resolution failure test

## 7.6 Implement `net.stp_loop_anomaly`

### 7.6.1 Input/output plumbing
- [ ] Create `skills/net-stp-loop-anomaly/SKILL.md`
- [ ] Create `skills/net-stp-loop-anomaly/net_stp_loop_anomaly.py`
- [ ] Create STP anomaly input model

### 7.6.2 Data collection
- [ ] Query STP/topology event summaries
- [ ] Query MAC flap events
- [ ] Query suspect interface data if available

### 7.6.3 Analysis logic
- [ ] Detect unusual topology churn
- [ ] Detect root changes
- [ ] Detect MAC flap severity
- [ ] Surface suspect ports
- [ ] Score likely loop severity

### 7.6.4 Findings and recommendations
- [ ] Emit topology churn findings
- [ ] Emit probable loop findings
- [ ] Recommend operator review and targeted switch investigation

### 7.6.5 Tests
- [ ] Stable topology test
- [ ] topology churn warning test
- [ ] MAC flap failure test
- [ ] missing switch data test

---

## 8. Phase 6 - Implement Priority 2 skills

## 8.1 Implement `net.roaming_analysis`

### 8.1.1 Data collection
- [ ] Create `skills/net-roaming-analysis/SKILL.md`
- [ ] Create `skills/net-roaming-analysis/net_roaming_analysis.py`
- [ ] Query roam event history
- [ ] Query associated client metrics over same window
- [ ] Resolve AP transitions

### 8.1.2 Analysis
- [ ] Detect excessive roam count
- [ ] Detect high roam latency
- [ ] Detect failed roams
- [ ] Detect sticky-client patterns

### 8.1.3 Recommendations
- [ ] Recommend AP RF health
- [ ] Recommend client health review
- [ ] Recommend site tuning review

### 8.1.4 Tests
- [ ] healthy roaming test
- [ ] failed roam test
- [ ] sticky client test

## 8.2 Implement `net.auth_8021x_radius`

### 8.2.1 Data collection
- [ ] Create `skills/net-auth-8021x-radius/SKILL.md`
- [ ] Create `skills/net-auth-8021x-radius/net_auth_8021x_radius.py`
- [ ] Query auth events
- [ ] Query RADIUS RTT/reachability
- [ ] Categorize failure causes

### 8.2.2 Analysis
- [ ] Compute auth success rate
- [ ] Detect timeouts
- [ ] Separate credential issues from infra issues
- [ ] Detect certificate-related recurring failures if visible

### 8.2.3 Recommendations
- [ ] Recommend service path checks
- [ ] Recommend credential/policy review
- [ ] Recommend segmentation/policy checks

### 8.2.4 Tests
- [ ] healthy auth test
- [ ] timeout-heavy auth test
- [ ] credential failure test
- [ ] RADIUS unreachable test

## 8.3 Implement `net.path_probe`

### 8.3.1 Data collection
- [ ] Create `skills/net-path-probe/SKILL.md`
- [ ] Create `skills/net-path-probe/net_path_probe.py`
- [ ] Define probe request model
- [ ] Select destinations
- [ ] Invoke probe adapter
- [ ] Collect latency/jitter/loss summaries

### 8.3.2 Analysis
- [ ] Compare internal targets
- [ ] Compare optional external target
- [ ] Identify failing segment category

### 8.3.3 Recommendations
- [ ] Recommend DNS/DHCP/auth follow-up based on failing service
- [ ] Recommend AP/client follow-up if only Wi-Fi probe nodes degrade

### 8.3.4 Tests
- [ ] clean path test
- [ ] internal service degradation test
- [ ] site-wide loss test

## 8.4 Implement `net.segmentation_policy`

### 8.4.1 Data collection
- [ ] Create `skills/net-segmentation-policy/SKILL.md`
- [ ] Create `skills/net-segmentation-policy/net_segmentation_policy.py`
- [ ] Query observed client placement
- [ ] Query expected VLAN/policy mapping
- [ ] Query DHCP scope/gateway alignment

### 8.4.2 Analysis
- [ ] Detect expected vs actual VLAN mismatch
- [ ] Detect policy mismatch
- [ ] Detect wrong gateway/scope alignment

### 8.4.3 Recommendations
- [ ] Recommend auth/NAC review
- [ ] Recommend DHCP / SSID mapping review

### 8.4.4 Tests
- [ ] correct placement test
- [ ] wrong VLAN test
- [ ] wrong policy group test

---

## 9. Phase 7 - Implement Priority 3 supporting skills

## 9.1 Implement `net.incident_intake`
- [ ] Create `skills/net-incident-intake/SKILL.md`
- [ ] Create `skills/net-incident-intake/net_incident_intake.py`
- [ ] Define incident schema
- [ ] Define prompt/parse logic for structured intake
- [ ] Normalize:
  - [ ] location
  - [ ] time
  - [ ] device type
  - [ ] affected SSID
  - [ ] stationary vs moving
  - [ ] wired vs wireless comparison
  - [ ] reconnect behavior
- [ ] Add tests for common complaint formats

## 9.2 Implement `net.incident_correlation`
- [ ] Create `skills/net-incident-correlation/SKILL.md`
- [ ] Create `skills/net-incident-correlation/net_incident_correlation.py`
- [ ] Accept incident record and time window
- [ ] Pull relevant data from prior skills or source adapters
- [ ] Rank correlated anomalies
- [ ] Emit likely cause clusters
- [ ] Add tests for multi-source correlation

## 9.3 Implement `net.change_detection`
- [ ] Create `skills/net-change-detection/SKILL.md`
- [ ] Create `skills/net-change-detection/net_change_detection.py`
- [ ] Query config/inventory change sources
- [ ] Query firmware/event changes
- [ ] Rank changes by temporal correlation and scope overlap
- [ ] Add tests for “recent hardware change likely relevant” scenarios

## 9.4 Implement `net.capture_trigger`
- [ ] Create `skills/net-capture-trigger/SKILL.md`
- [ ] Create `skills/net-capture-trigger/net_capture_trigger.py`
- [ ] Define capture request schema
- [ ] Define authorization gating
- [ ] Define safe trigger rules
- [ ] Emit capture plan output
- [ ] Optionally integrate capture execution later
- [ ] Add tests for unauthorized vs authorized behavior

---

## 10. Phase 8 - Orchestration and chaining

### 10.1 Shared skill execution wrapper
- [ ] Implement common invocation wrapper
- [ ] Add logging, timing, and standardized error handling
- [ ] Ensure every skill emits `next_actions`

### 10.2 Skill chaining examples
- [ ] Implement single-user complaint chain helper
- [ ] Implement site-wide slowdown chain helper
- [ ] Ensure follow-up suggestions are deterministic and testable

### 10.3 Identifier resolution
- [ ] Build helper to resolve:
  - [ ] client MAC ↔ client ID
  - [ ] AP name ↔ AP ID
  - [ ] AP ↔ switch port
- [ ] Add caching for common lookups

---

## 11. Phase 9 - Testing and validation

### 11.1 Unit testing
- [ ] Add unit tests for all analysis helpers
- [ ] Add unit tests for threshold boundaries
- [ ] Add unit tests for recommendation builders
- [ ] Add unit tests for error translation

### 11.2 Integration testing
- [ ] Create end-to-end tests for:
  - [ ] weak client RF case
  - [ ] overloaded AP case
  - [ ] slow DHCP case
  - [ ] slow DNS case
  - [ ] auth timeout case
  - [ ] AP uplink issue case
  - [ ] STP loop symptom case
  - [ ] wrong VLAN case

### 11.3 Failure mode testing
- [ ] Test source adapter timeouts
- [ ] Test partial data returns
- [ ] Test missing identifiers
- [ ] Test contradictory data from multiple sources

### 11.4 Output contract testing
- [ ] Verify every skill returns valid `SkillResult`
- [ ] Verify every finding code is stable and documented
- [ ] Verify all timestamps are ISO-8601
- [ ] Verify `next_actions` reference valid skill names

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
