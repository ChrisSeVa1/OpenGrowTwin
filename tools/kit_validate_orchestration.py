"""OGT-104 acceptance for extension loading and simulation orchestration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import omni.kit.app
from pxr import Usd


repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository / "src"))

from opengrow.orchestration import simulate_stage  # noqa: E402


manager = omni.kit.app.get_app().get_extension_manager()
if not manager.is_extension_enabled("opengrow.twin"):
    raise AssertionError("opengrow.twin extension is not enabled")
stage = Usd.Stage.Open(str(repository / "demo" / "grow_chamber.usda"))
if stage is None:
    raise RuntimeError("could not open demo/grow_chamber.usda")

preview = simulate_stage(stage, "preview")
final = simulate_stage(stage, "final")
if preview["mode_shape"] != [21, 13]:
    raise AssertionError(f"unexpected preview shape {preview['mode_shape']}")
if final["mode_shape"] != [41, 25]:
    raise AssertionError(f"unexpected final shape {final['mode_shape']}")
mean_difference_fraction = abs(
    preview["metrics"]["mean_ppfd_umol_m2_s"] - final["metrics"]["mean_ppfd_umol_m2_s"]
) / final["metrics"]["mean_ppfd_umol_m2_s"]
if mean_difference_fraction > 0.02:
    raise AssertionError("preview and final mean PPFD diverge unexpectedly")

print("[OpenGrowTwin] OGT-104 Kit orchestration valid")
print(json.dumps({
    "extension_enabled": True,
    "preview_shape": preview["mode_shape"],
    "final_shape": final["mode_shape"],
    "preview_mean_ppfd": preview["metrics"]["mean_ppfd_umol_m2_s"],
    "final_mean_ppfd": final["metrics"]["mean_ppfd_umol_m2_s"],
    "mean_difference_fraction": mean_difference_fraction,
    "preview_total_rays": preview["total_ray_count"],
    "final_total_rays": final["total_ray_count"],
}, indent=2))
