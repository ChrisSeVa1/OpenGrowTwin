"""OGT-103 acceptance: a moved USD proxy box produces partial shadows."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pxr import Gf, Usd


repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository / "src"))

from opengrow.physics.direct_solver import simulate_design  # noqa: E402
from opengrow.usd.stage_reader import stage_to_solver_design  # noqa: E402


stage = Usd.Stage.Open(str(repository / "demo" / "grow_chamber.usda"))
if stage is None:
    raise RuntimeError("could not open demo/grow_chamber.usda")
occluder = stage.GetPrimAtPath("/World/GrowInstallation/Occluders/Occluder_01")
translate = occluder.GetAttribute("xformOp:translate")

clear_design = stage_to_solver_design(stage)
clear = simulate_design(clear_design)
translate.Set(Gf.Vec3d(0.0, 0.0, 0.3))
blocked_design = stage_to_solver_design(stage)
blocked = simulate_design(blocked_design)

blocked_rays = blocked["blocked_ray_count"]
total_rays = blocked["total_ray_count"]
affected_cells = int((blocked["ppfd"] < clear["ppfd"] - 1e-12).sum())
if clear["blocked_ray_count"] != 0:
    raise AssertionError(f"parked occluder unexpectedly blocked {clear['blocked_ray_count']} rays")
if not 0 < blocked_rays < total_rays:
    raise AssertionError(f"expected partial occlusion, got {blocked_rays}/{total_rays}")
if not 0 < affected_cells < int(blocked["ppfd"].size):
    raise AssertionError(f"expected a spatially localized shadow, affected cells={affected_cells}")
if float(blocked["ppfd"].mean()) >= float(clear["ppfd"].mean()):
    raise AssertionError("occluder did not produce a localized PPFD reduction")

print("[OpenGrowTwin] OGT-103 geometry-aware visibility valid")
print(json.dumps({
    "clear_mean_ppfd": float(clear["ppfd"].mean()),
    "blocked_mean_ppfd": float(blocked["ppfd"].mean()),
    "blocked_ray_count": blocked_rays,
    "total_ray_count": total_rays,
    "blocked_ray_fraction": blocked_rays / total_rays,
    "affected_sensor_cells": affected_cells,
    "total_sensor_cells": int(blocked["ppfd"].size),
}, indent=2))
