# List Skills Skill

## Purpose
Use this skill to discover, summarize, and recommend available skills from the shared skills library.

## When to use
Use this skill when:
- the user asks what skills are available
- the task is ambiguous and a skill should be selected first
- another instruction says to consult the shared skills library

## Required workflow
1. Read `skills/SKILL_LIST.md`.
2. Extract the available skills, their paths, and their purposes.
3. Summarize them clearly.
4. If there is a current user task, recommend the most relevant skill or top 2 skills.
5. Do not claim a skill exists unless it is listed in `skills/SKILL_LIST.md`.

## Output format
Produce:
- Available skills
- What each skill is for
- Best match for the current task, if applicable

## Constraints
- `skills/SKILL_LIST.md` is the source of truth.
- Do not invent skills.
- If the list is missing or incomplete, say so explicitly.
