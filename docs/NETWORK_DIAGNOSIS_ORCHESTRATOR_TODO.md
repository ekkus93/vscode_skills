# NETWORK_DIAGNOSIS_ORCHESTRATOR_TODO.md

## 1. Overview

This TODO list breaks the orchestrator spec into practical implementation tasks for Github Copilot.

The goal is to build a top-level `net.diagnose_incident` skill that controls the lower-level network skills in a disciplined and testable way.

---

## 2. Phase 0 - Module scaffolding

### 2.1 Create orchestrator package structure
- [x] Create `nettools/orchestrator/`
- [ ] Create files:
  - [x] `diagnose_incident.py`
  - [x] `playbooks.py`
  - [ ] `branch_rules.py`
  - [x] `state.py`
  - [ ] `scoring.py`
  - [ ] `stop_conditions.py`
  - [ ] `sampling.py`
  - [ ] `report_builder.py`
  - [x] `execution.py`
  - [ ] `config.py`

### 2.2 Create test structure
- [ ] Create:
  - [ ] `tests/unit/orchestrator/`
  - [ ] `tests/integration/orchestrator/`
  - [ ] `tests/fixtures/orchestrator/`

### 2.3 Documentation scaffolding
- [ ] Add orchestrator README section
- [ ] Add playbook documentation stub
- [ ] Add configuration documentation stub

---

## 3. Phase 1 - Core data structures

### 3.1 Define incident classification enums
- [x] Create incident type enum
  - [x] `single_client`
  - [x] `single_area`
  - [x] `site_wide`
  - [x] `auth_or_onboarding`
  - [x] `intermittent_unclear`
  - [x] `unknown_scope`

### 3.2 Define diagnostic domain enums
- [x] Create domain enum
  - [x] `single_client_rf`
  - [x] `single_ap_rf`
  - [x] `roaming_issue`
  - [x] `dhcp_issue`
  - [x] `dns_issue`
  - [x] `auth_issue`
  - [x] `ap_uplink_issue`
  - [x] `l2_topology_issue`
  - [x] `segmentation_policy_issue`
  - [x] `site_wide_internal_lan_issue`
  - [x] `wan_or_external_issue`
  - [x] `unknown`

### 3.3 Create incident state model
- [x] Implement `IncidentState`
  - [x] incident_id
  - [x] created_at
  - [x] updated_at
  - [x] incident_type
  - [x] playbook_used
  - [x] status
  - [x] scope_summary
  - [x] suspected_domains
  - [x] eliminated_domains
  - [x] domain_scores
  - [x] evidence_log
  - [x] skill_trace
  - [x] dependency_failures
  - [x] recommended_next_skill
  - [x] stop_reason

### 3.4 Create supporting state models
- [x] Implement `DomainScore`
- [x] Implement `ExecutionRecord`
- [x] Implement `EvidenceEntry`
- [x] Implement `StopReason`
- [x] Implement `RankedCause`
- [x] Implement `DiagnosisReport`

### 3.5 Model tests
- [x] Add serialization tests
- [x] Add validation tests
- [x] Add default-state tests
- [x] Add state update tests

---

## 4. Phase 2 - Playbook definitions

### 4.1 Define playbook model
- [x] Create `PlaybookDefinition`
  - [x] playbook name
  - [x] incident types supported
  - [x] default sequence
  - [x] required skills
  - [x] optional skills
  - [x] allowed branch transitions
  - [x] stop settings
  - [x] sampling settings

### 4.2 Implement initial playbooks
- [x] Implement `single_client_wifi_issue`
- [x] Implement `area_based_wifi_issue`
- [x] Implement `site_wide_internal_slowdown`
- [x] Implement `auth_or_onboarding_issue`
- [x] Implement `unclear_general_network_issue`

### 4.3 Playbook validation
- [x] Validate that all referenced skills exist
- [x] Validate that all branch transitions are legal
- [x] Validate stop settings
- [x] Validate sampling settings

