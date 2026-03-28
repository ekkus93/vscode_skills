# NETWORK_DIAGNOSIS_ORCHESTRATOR_TODO.md

## 1. Overview

This TODO list breaks the orchestrator spec into practical implementation tasks for Github Copilot.

The goal is to build a top-level `net.diagnose_incident` skill that controls the lower-level network skills in a disciplined and testable way.

---

## 2. Phase 0 - Module scaffolding

### 2.1 Create orchestrator package structure
- [ ] Create `nettools/orchestrator/`
- [ ] Create files:
  - [ ] `diagnose_incident.py`
  - [ ] `playbooks.py`
  - [ ] `branch_rules.py`
  - [ ] `state.py`
  - [ ] `scoring.py`
  - [ ] `stop_conditions.py`
  - [ ] `sampling.py`
  - [ ] `report_builder.py`
  - [ ] `execution.py`
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
- [ ] Create incident type enum
  - [ ] `single_client`
  - [ ] `single_area`
  - [ ] `site_wide`
  - [ ] `auth_or_onboarding`
  - [ ] `intermittent_unclear`
  - [ ] `unknown_scope`

### 3.2 Define diagnostic domain enums
- [ ] Create domain enum
  - [ ] `single_client_rf`
  - [ ] `single_ap_rf`
  - [ ] `roaming_issue`
  - [ ] `dhcp_issue`
  - [ ] `dns_issue`
  - [ ] `auth_issue`
  - [ ] `ap_uplink_issue`
  - [ ] `l2_topology_issue`
  - [ ] `segmentation_policy_issue`
  - [ ] `site_wide_internal_lan_issue`
  - [ ] `wan_or_external_issue`
  - [ ] `unknown`

### 3.3 Create incident state model
- [ ] Implement `IncidentState`
  - [ ] incident_id
  - [ ] created_at
  - [ ] updated_at
  - [ ] incident_type
  - [ ] playbook_used
  - [ ] status
  - [ ] scope_summary
  - [ ] suspected_domains
  - [ ] eliminated_domains
  - [ ] domain_scores
  - [ ] evidence_log
  - [ ] skill_trace
  - [ ] dependency_failures
  - [ ] recommended_next_skill
  - [ ] stop_reason

### 3.4 Create supporting state models
- [ ] Implement `DomainScore`
- [ ] Implement `ExecutionRecord`
- [ ] Implement `EvidenceEntry`
- [ ] Implement `StopReason`
- [ ] Implement `RankedCause`
- [ ] Implement `DiagnosisReport`

### 3.5 Model tests
- [ ] Add serialization tests
- [ ] Add validation tests
- [ ] Add default-state tests
- [ ] Add state update tests

---

## 4. Phase 2 - Playbook definitions

### 4.1 Define playbook model
- [ ] Create `PlaybookDefinition`
  - [ ] playbook name
  - [ ] incident types supported
  - [ ] default sequence
  - [ ] required skills
  - [ ] optional skills
  - [ ] allowed branch transitions
  - [ ] stop settings
  - [ ] sampling settings

### 4.2 Implement initial playbooks
- [ ] Implement `single_client_wifi_issue`
- [ ] Implement `area_based_wifi_issue`
- [ ] Implement `site_wide_internal_slowdown`
- [ ] Implement `auth_or_onboarding_issue`
- [ ] Implement `unclear_general_network_issue`

### 4.3 Playbook validation
- [ ] Validate that all referenced skills exist
- [ ] Validate that all branch transitions are legal
- [ ] Validate stop settings
- [ ] Validate sampling settings

### 4.4 Playbook tests
- [ ] Test playbook loading
- [ ] Test playbook skill order
- [ ] Test allowed transitions
- [ ] Test invalid playbook definitions fail cleanly

---

## 5. Phase 3 - Intake classification and playbook selection

### 5.1 Build incident classification logic
- [ ] Accept normalized intake result
- [ ] Infer affected scope from intake fields
- [ ] Detect auth/onboarding patterns
- [ ] Detect likely site-wide patterns
- [ ] Detect likely single-area patterns
- [ ] Handle sparse or incomplete intake data

