#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1] / "nettools-core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))


def main() -> int:
    from nettools.orchestrator.diagnose_incident import main_diagnose_incident

    return main_diagnose_incident()


if __name__ == "__main__":
    raise SystemExit(main())