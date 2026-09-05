#!/usr/bin/env python3
"""Validate manufacturer IES binding on synchronized RTX lights inside Kit.

Vendor IES files are expected under ``sources/osram/extracted`` and remain
user-supplied/local. The validator verifies authored UsdLux shaping attributes
without committing or redistributing manufacturer assets.
"""

from __future__ import annotations

from pathlib import Path

from pxr import Usd, UsdLux

from opengrow.usd.rtx_lights import sync_rtx_lights


PROJECT = Path(__file__).resolve().parents[1]
STAGE_PATH = PROJECT / "demo/grow_chamber.usda"
ASSET_ROOT = PROJECT / "sources/osram/extracted"

IES_BY_CHANNEL = {
    "blue": str(ASSET_ROOT / "GD_PUBRA1_15_20250529.ies"),
    "red": str(ASSET_ROOT / "GH_PUBRA1_25_20250526.ies"),
    "far_red": str(ASSET_ROOT / "GF_PUBRA1_25_20250603.ies"),
}


def main() -> None:
    print("=== OGT-301A STEP 6 RTX IES VALIDATION ===")
    print("stage:", STAGE_PATH)

    stage = Usd.Stage.Open(str(STAGE_PATH))
    if stage is None:
        raise RuntimeError(f"Could not open stage: {STAGE_PATH}")

    emitters = []
    for prim in stage.Traverse():
        if not prim.HasAttribute("opengrow:role"):
            continue
        if str(prim.GetAttribute("opengrow:role").Get()) == "emitter":
            emitters.append(str(prim.GetPath()))

    print("scientific_emitter_count:", len(emitters))
    assert len(emitters) == 20

    for channel, path in IES_BY_CHANNEL.items():
        assert Path(path).is_file(), f"Missing {channel} IES: {path}"

    result = sync_rtx_lights(stage, ies_by_channel=IES_BY_CHANNEL)

    print("light_count:", result["light_count"])
    print("ies_channel_count:", result["ies_channel_count"])

    manufacturer_count = 0
    for item in result["lights"]:
        light_prim = stage.GetPrimAtPath(item["light_path"])
        assert light_prim.IsValid()

        shaping = UsdLux.ShapingAPI(light_prim)
        ies_file = shaping.GetShapingIesFileAttr().Get()
        ies_normalize = shaping.GetShapingIesNormalizeAttr().Get()
        ies_angle_scale = shaping.GetShapingIesAngleScaleAttr().Get()

        visual_only = light_prim.GetAttribute("opengrow:visualOnly").Get()
        source_path = light_prim.GetAttribute("opengrow:scientificSourcePath").Get()

        if item["angular_model"] == "manufacturer_ies":
            manufacturer_count += 1

        print(
            item["channel"],
            item["light_path"],
            "IES=", ies_file,
            "normalize=", ies_normalize,
            "angleScale=", ies_angle_scale,
            "visualOnly=", visual_only,
            "source=", source_path,
        )

        assert ies_file is not None
        assert bool(ies_normalize) is True
        assert float(ies_angle_scale) == 1.0
        assert bool(visual_only) is True
        assert str(source_path) == item["emitter_path"]

    print("manufacturer_ies_light_count:", manufacturer_count)

    assert result["light_count"] == 20
    assert result["ies_channel_count"] == 3
    assert manufacturer_count == 20

    print("PASS: 20 scientific emitters synchronized to RTX")
    print("PASS: all 20 RTX lights carry manufacturer IES shaping")
    print("PASS: RTX lights remain explicitly visualOnly")
    print("=== END VALIDATION ===")


if __name__ == "__main__":
    main()
