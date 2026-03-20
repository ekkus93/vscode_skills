# Copilot Instructions for This Repository

## General behavior
- Prioritize correctness over style.
- Do not invent files, functions, behavior, or APIs.
- Before proposing edits, inspect nearby files that are likely to be affected.
- When uncertain, state the uncertainty explicitly.

## Shared skills library
This workspace includes a shared `skills/` folder.

When a task appears to match a reusable skill:
1. Read `skills/SKILL_LIST.md`
2. Select the most relevant skill
3. Read that skill's `SKILL.md`
4. Follow the skill's workflow, constraints, and output format

Do not claim to have used a skill unless you actually read its `SKILL.md`.

## When to consult a skill
Consult a skill for tasks like:
- code review
- bug triage
- test planning
- KiCad work
- ESP-IDF workflows
- structured planning

If no skill is clearly relevant, continue normally.

## Response style
- Be concrete
- Be explicit about assumptions
- Prefer actionable TODO lists over generic advice

## Memory file
- You have access to a persistent memory file, memory.md, that stores context about the project, previous interactions, and user preferences.
- Use this memory to inform your decisions, remember user preferences, and maintain continuity across sessions. 
- Before sending back a response, update memory.md with any new relevant information learned during the interaction. Make sure to timestamp and format entries clearly.
- Include the GitHub Copilot model used for the entry in the heading line so memory history records both time and model (for example: `## 2024-06-01T12:00:00Z - GPT-5.4 - User prefers concise responses`).
- **NEVER fabricate or guess timestamps.** Always obtain the current time by running `date -u +"%Y-%m-%dT%H:%M:%SZ"` in the terminal immediately before writing the entry. If the entry describes a specific commit, use `git log -1 --format="%aI" <hash>` for that commit's actual timestamp.
- For each entry, add an ISO 8601 timestamp and a brief description of the information added. For example:
```markdown

## 2024-06-01T12:00:00Z - GPT-5.4 - User prefers concise responses
- User has expressed a preference for concise, to-the-point answers without unnecessary elaboration.
```
