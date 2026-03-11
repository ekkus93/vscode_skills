# OpenClaw Skills Reference

Research date: 2026-03-11

This file summarizes what I found from official OpenClaw docs and official repo examples about how OpenClaw skills work and what syntax they use.

## Short answer

OpenClaw skills are folder-based skills that follow an AgentSkills-compatible layout.

The practical minimum is:

1. A folder for the skill.
2. A `SKILL.md` file inside that folder.
3. YAML frontmatter at the top of `SKILL.md`.
4. A markdown body describing when and how the agent should use the skill.

OpenClaw then adds its own extensions under `metadata.openclaw` for gating, install hints, UI metadata, and env/config integration.

## Minimal folder layout

```text
my-skill/
	SKILL.md
	optional-script.sh
	optional-template.txt
	optional-assets/
```

The docs describe a skill as a folder with `SKILL.md` plus optional supporting files.

## Required SKILL.md syntax

Official docs say `SKILL.md` must include at least:

```md
---
name: my-skill
description: One-line description of what this skill does and when to use it.
---

# my-skill

Instructions for the agent.
```

### Required frontmatter fields

- `name`: skill name
- `description`: short description used for discovery and prompt injection

### Important parser constraints

This is one of the most important findings.

- OpenClaw says its embedded parser supports single-line frontmatter keys only.
- `metadata` should be a single-line JSON object.
- The docs show pretty-printed examples, but the rule text says to keep `metadata` as a one-line JSON object.

Practical takeaway: keep frontmatter simple and conservative. Do not rely on complex multi-line YAML structures inside frontmatter.

## OpenClaw-specific frontmatter extensions

Official docs list these optional top-level keys:

- `homepage`: URL shown as "Website" in the macOS Skills UI
- `user-invocable`: `true|false`, default `true`
- `disable-model-invocation`: `true|false`, default `false`
- `command-dispatch`: optional, currently `tool`
- `command-tool`: tool name to invoke when `command-dispatch: tool`
- `command-arg-mode`: for tool dispatch, default `raw`
- `metadata`: single-line JSON object

### What `command-dispatch: tool` means

When a skill is configured for tool dispatch, the slash command bypasses the model and directly invokes a tool.

Docs say the tool receives params in this shape:

```json
{
	"command": "<raw args>",
	"commandName": "<slash command>",
	"skillName": "<skill name>"
}
```

## `metadata.openclaw` syntax

The main OpenClaw extension point is `metadata.openclaw`.

Docs describe it as JSON stored inside the `metadata` frontmatter field.

Example, written in the conservative one-line style the docs recommend:

```md
---
name: my-skill
description: Example skill with OpenClaw metadata.
metadata: {"openclaw":{"emoji":"wrench","requires":{"bins":["uv"],"env":["MY_API_KEY"],"config":["browser.enabled"]},"primaryEnv":"MY_API_KEY"}}
---
```

Note: I used ASCII `wrench` as plain text here instead of emoji because the docs allow emoji but we do not need it for authoring.

### Supported `metadata.openclaw` fields

From the official skills docs:

- `always: true`
	- Always include the skill and skip other gating checks.
- `emoji`
	- Optional UI icon for the macOS Skills UI.
- `homepage`
	- Optional website URL shown in the UI.
- `os`
	- Optional list of allowed platforms: `darwin`, `linux`, `win32`.
- `skillKey`
	- Alternate config key used under `skills.entries.<skillKey>`.
- `primaryEnv`
	- Env var name associated with `skills.entries.<name>.apiKey`.
- `requires.bins`
	- All listed binaries must exist on `PATH`.
- `requires.anyBins`
	- At least one listed binary must exist on `PATH`.
- `requires.env`
	- Required environment variables.
- `requires.config`
	- Required truthy config paths from `openclaw.json`.
- `install`
	- Optional installer specs for the UI.

## Installer metadata

Docs say `metadata.openclaw.install` can describe install methods used by the OpenClaw UI.

Documented installer kinds include:

- `brew`
- `node`
- `go`
- `uv`
- `download`

Documented installer-related fields include:

- `id`
- `kind`
- `label`
- `bins`
- `formula` for brew installs
- `package` for node installs
- `os` to restrict an installer to certain platforms

For `download`, docs mention:

- `url`
- `archive`: `tar.gz`, `tar.bz2`, or `zip`
- `extract`
- `stripComponents`
- `targetDir`

## Skill body syntax

Below the frontmatter, the body is normal markdown instruction content.

Official examples use plain markdown sections like:

- what the skill is for
- prerequisites or API keys
- quick-start commands
- usage rules
- model-specific behavior
- command examples

This means the body is mostly instruction text, not a strict schema.

## Referencing files inside the skill

Official docs explicitly mention using `{baseDir}` in instructions to reference the skill folder path.

That implies a skill can include helper files and scripts and refer to them relative to its own directory.

Example pattern:

```md
Run `{baseDir}/scripts/do-the-thing.sh` when you need to ...
```

I did not find an official built-in skill example using `{baseDir}`, but the docs explicitly state that it is supported.

## Where skills live

Official OpenClaw docs say skills are loaded from three main places:

1. Bundled skills shipped with OpenClaw
2. Managed or local skills in `~/.openclaw/skills`
3. Workspace skills in `<workspace>/skills`

Additional skill directories can be configured with:

- `skills.load.extraDirs`

### Precedence order

If names conflict, precedence is:

1. `<workspace>/skills`
2. `~/.openclaw/skills`
3. bundled skills
4. extraDirs are lowest precedence

