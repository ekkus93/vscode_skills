# NETWORK_DIAGNOSIS_ORCHESTRATOR_SPECS.md

## 1. Purpose

This document defines a top-level OpenClaw orchestration skill for network diagnosis.

Unlike the lower-level network diagnostic skills, which each inspect one domain of evidence, this orchestrator skill is responsible for:

- accepting an incident or complaint
- classifying the likely scope of the issue
- selecting an appropriate diagnostic playbook
- invoking lower-level skills in a controlled order
- branching based on findings
- stopping when sufficient confidence is reached
- producing a ranked, operator-friendly diagnosis report

The orchestrator is the decision-making layer that turns a set of network diagnostic primitives into a disciplined troubleshooting system.

---

## 2. Proposed skill name

Primary recommendation:

- `net.diagnose_incident`

Alternative acceptable names:

- `net.network_triage`
- `net.run_diagnostic_playbook`
- `net.troubleshoot_network_issue`

This spec uses `net.diagnose_incident`.

---

## 3. Problem statement

The lower-level network skills are useful but insufficient on their own.

Without orchestration, the system risks:
- running the wrong skills
- running too many skills
- chasing weak evidence
- repeating checks unnecessarily
- failing to stop when one fault domain is already strongly supported
- producing a telemetry dump instead of a diagnosis

The orchestrator solves this by encoding a repeatable diagnostic protocol.

---

## 4. Goals

### 4.1 Primary goals

1. Convert a vague complaint into a structured investigation.
2. Select the most appropriate troubleshooting playbook.
3. Minimize unnecessary skill execution.
4. Collect evidence in a deterministic, explainable order.
5. Stop once a fault domain is supported strongly enough.
6. Produce an operator-ready diagnosis summary.
7. Preserve an auditable trace of the investigation.

### 4.2 Secondary goals

1. Allow future tuning of branching behavior without rewriting all skills.
2. Support both:
   - single-user troubleshooting
   - area-based troubleshooting
   - site-wide incidents
3. Make diagnosis behavior consistent across operators and sessions.

### 4.3 Non-goals

1. Full autonomous remediation in v1.
2. Free-form chain-of-thought style debugging.
3. Vendor-specific auto-repair logic.
4. Continuous NOC-style monitoring and alerting.
5. Infinite exploratory investigation without budget/stop controls.

---

## 5. Relationship to existing skills

The orchestrator depends on the existing primitive skills.

### 5.1 Required primitive skills

- `net.incident_intake`
- `net.client_health`
- `net.ap_rf_health`
- `net.roaming_analysis`
- `net.dhcp_path`
- `net.dns_latency`
- `net.auth_8021x_radius`
- `net.ap_uplink_health`
- `net.stp_loop_anomaly`
- `net.path_probe`
- `net.segmentation_policy`
- `net.incident_correlation`
- `net.change_detection`

### 5.2 Optional supporting skill

- `net.capture_trigger`

This should remain optional and gated in v1.

---

## 6. Core model

The orchestrator should be implemented as a controlled state machine, not as loose agentic improvisation.

At a high level, it should perform the following loop:

1. create or load incident state
2. classify the issue
3. choose a playbook
4. execute next skill
5. update hypotheses and confidence
6. decide:
   - continue
   - branch
   - stop
7. emit final report

---

## 7. Diagnostic domains

The orchestrator should reason in terms of normalized fault domains.

### 7.1 Required diagnostic domains

- `single_client_rf`
- `single_ap_rf`
- `roaming_issue`
- `dhcp_issue`
- `dns_issue`
- `auth_issue`
- `ap_uplink_issue`
- `l2_topology_issue`
- `segmentation_policy_issue`
- `site_wide_internal_lan_issue`
- `wan_or_external_issue`
- `unknown`

These domains should be used in hypothesis tracking and final reports.

---

## 8. Incident classifications

The orchestrator should classify incidents into one of these top-level categories:

- `single_client`
- `single_area`
- `site_wide`
- `auth_or_onboarding`
- `intermittent_unclear`
- `unknown_scope`

### 8.1 Classification inputs

Classification should use the incident intake result and infer from:

- number of affected users
- number of affected devices
- whether affected users are co-located
- whether wired users are also affected
- whether symptoms are connect/auth related
- whether users are moving when symptoms occur
- whether the issue correlates with a recent change
- whether the complaint is broad or highly localized

---

## 9. Playbooks

The orchestrator should support deterministic playbooks.

### 9.1 Playbook: `single_client_wifi_issue`

Used when:
- one user or one device is affected
- complaint sounds local
- no strong evidence of broader impact yet

Default sequence:
1. `net.incident_intake`
2. `net.client_health`
3. `net.roaming_analysis` if mobility suspected
4. `net.ap_rf_health`
5. `net.ap_uplink_health`
6. `net.dns_latency`
7. `net.dhcp_path` if reconnect/address symptoms exist
8. `net.segmentation_policy` if placement/policy symptoms exist
9. `net.incident_correlation`

### 9.2 Playbook: `area_based_wifi_issue`

Used when:
- several people in one room/area/floor are affected
- symptoms appear localized geographically

Default sequence:
1. `net.incident_intake`
2. `net.ap_rf_health`
3. `net.ap_uplink_health`
4. sample `net.client_health` for 2 to 5 affected clients
5. `net.roaming_analysis` if mobility is involved
6. `net.dns_latency`
7. `net.dhcp_path` if onboarding symptoms exist
8. `net.incident_correlation`

### 9.3 Playbook: `site_wide_internal_slowdown`

Used when:
- multiple users across different areas complain
- issue seems broader than one AP cell
- internal network is suspected
- recent network changes exist

Default sequence:
1. `net.incident_intake`
2. `net.change_detection`
3. `net.path_probe`
4. `net.stp_loop_anomaly`
5. `net.ap_uplink_health` on representative APs / ports
6. `net.dns_latency`
7. `net.dhcp_path`
8. sample `net.ap_rf_health`
9. sample `net.client_health`
10. `net.incident_correlation`

### 9.4 Playbook: `auth_or_onboarding_issue`

Used when:
- users cannot connect
- users connect but do not get working access
- reconnect temporarily helps
- SSID authentication problems are suspected

Default sequence:
1. `net.incident_intake`
2. `net.auth_8021x_radius`
3. `net.dhcp_path`
4. `net.segmentation_policy`
5. `net.dns_latency`
6. `net.client_health`
7. `net.incident_correlation`

### 9.5 Playbook: `unclear_general_network_issue`

Used when:
- symptoms are vague
- scope is not yet clear
- intake data is incomplete

Default sequence:
1. `net.incident_intake`
2. `net.path_probe`
3. `net.dns_latency`
4. `net.dhcp_path`
5. `net.client_health` if a device is known
6. `net.ap_rf_health` if an AP or area is known
7. `net.incident_correlation`

---

## 10. Incident state model

The orchestrator should maintain an internal structured state object across the investigation.

### 10.1 Required incident state fields

```json
{
  "incident_id": "string",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "incident_type": "single_client|single_area|site_wide|auth_or_onboarding|intermittent_unclear|unknown_scope",
  "playbook_used": "string",
  "status": "running|completed|blocked|failed",
  "scope_summary": {
    "site_id": "optional string",
    "ssid": "optional string",
    "affected_users_estimate": "optional integer",
    "affected_areas": [],
    "known_clients": [],
    "known_aps": []
  },
  "suspected_domains": [],
  "eliminated_domains": [],
  "domain_scores": {},
  "evidence_log": [],
  "skill_trace": [],
  "dependency_failures": [],
  "recommended_next_skill": "optional string",
  "stop_reason": "optional string"
}
```

### 10.2 State behavior requirements

1. Must be serializable.
2. Must survive partial failures.
3. Must support appending evidence from multiple skills.
4. Must support deterministic replay for debugging.

---

## 11. Hypothesis and confidence model

The orchestrator should score fault domains over time.

### 11.1 Domain score structure

```json
{
  "domain": "dns_issue",
  "score": 0.78,
  "confidence": "medium",
  "supporting_findings": ["DNS_HIGH_LATENCY", "DNS_TIMEOUTS"],
  "contradicting_findings": ["PATH_TO_DNS_SERVER_CLEAN"]
}
```

### 11.2 Confidence guidance

This is not statistical truth. It is operational confidence.