### 4.4 Playbook tests
- [x] Test playbook loading
- [x] Test playbook skill order
- [ ] Test allowed transitions
- [x] Test invalid playbook definitions fail cleanly

---

## 5. Phase 3 - Intake classification and playbook selection

### 5.1 Build incident classification logic
- [x] Accept normalized intake result
- [x] Infer affected scope from intake fields
- [x] Detect auth/onboarding patterns
- [x] Detect likely site-wide patterns
- [x] Detect likely single-area patterns
- [x] Handle sparse or incomplete intake data

### 5.2 Build playbook selection logic
- [x] Map incident type to default playbook
- [x] Allow explicit playbook override
- [x] Allow config-driven selection rules
- [x] Record selection rationale in incident state

### 5.3 Tests
- [x] single-user complaint classification test
- [x] area-based complaint classification test
- [x] site-wide complaint classification test
- [x] auth/onboarding complaint classification test
- [x] ambiguous complaint classification test

---

## 6. Phase 4 - Skill execution wrapper

### 6.1 Implement common skill invocation wrapper
- [ ] Create function to invoke primitive skills
- [ ] Add invocation ID
- [ ] Add timing measurement
- [ ] Add structured logging
- [ ] Capture raw result
- [ ] Normalize wrapper return record

### 6.2 Error handling
- [ ] Catch dependency failures
- [ ] Catch timeouts
- [ ] Catch schema validation errors
- [ ] Catch unsupported-skill errors
- [ ] Convert failures into execution records

### 6.3 State integration
- [ ] Append skill trace
- [ ] Append evidence summary
- [ ] Append dependency failures
- [ ] Update updated_at timestamp

### 6.4 Tests
- [ ] successful invocation test
- [ ] timeout test
- [ ] dependency unavailable test
- [ ] malformed result test
- [ ] repeated invocation handling test

---

## 7. Phase 5 - Branching engine

### 7.1 Create branch rule model
- [x] Define branch rule structure
  - [x] source skill
  - [x] triggering findings / conditions
  - [x] candidate next skills
  - [x] score adjustments
  - [x] branch priority

### 7.2 Implement explicit branch rules
- [x] Rules from `net.client_health`
- [x] Rules from `net.ap_rf_health`
- [x] Rules from `net.roaming_analysis`
- [x] Rules from `net.dhcp_path`
- [x] Rules from `net.dns_latency`
- [x] Rules from `net.auth_8021x_radius`
- [x] Rules from `net.ap_uplink_health`
- [x] Rules from `net.stp_loop_anomaly`
- [x] Rules from `net.path_probe`
- [x] Rules from `net.segmentation_policy`

### 7.3 Branch selection logic
- [x] Combine playbook ordering with branch rules
- [x] Respect allowed transitions
- [x] Avoid loops
- [x] Avoid exhausted skills
- [x] Prefer highest-value next step
- [x] Respect dependency failures

### 7.4 Tests
- [x] branch from client RF degradation test
- [x] branch from clean RF to service checks test
- [x] branch from DHCP failure to segmentation/auth follow-up test
- [ ] branch from STP anomaly to stop-early path test
- [x] illegal transition prevention test

---

## 8. Phase 6 - Hypothesis scoring engine

### 8.1 Implement domain scoring structures
- [x] Initialize all diagnostic domains
- [x] Add score values
- [x] Add confidence labels
- [x] Track supporting and contradicting findings

### 8.2 Define score update rules
- [x] Map finding codes to domain score changes
- [x] Support positive evidence
- [x] Support negative evidence
- [x] Support cross-domain suppression
- [x] Support multi-domain ambiguity

### 8.3 Implement confidence mapping
- [x] configurable thresholds for low/medium/high
- [x] deterministic score-to-confidence mapping

### 8.4 Tests
- [x] DNS issue score increase test
- [x] RF issue score decrease after clean AP/client data test
- [x] AP uplink issue score increase from CRC/flap findings test
- [x] L2 issue score increase from MAC flap findings test
- [x] mixed evidence ambiguity test

