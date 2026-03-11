# Visual Studio Code Skills

This repository is a small workspace for experimenting with reusable agent skills, documenting how those skills are structured, and wiring them into a prompt-driven workflow.

The project is split across two workspace folders:

- `${HOME}/work/vscode_skills`
- `${HOME}/skills`

The `vs_skills` repository holds the repo-specific instructions, prompts, and documentation. This can really be any Visual Studio Code workspace you want to use the shared skills library from. The main thing is that the contents of .github and AGENTS.md are copied/merged into the target repo.

The `${HOME}/skills` folder holds the actual shared skill library. Unzip the skills.zip file here. It's in your home directory so it can be reused across multiple coding-agent workspaces.

## What This Project Does

This project gives you a place to:

- define reusable skills as folders with `SKILL.md` files
- keep a human-maintained skill index in `SKILL_LIST.md`
- route tasks through a prompt that tells the agent to choose and read a skill first
- experiment with OpenClaw-style skill authoring and invocation patterns

In short, this repo is the control layer, and the shared `skills` folder is the content layer.

## How It Works

There are three main pieces.

### 1. Repo instructions

This repo includes:

- `AGENTS.md`
- `.github/copilot-instructions.md`

These files tell the coding agent how to behave in this repository. They establish rules like:

- read relevant instructions before changing files
- consult the shared skills library when a task matches a reusable skill
- prefer small, explicit, low-risk changes

### 2. Prompt-driven skill selection

This repo includes a prompt file:

- `.github/prompts/use-a-skill.prompt.md`

Its job is simple: tell the agent to read the shared skill index, pick the closest matching skill, open that skill's `SKILL.md`, and follow it.

That means the prompt does not contain the skill logic itself. It delegates to the shared skill library.

### 3. Shared skill library

The real skills live in:

- `${HOME}/skills`

That folder contains:

- `SKILL_LIST.md`: the index of officially available skills
- one folder per skill
- a `SKILL.md` inside each skill folder

Examples currently in the shared library include:

- `yahoo-finance-cli`
- `current-date-time`
- `weather`
- `wikipedia`
- `docx-to-markdown`

The important rule is that `SKILL_LIST.md` is the source of truth. A skill folder existing on disk is not enough by itself. If it is not listed in the index, it should not be treated as officially available.

## Project Structure

Current repo structure:

```text
vs_skills/
	.github/
		copilot-instructions.md
		prompts/
			use-a-skill.prompt.md
	AGENTS.md
	OPEN_CLAW_SKILL.md
	README.md
```

Current shared skills structure:

```text
${HOME}/skills/
	README.md
	SKILL_LIST.md
	current-date-time/
		SKILL.md
	docx-to-markdown/
		SKILL.md
	list-skills/
		SKILL.md
	weather/
		SKILL.md
	wikipedia/
		SKILL.md
	yahoo-finance-cli/
		SKILL.md
		_meta.json
```

## Setup

### Prerequisites

You need:

- VS Code
- GitHub Copilot Chat or another compatible coding-agent workflow in VS Code
- both workspace folders available locally

Optional but useful, depending on which skills you want to use:

- `jq`
- `curl`
- `date`
- Yahoo Finance CLI support through `yahoo-finance2`

### Workspace setup

Open both folders in the same VS Code workspace:

- `${HOME}/work/vs_skills`
- `${HOME}/skills`

This matters because:

- the repo contains the instructions and prompt files
- the separate `skills` folder contains the reusable skill definitions

### Skill library setup

The shared library should contain:

1. `SKILL_LIST.md`
2. one directory per skill
3. a `SKILL.md` inside each skill directory

If you move the skills directory somewhere else, update any references and prompts that assume the current workspace layout.

### Tool setup for current example skills

For the skills currently in the shared library:

- `current-date-time` needs the system `date` command
- `docx-to-markdown` needs `pandoc`
- `weather` needs `curl`
- `wikipedia` needs `curl` and `python3`
- `yahoo-finance-cli` needs `jq` and Yahoo Finance CLI support

Example install that has already been used in this workspace:

```bash
npm install yahoo-finance2
```

Depending on how you want to expose it, you may also need a `yf` executable or wrapper.

## Day-To-Day Workflow

Typical usage looks like this:

1. Ask the agent to use a skill-oriented prompt or give it a task that matches a known skill.
2. The agent reads `SKILL_LIST.md`.
3. The agent chooses the closest matching skill.
4. The agent reads that skill's `SKILL.md`.
5. The agent follows that workflow to answer the request or perform the action.

For OpenClaw-style skills, the `SKILL.md` can also include frontmatter such as:

- `name`
- `description`
- `metadata`
- `user-invocable`

That allows skills like `/current-date-time` or `/weather Oakland` to behave more like named commands.

Current examples of slash-style skills in this library include:

- `/current-date-time`
- `/weather Oakland`
- `/wikipedia Ada Lovelace`
- `/docx-to-markdown report.docx`

## Adding A New Skill

To add a new shared skill:

1. Create a new folder under `${HOME}/skills`.
2. Add a `SKILL.md` file.
3. Write the skill instructions.
4. Register the skill in `${HOME}/skills/SKILL_LIST.md`.
5. Update `${HOME}/skills/README.md` if the library overview changed.

For simple markdown-only skills, a plain instructional `SKILL.md` is enough.

For OpenClaw-style skills, use a folder-based `SKILL.md` with YAML frontmatter and keep the frontmatter conservative.

## OpenClaw Notes

This repo also contains:

- `OPEN_CLAW_SKILL.md`

That file documents what was learned about OpenClaw skill syntax and authoring. It is a reference for creating future OpenClaw-compatible skills.

The main points are:

- OpenClaw skills are folder-based
- `SKILL.md` is the main file
- frontmatter should stay simple
- `metadata` should be kept as a single-line JSON object
- skill content below the frontmatter is normal markdown instructions

See the shared skill index for the current active set of skills:

- `${HOME}/skills/SKILL_LIST.md`

## Current Purpose Of The Repo

At the moment, this project is best understood as a sandbox for:

- building a reusable shared skills library
- testing prompt-based skill selection
- experimenting with OpenClaw-compatible skills
- documenting the conventions so future skills stay consistent

## Quick Start

If you want the shortest setup path:

1. Open both `${HOME}/work/vs_skills` and `${HOME}/skills` in one VS Code workspace.
2. Make sure the basic tools you need are installed, such as `curl`, `date`, and any skill-specific CLIs.
3. Keep `${HOME}/skills/SKILL_LIST.md` in sync with the actual skills you want available.
4. Use the prompt in `.github/prompts/use-a-skill.prompt.md` when you want the agent to route through the skills library.
5. Add new skills as folders with `SKILL.md`, then register them in the shared index.
