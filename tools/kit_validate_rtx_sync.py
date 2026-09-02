"""OGT-106 acceptance: scientific emitter state drives RTX light state."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pxr import Usd


repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository / "src"))

from opengrow.orchestration import simulate_stage  # noqa: E402
from opengrow.usd.rtx_lights import RTX_LIGHT_NAME, sync_rtx_lights  # noqa: E402


stage = Usd.Stage.Open(str(repository / "demo" / "grow_chamber.usda"))
if stage is None:
    raise RuntimeError("could not open demo/grow_chamber.usda")
emitter_path = "/World/GrowInstallation/Fixtures/Fixture_01/Emitters/Blue_01"
emitter = stage.GetPrimAtPath(emitter_path)
power = emitter.GetAttribute("opengrow:radiantPowerW")

baseline_sync = sync_rtx_lights(stage)
baseline = simulate_stage(stage, "final")
light = stage.GetPrimAtPath(f"{emitter_path}/{RTX_LIGHT_NAME}")
baseline_intensity = float(light.GetAttribute("inputs:intensity").Get())
power.Set(float(power.Get()) * 2.0)
updated_sync = sync_rtx_lights(stage)
updated = simulate_stage(stage, "final")
updated_intensity = float(light.GetAttribute("inputs:intensity").Get())

if baseline_sync["light_count"] != 20 or updated_sync["light_count"] != 20:
    raise AssertionError("expected one RTX light for each of 20 scientific emitters")
if abs(updated_intensity / baseline_intensity - 2.0) > 1e-12:
    raise AssertionError("RTX intensity did not track scientific radiant power linearly")
if updated["metrics"]["mean_ppfd_umol_m2_s"] <= baseline["metrics"]["mean_ppfd_umol_m2_s"]:
    raise AssertionError("scientific solver did not consume the same updated emitter power")
if list(light.GetAttribute("opengrow:spectrumWavelengthsNm").Get()) != [450.0]:
    raise AssertionError("RTX light spectral provenance is missing")
if not light.GetAttribute("opengrow:visualOnly").Get():
    raise AssertionError("RTX presentation scaling is not clearly labeled")

print("[OpenGrowTwin] OGT-106 RTX/scientific emitter synchronization valid")
print(json.dumps({
    "light_count": updated_sync["light_count"],
    "scientific_emitter_path": emitter_path,
    "baseline_radiant_power_w": 2.25,
    "updated_radiant_power_w": float(power.Get()),
    "baseline_rtx_intensity": baseline_intensity,
    "updated_rtx_intensity": updated_intensity,
    "visual_intensity_scale": updated_sync["intensity_scale"],
    "baseline_mean_ppfd": baseline["metrics"]["mean_ppfd_umol_m2_s"],
    "updated_mean_ppfd": updated["metrics"]["mean_ppfd_umol_m2_s"],
    "spectral_metadata_nm": list(light.GetAttribute("opengrow:spectrumWavelengthsNm").Get()),
    "visual_only": bool(light.GetAttribute("opengrow:visualOnly").Get()),
}, indent=2))
