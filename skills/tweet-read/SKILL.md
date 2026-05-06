---
name: tweet-read
description: Read a single public or login-gated X or Twitter status URL with Selenium and a local Chrome-family browser, then return the tweet text, author, timestamp, canonical URL, visible media links, quoted-tweet text, and reply count when visible.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["python3"]},"install":[{"id":"python-selenium","kind":"uv","label":"Install Selenium for Python"}]}}
user-invocable: true
---

# Tweet Read

## Purpose

Use this skill to read one X or Twitter status URL with Selenium and return a structured, read-only summary.

This skill is intentionally limited to reading a single tweet URL.
It does not post, like, reply, repost, bookmark, or perform any other interaction.

The helper uses a persistent Chromium profile outside the repository so a one-time login can be reused across later reads.
The default profile path is:

- `~/vscode-skills-data/tweet-read/chromium-profile`

## Invocation

- `/tweet-read <tweet-url>`

Examples:

- `/tweet-read https://x.com/jack/status/20`
- `/tweet-read https://twitter.com/Interior/status/463440424141459456`

If the user does not provide a single tweet URL, ask for that URL before continuing.

## When to use

- The user wants the contents of one specific tweet.
- The tweet may require a logged-in X session to be readable.
- The user wants the visible tweet text plus nearby metadata.

## When not to use

- The user wants an entire timeline, search result set, or account archive.
- The user wants replies beyond the visible reply count.
- The user wants to post, like, reply, repost, follow, or otherwise interact with X.
- The user wants scraping that bypasses login requirements by inventing unsupported fallbacks.

## Intended workflow

1. Accept exactly one X or Twitter status URL.
2. Normalize the URL to a canonical status URL.
3. Use the bundled Python helper with Selenium.
4. Launch a local Chrome-family browser with the persistent profile stored under the user's home directory, not in the repository.
5. Navigate to the tweet URL and wait for the main tweet article to load.
6. If X redirects to login or the login wall is detected, stop and tell the user they need to log in first.
7. After the user has logged in once, reuse the saved Chromium profile for future reads.
8. Extract the visible main tweet text, author, handle when visible, timestamp, canonical URL, visible media links, quoted-tweet text when present, and reply count when visible.
9. Return the extracted data clearly.
10. If extraction fails, report the failure honestly instead of guessing.

## Commands

Read one tweet URL:

```bash
python3 "{baseDir}/tweet_read.py" "https://x.com/jack/status/20"
```

Open the persistent browser profile so the user can log in manually:

```bash
python3 "{baseDir}/tweet_read.py" --login
```

Install the Python package:

```bash
python3 -m pip install selenium
```

## Output requirements

- Include the main tweet text.
- Include the author display name when visible.
- Include the author handle when visible.
- Include the timestamp when visible.
- Include the canonical tweet URL.
- Include visible media links when present.
- Include quoted-tweet text when present.
- Include reply count when visible.
- If login is required, say that explicitly and stop.

## Constraints

- Read-only only. Never post or interact with X content.
- Accept only one tweet URL in V1.
- Use Selenium with a local Chrome-family browser through the bundled helper rather than ad hoc scraping.
- Keep the browser profile outside the repository.
- Do not claim content that was not visibly extracted.
- Do not bypass a login wall with unsupported hidden APIs.

## Failure handling

If the URL is not a valid X or Twitter status URL:

- Say that the input must be a single tweet or status URL.

If Selenium or a local Chrome-family browser is not installed:

- Say that the local browser automation environment is incomplete.
- Tell the user to install `selenium` and ensure Chrome or Chromium is installed locally.

If login is required:

- Say that X requires login for this tweet.
- Tell the user to run the login command for this skill, complete login in the opened browser, and retry.

If the page loads but the tweet still cannot be extracted:

- Report that the tweet could not be read from the visible page.
- Do not invent text or metadata.
