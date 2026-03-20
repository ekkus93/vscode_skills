## 2026-03-20T00:27:15Z - GPT-5.4 - Repo structure and skill authoring rules
- `vscode_skills` is the control layer for prompts, repo instructions, and documentation, while the shared skills library lives outside the repo under `${HOME}/skills`.
- Shared skills are only officially available when registered in `${HOME}/skills/SKILL_LIST.md`; a skill folder alone is not sufficient.
- Creating a new shared skill normally means adding a folder under `${HOME}/skills`, adding `SKILL.md`, registering it in `SKILL_LIST.md`, and updating the shared skills README when the overview changes.
- OpenClaw-compatible skills should use conservative `SKILL.md` YAML frontmatter with required `name` and `description`, and keep `metadata` as a single-line JSON object.
- OpenClaw skill bodies are flexible markdown instructions; helper files can live beside `SKILL.md`, and `{baseDir}` can be used to reference them.

## 2026-03-20T00:29:11Z - GPT-5.4 - Current shared skills library state
- The shared library at `${HOME}/skills` currently contains registered skills for `bitcoin-price`, `current-date-time`, `docx-to-markdown`, `hacker-news-top10`, `image-ocr`, `weather`, `wikipedia`, and `yahoo-finance-cli`.
- `${HOME}/skills/list-skills/` exists with a `SKILL.md` file but is intentionally not registered in `${HOME}/skills/SKILL_LIST.md`, matching the shared library README's warning that the index is authoritative.
- The repo README in `vscode_skills` is stale relative to the actual shared library: it lists only an older subset of skills in examples and omits `bitcoin-price`, `hacker-news-top10`, and `image-ocr` from the documented current shared skills structure.

## 2026-03-20T00:45:05Z - GPT-5.4 - Ported arxiv-search into shared skills library
- Ported the OpenCode `arxiv-search` skill from `opencode_skills/.opencode/skills/arxiv-search` into the shared library as `${HOME}/skills/arxiv-search`.
- The shared version is self-contained instead of repo-specific: it uses `${HOME}/skills/arxiv-search/arxiv_search.py` via `python3 "{baseDir}/arxiv_search.py" ...` rather than depending on the OpenCode repo's `.opencode/scripts/arxiv_search.sh` wrapper.
- Registered `arxiv-search` in `${HOME}/skills/SKILL_LIST.md` and updated `${HOME}/skills/README.md` to include the new skill and helper script in the documented library layout.
- Validated the helper with a live query: `python3 /home/phil/skills/arxiv-search/arxiv_search.py "transformer attention" --max-results 2` returned formatted arXiv results successfully.

## 2026-03-20T00:47:31Z - GPT-5.4 - Added unit tests for shared arxiv-search skill
- Added `${HOME}/skills/arxiv-search/test_arxiv_search.py` with pytest coverage for query normalization, empty-query validation, feed parsing, formatted output sections, and empty-result formatting.
- Reused the original OpenCode helper test style by loading the standalone helper module from disk rather than requiring package installation.
- Verified the new tests with `/bin/python3 -m pytest /home/phil/skills/arxiv-search/test_arxiv_search.py`, which passed with 6 tests.

## 2026-03-20T00:51:50Z - GPT-5.4 - Added vscode_skills Copilot-in-the-loop eval harness
- Added `vscode_skills/evals/runner/skill_eval.py`, `vscode_skills/evals/README.md`, and a sample case at `vscode_skills/evals/cases/arxiv-search/arxiv-search-topic-success.json`.
- The harness is intentionally output-based: it grades captured assistant output against assertions because this repo does not currently have a supported local CLI or API path to invoke GitHub Copilot directly from a Python test process.
- Added `vscode_skills/tests/test_skill_eval_runner.py`; `/bin/python3 -m pytest /home/phil/work/vscode_skills/tests/test_skill_eval_runner.py` passed with 4 tests.
- Smoke-tested the CLI runner with the sample arXiv case and representative output; it returned `Result: PASS`.

