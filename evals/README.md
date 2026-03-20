# Skill Evals

This directory holds prompt-driven eval cases for the shared skills used from this workspace.

## What These Evals Are

These evals are for Copilot-in-the-loop testing.

The intended workflow is:

1. Pick a case JSON file from `evals/cases/`.
2. Give the case prompt to Copilot using the repo's skill-selection workflow, for example with `.github/prompts/use-a-skill.prompt.md`.
3. Capture the final assistant output as plain text.
4. Run the eval runner against that captured output.

Unlike the `opencode_skills` repo, this workspace does not currently have a supported repo-local CLI that can invoke GitHub Copilot directly from a Python test process. Because of that, these evals grade captured model output rather than launching the model automatically from the runner.

## Case Format

Each case is a JSON file with fields like:

- `id`
- `skill`
- `prompt`
- `expected_outcome`
- `assertions`

Supported assertion keys:

- `text_contains`
- `text_not_contains`
- `regex_contains`
- `regex_not_contains`
- `min_nonempty_lines`

## Sample Outputs

Representative captured-output fixtures live under `evals/sample_outputs/`.

Use the same per-skill directory layout as `evals/cases/`, and name each `.txt` file to match its corresponding case when practical.
These files are useful as checked-in examples of what a passing captured response can look like, and they can be passed directly to the runner with `--output-file`.

## Running An Eval

With output saved in a file:

```bash
python3 evals/runner/skill_eval.py \
  --case evals/cases/arxiv-search/arxiv-search-topic-success.json \
  --output-file /tmp/arxiv-output.txt
```

Or pass the output directly:

```bash
python3 evals/runner/skill_eval.py \
  --case evals/cases/arxiv-search/arxiv-search-topic-success.json \
  --output-text "Found 2 arXiv result(s)..."
```

Exit codes:

- `0`: all assertions passed
- `1`: assertion failure
- `2`: invalid runner usage

## Current Limitation

These are not fully automated end-to-end Copilot tests yet.

To make them fully automated, this repo would need a supported way to invoke the Copilot model from a local runner and capture the final answer programmatically. Until then, the runner is useful for repeatable grading of captured outputs, and Copilot can act as the model under test during manual or agent-assisted eval runs.