### 5.2 Build playbook selection logic
- [ ] Map incident type to default playbook
- [ ] Allow explicit playbook override
- [ ] Allow config-driven selection rules
- [ ] Record selection rationale in incident state

### 5.3 Tests
- [ ] single-user complaint classification test
- [ ] area-based complaint classification test
- [ ] site-wide complaint classification test
- [ ] auth/onboarding complaint classification test
- [ ] ambiguous complaint classification test

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
- [ ] Define branch rule structure
  - [ ] source skill
  - [ ] triggering findings / conditions
  - [ ] candidate next skills
  - [ ] score adjustments
  - [ ] branch priority

### 7.2 Implement explicit branch rules
- [ ] Rules from `net.client_health`
- [ ] Rules from `net.ap_rf_health`
- [ ] Rules from `net.roaming_analysis`
- [ ] Rules from `net.dhcp_path`
- [ ] Rules from `net.dns_latency`
- [ ] Rules from `net.auth_8021x_radius`
- [ ] Rules from `net.ap_uplink_health`
- [ ] Rules from `net.stp_loop_anomaly`
- [ ] Rules from `net.path_probe`
- [ ] Rules from `net.segmentation_policy`

### 7.3 Branch selection logic
- [ ] Combine playbook ordering with branch rules
- [ ] Respect allowed transitions
- [ ] Avoid loops
- [ ] Avoid exhausted skills
- [ ] Prefer highest-value next step
- [ ] Respect dependency failures

### 7.4 Tests
- [ ] branch from client RF degradation test
- [ ] branch from clean RF to service checks test
- [ ] branch from DHCP failure to segmentation/auth follow-up test
- [ ] branch from STP anomaly to stop-early path test
- [ ] illegal transition prevention test

---

## 8. Phase 6 - Hypothesis scoring engine

### 8.1 Implement domain scoring structures
- [ ] Initialize all diagnostic domains
- [ ] Add score values
- [ ] Add confidence labels
- [ ] Track supporting and contradicting findings

### 8.2 Define score update rules
- [ ] Map finding codes to domain score changes
- [ ] Support positive evidence
- [ ] Support negative evidence
- [ ] Support cross-domain suppression
- [ ] Support multi-domain ambiguity

### 8.3 Implement confidence mapping
- [ ] configurable thresholds for low/medium/high
- [ ] deterministic score-to-confidence mapping

### 8.4 Tests
- [ ] DNS issue score increase test
- [ ] RF issue score decrease after clean AP/client data test
- [ ] AP uplink issue score increase from CRC/flap findings test
- [ ] L2 issue score increase from MAC flap findings test
- [ ] mixed evidence ambiguity test

---

## 9. Phase 7 - Stop condition engine

### 9.1 Implement stop condition checks
- [ ] high-confidence single-domain stop
- [ ] bounded ambiguity stop
- [ ] skill budget exhausted stop
- [ ] elapsed-time budget stop
- [ ] branch-depth exhausted stop
- [ ] blocked-by-dependencies stop
- [ ] no-new-information stop

### 9.2 Implement stop reason recording
- [ ] code
- [ ] message
- [ ] supporting context
- [ ] uncertainty summary

### 9.3 Tests
- [ ] high-confidence stop test
- [ ] ambiguity stop test
- [ ] budget stop test
- [ ] dependency-block stop test
- [ ] no-progress stop test

---

## 10. Phase 8 - Sampling strategy

### 10.1 Implement sampling models
- [ ] define AP sampling inputs
- [ ] define client sampling inputs
- [ ] define comparison/control sample support

### 10.2 Implement deterministic sampling logic
- [ ] representative AP selection
- [ ] representative client selection
- [ ] inclusion of changed hardware where relevant
- [ ] inclusion of control sample where possible

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
- [ ] create/load incident state
- [ ] call `net.incident_intake` if needed
- [ ] classify incident
- [ ] select playbook
- [ ] execute first skill
- [ ] enter controlled loop
- [ ] update state after each skill
- [ ] evaluate stop conditions after each step
- [ ] branch or continue
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
