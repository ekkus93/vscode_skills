---
name: net-diagnose-incident
description: Orchestrate NETTOOLS incident diagnosis across the lower-level network skills using the bundled helper.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Net Diagnose Incident

## Purpose

Use this skill to run the NETTOOLS state-machine orchestrator over a normalized complaint or incident scope and produce a structured diagnosis report.

## Status

Implemented orchestrator with typed reporting, policy controls, persisted audit-trail replay, and fixture-backed deterministic testing. The bundled helper normalizes intake when needed, selects a playbook, runs lower-level NETTOOLS skills in a controlled sequence, scores diagnostic domains, evaluates stop conditions, and returns a final diagnosis report plus replayable investigation artifacts.

## Inputs

- Optional complaint intake: `--complaint`, `--reporter`, `--incident-id`, `--location`, `--device-type`, `--movement-state`, `--wired-also-affected`, `--reconnect-helps`, `--occurred-at`, `--impacted-app`, `--note`
- Optional explicit scope selectors: `--site-id`, `--client-id`, `--client-mac`, `--ap-id`, `--ap-name`, `--ssid`, `--switch-id`, `--switch-port`, `--vlan-id`
- Optional candidate resolution hints: `--candidate-client-id`, `--candidate-client-mac`, `--candidate-ap-id`, `--candidate-ap-name`, `--candidate-area`, `--comparison-ap-id`, `--comparison-ap-name`, `--comparison-area`
- Replay and persisted-state inputs: `--replay-audit-trail-file`, `--replay-state-file`, `--replay-incident-record-file`
- Capture-planning inputs: `--capture-authorized`, `--capture-approval-ticket`, `--capture-protocol`, `--capture-target-host`, `--capture-interface-scope`
- Orchestrator controls: `--playbook-override`, `--max-steps`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Returns a final diagnosis report plus the orchestrator trace of invoked lower-level skills
- Populates `evidence` with `diagnosis_report`, `incident_state`, `audit_trail`, `investigation_metrics`, and the normalized `incident_record`
- Includes `replay_debug` whenever the helper reconstructs a result from a serialized replay state or persisted audit trail
- May include finding codes from intake, correlation, and the lower-level skills executed during the run
- Preserves a machine-readable investigation path in `evidence` and `next_actions` rather than collapsing the run into prose

## State Model

The orchestrator keeps its working state in `IncidentState` and emits that state back inside `evidence["incident_state"]` for traceability.

Key `IncidentState` fields:

- `incident_id`, `created_at`, `updated_at`: stable investigation identity and timing
- `incident_type`: classified scope such as `single_client`, `single_area`, `site_wide`, or `auth_or_onboarding`
- `playbook_used`: selected playbook name
- `status`: `running`, `completed`, `blocked`, or `failed`
- `scope_summary`: normalized scope, discovered identifiers, and sampled AP, client, and area selections
- `suspected_domains` and `eliminated_domains`: current domain shortlist and ruled-out domains
- `domain_scores`: scored diagnostic domains with confidence plus supporting and contradicting findings
- `evidence_log`: condensed evidence emitted by each executed lower-level skill
- `skill_trace`: ordered execution records with timing, inputs, result payloads, and error types
- `dependency_failures`: normalized downstream failures that blocked or degraded the investigation
- `recommended_next_skill`: the best remaining automated follow-up, if one exists
- `stop_reason`: the final stop condition with machine-readable context and human-action hints
- `investigation_trace`: trace events for playbook selection, branch decisions, score updates, and stop-condition evaluation

Related emitted models:

- `diagnosis_report`: public report payload with ranked causes, evidence summaries, sampling summary, stop reason, and recommended actions
- `audit_trail`: persisted replay bundle containing the serialized state, execution records, trace entries, and metrics summary
- `investigation_metrics`: per-investigation summary used for replay parity and observability

## Playbook Selection

`net.diagnose_incident` selects a playbook in two stages.

1. It normalizes or accepts an `IncidentRecord` and classifies the complaint into one of the current incident types.
2. It maps that incident type to a playbook unless an explicit `--playbook-override` is supplied.

Current default mapping:

- `single_client` -> `single_client_wifi_issue`
- `single_area` -> `area_based_wifi_issue`
- `site_wide` -> `site_wide_internal_slowdown`
- `auth_or_onboarding` -> `auth_or_onboarding_issue`
- `intermittent_unclear` and `unknown_scope` -> `unclear_general_network_issue`

Primary classification heuristics:

- auth or onboarding wording, or `--reconnect-helps`, biases toward `auth_or_onboarding`
- wired impact or broad multi-area language biases toward `site_wide`
- co-located multi-user complaints with a known location bias toward `single_area`
- a concrete client or device context biases toward `single_client`
- intermittent complaints without reliable scope bias toward `intermittent_unclear`

Selection rationale is preserved in the emitted `incident_state` as `classification_rationale` and `playbook_selection_rationale`.

## Stop Conditions

The helper stops automatically when one of the implemented stop conditions matches.

