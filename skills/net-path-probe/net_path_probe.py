#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1] / "nettools-core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from nettools.priority2 import main_path_probe


if __name__ == "__main__":
    raise SystemExit(main_path_probe())
