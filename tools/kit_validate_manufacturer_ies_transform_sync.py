#!/usr/bin/env python3
"""Validate shared OpenUSD orientation for scientific IES transport and RTX.

The validator rotates one scientific emitter by +90 degrees about local Z,
proves the Kit-side discovery orientation and inherited RTX-light orientation
remain identical, and verifies the manufacturer-IES field rotates about the
same optical axis. Vendor IES files remain local and are not redistributed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdLux

from opengrow.physics.direct_solver import manufacturer_ies_irradiance, sensor_grid
from opengrow.physics.photometry import load_ies
from opengrow.usd.rtx_lights import sync_rtx_lights
from opengrow.usd.stage_reader import discover_stage


PROJECT = Path(__file__).resolve().parents[1]
STAGE_PATH = PROJECT / "demo/grow_chamber.usda"
ASSET_ROOT = PROJECT / "sources/osram/extracted"
IES_PATH = ASSET_ROOT / "GD_PUBRA1_15_20250529.ies"

EMITTER_PATH = "/World/GrowInstallation/Fixtures/Fixture_01/Emitters/Blue_01"
RTX_PATH = EMITTER_PATH + "/RTXLight"

IES_BY_CHANNEL = {
    "blue": str(ASSET_ROOT / "GD_PUBRA1_15_20250529.ies"),
    "red": str(ASSET_ROOT / "GH_PUBRA1_25_20250526.ies"),
    "far_red": str(ASSET_ROOT / "GF_PUBRA1_25_20250603.ies"),
}


def _matrix3_from_world_xform(matrix4):
    axes = []
    for vector in (
        Gf.Vec3d(1, 0, 0),
        Gf.Vec3d(0, 1, 0),
        Gf.Vec3d(0, 0, 1),
    ):
        axes.append(matrix4.TransformDir(vector).GetNormalized())
    return np.array(
        [[axes[column][row] for column in range(3)] for row in range(3)],
        dtype=float,
    )


def _discovered_emitter(stage, path: str) -> dict:
    discovered = discover_stage(stage)
    for item in discovered["entities"]["emitter"]:
        if item["path"] == path:
            return item
    raise RuntimeError(f"Emitter not found: {path}")


def main() -> None:
    print("=== OGT-301A STEP 6 TRANSFORM SYNC ===")

    stage = Usd.Stage.Open(str(STAGE_PATH))
    if stage is None:
        raise RuntimeError(f"Could not open stage: {STAGE_PATH}")

    for channel, path in IES_BY_CHANNEL.items():
        assert Path(path).is_file(), f"Missing {channel} IES: {path}"

    sync_rtx_lights(stage, ies_by_channel=IES_BY_CHANNEL)

    emitter_prim = stage.GetPrimAtPath(EMITTER_PATH)
    rtx_prim = stage.GetPrimAtPath(RTX_PATH)
    assert emitter_prim.IsValid()
    assert rtx_prim.IsValid()

    baseline_record = _discovered_emitter(stage, EMITTER_PATH)
    baseline_science_orientation = np.asarray(
        baseline_record["orientation_matrix"], dtype=float
    )

    cache = UsdGeom.XformCache()
    baseline_emitter_orientation = _matrix3_from_world_xform(
        cache.GetLocalToWorldTransform(emitter_prim)
    )
    baseline_rtx_orientation = _matrix3_from_world_xform(
        cache.GetLocalToWorldTransform(rtx_prim)
    )

    assert np.allclose(
        baseline_science_orientation, baseline_emitter_orientation, atol=1e-10
    )
    assert np.allclose(
        baseline_rtx_orientation, baseline_emitter_orientation, atol=1e-10
    )
    print("baseline_science_equals_emitter_world: PASS")
    print("baseline_rtx_inherits_emitter_world: PASS")

    angular_distribution = load_ies(IES_PATH)
    bx, by, _ = baseline_record["position_m"]
    # Center the square validator under the emitter optical axis so a physical
    # azimuth rotation can be compared directly with a quarter-turn of the array.
    grid = sensor_grid(
        width_m=1.0,
        depth_m=1.0,
        nx=41,
        ny=41,
        center_m=[bx, by, 0.0],
    )

    baseline_field = manufacturer_ies_irradiance(
        grid,
        baseline_record["position_m"],
        1.0,
        angular_distribution,
        baseline_science_orientation,
    )

    xformable = UsdGeom.Xformable(emitter_prim)
    rotate_op = None
    for op in xformable.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeRotateZ:
            rotate_op = op
            break
    if rotate_op is None:
        rotate_op = xformable.AddRotateZOp(opSuffix="ogt301aValidation")
    rotate_op.Set(90.0)

    rotated_record = _discovered_emitter(stage, EMITTER_PATH)
    rotated_science_orientation = np.asarray(
        rotated_record["orientation_matrix"], dtype=float
    )

    cache = UsdGeom.XformCache()
    rotated_emitter_orientation = _matrix3_from_world_xform(
        cache.GetLocalToWorldTransform(emitter_prim)
    )
    rotated_rtx_orientation = _matrix3_from_world_xform(
        cache.GetLocalToWorldTransform(rtx_prim)
    )

    assert np.allclose(
        rotated_science_orientation, rotated_emitter_orientation, atol=1e-10
    )
    assert np.allclose(
        rotated_rtx_orientation, rotated_emitter_orientation, atol=1e-10
    )
    print("rotated_science_equals_emitter_world: PASS")
    print("rotated_rtx_inherits_emitter_world: PASS")

    angle = np.deg2rad(90.0)
    rz90 = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    expected_orientation = rz90 @ baseline_science_orientation
    rotation_matrix_error = float(
        np.max(np.abs(rotated_science_orientation - expected_orientation))
    )
    print("rotation_matrix_max_abs_error:", rotation_matrix_error)
    assert rotation_matrix_error < 1e-10
    print("scientific_orientation_is_exact_plus90Z: PASS")

    shaping = UsdLux.ShapingAPI(rtx_prim)
    assert shaping.GetShapingIesFileAttr().Get() is not None
    assert bool(shaping.GetShapingIesNormalizeAttr().Get()) is True
    assert float(shaping.GetShapingIesAngleScaleAttr().Get()) == 1.0
    print("rtx_ies_survives_transform_edit: PASS")

    rotated_field = manufacturer_ies_irradiance(
        grid,
        rotated_record["position_m"],
        1.0,
        angular_distribution,
        rotated_science_orientation,
    )
    # sensor_grid increases +Y with row index, so physical +90 degrees about +Z
    # corresponds to a clockwise quarter-turn in array coordinates.
    expected_rotated_field = np.rot90(baseline_field, k=-1)
    peak = float(np.max(np.abs(baseline_field)))
    max_abs_error = float(np.max(np.abs(rotated_field - expected_rotated_field)))
    fraction_of_peak = max_abs_error / peak if peak > 0.0 else 0.0

    print("field_rotation_max_abs_error:", max_abs_error)
    print("field_rotation_error_fraction_of_peak:", fraction_of_peak)
    assert fraction_of_peak < 1e-10
    print("scientific_ies_field_rotates_with_usd_transform: PASS")

    print("emitter_path:", EMITTER_PATH)
    print("rtx_path:", RTX_PATH)
    print(
        "scientific_orientation_after_rotation:",
        rotated_science_orientation.tolist(),
    )
    print("rtx_orientation_after_rotation:", rotated_rtx_orientation.tolist())
    print("PASS: scientific solver and RTX share authoritative OpenUSD transform")
    print("=== END VALIDATION ===")


if __name__ == "__main__":
    main()
