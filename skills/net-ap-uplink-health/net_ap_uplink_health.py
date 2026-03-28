#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1] / "nettools-core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from nettools.cli import run_placeholder_skill


if __name__ == "__main__":
    raise SystemExit(
        run_placeholder_skill(
            skill_name="net.ap_uplink_health",
            scope_type="switch_port",
            description="Validate the wired path behind an access point.",
        )
    )
