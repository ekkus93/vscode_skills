---
name: weather
description: Use when the user asks for the current weather, forecast, temperature, or conditions for a city or location.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["curl"]}}}
user-invocable: true
---

# Weather

## Purpose

Use this skill to fetch a simple text weather report for a location.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/weather <location>`

Examples:

- `/weather Portland`
- `/weather London`
- `/weather Tokyo`
- `/weather 94110`

If no location is provided, ask the user which location they want.

## When to use

- The user asks for the current weather.
- The user asks for the temperature in a city.
- The user asks for a quick forecast.
- The user asks about current conditions like rain, wind, or cloud cover.

## Workflow

1. Determine the location from the user's request.
2. If the location is missing or ambiguous, ask a short clarifying question.
3. Fetch a text weather report with `curl`.
4. Return a short human-readable summary.
5. If the user wants more detail, include the fuller text output.

## Commands

Short weather summary:

```bash
curl -fsSL "https://wttr.in/<location>?format=3"
```

Detailed text forecast:

```bash
curl -fsSL "https://wttr.in/<location>"
```

Examples:

```bash
curl -fsSL "https://wttr.in/Portland?format=3"
curl -fsSL "https://wttr.in/London?format=3"
curl -fsSL "https://wttr.in/Tokyo"
```

## Output

Prefer a short direct answer, for example:

- `Portland: +52F, Light rain`
- `London: +11C, Partly cloudy`

If the user asks for more detail, provide the fuller forecast text.

## Constraints

- Use the location the user asked for.
- Do not guess a location if the user did not provide one.
- Keep the first response concise unless the user asks for detail.
- If the weather service is unavailable, say that the weather could not be retrieved.