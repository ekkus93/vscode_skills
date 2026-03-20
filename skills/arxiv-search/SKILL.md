---
name: arxiv-search
description: Use when the user asks for arXiv papers on a topic, papers by a specific author, papers in an arXiv category, or a concise shortlist of relevant arXiv results with abstracts and links.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]}}}
user-invocable: true
---

# arXiv Search

## Purpose

Use this skill to search arXiv and return a concise, source-linked summary of the most relevant papers.

This shared skill is self-contained. Use the helper script bundled with the skill instead of writing a new arXiv API request, XML parser, or result formatter by hand.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/arxiv-search <query>`
- `/arxiv-search <query> --max-results 3`

Examples:

- `/arxiv-search transformer attention`
- `/arxiv-search author: Geoffrey Hinton`
- `/arxiv-search category: cs.LG`
- `/arxiv-search title: diffusion models`
- `/arxiv-search abstract: retrieval augmented generation`

If the query is missing, ask the user what they want to search for.

## When to use

- The user asks for recent arXiv papers on a topic.
- The user asks for papers by a specific author on arXiv.
- The user asks for arXiv results in a category such as `cs.LG`.
- The user wants a concise shortlist of relevant papers with abstracts and links.

## When not to use

- The request is not about arXiv or academic papers.
- The user needs full-text paper analysis rather than metadata-level search.
- The user needs general web research rather than arXiv specifically.

## Workflow

1. Determine the query from the user's request.
2. If the query is missing or ambiguous, ask a short clarifying question.
3. Run the bundled helper script with `python3`.
4. Return the helper output directly when it succeeds.
5. If the helper exits non-zero, treat stderr as the failure reason and report it plainly.
6. If no results are found, say so explicitly.
7. Do not guess paper titles, links, categories, or summaries.

## Commands

Basic topic search:

```bash
python3 "{baseDir}/arxiv_search.py" "transformer attention"
```

Author search:

```bash
python3 "{baseDir}/arxiv_search.py" "author: Geoffrey Hinton"
```

Category search:

```bash
python3 "{baseDir}/arxiv_search.py" "category: cs.LG"
```

Title or abstract search:

```bash
python3 "{baseDir}/arxiv_search.py" "title: diffusion models"
python3 "{baseDir}/arxiv_search.py" "abstract: retrieval augmented generation"
```

Limit the result count:

```bash
python3 "{baseDir}/arxiv_search.py" "transformer attention" --max-results 3
```

Check whether the required tool is installed:

```bash
command -v python3
```

Install `python3` on Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install -y python3
```

Install `python3` on macOS with Homebrew:

```bash
brew install python
```

## Input format

- Pass the query as one quoted argument.
- Supported query forms:
  - plain topic, for example `transformer attention`
  - `author: Geoffrey Hinton`
  - `category: cs.LG`
  - `title: diffusion models`
  - `abstract: retrieval augmented generation`
  - `all: retrieval augmented generation`
- Optional advanced form:
  - `python3 "{baseDir}/arxiv_search.py" "transformer attention" --max-results 3`
- Keep the query in one quoted string when using the shell command.

Valid example:

```bash
python3 "{baseDir}/arxiv_search.py" "author: Geoffrey Hinton"
```

Invalid example:

```bash
python3 "{baseDir}/arxiv_search.py" author: Geoffrey Hinton
```

## Output

Return the helper output directly when it succeeds.

Typical output includes:

- result count and sort mode
- numbered paper list
- title, authors, dates, category, short summary, abstract link, and PDF link
- confidence and freshness lines

## Constraints

- Use arXiv as the source for this skill.
- Use the bundled helper script instead of constructing a fresh API call and parser inline.
- `--max-results` must stay between 1 and 5.
- Do not dump raw XML.
- Do not guess paper metadata when arXiv returns no results or the request fails.
- If `python3` is missing, explain that the skill cannot run until it is installed.

## Missing Dependency Response

If `python3` is missing, prefer a short direct answer that includes install guidance, for example:

- `This skill needs python3. On Ubuntu or Debian, run: sudo apt-get update && sudo apt-get install -y python3`
- `This skill needs python3. On macOS with Homebrew, run: brew install python`