## Per-agent versus shared skills

Official docs distinguish:

- per-agent skills: `<workspace>/skills`
- shared skills: `~/.openclaw/skills`

In multi-agent setups, each agent workspace has its own `skills` folder.

## Plugin-provided skills

Official docs also say plugins can ship skills by listing `skills` directories in `openclaw.plugin.json`, relative to the plugin root.

Those skills participate in normal precedence rules.

## Config syntax in `~/.openclaw/openclaw.json`

All skill config lives under `skills`.

Official example shape:

```json5
{
	skills: {
		allowBundled: ["gemini", "peekaboo"],
		load: {
			extraDirs: ["~/Projects/shared-skills"],
			watch: true,
			watchDebounceMs: 250,
		},
		install: {
			preferBrew: true,
			nodeManager: "npm",
		},
		entries: {
			"my-skill": {
				enabled: true,
				apiKey: { source: "env", provider: "default", id: "MY_API_KEY" },
				env: {
					MY_API_KEY: "secret-value",
				},
				config: {
					endpoint: "https://example.invalid",
				},
			},
		},
	},
}
```

### Documented config fields

- `skills.allowBundled`
- `skills.load.extraDirs`
- `skills.load.watch`
- `skills.load.watchDebounceMs`
- `skills.install.preferBrew`
- `skills.install.nodeManager`
- `skills.entries.<skillKey>.enabled`
- `skills.entries.<skillKey>.env`
- `skills.entries.<skillKey>.apiKey`
- `skills.entries.<skillKey>.config`

### Config key matching rule

Docs say config entries match the skill name by default.

If the skill defines `metadata.openclaw.skillKey`, then that key is used under `skills.entries` instead.

## How env injection works

Official docs say that when an agent run starts, OpenClaw:

1. Reads skill metadata.
2. Applies any `skills.entries.<key>.env` or `apiKey` to `process.env`.
3. Builds the system prompt with eligible skills.
4. Restores the original environment after the run ends.

This injection is per agent run, not global shell state.

## Session and reload behavior

Official docs say:

- OpenClaw snapshots eligible skills when a session starts.
- Changes usually take effect on the next new session.
- With the skills watcher enabled, skills can refresh mid-session and become available on the next turn.

Watcher config:

```json5
{
	skills: {
		load: {
			watch: true,
			watchDebounceMs: 250,
		},
	},
}
```

## Security model and trust assumptions

Official docs are explicit here:

- Treat third-party skills as untrusted code.
- Read them before enabling.
- Workspace and extra-dir discovery only accepts skill roots and `SKILL.md` files whose realpath stays inside the configured root.
- Required binaries are checked on the host at load time.
- If the agent is sandboxed, the binary must also exist in the sandbox container.
- `skills.entries.*.env` and `apiKey` inject secrets into the host process for that agent turn, not the sandbox.

## ClawHub and skill publishing

OpenClaw has a public skills registry called ClawHub.

What I learned:

- A skill is a versioned bundle of files.
- It typically contains `SKILL.md` and optional supporting files.
- `clawhub install <slug>` installs a skill into `./skills` by default.
- OpenClaw picks that up as workspace skills on the next session.
- ClawHub can search, install, update, sync, and publish skill bundles.

Useful commands from official docs:

```bash
clawhub search "calendar"
clawhub install my-skill
clawhub update --all
clawhub publish ./my-skill --slug my-skill --name "My Skill" --version 1.0.0 --tags latest
clawhub sync --all
```

## Practical authoring rules

If we make our own skills later, these are the safest rules to follow:

1. Put each skill in its own folder.
2. Always name the main file `SKILL.md`.
3. Keep frontmatter minimal and single-line per key.
4. Make `metadata` a single-line JSON object.
5. Use a short, concrete `description` because OpenClaw uses it for discovery.
6. Keep supporting scripts and templates inside the skill folder.
7. Use `{baseDir}` when referencing sibling files.
8. Declare gating requirements in `metadata.openclaw.requires`.
9. Use `primaryEnv` if the skill relies on one main API key.
10. Assume third-party skills are untrusted until inspected.

## Recommended starter template

This template is consistent with the official docs and should be a safe starting point:

```md
---
name: my-skill
description: Use when you need to perform a specific task with a repeatable workflow.
metadata: {"openclaw":{"requires":{"bins":["bash"]}}}
---

# my-skill

## Purpose

Explain what the skill is for.

## When to use

- Use when ...
- Do not use when ...

## Workflow

1. First step.
2. Second step.
3. Final step.

## Commands

```bash
{baseDir}/scripts/example.sh
```

## Notes

- Caveat 1
- Caveat 2
```

## What is still uncertain

I found strong official documentation for:

- folder layout
- required frontmatter
- OpenClaw metadata fields
- load order
- config structure
- ClawHub lifecycle

I did not yet confirm, from official built-in examples alone, whether OpenClaw imposes any additional body-level conventions beyond normal markdown instructions.

My current conclusion is:

- the strict syntax is mostly in the frontmatter
- the markdown body is intentionally flexible
- OpenClaw-specific behavior is primarily driven by `metadata.openclaw` and skill location

## Sources used

Official docs:

- https://docs.openclaw.ai/tools/skills
- https://docs.openclaw.ai/tools/skills-config
- https://docs.openclaw.ai/tools/clawhub

Official repo:

- https://github.com/openclaw/openclaw
- https://raw.githubusercontent.com/openclaw/openclaw/main/skills/sag/SKILL.md