Suggested mapping:
- `low`: 0.00 to <0.40
- `medium`: 0.40 to <0.75
- `high`: 0.75 to 1.00

These thresholds must be configurable.

### 11.3 Scoring behavior

The orchestrator should:
- increase domain scores based on supporting findings
- decrease domain scores based on contradicting findings
- avoid impossible combinations where appropriate
- preserve multiple plausible domains when evidence is mixed

Example:
- If RF is clean across multiple clients/APs, reduce probability of `single_client_rf` and `single_ap_rf`.
- If DNS latency is high but gateway probes are clean, increase `dns_issue`.
- If MAC flapping and topology churn are present, strongly increase `l2_topology_issue`.

---

## 12. Branching logic

The orchestrator should branch based on skill output, not arbitrary intuition.

### 12.1 Branching inputs

Each executed skill may provide:
- status
- summary
- findings
- next_actions
- evidence
- dependency failures

### 12.2 Branching requirements

1. Prefer explicit branch rules over free-form reasoning.
2. Use `next_actions` from lower-level skills as hints, not absolute commands.
3. The playbook defines the allowed branch set.
4. Branch only to skills that are:
   - relevant
   - not already exhausted
   - not blocked by dependency failure
5. Avoid cycles unless explicitly permitted.

### 12.3 Example branch rules

#### From `net.client_health`
- High retries + low RSSI -> branch to `net.ap_rf_health`
- Many disconnects + movement context -> branch to `net.roaming_analysis`
- Good RF but user still slow -> branch to `net.dns_latency` or `net.path_probe`

#### From `net.ap_rf_health`
- High utilization -> reinforce RF domains
- Clean RF -> reduce RF domains and consider uplink/services
- Radio reset events -> keep AP-local domain active

#### From `net.path_probe`
- Internal service latency high + external okay -> internal services / LAN
- Gateway clean + DNS bad -> DNS issue
- Wide loss to multiple internal targets -> site-wide LAN / switching

#### From `net.stp_loop_anomaly`
- MAC flapping + topology churn -> strong L2 branch; can stop early if corroborated

---

## 13. Stop conditions

The orchestrator must know when to stop.

### 13.1 Required stop conditions

1. **High-confidence diagnosis**
   - one domain reaches high confidence and has sufficient supporting evidence

2. **Two-domain bounded ambiguity**
   - two plausible domains remain and further narrowing is unlikely without human action

3. **Investigation budget exhausted**
   - maximum number of skill invocations reached
   - maximum elapsed time reached
   - maximum branching depth reached

4. **Blocked by dependencies**
   - key source adapters unavailable
   - missing identifiers prevent further progress

5. **No new information**
   - recent skill outputs are not materially changing domain scores

### 13.2 Stop condition requirements

Each stop must include:
- stop reason code
- human-readable explanation
- remaining uncertainty
- recommended human next actions

---

## 14. Investigation budgets

To prevent endless diagnosis, the orchestrator should enforce configurable budgets.

### 14.1 Budget controls

- `max_skill_invocations`
- `max_branch_depth`
- `max_same_skill_repeats`
- `max_elapsed_seconds`
- `max_optional_branches`

### 14.2 Suggested defaults

- max skill invocations: 8 to 12
- max branch depth: 4
- max same-skill repeats: 1 or 2
- max optional branches: 3

These should be configurable by playbook.

---

## 15. Sampling strategy

The orchestrator should not brute-force every AP or client by default.

### 15.1 Sampling requirements

For broader incidents:
- sample affected users
- sample affected APs
- include one or more control samples where useful

### 15.2 Suggested defaults

#### Site-wide playbook
- 2 to 3 affected clients
- 3 to 5 representative APs
- 1 comparison AP or area if possible

#### Area-based playbook
- 2 to 5 affected clients
- 1 to 3 nearby APs

Sampling logic should be deterministic when possible.

---

## 16. Skill execution wrapper

All sub-skill execution should go through a common wrapper.

### 16.1 Wrapper responsibilities

- validate inputs
- assign invocation ID
- log start/end
- measure duration
- catch and classify errors
- update incident state
- append evidence and skill trace
- normalize dependency failure handling

### 16.2 Wrapper output