## 2026-03-20T00:55:42Z - GPT-5.4 - Repo-local lint and test baseline
- `vscode_skills` currently has two repo-local Python files under validation: `evals/runner/skill_eval.py` and `tests/test_skill_eval_runner.py`.
- Ran `ruff check evals/runner/skill_eval.py tests/test_skill_eval_runner.py` and all checks passed.
- Ran `mypy evals/runner/skill_eval.py tests/test_skill_eval_runner.py` and it reported success with no issues in 2 source files.
- Ran `/bin/python3 -m pytest` from the `vscode_skills` repo root and the full repo-local test suite passed: 4 tests in `tests/test_skill_eval_runner.py`.

## 2026-03-20T00:58:41Z - GPT-5.4 - Shared arxiv-search validation baseline
- Ran `ruff check arxiv_search.py test_arxiv_search.py` in `${HOME}/skills/arxiv-search`; all checks passed.
- Ran `mypy arxiv_search.py test_arxiv_search.py` in `${HOME}/skills/arxiv-search`; it reported success with no issues in 2 source files.
- Ran `/bin/python3 -m pytest` in `${HOME}/skills/arxiv-search`; the full shared skill test suite passed with 6 tests in `test_arxiv_search.py`.

## 2026-03-20T00:59:59Z - GPT-5.4 - Refreshed repo README for current skills and eval scaffolding
- Updated `vscode_skills/README.md` to replace stale `vs_skills` naming with `vscode_skills` and to document the repo as instructions plus eval/test scaffolding.
- Brought the shared-library examples and directory tree up to date, including `arxiv-search`, `bitcoin-price`, `hacker-news-top10`, and `image-ocr`.
- Expanded the README with an `Eval And Test Workflow` section covering repo-local Python validation, shared helper validation, and prompt-driven captured-output evals via `evals/runner/skill_eval.py`.

## 2026-03-20T01:07:55Z - GPT-5.4 - Ported stock review skill set into shared library
- Ported the four related OpenCode skills into `${HOME}/skills`: `stock-investment-review`, `stock-review-market-context`, `stock-review-output-contract`, and `stock-review-supporting-research`.
- Converted `stock-investment-review` into a self-contained shared skill by bundling `stock_investment_review.py`, `stock_research.py`, `company_research.py`, `news_search.py`, `yahoo_finance.py`, and `test_stock_investment_review.py` inside the skill folder.
- Rewrote the four `SKILL.md` files for shared-library use: the main skill is user-invocable and the three companion skills are internal (`user-invocable: false`), with commands pointing at bundled helper files instead of old OpenCode wrappers.
- Registered all four skills in `${HOME}/skills/SKILL_LIST.md`, updated `${HOME}/skills/README.md`, and refreshed `vscode_skills/README.md` so the shared-library inventory and dependency notes include the new stock-review skills.
- Validated `${HOME}/skills/stock-investment-review` with Ruff, MyPy, and pytest: all passed after annotating the optional `yfinance` import for MyPy; cleaned generated cache directories afterward.

## 2026-03-20T01:13:06Z - GPT-5.4 - Split standalone stock research helper skills out of stock-investment-review
- Ported standalone shared skills for `yahoo-finance`, `news-search`, `company-research`, and `stock-research` into `${HOME}/skills`, each with its own `SKILL.md`, helper module, and pytest file.
- Rewired `company-research` to load the shared `news-search` helper from `../news-search/news_search.py`, rewired `stock-research` to load the shared `yahoo-finance`, `company-research`, and `news-search` helpers from sibling skill folders, and rewired `stock-investment-review` to load the shared `yahoo-finance` and `stock-research` helpers.
- Removed duplicated helper modules from `${HOME}/skills/stock-investment-review/` after the standalone skills were in place, leaving `stock_investment_review.py` and its test as the only code in that skill folder.
- Updated `${HOME}/skills/SKILL_LIST.md`, `${HOME}/skills/README.md`, and `vscode_skills/README.md` so the shared library inventory and dependency notes now reflect the standalone stock research ecosystem.
- Validation results after the split: `yahoo-finance` 9 tests passed, `news-search` 9 tests passed, `company-research` 20 tests passed, `stock-research` 10 tests passed, and the repointed `stock-investment-review` 3 tests passed; Ruff and MyPy also passed for each folder.

