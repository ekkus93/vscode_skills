# Making Skills With GitHub Copilot

This is a short practical guide for creating a new shared skill in this workspace.

The setup used here is:

- the repo and prompt files live in `${HOME}/work/vs_skills`
- the shared skills library lives in `${HOME}/skills`

The important idea is that a skill is not just a folder. It is:

1. a folder under `${HOME}/skills`
2. a `SKILL.md` file inside that folder
3. an entry in `${HOME}/skills/SKILL_LIST.md`

## What Copilot Should Help You Do

When you ask GitHub Copilot to make a new skill, it should usually do these things:

1. create a new folder in `${HOME}/skills`
2. add a `SKILL.md` file
3. write the skill instructions
4. register the skill in `${HOME}/skills/SKILL_LIST.md`
5. update `${HOME}/skills/README.md` if the library overview changed

If you want the skill to feel more like an OpenClaw-style slash command, Copilot can also add frontmatter such as:

- `name`
- `description`
- `metadata`
- `user-invocable: true`

## The Fastest Way To Ask Copilot

Use a direct request like:

```text
Create a new skill in ${HOME}/skills called weather.
Make it an OpenClaw-style skill.
Register it in SKILL_LIST.md.
Update the skills README if needed.
```

Or for a more specific skill:

```text
Create a skill called docx-to-markdown.
It should convert .docx files to .md using pandoc.
Put it in ${HOME}/skills, register it in SKILL_LIST.md, and update the README.
```

## Recommended Skill Structure

The simplest skill layout is:

```text
${HOME}/skills/my-skill/
	SKILL.md
```

If the skill needs helper files, you can add them to the same folder.

## Basic SKILL.md Template

For a plain instructional skill:

```md
# My Skill

## Purpose

Explain what the skill does.

## When to use

- Use when ...
- Do not use when ...

## Workflow

1. First step.
2. Second step.
3. Final step.

## Output

Describe the expected response or result.

## Constraints

- Important limitation 1
- Important limitation 2
```

## OpenClaw-Style Template

If you want the skill to behave more like a named command, use a conservative frontmatter block.

```md
---
name: my-skill
description: Use when the user wants help with a specific task.
metadata: {"openclaw":{"requires":{"bins":["curl"]}}}
user-invocable: true
---

# My Skill

## Purpose

Explain what the skill does.

## Invocation

- `/my-skill <args>`

## When to use

- Use when ...

## Workflow

1. Step one.
2. Step two.

## Commands

```bash
echo "example"
```

## Constraints

- Keep the behavior simple.
```

## Important Rules

When creating skills in this workspace, keep these rules in mind:

1. `SKILL_LIST.md` is the source of truth.
2. A folder on disk is not enough by itself.
3. If the skill is not added to `SKILL_LIST.md`, it should not be treated as officially available.
4. Keep frontmatter simple.
5. For OpenClaw-style skills, keep `metadata` as a single-line JSON object.
6. Write the description so the trigger phrases are obvious.

## Good Prompt Patterns

These requests work well with Copilot:

```text
Make a new skill to search Wikipedia.
```

```text
Add a skill that gets the current date and time.
Make it user-invocable.
```

```text
Create a skill to convert .docx files to markdown.
Use pandoc and document the constraints.
```

## After Copilot Creates The Skill

After the files are created, check these things:

1. Does the skill have its own folder?
2. Does that folder contain `SKILL.md`?
3. Is the skill listed in `${HOME}/skills/SKILL_LIST.md`?
4. Is the description clear enough for discovery?
5. If it is OpenClaw-style, is the frontmatter simple and valid?

## Practical Workflow

A good real-world sequence is:

1. Start with a very small skill.
2. Test it on one real example.
3. Improve the workflow only after the first version works.
4. Keep the skill focused on one job.

That is how the current example skills in this workspace were built.

## One Good Default Prompt

If you want one reusable prompt for Copilot, use this:

```text
Create a new skill in ${HOME}/skills called <skill-name>.
Make a folder for it and add SKILL.md.
Use an OpenClaw-style format when appropriate.
Register it in ${HOME}/skills/SKILL_LIST.md.
Update ${HOME}/skills/README.md if needed.
Keep the instructions concrete and simple.
```
