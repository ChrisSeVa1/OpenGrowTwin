"""True headless RTX render-product capture for OpenGrowTwin.

Run with the generated Kit launcher via --exec and enable:
omni.kit.capture.viewport, omni.graph, omni.graph.nodes, and
omni.graph.examples.cpp.
"""

from __future__ import annotations

import asyncio
import os
import traceback

import omni.kit.app
import omni.usd
from omni.kit.capture.viewport import (
    CaptureExtension,
    CaptureOptions,
    CaptureRenderPreset,
)
from pxr import Gf, UsdGeom, UsdLux, UsdRender


PROJECT_ROOT = os.environ.get(
    "OPENGROW_ROOT",
    "/home/chris_sevilla_v_de/projects/OpenGrowTwin",
)
STAGE_PATH = os.path.join(PROJECT_ROOT, "build", "optimization", "ppfd_heatmap.usda")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "build", "captures")
OUTPUT_STEM = "ppfd_heatmap_rtx"
MESH_PATH = "/OpenGrowTwinResults/PPFDHeatmap"
CAMERA_PATH = "/OpenGrowTwinResults/CaptureCamera"
LIGHT_PATH = "/OpenGrowTwinResults/CaptureDomeLight"
RENDER_PRODUCT_PATH = "/Render/OpenGrowTwinProduct"
RENDER_SETTINGS_PATH = "/Render/OpenGrowTwinSettings"


async def capture() -> None:
    app = omni.kit.app.get_app()
    failed = False
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if not os.path.isfile(STAGE_PATH):
            raise FileNotFoundError(
                f"Missing {STAGE_PATH}; run 'python -m opengrow optimize ...' first"
            )

        print(f"[OpenGrowTwin] Opening stage: {STAGE_PATH}", flush=True)
        context = omni.usd.get_context()
        opened = context.open_stage(STAGE_PATH)
        if opened is False:
            raise RuntimeError("Kit reported that the stage could not be opened")
        for _ in range(20):
            await app.next_update_async()

        stage = context.get_stage()
        if stage is None:
            raise RuntimeError("No USD stage is active")
        mesh = stage.GetPrimAtPath(MESH_PATH)
        if not mesh.IsValid():
            raise RuntimeError(f"Missing mesh prim: {MESH_PATH}")
        ppfd = mesh.GetAttribute("primvars:opengrow:ppfd").Get()
        colors = mesh.GetAttribute("primvars:displayColor").Get()
        if not ppfd or len(ppfd) != 1025:
            raise RuntimeError(f"Unexpected PPFD count: {len(ppfd) if ppfd else 0}")
        if not colors or len(colors) != 1025:
            raise RuntimeError(f"Unexpected color count: {len(colors) if colors else 0}")
        print(
            f"[OpenGrowTwin] Stage valid; PPFD={len(ppfd)}, colors={len(colors)}, "
            f"range=({min(ppfd):.3f}, {max(ppfd):.3f})",
            flush=True,
        )

        # A top-down camera: USD cameras look down local -Z, so translation is
        # sufficient for the horizontal heatmap centered at the origin.
        camera = UsdGeom.Camera.Define(stage, CAMERA_PATH)
        camera.CreateProjectionAttr("perspective")
        camera.CreateHorizontalApertureAttr(20.955)
        camera.CreateVerticalApertureAttr(11.787)
        camera.CreateFocalLengthAttr(50.0)
        camera.CreateClippingRangeAttr(Gf.Vec2f(0.01, 100.0))
        UsdGeom.Xformable(camera).AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, 3.0))

        light = UsdLux.DomeLight.Define(stage, LIGHT_PATH)
        light.CreateIntensityAttr(800.0)

        product = UsdRender.Product.Define(stage, RENDER_PRODUCT_PATH)
        product.CreateCameraRel().SetTargets([camera.GetPath()])
        product.CreateResolutionAttr(Gf.Vec2i(1280, 720))
        settings = UsdRender.Settings.Define(stage, RENDER_SETTINGS_PATH)
        settings.CreateProductsRel().SetTargets([product.GetPath()])

        print("[OpenGrowTwin] Starting headless RTX render product", flush=True)
        capture_instance = CaptureExtension.get_instance()
        options = CaptureOptions()
        options.camera = CAMERA_PATH
        options.output_folder = OUTPUT_DIR
        options.file_name = OUTPUT_STEM
        options.file_type = ".png"
        options.render_preset = CaptureRenderPreset.PATH_TRACE
        options.render_product = RENDER_PRODUCT_PATH
        capture_instance.options = options
        if not capture_instance.start():
            raise RuntimeError("CaptureExtension refused to start the render")

        while not capture_instance.done:
            await app.next_update_async()
        outputs = capture_instance.get_outputs()
        print(f"[OpenGrowTwin] Capture outputs: {outputs}", flush=True)
        existing = [
            path for path in outputs
            if isinstance(path, str) and os.path.isfile(path) and os.path.getsize(path) > 0
        ]
        if not existing:
            raise RuntimeError("Render-product capture produced no non-empty image")
        for path in existing:
            print(
                f"[OpenGrowTwin] RTX CAPTURE PASSED: {path} "
                f"({os.path.getsize(path)} bytes)",
                flush=True,
            )
    except Exception:
        failed = True
        print("[OpenGrowTwin] RTX CAPTURE FAILED", flush=True)
        traceback.print_exc()
    finally:
        # Give renderer tasks time to retire before shutdown.
        for _ in range(20):
            await app.next_update_async()
        app.post_quit(1 if failed else 0)


asyncio.ensure_future(capture())
