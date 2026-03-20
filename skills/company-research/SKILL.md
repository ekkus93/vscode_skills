---
name: company-research
description: Research a company from its official site first, then add recent news context, returning a concise profile with summary, products, pricing, docs, hiring signals, and recent news.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# Company Research

## Purpose
Build a concise company profile from official sources first, then add recent news as supporting context.

For company research in this repository, prefer the official website as the primary source of truth for what the company says about itself.
Use recent news only as supporting context, not as the main source of factual company description.
Keep facts separate from inferred positioning.
Prefer an explicit company site URL when name-only website resolution is weak.
Do not hand-build search or news `curl` URLs for company lookups when this workflow plus the shared `news-search` helper already covers the task.

## When to use
- The user wants a concise profile of a SaaS company, startup, or technology vendor.
- The user wants summary, products, pricing/docs signals, hiring signals, and recent news in one place.
- The user can provide the official site, or the company name is distinctive enough to resolve safely.

## When not to use
- The user needs a deep financial or investor-grade diligence report.
- The task is really about recent news only; use `news-search` instead.
- The task is really about product docs; use `documentation-research` instead.

## Workflow
1. Accept an official site URL directly, or a company name optionally followed by `| site:https://...`.
2. If name-only site resolution is weak, ask for the official site URL instead of guessing.
3. Fetch the homepage and inspect official wording, navigation links, and metadata.
4. Extract summary, products or platform links, pricing link, docs link, careers link, and about link where available.
5. Describe hiring signals only from observable evidence like careers/jobs links or page wording.
6. Add recent company news as supporting context using the deterministic news-search workflow.
7. Return a concise profile with clear separation between official-site facts and news context.
8. If live retrieval fails, fail honestly instead of guessing.

## Output requirements
- Lead with a short company summary grounded in official site wording.
- Include sections for products, pricing, docs, hiring signals, and recent news.
- Prefer official-site URLs for company facts.
- Make clear when official-site resolution came from a search heuristic rather than an explicit URL.
- Avoid guessing private-company details that are not stated in inspected sources.
- Include a confidence label and freshness date.

## Example prompts
- `/company-research https://vercel.com`
- `/company-research PostHog | site:https://posthog.com | limit:2`

## Commands

Use a single request string:

```bash
python3 "{baseDir}/company_research.py" "PostHog | site:https://posthog.com | limit:2"
```

Use explicit flags:

```bash
python3 "{baseDir}/company_research.py" --company "PostHog" --site https://posthog.com --news week --limit 2
```

## Constraints
- Use the official site as the primary source of truth when available.
- Use recent news only as supporting context.
- Use the shared `news-search` helper logic through the bundled helper path rather than ad hoc search requests.