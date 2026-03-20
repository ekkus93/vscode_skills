---
name: bitcoin-price
description: Use when the user asks for the current price of Bitcoin, the BTC price, or how much Bitcoin is worth right now.
metadata: {"openclaw":{"os":["darwin","linux"],"requires":{"bins":["curl","python3"]}}}
user-invocable: true
---

# Bitcoin Price

## Purpose

Use this skill to fetch the current Bitcoin price in USD.

## Invocation

This skill is intended to be user-invocable by name.

If the runtime exposes skill slash commands, invoke it as:

- `/bitcoin-price`

## When to use

- The user asks for the current price of Bitcoin.
- The user asks what BTC is trading at right now.
- The user asks how much Bitcoin is worth in USD.

## Workflow

1. Fetch the current Bitcoin price from CoinGecko.
2. Parse the returned JSON to extract the USD price.
3. Return the price directly and clearly.
4. If the fetch fails, report the error clearly.
5. If `curl` or `python3` is missing, tell the user what to install before retrying.

## Commands

Fetch the current Bitcoin price in USD:

```bash
curl -fsSL "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd" | python3 -c "import json,sys; data=json.load(sys.stdin); print(data['bitcoin']['usd'])"
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

Prefer a short direct answer, for example:

- `Bitcoin is trading at $82,341 USD.`
- `Current BTC price: $82,341 USD`

## Constraints

- Use CoinGecko as the source for this skill.
- Return the current Bitcoin price in USD unless the user explicitly asks for another currency.
- If the API request fails, say that the price could not be retrieved right now.
- If a required tool is missing, explain which tool is missing and how to install it.

## Missing Dependency Response

If `curl` or `python3` is missing, prefer a short direct answer that includes install guidance, for example:

- `This skill needs curl and python3. On Ubuntu or Debian, run: sudo apt-get update && sudo apt-get install -y curl python3`
- `This skill needs curl and python3. On macOS with Homebrew, run: brew install curl python`