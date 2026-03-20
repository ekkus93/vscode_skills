---
name: stock-review-output-contract
description: Internal companion skill for stock-investment-review that defines the required TODO file, report file, and final decision template.
metadata: {"openclaw":{"os":["darwin","linux"]}}
user-invocable: false
---

# Stock Review Output Contract

## Purpose
Define the output contract for `stock-investment-review`.

This companion skill keeps file-creation requirements, TODO structure, report sections, and the final decision template out of the main orchestration skill.

## When to use
- `stock-investment-review` needs the exact TODO and report deliverables.
- An investment-review workflow must create files instead of only returning inline chat output.
- The workflow needs a standard final decision template with exact headings.

## When not to use
- The task only needs a quick inline research answer.
- The task is not producing saved review artifacts.

## Workflow
1. Create exactly two files in the current directory before the analysis is treated as complete:
   - `<TICKER>_TODO.md`
   - `<TICKER>.md`
2. Structure `<TICKER>_TODO.md` into clear phases such as market data, technical review, company context, recent catalysts, scenario analysis, and final write-up.
3. As work is completed, visibly mark checklist items complete in `<TICKER>_TODO.md`.
4. Save all material findings, assumptions, risks, and scenario-based recommendations in `<TICKER>.md`.
5. The report must include objective and horizon, source basis, market snapshot, technical levels from the past year, business and company context, recent catalysts and risks, bull/base/bear scenarios, and a final conclusion on whether the setup looks attractive over the requested horizon.
6. The final report must not stop at general position-management advice; it must end with a clear action or a clear no-trade conclusion.
7. Do not treat the task as complete until both files exist and the TODO file reflects completed work.

## Final decision template
Use this exact final section structure at the end of the report.

```md
## Action
- One clear call: `buy now`, `buy on pullback`, `wait`, or `do not trade`.
- One short explanation of why.

## Entry
- Entry price or range.
- Entry timing window or trigger condition.

## Exit
- Target exit price or range.
- Exit timing window or trigger condition.

## Invalidation
- Stop-loss or thesis-break condition.
- What would prove the setup is wrong.

## No-Trade Condition
- The exact condition under which no position should be opened.
- If the recommendation is already `do not trade`, say that explicitly here too.
```

## Output requirements
- Do not return only an inline chat summary when this workflow is used; the two Markdown files are required deliverables.
- Include a caveat that the report is informational research, not personalized financial advice.
- Make source quality explicit when relying on weaker web evidence.