## 2026-03-20T01:17:47Z - GPT-5.4 - Added prompt-driven eval cases for standalone stock helper skills
- Added captured-output eval case JSON files under `vscode_skills/evals/cases/` for `yahoo-finance`, `news-search`, `company-research`, and `stock-research`.
- The new cases assert each skill's documented output contract rather than exact wording, covering required sections, links or freshness labels, period or news-window parameters, and non-advisory language where applicable.
- Parsed all four new JSON files successfully with `python -m json.tool` and smoke-tested the runner against the new `yahoo-finance` case with representative output; the eval returned `Result: PASS`.

## 2026-03-20T01:19:26Z - GPT-5.4 - Added sample captured outputs for standalone stock helper eval cases
- Added representative captured-output text fixtures under `vscode_skills/evals/sample_outputs/` for the `yahoo-finance`, `news-search`, `company-research`, and `stock-research` success cases.
- Verified each new sample output by running `evals/runner/skill_eval.py` with its matching case file and output file; all four case-output pairs returned `Result: PASS`.

## 2026-03-20T01:20:41Z - GPT-5.4 - Added sample captured output for arxiv-search eval case
- Added `vscode_skills/evals/sample_outputs/arxiv-search/arxiv-search-topic-success.txt` as a representative captured-output fixture for the existing `arxiv-search` success case.
- Verified the new fixture with `evals/runner/skill_eval.py --case evals/cases/arxiv-search/arxiv-search-topic-success.json --output-file evals/sample_outputs/arxiv-search/arxiv-search-topic-success.txt`; the eval returned `Result: PASS`.

## 2026-03-20T01:21:53Z - GPT-5.4 - Documented eval sample_outputs convention
- Updated `vscode_skills/evals/README.md` with a short `Sample Outputs` section describing the `evals/sample_outputs/` tree, the per-skill directory layout, the file naming convention, and the intended use with `--output-file`.

## 2026-03-20T01:22:47Z - GPT-5.4 - Added pytest smoke coverage for checked-in eval fixtures
- Extended `vscode_skills/tests/test_skill_eval_runner.py` with a parameterized smoke test that pairs checked-in `evals/cases/*/*.json` files with matching `evals/sample_outputs/*/*.txt` files and asserts each pair passes through `evaluate_assertions`.
- Validated the updated test module with `/bin/python3 -m pytest tests/test_skill_eval_runner.py`; all 9 tests passed.
- The currently configured repo Python venv does not include `pytest`, so system Python was used for the validation run.

## 2026-03-20T01:23:33Z - GPT-5.4 - Added completeness check for eval case sample outputs
- Extended `vscode_skills/tests/test_skill_eval_runner.py` with a dedicated test that fails if any checked-in `evals/cases/*/*.json` file does not have a matching `evals/sample_outputs/<skill>/<case-stem>.txt` fixture.
- Validated the updated test module with `/bin/python3 -m pytest tests/test_skill_eval_runner.py`; all 10 tests passed.

## 2026-03-20T01:27:59Z - GPT-5.4 - Refreshed lint, type-check, and test baseline for vscode_skills and shared skills
- In `vscode_skills`, `ruff check evals/runner/skill_eval.py tests/test_skill_eval_runner.py` passed, `mypy evals/runner/skill_eval.py tests/test_skill_eval_runner.py` reported no issues in 2 files, and `/bin/python3 -m pytest` passed with 10 tests.
- In `${HOME}/skills`, Ruff passed across the 12 checked-in helper and test modules for `arxiv-search`, `yahoo-finance`, `news-search`, `company-research`, `stock-research`, and `stock-investment-review`.
- In `${HOME}/skills`, MyPy reported success with no issues in those same 12 source files.
- In `${HOME}/skills`, `/bin/python3 -m pytest` across the six checked-in test modules passed with 57 tests total.