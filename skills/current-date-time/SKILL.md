---
name: current-date-time
description: Use when the user asks for the current date, current time, current datetime, or what time it is right now.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["date"]}}}
user-invocable: true
---

# Current Date Time

## Purpose

Use this skill to get the current local date and time from the system clock.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/current-date-time`

Optional arguments can be interpreted as a format hint, for example:

- `/current-date-time utc`
- `/current-date-time local`
- `/current-date-time date-only`
- `/current-date-time time-only`

## When to use

- The user asks for the current date.
- The user asks for the current time.
- The user asks what time it is right now.
- The user asks for the current datetime.

## Workflow

1. Run the system `date` command.
2. Use the local system timezone unless the user explicitly asks for UTC or another timezone.
3. If the user passes `utc`, return UTC.
4. If the user passes `date-only`, return only the date.
5. If the user passes `time-only`, return only the time.
6. Otherwise, return the local datetime.
7. Return the result directly and clearly.
8. If useful, include the timezone abbreviation in the response.

## Commands

Local datetime:

```bash
date '+%Y-%m-%d %H:%M:%S %Z'
```

UTC datetime:

```bash
date -u '+%Y-%m-%d %H:%M:%S UTC'
```

Date only:

```bash
date '+%Y-%m-%d'
```

Time only:

```bash
date '+%H:%M:%S %Z'
```

## Output

Prefer a short direct answer, for example:

- `2026-03-11 16:45:03 PDT`
- `Current local time: 2026-03-11 16:45:03 PDT`
- `2026-03-11`
- `09:37:10 PDT`

## Constraints

- Use the actual system clock, not a guessed or cached value.
- Do not convert to another timezone unless the user asks.
- Keep the slash-style invocation simple and name-based.
- Do not add direct tool dispatch metadata unless the target OpenClaw tool name is verified.
- If the command fails, say that the system time could not be retrieved.