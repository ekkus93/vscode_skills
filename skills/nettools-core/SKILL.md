---
name: nettools-core
description: Internal support package for the NETTOOLS skill suite, including shared scaffolding, logging, configuration notes, and helper entrypoints used by the repo-local network troubleshooting skills.
metadata: {"openclaw":{"os":["linux"],"requires":{"bins":["python3"]}}}
user-invocable: false
---

# NETTOOLS Core

## Purpose

Use this internal support folder when working on shared NETTOOLS code that should be reused across multiple network-diagnostics skills.

This folder is not the primary operator entrypoint. The user-facing surface should stay in the individual `net-*` skill folders.

## What lives here

- shared Python package bootstrap under `nettools/`
- placeholder CLI scaffolding for Phase 0
- shared logging bootstrap
- NETTOOLS-specific README, architecture, configuration, and testing notes

## Constraints

- Do not expose this folder as the main troubleshooting workflow for operators.
- Keep cross-skill logic here and keep skill-specific behavior in the individual `net-*` folders.