Each wrapped execution should produce:
- raw skill result
- normalized execution record
- state delta

---

## 17. Final diagnosis report

The orchestrator should output a final structured diagnosis report.

### 17.1 Required final fields

```json
{
  "status": "ok|warn|fail|unknown",
  "incident_id": "string",
  "incident_type": "string",
  "playbook_used": "string",
  "summary": "string",
  "ranked_causes": [],
  "eliminated_domains": [],
  "skill_trace": [],
  "evidence_summary": [],
  "dependency_failures": [],
  "stop_reason": {
    "code": "string",
    "message": "string"
  },
  "recommended_human_actions": [],
  "recommended_followup_skills": [],
  "confidence": "low|medium|high"
}
```

### 17.2 Ranked cause structure

```json
{
  "domain": "ap_uplink_issue",
  "confidence": "high",
  "score": 0.87,
  "evidence": [
    "CRC errors on multiple AP uplink ports",
    "Issue began after hardware changes",
    "Clients across multiple APs affected"
  ]
}
```

### 17.3 Human action quality requirements

Human actions should be:
- concrete
- narrow
- actionable
- tied to evidence

Bad:
- “Check the network”

Good:
- “Inspect switch ports connected to AP-2F-EAST-03 and AP-2F-EAST-05 for CRC errors, flaps, or negotiated speed mismatches”

---

## 18. Traceability and auditability

The orchestrator must preserve an investigation trail.

### 18.1 Required trace artifacts

- playbook selected
- branch decisions
- skill order
- per-skill result summary
- domain score evolution
- stop decision rationale
- dependency failures

This is critical for debugging and operator trust.

---

## 19. Config requirements

Create dedicated orchestrator config.

### 19.1 Required config fields

- playbook selection rules
- branch rules
- stop thresholds
- domain score thresholds
- per-playbook budgets
- sampling defaults
- allowed follow-up transitions
- required primitive skills by playbook
- feature flags for optional steps

### 19.2 Examples

- whether `net.change_detection` is mandatory for site-wide incidents
- whether `net.capture_trigger` is allowed
- whether to prefer DNS checks before DHCP in a given environment

---

## 20. Failure handling

The orchestrator must distinguish between:

- no issue found
- unresolved due to insufficient evidence
- blocked by missing dependencies
- misclassified scope
- conflicting evidence
- successful high-confidence diagnosis

### 20.1 Failure-handling requirements

1. Do not treat dependency failures as proof of network issues.
2. Continue with alternative branches where reasonable.
3. Surface blocked branches in final report.
4. Track unresolved ambiguity explicitly.

---

## 21. Security and safety

1. Orchestrator should be read-only in v1.
2. Optional active checks must respect policy gates.
3. Packet capture triggering must require explicit authorization.
4. Logs must redact secrets and sensitive internal data.
5. Investigation output should avoid dumping unnecessary infrastructure secrets.

---

## 22. Suggested repository layout

```text
nettools/
  orchestrator/
    diagnose_incident.py
    playbooks.py
    branch_rules.py
    state.py
    scoring.py
    stop_conditions.py
    sampling.py
    report_builder.py
    execution.py
    config.py

  skills/
    ...
```

---

## 23. Acceptance criteria

The orchestrator is successful when:

1. It can choose the correct playbook for:
   - single-client issues
   - area-based issues
   - site-wide issues
   - auth/onboarding issues
   - unclear issues

2. It can correctly narrow at least these scenarios:
   - weak RF
   - overloaded AP
   - slow DHCP
   - slow DNS
   - auth timeout
   - AP uplink problem
   - L2 topology instability
   - wrong VLAN / wrong policy

3. It stops appropriately instead of exploring endlessly.

4. It produces final reports with:
   - ranked causes
   - eliminated domains
   - skill trace
   - stop reason
   - recommended human actions

5. The investigation trace is reproducible for testing.

---

## 24. Copilot implementation notes

1. Implement this as a state machine, not a free-form agent loop.
2. Keep branch rules declarative where possible.
3. Make domain scoring testable and deterministic.
4. Keep playbooks explicit and configurable.
5. Start with rule-based logic before any future ML-assisted ranking.
6. Prioritize auditability and operator trust over cleverness.
