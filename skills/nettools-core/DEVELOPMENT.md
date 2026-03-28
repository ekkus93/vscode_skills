# NETTOOLS Development Guide

This guide describes the current extension points for the NETTOOLS orchestrator and how to change them safely.

## Add A New Playbook

1. Define the playbook in `skills/nettools-core/nettools/orchestrator/playbooks.py`.
2. Give it a unique `name`, supported `incident_types`, a `default_sequence`, and any `required_skills`, `optional_skills`, and `allowed_branch_transitions`.
3. Keep every referenced skill in `SKILL_REGISTRY`; `PlaybookDefinition` validation rejects unknown skills or illegal transition sources.
4. If the playbook should be selected automatically, update the mapping in `DEFAULT_PLAYBOOK_BY_INCIDENT_TYPE` in `skills/nettools-core/nettools/orchestrator/classification.py` or document that it is override-only.
5. If the playbook needs different budgets or sampling defaults, set `stop_settings` and `sampling_settings` directly in the playbook and confirm they still make sense with `OrchestratorConfig` overrides.
6. Add or update docs in `skills/nettools-core/PLAYBOOKS.md` and `skills/net-diagnose-incident/SKILL.md` if the playbook is operator-visible.

Recommended validation after adding a playbook:

- playbook model tests
- branching tests covering legal and illegal transitions
- at least one `evaluate_diagnose_incident(...)` path test or replay scenario

## Add A New Diagnostic Domain

1. Add the enum value to `DiagnosticDomain` in `skills/nettools-core/nettools/orchestrator/state.py`.
2. Add scoring behavior in `skills/nettools-core/nettools/orchestrator/scoring.py`.
3. Update report-resolution behavior where needed, especially:
   - ranked-cause expectations
   - human-action generation in `skills/nettools-core/nettools/orchestrator/diagnose_incident.py`
   - any domain-specific suppressions or ambiguity handling
4. Extend fixtures, replay scenarios, and operator docs if the domain becomes part of a public troubleshooting flow.

Safe rule of thumb:

- A new domain is incomplete until it can be scored, surfaced in reports, and explained in human-action output.

## Add A New Branch Rule

1. Add or update the rule in `skills/nettools-core/nettools/orchestrator/branch_rules.py`.
2. Keep the rule aligned with the playbook’s `allowed_branch_transitions`; the branch selector only works cleanly when both agree.
3. If the rule is playbook-specific rather than global, prefer constraining it through playbook transitions or config overrides instead of making the global branch table ambiguous.
4. Make sure the target skill is runnable with the identifiers that are likely to exist at that point in the flow.
5. Add or update tests for:
   - branch ranking
   - blocked or exhausted skill filtering
   - one end-to-end orchestrator path that uses the new rule

## Adjust Score Weights Safely

Score changes affect three things at once:

- which domains become suspected or eliminated
- which stop conditions trigger
- which human actions and follow-up skills are emitted

When changing score weights or thresholds:

1. Update the scoring rule or threshold in `skills/nettools-core/nettools/orchestrator/scoring.py` or the related config model.
2. Check whether cross-domain suppression logic still makes sense with the new weight.
3. Check whether `high_confidence_diagnosis`, `two_domain_bounded_ambiguity`, or `no_new_information` would now trigger earlier or later than intended.
4. Re-run the focused scoring, stop-condition, and diagnose-incident tests first.
5. Re-run the replay scenarios to confirm persisted investigations still reconstruct into sensible reports after the score change.

Recommended validation sequence:

```bash
/home/phil/.local/bin/ruff check .
/home/phil/work/vscode_skills/.venv/bin/python -m mypy .
/home/phil/work/vscode_skills/.venv/bin/python -m pytest tests/unit/nettools/test_orchestrator_scoring.py tests/unit/nettools/test_orchestrator_stop_conditions.py tests/unit/nettools/test_orchestrator_diagnose_incident.py tests/integration/nettools/test_replay_scenarios.py
/home/phil/work/vscode_skills/.venv/bin/python -m pytest
```

## Practical Checklist For Any Orchestrator Extension

- update code and docs together
- keep new behavior deterministic under fixtures or replay data
- prefer narrow, explainable rules over broad heuristics
- preserve replay compatibility when changing report or state shapes
- update roadmap and memory only after the change is validated