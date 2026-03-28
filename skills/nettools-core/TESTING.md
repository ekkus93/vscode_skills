# NETTOOLS Testing

Phase 0 adds the test directory layout needed for later work:

- `tests/unit/nettools/`
- `tests/integration/nettools/`
- `tests/fixtures/nettools/`

Testing expectations for later phases:

- no live vendor dependencies in automated tests
- stub adapters and checked-in fixtures for deterministic behavior
- contract tests for standardized skill outputs
- scenario tests for weak RF, DHCP slowness, DNS slowness, auth failures, AP uplink issues, and L2 instability

Useful validation commands once NETTOOLS code exists:

```bash
ruff check skills/nettools-core skills/net-*
mypy skills/nettools-core/nettools
pytest tests/unit/nettools tests/integration/nettools
```
