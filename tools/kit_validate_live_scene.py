"""Validate and print OGT-101 discovery data; run through Kit with --exec."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pxr import Usd


repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository / "src"))

from opengrow.usd.stage_reader import discover_stage  # noqa: E402


stage_path = Path(sys.argv[1] if len(sys.argv) > 1 else repository / "demo" / "grow_chamber.usda")
stage = Usd.Stage.Open(str(stage_path))
if stage is None:
    raise RuntimeError(f"could not open {stage_path}")
result = discover_stage(stage)
print("[OpenGrowTwin] OGT-101 live scene contract valid")
print(json.dumps(result, indent=2))
