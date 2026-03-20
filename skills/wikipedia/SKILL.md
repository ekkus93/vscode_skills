---
name: wikipedia
description: Use when the user asks to look up a topic on Wikipedia, get a short encyclopedia summary, or search Wikipedia for a person, place, event, or concept.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["curl","python3"]}}}
user-invocable: true
---

# Wikipedia

## Purpose

Use this skill to search Wikipedia and return a concise summary for a topic.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/wikipedia <topic>`

Examples:

- `/wikipedia Ada Lovelace`
- `/wikipedia Oakland`
- `/wikipedia Apollo 11`
- `/wikipedia Fourier transform`

If no topic is provided, ask the user what they want to look up.

## When to use

- The user asks what something is.
- The user asks for a Wikipedia summary.
- The user asks to search Wikipedia for a topic.
- The user wants a quick factual overview of a person, place, event, or concept.

## Workflow

1. Determine the topic from the user's request.
2. If the topic is missing or ambiguous, ask a short clarifying question.
3. Search Wikipedia for the best matching page title.
4. Fetch the page summary for the best match.
5. Return a short human-readable summary.
6. If the first search result is obviously wrong or ambiguous, mention that and offer alternatives.

## Commands

Search for the best matching page title:

```bash
curl -fsSL "https://en.wikipedia.org/w/api.php?action=opensearch&search=<topic>&limit=1&namespace=0&format=json" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data[1][0] if data[1] else '')"
```

Fetch the summary for a known page title:

```bash
curl -fsSL "https://en.wikipedia.org/api/rest_v1/page/summary/<title>" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('title','')); print(); print(data.get('extract',''))"
```

Combined flow example:

```bash
title=$(curl -fsSL "https://en.wikipedia.org/w/api.php?action=opensearch&search=Ada%20Lovelace&limit=1&namespace=0&format=json" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data[1][0] if data[1] else '')")
curl -fsSL "https://en.wikipedia.org/api/rest_v1/page/summary/${title// /_}" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('title','')); print(); print(data.get('extract',''))"
```

## Output

Prefer a short direct answer, for example:

- `Ada Lovelace was an English mathematician and writer best known for her work on Charles Babbage's Analytical Engine. She is often regarded as one of the first computer programmers.`
- `Oakland is a major port city in Alameda County, California, located on the east side of San Francisco Bay.`

If useful, include the resolved Wikipedia page title before the summary.

## Constraints

- Use Wikipedia as the source for this skill.
- If the topic is ambiguous, do not pretend the first result is definitely correct.
- Keep the first response concise unless the user asks for more detail.
- If Wikipedia does not return a useful result, say that no good Wikipedia match was found.