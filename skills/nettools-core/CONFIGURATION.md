# NETTOOLS Configuration

Phase 0 configuration decisions:

- Python target: 3.10
- model/config direction: Pydantic
- logging stack: standard-library logging plus JSON formatting
- runtime target: OpenClaw on Debian on a Dell Chromebook

Current environment template lives in the repo root `.env.example` and reserves placeholders for:

- log level
- default time window
- active probe authorization
- capture authorization
- provider selection

Future phases will add typed configuration schemas for:

- provider endpoints and credentials
- per-skill thresholds
- cache TTLs
- feature flags
- site and identifier resolution settings