---

## 9. Phase 7 - Stop condition engine

### 9.1 Implement stop condition checks
- [x] high-confidence single-domain stop
- [x] bounded ambiguity stop
- [x] skill budget exhausted stop
- [x] elapsed-time budget stop
- [x] branch-depth exhausted stop
- [x] blocked-by-dependencies stop
- [x] no-new-information stop

### 9.2 Implement stop reason recording
- [x] code
- [x] message
- [x] supporting context
- [x] uncertainty summary

### 9.3 Tests
- [x] high-confidence stop test
- [x] ambiguity stop test
- [x] budget stop test
- [x] dependency-block stop test
- [x] no-progress stop test

---

## 10. Phase 8 - Sampling strategy

### 10.1 Implement sampling models
- [ ] define AP sampling inputs
- [ ] define client sampling inputs
- [x] define comparison/control sample support

### 10.2 Implement deterministic sampling logic
- [ ] representative AP selection
- [ ] representative client selection
- [ ] inclusion of changed hardware where relevant
- [x] inclusion of control sample where possible

Notes:
- site-wide sampling now supports implicit comparison AP reservation and implicit comparison area reservation when evidence contains stronger area coverage than AP coverage.
- operators can now explicitly seed area sampling with candidate areas and override comparison-area selection with explicit comparison areas.
- client, AP, and area sampling now all use the same primary-candidate plus explicit-control and implicit-control pool structure.
- report payload sampling state is now validated through a shared sampling-summary model instead of being assembled as an untyped dict.
- the top-level `diagnosis_report` payload is now built from a typed public report model, including validated skill-trace, evidence-summary, stop-reason, confidence, and sampling-summary sections.
- the older state-level report model has been renamed to `IncidentStateReport` so it no longer overlaps semantically with the public `DiagnoseIncidentReport` payload model.

### 10.3 Playbook integration
- [ ] site-wide playbook sampling defaults
- [ ] area-based playbook sampling defaults
- [ ] single-client bypass logic

### 10.4 Tests
- [ ] site-wide sample size test
- [ ] area-based sample size test
- [ ] deterministic sample ordering test

---

## 11. Phase 9 - Main orchestrator loop

### 11.1 Implement `net.diagnose_incident`
- [x] create/load incident state
- [x] call `net.incident_intake` if needed
- [x] classify incident
- [x] select playbook
- [x] execute first skill
- [x] enter controlled loop
- [x] update state after each skill
- [x] evaluate stop conditions after each step
- [x] branch or continue
- [ ] finalize report

### 11.2 Prevent uncontrolled execution
- [ ] enforce skill budget
- [ ] enforce branch budget
- [ ] prevent same-skill runaway repeats
- [ ] reject skills outside playbook/allowed transitions

### 11.3 Handle partial investigations
- [ ] support blocked state
- [ ] support unresolved state
- [ ] support replay/debug mode

### 11.4 Tests
- [ ] single-client end-to-end path test
- [ ] site-wide end-to-end path test
- [ ] auth/onboarding end-to-end path test
- [ ] unresolved ambiguous end-to-end test
- [ ] blocked dependency end-to-end test

---

## 12. Phase 10 - Report builder

### 12.1 Implement final report assembly
- [ ] compute top-ranked causes
- [ ] collect eliminated domains
- [ ] summarize evidence
- [ ] include skill trace
- [ ] include dependency failures
- [ ] include stop reason
- [ ] include confidence

### 12.2 Implement human action generator
- [ ] generate evidence-linked actions
- [ ] prefer narrow, operationally useful actions
- [ ] avoid vague actions
- [ ] include specific APs / ports / services when available

### 12.3 Implement follow-up skill recommendations
- [ ] suggest next primitive skills if unresolved
- [ ] suggest capture trigger only when authorized and useful

### 12.4 Tests
- [ ] ranked cause formatting test
- [ ] eliminated domain formatting test
- [ ] human action specificity test
- [ ] unresolved report formatting test