- `high_confidence_diagnosis`: one domain reaches high confidence with enough supporting findings
- `two_domain_bounded_ambiguity`: two domains remain close enough that more automation is unlikely to reduce uncertainty
- `investigation_budget_exhausted`: skill count, elapsed time, or branch depth reaches the configured limit
- `dependency_blocked`: required downstream data is unavailable and no further automated branch is viable
- `no_new_information`: recent skill executions are not materially changing domain scores

The final matched stop condition is emitted in both `incident_state.stop_reason` and `diagnosis_report.stop_reason`.

## Replay And Audit Use

Use replay mode when you want to reconstruct a previous diagnosis without re-running primitive skills.

- `--replay-audit-trail-file` rehydrates a full persisted `DiagnoseIncidentAuditTrail`
- `--replay-state-file` rehydrates `IncidentState` directly
- `--replay-incident-record-file` supplements replay state with the original incident context when needed

Replay mode preserves report assembly, ranked causes, metrics, and next-action generation, but it does not invoke lower-level skills again.

## Example Traces

Typical trace shapes:

- Single-client service issue:
	`net.incident_intake` -> `net.client_health` -> `net.dns_latency` -> high-confidence DNS diagnosis
- Area-based wireless issue:
	`net.incident_intake` -> sampled `net.ap_rf_health` -> `net.ap_uplink_health` -> optional `net.client_health` or `net.roaming_analysis` -> area-scoped conclusion
- Site-wide slowdown:
	`net.incident_intake` -> `net.change_detection` -> `net.path_probe` -> `net.stp_loop_anomaly` -> sampled AP or service checks -> broad-impact conclusion
- Auth ambiguity with capture recommendation:
	`net.incident_intake` -> `net.auth_8021x_radius` -> `net.dhcp_path` -> bounded ambiguity stop -> optional `net.capture_trigger` recommendation if authorized
- Replay path:
	persisted `audit_trail` or `incident_state` -> report reconstruction -> `replay_debug` evidence, no primitive skill invocations

## Dependencies

- `python3`
- The shared NETTOOLS package under `skills/nettools-core/`
- The lower-level NETTOOLS adapters needed by whichever playbook branches are executed, or a JSON fixture file passed with `--fixture-file`

## Commands

```bash
python3 "{baseDir}/net_diagnose_incident.py" --site-id "hq-1" --client-id "client-42" --complaint "My laptop cannot connect to CorpWiFi and reconnect helps"
python3 "{baseDir}/net_diagnose_incident.py" --site-id "hq-1" --complaint "Everyone on the second floor says the office network is slow and wired is also affected"
```

## Example Result

```json
{
	"status": "warn",
	"skill_name": "net.diagnose_incident",
	"scope_type": "service",
	"scope_id": "hq-1",
	"summary": "High-confidence diagnosis points to dns_issue with high confidence.",
	"confidence": "high",
	"observed_at": "2026-03-28T10:00:00Z",
	"time_window": {
		"start": "2026-03-28T09:55:00Z",
		"end": "2026-03-28T10:00:00Z"
	},
	"evidence": {
		"incident_record": {
			"incident_id": "replay-single-client-1",
			"summary": "Laptop has slow browsing and intermittent DNS lookups",
			"site_id": "hq-1",
			"client_id": "client-42",
			"ssid": "CorpWiFi"
		},
		"diagnosis_report": {
			"incident_type": "single_client",
			"playbook_used": "single_client_wifi_issue",
			"ranked_causes": [
				{
					"domain": "dns_issue",
					"score": 0.84,
					"confidence": "high"
				}
			],
			"stop_reason": {
				"code": "high_confidence_diagnosis",
				"message": "High-confidence diagnosis points to dns_issue with high confidence."
			}
		},
		"investigation_metrics": {
			"playbook_invocations": {
				"single_client_wifi_issue": 1
			}
		},
		"replay_debug": {
			"enabled": true,
			"source": "audit_trail",
			"replayed_skill_count": 2
		}
	},
	"findings": [],
	"next_actions": [],
	"raw_refs": [
		"fixture:replay:single_client:client_health",
		"fixture:replay:single_client:dns_latency"
	]
}
```

## Common Failure Cases

- Scope and complaint are both missing: the orchestrator lacks enough context to choose a playbook and validation fails
- Required downstream adapters are unavailable for the chosen playbook: returns a dependency-unavailable result instead of partial fiction
- Lower-level skills return insufficient evidence repeatedly: the diagnosis remains conservative and may stop with low-confidence output
- Invalid candidate identifiers or playbook overrides: input validation fails before orchestration starts
- Replay files do not validate against `IncidentState`, `IncidentRecord`, or `DiagnoseIncidentAuditTrail`: replay-mode input validation fails before report reconstruction starts

## Constraints

- Use the bundled helper.
- Prefer passing the best available scope identifiers such as `client-id`, `site-id`, `ap-id`, or `ssid`.
- Return the helper's structured `SkillResult` output directly so the diagnosis report and investigation trace remain intact.
- This v1 orchestrator is read-only and should not imply that any remediation action was executed.