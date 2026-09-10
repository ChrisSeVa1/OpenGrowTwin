"""OGT-102 acceptance: live fixture transforms drive solver input."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from pxr import Gf, Usd, UsdGeom


repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository / "src"))

from opengrow.usd.stage_reader import stage_to_solver_design  # noqa: E402


stage_path = repository / "demo" / "grow_chamber.usda"
stage = Usd.Stage.Open(str(stage_path))
if stage is None:
    raise RuntimeError(f"could not open {stage_path}")

baseline = stage_to_solver_design(stage)
fixture = stage.GetPrimAtPath("/World/GrowInstallation/Fixtures/Fixture_01")
translate = fixture.GetAttribute("xformOp:translate")
original_translation = translate.Get()
translate.Set(Gf.Vec3d(original_translation[0], original_translation[1], original_translation[2] + 0.1))
moved = stage_to_solver_design(stage)

xformable = UsdGeom.Xformable(fixture)
rotate = xformable.AddRotateXOp(opSuffix="ogt102Validation")
rotate.Set(10.0)
rotated = stage_to_solver_design(stage)

baseline_emitter = baseline["channels"][0]["emitters"][0]
moved_emitter = moved["channels"][0]["emitters"][0]
rotated_emitter = rotated["channels"][0]["emitters"][0]
height_delta = moved_emitter["position_m"][2] - baseline_emitter["position_m"][2]
direction_delta = math.dist(moved_emitter["direction"], rotated_emitter["direction"])
if not math.isclose(height_delta, 0.1, abs_tol=1e-9):
    raise AssertionError(f"fixture translation did not propagate: delta={height_delta}")
if direction_delta <= 0.01:
    raise AssertionError(f"fixture rotation did not propagate: delta={direction_delta}")

print("[OpenGrowTwin] OGT-102 USD-to-solver adapter valid")
print(json.dumps({
    "channels": len(baseline["channels"]),
    "emitters": sum(len(channel["emitters"]) for channel in baseline["channels"]),
    "baseline_position_m": baseline_emitter["position_m"],
    "moved_position_m": moved_emitter["position_m"],
    "baseline_direction": baseline_emitter["direction"],
    "rotated_direction": rotated_emitter["direction"],
}, indent=2))