---

## 13. Phase 11 - Traceability and observability

### 13.1 Investigation trace logging
- [ ] log playbook selection
- [ ] log branch decisions
- [ ] log score updates
- [ ] log stop-condition checks
- [ ] log final stop rationale

### 13.2 Audit trail persistence
- [ ] support serializing final incident state
- [ ] support storing execution records
- [ ] support replay from trace for debugging

### 13.3 Metrics
- [ ] count invocations by playbook
- [ ] count stop reasons
- [ ] count diagnosis domains by outcome
- [ ] record average skill count per investigation

### 13.4 Tests
- [ ] trace completeness test
- [ ] replayability test
- [ ] log redaction test

---

## 14. Phase 12 - Configuration and policy controls

### 14.1 Orchestrator config schema
- [ ] playbook mapping
- [ ] branch rules
- [ ] stop thresholds
- [ ] domain score thresholds
- [ ] investigation budgets
- [ ] sampling defaults
- [ ] allowed optional branches

### 14.2 Policy controls
- [ ] gate active probes if needed
- [ ] gate capture triggers
- [ ] gate external resolver comparisons
- [ ] gate optional expensive branches

### 14.3 Tests
- [ ] default config load test
- [ ] invalid config test
- [ ] policy-gated branch suppression test

---

## 15. Phase 13 - Integration with primitive skills

### 15.1 Primitive skill contract validation
- [ ] verify required fields from all dependent skills
- [ ] validate `next_actions` format
- [ ] validate finding code stability
- [ ] validate result status compatibility

### 15.2 Skill adapter layer if needed
- [ ] create compatibility wrappers for primitive skills
- [ ] normalize legacy outputs if required

### 15.3 Tests
- [ ] primitive skill contract mismatch test
- [ ] compatibility wrapper test

---

## 16. Phase 14 - Scenario fixtures

### 16.1 Create canonical scenario fixtures
- [ ] weak single-client RF
- [ ] overloaded AP / dense RF area
- [ ] slow DHCP
- [ ] slow DNS
- [ ] auth timeout
- [ ] AP uplink CRC/flap issue
- [ ] STP loop / MAC flap instability
- [ ] wrong VLAN / policy placement
- [ ] mixed evidence two-domain ambiguity
- [ ] dependency failure scenario

### 16.2 Build replay scenarios
- [ ] single-client scenario
- [ ] area-based scenario
- [ ] site-wide slowdown scenario
- [ ] onboarding/auth scenario
- [ ] ambiguous scenario

---

## 17. Phase 15 - Documentation and operator playbooks

### 17.1 Skill documentation
- [ ] document `net.diagnose_incident`
  - [ ] purpose
  - [ ] inputs
  - [ ] state model
  - [ ] outputs
  - [ ] playbook selection
  - [ ] stop conditions
  - [ ] example traces

### 17.2 Operator runbook docs
- [ ] document single-client troubleshooting path
- [ ] document area-based troubleshooting path
- [ ] document site-wide troubleshooting path
- [ ] document auth/onboarding troubleshooting path

### 17.3 Developer docs
- [ ] how to add a new playbook
- [ ] how to add a new diagnostic domain
- [ ] how to add a new branch rule
- [ ] how to adjust score weights safely

---

## 18. Nice-to-have enhancements after v1

- [ ] learning-based ranking of branch usefulness
- [ ] historical similarity lookup for repeated incidents
- [ ] dashboard-style rendering of investigation graph
- [ ] optional multi-incident clustering
- [ ] operator approval workflow before expensive or invasive steps

---

## 19. Definition of done

The orchestrator is done when:

- [ ] it can select a correct playbook from intake data
- [ ] it can run a controlled investigation loop
- [ ] it can branch deterministically
- [ ] it can stop appropriately
- [ ] it can rank likely root causes
- [ ] it can generate actionable final reports
- [ ] all major scenarios have integration tests
- [ ] investigation traces are reproducible
