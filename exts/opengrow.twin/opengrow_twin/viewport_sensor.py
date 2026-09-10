"""Viewport interaction for the OpenGrowTwin virtual quantum sensor."""

from __future__ import annotations

from typing import Callable, Iterable

import omni.ui.scene as sc
import omni.usd
from omni.kit.viewport.utility import get_active_viewport_and_window
from pxr import Gf, Sdf, UsdGeom


MARKER_PATH = "/World/GrowInstallation/Results/VirtualSensorMarker"


class ViewportSensorController:
    """Attach an opt-in viewport click layer and author a visual-only sensor marker."""

    def __init__(
        self,
        on_pick: Callable[[Iterable[float], str], None],
        on_status: Callable[[str], None],
    ):
        self._on_pick = on_pick
        self._on_status = on_status
        self._viewport_api = None
        self._viewport_window = None
        self._scene_view = None
        self._screen = None

    @property
    def enabled(self) -> bool:
        return self._scene_view is not None

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self._attach()
        else:
            self._detach()

    def _attach(self) -> None:
        if self.enabled:
            return
        viewport_api, window = get_active_viewport_and_window()
        if viewport_api is None or window is None:
            self._on_status("No active viewport available for sensor selection.")
            return
        self._viewport_api = viewport_api
        self._viewport_window = window
        with window.get_frame("opengrow_virtual_sensor"):
            self._scene_view = sc.SceneView()
            viewport_api.add_scene_view(self._scene_view)
            with self._scene_view.scene:
                self._screen = sc.Screen(
                    gesture=sc.ClickGesture(
                        name="OpenGrowTwin virtual sensor pick",
                        on_ended_fn=self._on_click,
                    )
                )
        self._on_status("Sensor selection active: click the canopy or PPFD heatmap.")

    def _detach(self) -> None:
        if self._viewport_api is not None and self._scene_view is not None:
            try:
                self._viewport_api.remove_scene_view(self._scene_view)
            except Exception:
                pass
        self._screen = None
        self._scene_view = None
        self._viewport_api = None
        self._viewport_window = None
        self._on_status("Sensor selection disabled; existing sensor remains active.")

    def _on_click(self, shape) -> None:
        if self._viewport_api is None:
            return
        try:
            mouse_ndc = shape.gesture_payload.mouse
            pixel, in_viewport = self._viewport_api.map_ndc_to_texture_pixel(mouse_ndc)
            if not in_viewport:
                self._on_status("Sensor click was outside the rendered viewport.")
                return
            self._viewport_api.request_query(
                pixel,
                self._on_query_complete,
                query_name="opengrow_virtual_sensor",
            )
        except Exception as exc:
            self._on_status(f"Sensor pick error: {exc}")

    def _on_query_complete(self, prim_path, world_pos, *args) -> None:
        if not prim_path:
            self._on_status("No scene surface was hit. Click the canopy or heatmap.")
            return
        try:
            self._on_pick(world_pos, str(prim_path))
        except Exception as exc:
            self._on_status(f"Sensor selection rejected: {exc}")

    @staticmethod
    def update_marker(world_point_m: Iterable[float]) -> None:
        """Author/update a small visual-only USD marker above the selected point."""
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        point = [float(v) for v in world_point_m]
        if len(point) != 3:
            raise ValueError("sensor marker requires a three-vector")
        UsdGeom.Xform.Define(stage, "/World/GrowInstallation/Results")
        sphere = UsdGeom.Sphere.Define(stage, MARKER_PATH)
        sphere.CreateRadiusAttr(0.012)
        UsdGeom.XformCommonAPI(sphere).SetTranslate(Gf.Vec3d(point[0], point[1], point[2] + 0.008))
        sphere.CreateDisplayColorPrimvar(UsdGeom.Tokens.constant).Set(
            [(1.0, 0.9, 0.1)]
        )
        prim = sphere.GetPrim()
        prim.CreateAttribute("opengrow:role", Sdf.ValueTypeNames.Token, custom=True).Set("virtualSensorMarker")
        prim.CreateAttribute("opengrow:visualOnly", Sdf.ValueTypeNames.Bool, custom=True).Set(True)

    @staticmethod
    def clear_marker() -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is not None and stage.GetPrimAtPath(MARKER_PATH):
            stage.RemovePrim(MARKER_PATH)
