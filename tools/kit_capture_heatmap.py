"""Headless Kit/RTX capture for the generated OpenGrowTwin PPFD heatmap.

Run this file with the generated Kit application launcher via --exec.
It intentionally uses only modules supplied by Kit.
"""

from __future__ import annotations

import asyncio
import os
import traceback

import omni.kit.app
import omni.usd
from omni.kit.viewport.utility import (
    capture_viewport_to_file,
    create_viewport_window,
    frame_viewport_prims,
    next_viewport_frame_async,
)


PROJECT_ROOT = os.environ.get(
    "OPENGROW_ROOT",
    "/home/chris_sevilla_v_de/projects/OpenGrowTwin",
)
STAGE_PATH = os.path.join(PROJECT_ROOT, "build", "optimization", "ppfd_heatmap.usda")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "build", "captures")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "ppfd_heatmap_rtx.png")
MESH_PATH = "/OpenGrowTwinResults/PPFDHeatmap"


async def capture() -> None:
    app = omni.kit.app.get_app()
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

        # Allow USD population and renderer resources to initialize.
        for _ in range(10):
            await app.next_update_async()

        stage = context.get_stage()
        if stage is None:
            raise RuntimeError("No USD stage is active after opening the result layer")
        mesh = stage.GetPrimAtPath(MESH_PATH)
        if not mesh.IsValid():
            raise RuntimeError(f"Missing mesh prim: {MESH_PATH}")

        ppfd = mesh.GetAttribute("primvars:opengrow:ppfd").Get()
        colors = mesh.GetAttribute("primvars:displayColor").Get()
        if not ppfd or len(ppfd) != 1025:
            raise RuntimeError(f"Unexpected PPFD value count: {len(ppfd) if ppfd else 0}")
        if not colors or len(colors) != 1025:
            raise RuntimeError(
                f"Unexpected display-color count: {len(colors) if colors else 0}"
            )

        print(
            f"[OpenGrowTwin] Stage valid; PPFD={len(ppfd)}, colors={len(colors)}, "
            f"range=({min(ppfd):.3f}, {max(ppfd):.3f})",
            flush=True,
        )

        viewport_window = create_viewport_window(
            name="OpenGrowTwinCapture",
            width=1280,
            height=720,
        )
        if viewport_window is None:
            raise RuntimeError("Kit could not create the off-screen viewport")
        viewport = viewport_window.viewport_api
        frame_viewport_prims(viewport, prims=[MESH_PATH])

        print("[OpenGrowTwin] Waiting for RTX frames", flush=True)
        await next_viewport_frame_async(viewport, n_frames=60)

        print(f"[OpenGrowTwin] Capturing: {OUTPUT_PATH}", flush=True)
        helper = capture_viewport_to_file(viewport, file_path=OUTPUT_PATH)
        await helper.wait_for_result(completion_frames=30)

        if not os.path.isfile(OUTPUT_PATH) or os.path.getsize(OUTPUT_PATH) == 0:
            raise RuntimeError("Viewport capture did not produce a non-empty image")

        print(
            f"[OpenGrowTwin] RTX CAPTURE PASSED: {OUTPUT_PATH} "
            f"({os.path.getsize(OUTPUT_PATH)} bytes)",
            flush=True,
        )
    except Exception:
        print("[OpenGrowTwin] RTX CAPTURE FAILED", flush=True)
        traceback.print_exc()
    finally:
        app.post_quit()


asyncio.ensure_future(capture())
