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

Implemented first-pass orchestrator loop. The bundled helper now normalizes intake when needed, selects a playbook, runs lower-level NETTOOLS skills in a controlled sequence, scores diagnostic domains, evaluates stop conditions, and returns a final diagnosis report.

## Inputs

- Optional complaint intake: `--complaint`, `--reporter`, `--incident-id`, `--location`, `--device-type`, `--movement-state`, `--wired-also-affected`, `--reconnect-helps`, `--occurred-at`, `--impacted-app`, `--note`
- Optional explicit scope selectors: `--site-id`, `--client-id`, `--client-mac`, `--ap-id`, `--ap-name`, `--ssid`, `--switch-id`, `--switch-port`, `--vlan-id`
- Optional candidate resolution hints: `--candidate-client-id`, `--candidate-client-mac`, `--candidate-ap-id`, `--candidate-ap-name`, `--candidate-area`, `--comparison-ap-id`, `--comparison-ap-name`, `--comparison-area`
- Orchestrator controls: `--playbook-override`, `--max-steps`
- Time controls: `--time-window-minutes`, `--start-time`, `--end-time`
- Output controls: `--include-raw`
- Test mode: `--fixture-file`

## Outputs

- Writes a JSON `SkillResult` to stdout
- Returns a final diagnosis report plus the orchestrator trace of invoked lower-level skills
- Populates evidence with the selected playbook, ranked diagnostic domains, stop-condition state, and normalized incident context
- May include finding codes from intake, correlation, and the lower-level skills executed during the run
- Preserves a machine-readable investigation path in `evidence` and `next_actions` rather than collapsing the run into prose

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
	"summary": "Diagnosis converged on an internal service-path issue with supporting network evidence.",
	"confidence": "high",
	"observed_at": "2026-03-28T15:00:00Z",
	"time_window": {
		"start": "2026-03-28T14:45:00Z",
		"end": "2026-03-28T15:00:00Z"
	},
	"evidence": {
		"diagnosis_report": {
			"playbook_used": "site_wide_slowdown",
			"top_domain": "service_path_issue"
		},
		"executed_skills": [
			"net.incident_intake",
			"net.path_probe",
			"net.dns_latency"
		]
	},
	"findings": [],
	"next_actions": [
		{
			"skill": "net.change_detection",
			"reason": "A recent change may explain the diagnosed service-path issue."
		}
	],
	"raw_refs": []
}
```

## Common Failure Cases

- Scope and complaint are both missing: the orchestrator lacks enough context to choose a playbook and validation fails
- Required downstream adapters are unavailable for the chosen playbook: returns a dependency-unavailable result instead of partial fiction
- Lower-level skills return insufficient evidence repeatedly: the diagnosis remains conservative and may stop with low-confidence output
- Invalid candidate identifiers or playbook overrides: input validation fails before orchestration starts

## Constraints

- Use the bundled helper.
- Prefer passing the best available scope identifiers such as `client-id`, `site-id`, `ap-id`, or `ssid`.
- Return the helper's structured `SkillResult` output directly so the diagnosis report and investigation trace remain intact.
- This v1 orchestrator is read-only and should not imply that any remediation action was executed.