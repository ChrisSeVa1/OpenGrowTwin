"""OGT-105 acceptance: update heatmaps and metrics in one open stage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pxr import Gf, Usd, UsdGeom


repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository / "src"))

from opengrow.orchestration import simulate_stage  # noqa: E402
from opengrow.usd.live_results import HEATMAP_PATHS, set_display_mode, update_live_results  # noqa: E402


stage = Usd.Stage.Open(str(repository / "demo" / "grow_chamber.usda"))
if stage is None:
    raise RuntimeError("could not open demo/grow_chamber.usda")
stage_identity = id(stage)
baseline = simulate_stage(stage, "final")
first_update = update_live_results(stage, baseline)

occluder = stage.GetPrimAtPath("/World/GrowInstallation/Occluders/Occluder_01")
occluder.GetAttribute("xformOp:translate").Set(Gf.Vec3d(0.0, 0.0, 0.3))
current = simulate_stage(stage, "final")
second_update = update_live_results(stage, current, baseline)
if id(stage) != stage_identity or first_update["stage"] is not stage or second_update["stage"] is not stage:
    raise AssertionError("live result update replaced the open stage")

baseline_prim = stage.GetPrimAtPath(HEATMAP_PATHS["baseline"])
current_prim = stage.GetPrimAtPath(HEATMAP_PATHS["current"])
baseline_ppfd = baseline_prim.GetAttribute("primvars:opengrow:ppfd").Get()
current_ppfd = current_prim.GetAttribute("primvars:opengrow:ppfd").Get()
current_colors = current_prim.GetAttribute("primvars:displayColor").Get()
if len(baseline_ppfd) != 1025 or len(current_ppfd) != 1025 or len(current_colors) != 1025:
    raise AssertionError("live heatmap vertex attributes are incomplete")
if list(baseline_ppfd) == list(current_ppfd):
    raise AssertionError("current PPFD did not change after moving the occluder")
if current_prim.GetAttribute("opengrow:results:meanPPFD").Get() >= baseline_prim.GetAttribute(
    "opengrow:results:meanPPFD"
).Get():
    raise AssertionError("current live metric did not reflect the shadow")

set_display_mode(stage, "baseline")
baseline_visible = UsdGeom.Imageable(baseline_prim).ComputeVisibility() != UsdGeom.Tokens.invisible
current_hidden = UsdGeom.Imageable(current_prim).ComputeVisibility() == UsdGeom.Tokens.invisible
set_display_mode(stage, "current")
current_visible = UsdGeom.Imageable(current_prim).ComputeVisibility() != UsdGeom.Tokens.invisible
if not (baseline_visible and current_hidden and current_visible):
    raise AssertionError("baseline/current visibility toggle failed")

print("[OpenGrowTwin] OGT-105 live heatmap update valid")
print(json.dumps({
    "same_open_stage": True,
    "vertex_count": len(current_ppfd),
    "baseline_mean_ppfd": baseline["metrics"]["mean_ppfd_umol_m2_s"],
    "current_mean_ppfd": current["metrics"]["mean_ppfd_umol_m2_s"],
    "legend_min": second_update["legend_min"],
    "legend_max": second_update["legend_max"],
    "baseline_toggle_visible": baseline_visible,
    "current_toggle_visible": current_visible,
    "dli": current["metrics"]["dli_mol_m2_day"],
    "mean_far_red": current["metrics"]["mean_far_red_umol_m2_s"],
}, indent=2))
