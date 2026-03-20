---
name: hacker-news-top10
description: Use when the user asks for the top Hacker News stories, the top 10 articles from Hacker News, or a summary of what is trending on news.ycombinator.com right now.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["curl","python3"]}}}
user-invocable: true
---

# Hacker News Top 10

## Purpose

Use this skill to fetch the current top 10 Hacker News stories and return each story's title, URL, and a short summary.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/hacker-news-top10`

## When to use

- The user asks for the top stories on Hacker News.
- The user asks for the top 10 articles from Hacker News.
- The user wants a quick summary of what is trending on news.ycombinator.com.
- The user wants titles, URLs, and brief summaries for current Hacker News items.

## Workflow

1. Fetch the current top story IDs from the official Hacker News API.
2. Take the first 10 story IDs.
3. Fetch the story details for each ID.
4. Extract the story title and URL for each item.
5. For each story with a URL, fetch the linked page content with the webpage-fetch tool when available; otherwise use `curl` and summarize conservatively from the article title and any clear lead text.
6. For Ask HN or other items without an external URL, use the Hacker News item text or discussion context as the basis for the short summary.
7. Write a short summary for each item, keeping it to 1 or 2 sentences.
8. Return the results as a numbered list with title, URL, and summary for all 10 items.
9. If some article pages cannot be fetched, still return the title and URL, and say that a reliable summary could not be generated for that item.
10. If required tools are missing, provide setup instructions before retrying.

## Commands

Fetch the current top story IDs:

```bash
curl -fsSL "https://hacker-news.firebaseio.com/v0/topstories.json"
```

Fetch one story item by ID:

```bash
curl -fsSL "https://hacker-news.firebaseio.com/v0/item/<id>.json"
```

Fetch the first 10 top story IDs:

```bash
curl -fsSL "https://hacker-news.firebaseio.com/v0/topstories.json" | python3 -c "import json,sys; data=json.load(sys.stdin); print('\n'.join(str(x) for x in data[:10]))"
```

Fetch the first 10 top stories with title and URL:

```bash
python3 - <<'PY'
import json
import urllib.request

top_ids = json.load(urllib.request.urlopen('https://hacker-news.firebaseio.com/v0/topstories.json'))[:10]
for story_id in top_ids:
    item = json.load(urllib.request.urlopen(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json'))
    print(item.get('title', ''))
    print(item.get('url', f'https://news.ycombinator.com/item?id={story_id}'))
    print()
PY
```

Check whether the required tools are installed:

```bash
command -v curl
command -v python3
```

Install `curl` and `python3` on Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y curl python3
```

Install `curl` and `python3` on macOS with Homebrew:

```bash
brew install curl python
```

## Output

Prefer a clear numbered list. Each item should include:

1. The article title
2. The URL
3. A short summary

Example format:

1. `Example Story Title`
   URL: `https://example.com/story`
   Summary: `A short one- or two-sentence summary of the linked article or the Hacker News post.`

## Constraints

- Use the official Hacker News API as the source for the top story list and story metadata.
- Return 10 items unless the API returns fewer.
- Keep each summary brief and factual.
- Do not invent article content when a page cannot be fetched or parsed reliably.
- If a story has no external URL, use the Hacker News discussion link or post text instead.
- If the Hacker News API is unavailable, say that the top stories could not be retrieved right now.
- If a required tool is missing, explain which tool is missing and how to install it.

## Missing Dependency Response

If `curl` or `python3` is missing, prefer a short direct answer that includes install guidance, for example:

- `This skill needs curl and python3. On Ubuntu or Debian, run: sudo apt-get update && sudo apt-get install -y curl python3`
- `This skill needs curl and python3. On macOS with Homebrew, run: brew install curl python`