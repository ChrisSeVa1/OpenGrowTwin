"""Scientific display section for the OpenGrowTwin Kit panel."""

from __future__ import annotations

import omni.ui as ui
import omni.usd
from pxr import Sdf

from opengrow.display_state import optical_model_summary, ppfd_legend, spectrum_plot_curves
from opengrow.usd.live_results import set_heatmap_visualization_mode
from opengrow.virtual_sensor import VirtualSensorState
from .viewport_sensor import ViewportSensorController


# omni.ui packed colors are AABBGGRR. These are the same five viridis anchors
# used by the scientific heatmap in opengrow.usd.live_results.
_PPFD_LEGEND_COLORS = (
    0xFF540144,
    0xFF8B523B,
    0xFF8C9121,
    0xFF62C95E,
    0xFF25E7FD,
)

_FIXTURE_PATH = "/World/GrowInstallation/Fixtures/Fixture_01"
_OPTICAL_MODEL_ATTR = "opengrow:activeOpticalModel"


class ScientificPanel:
    """Render optical-model, spectrum, legend, viewport, and sensor state."""

    _PLOT_SAMPLE_COUNT = 211

    def __init__(self, manufacturer_available: bool):
        self._manufacturer_available = bool(manufacturer_available)
        self._optical_model = None
        self._optical_model_subscription = None
        self._viewport_mode = None
        self._viewport_mode_subscription = None
        self._active_model = None
        self._profiles = None
        self._provenance = None
        self._plot_blue = None
        self._plot_red = None
        self._plot_far_red = None
        self._legend_min = None
        self._legend_max = None
        self._legend_unit = None
        self._sensor_enabled = None
        self._sensor_status = None
        self._sensor_position = None
        self._sensor_values = None
        self._sensor_toggle_subscription = None
        self._displayed_result = None
        self._sensor_state = VirtualSensorState()
        self._viewport_sensor = ViewportSensorController(
            on_pick=self._on_viewport_pick,
            on_status=self.set_sensor_status,
        )

    def build(self):
        ui.Separator(height=4)
        ui.Label("Optical Model", height=24)
        default_index = 0 if self._manufacturer_available else 1
        self._optical_model = ui.ComboBox(
            default_index,
            "Manufacturer IES + SPD",
            "Simplified / Lambertian",
        )
        self._optical_model_subscription = self._optical_model.model.get_item_value_model().subscribe_value_changed_fn(
            self._on_optical_model_changed
        )
        self._active_model = ui.Label(
            "Manufacturer bundle available" if self._manufacturer_available else "Manufacturer bundle unavailable",
            word_wrap=True,
            height=22,
        )
        self._profiles = ui.Label("Profiles: run simulation to resolve active optics", word_wrap=True, height=48)

        ui.Label("Spectrum", height=22)
        self._provenance = ui.Label(
            "Run simulation to display active spectral model",
            word_wrap=True,
            height=22,
        )
        zeros = [0.0] * self._PLOT_SAMPLE_COUNT
        with ui.ZStack(height=125):
            ui.Rectangle(style={"background_color": 0xFF202020})
            self._plot_blue = ui.Plot(
                ui.Type.LINE, 0.0, 1.0, *zeros, height=125,
                style={"color": 0xFFFF7040, "background_color": 0x00000000},
            )
            self._plot_red = ui.Plot(
                ui.Type.LINE, 0.0, 1.0, *zeros, height=125,
                style={"color": 0xFF4040FF, "background_color": 0x00000000},
            )
            self._plot_far_red = ui.Plot(
                ui.Type.LINE, 0.0, 1.0, *zeros, height=125,
                style={"color": 0xFF8050B0, "background_color": 0x00000000},
            )
        with ui.HStack(height=20):
            ui.Label("380 nm", width=70)
            ui.Spacer()
            ui.Label("Relative spectral power", alignment=ui.Alignment.CENTER)
            ui.Spacer()
            ui.Label("800 nm", width=70)

        ui.Label("PPFD Heatmap", height=22)
        with ui.HStack(height=28, spacing=6):
            self._legend_min = ui.Label("--", width=58)
            with ui.HStack(spacing=0, height=22):
                for color in _PPFD_LEGEND_COLORS:
                    ui.Rectangle(style={"background_color": color}, width=ui.Fraction(1))
            self._legend_max = ui.Label("--", width=58)
        self._legend_unit = ui.Label("µmol m⁻² s⁻¹", alignment=ui.Alignment.CENTER, height=20)

        ui.Label("Viewport Display", height=22)
        self._viewport_mode = ui.ComboBox(
            0,
            "Scientific PPFD",
            "RTX LED Colors",
            "Combined",
        )
        self._viewport_mode_subscription = self._viewport_mode.model.get_item_value_model().subscribe_value_changed_fn(
            self._on_viewport_mode_changed
        )
        ui.Label(
            "Scientific = deterministic false color; RTX = visual LED color only; Combined = transparent scientific overlay.",
            word_wrap=True,
            height=40,
        )

        ui.Separator(height=4)
        ui.Label("Virtual Quantum Sensor", height=24)
        with ui.HStack(height=26, spacing=8):
            self._sensor_enabled = ui.CheckBox(width=22)
            ui.Label("Enable sensor selection")
        self._sensor_toggle_subscription = self._sensor_enabled.model.subscribe_value_changed_fn(
            self._on_sensor_toggle
        )
        self._sensor_status = ui.Label(
            "Enable selection, then choose a canopy point.", word_wrap=True, height=34
        )
        self._sensor_position = ui.Label("Position: --", word_wrap=True, height=22)
        self._sensor_values = ui.Label(
            "PPFD: --\nDLI: --\nFar-red: --\nBlue: --\nRed: --",
            word_wrap=True,
            height=92,
        )
        ui.Button("Clear Sensor", height=30, clicked_fn=self._clear_sensor_clicked)

    def _on_optical_model_changed(self, model):
        """Persist optical-model selection on the authoritative fixture USD prim."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return
        fixture = stage.GetPrimAtPath(_FIXTURE_PATH)
        if not fixture:
            return
        selected = "manufacturer" if int(model.as_int) == 0 else "simplified"
        fixture.CreateAttribute(_OPTICAL_MODEL_ATTR, Sdf.ValueTypeNames.Token, custom=True).Set(selected)

    def _on_viewport_mode_changed(self, model):
        """Switch scientific/RTX viewport presentation without rerunning physics."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return
        index = int(model.as_int)
        mode = ("scientific", "rtx", "combined")[max(0, min(index, 2))]
        set_heatmap_visualization_mode(stage, mode)

    def sensor_selection_enabled(self) -> bool:
        return bool(self._sensor_enabled and self._sensor_enabled.model.as_bool)

    def _on_sensor_toggle(self, model):
        enabled = bool(model.as_bool)
        if enabled and self._displayed_result is None:
            self.set_sensor_status("Run a simulation before selecting a sensor point.")
            return
        self._viewport_sensor.set_enabled(enabled)

    def _on_viewport_pick(self, world_point_m, prim_path: str):
        if self._displayed_result is None:
            self.set_sensor_status("Run a simulation before selecting a sensor point.")
            return
        sample = self._sensor_state.select(self._displayed_result, world_point_m)
        self.update_sensor(sample)
        ViewportSensorController.update_marker(self._sensor_state.world_point_m)
        self.set_sensor_status(f"Sensor selected from {prim_path}; bilinear scientific sample active.")

    def _clear_sensor_clicked(self):
        self._sensor_state.clear()
        ViewportSensorController.clear_marker()
        self.clear_sensor()

    def clear_sensor(self):
        self._sensor_position.text = "Position: --"
        self._sensor_values.text = "PPFD: --\nDLI: --\nFar-red: --\nBlue: --\nRed: --"
        if self.sensor_selection_enabled():
            self._sensor_status.text = "Sensor cleared. Click the canopy or PPFD heatmap to place it again."
        else:
            self._sensor_status.text = "Enable selection, then choose a canopy point."

    def set_sensor_status(self, text: str):
        if self._sensor_status is not None:
            self._sensor_status.text = str(text)

    def update_sensor(self, sensor: dict):
        """Render one bilinearly sampled sensor result in the existing panel."""
        u, v = sensor["grid_uv_m"]
        channels = sensor.get("channel_ppfd_umol_m2_s", {})
        self._sensor_position.text = f"Position: X {u:+.3f} m   Y {v:+.3f} m"
        self._sensor_values.text = (
            f"PPFD: {sensor['ppfd_umol_m2_s']:.2f} µmol m⁻² s⁻¹\n"
            f"DLI: {sensor['dli_mol_m2_day']:.3f} mol m⁻² day⁻¹\n"
            f"Far-red: {sensor['far_red_umol_m2_s']:.2f} µmol m⁻² s⁻¹\n"
            f"Blue: {channels.get('blue', 0.0):.2f} µmol m⁻² s⁻¹\n"
            f"Red: {channels.get('red', 0.0):.2f} µmol m⁻² s⁻¹"
        )

    def selected_optical_model(self) -> str:
        """Return the real scientific optical-model selection."""
        index = self._optical_model.model.get_item_value_model().as_int
        return "manufacturer" if index == 0 else "simplified"

    def update_from_result(self, result: dict):
        """Update all scientific widgets from one authoritative displayed result."""
        self._displayed_result = result
        design = result["design"]
        summary = optical_model_summary(design)
        self._active_model.text = f"Active: {summary['label']}"
        if summary["profiles"]:
            profiles = {item["channel_id"]: item["part_number"] for item in summary["profiles"]}
            self._profiles.text = (
                f"Blue: {profiles.get('blue', '--')}\n"
                f"Red: {profiles.get('red', '--')}\n"
                f"Far-red: {profiles.get('far_red', '--')}"
            )
        else:
            self._profiles.text = "Profiles: nominal wavelength / generalized Lambertian fallback"

        plot = spectrum_plot_curves(
            design, minimum_nm=380.0, maximum_nm=800.0, sample_count=self._PLOT_SAMPLE_COUNT
        )
        curves = plot["curves"]
        self._plot_blue.set_data(*curves.get("blue", [0.0] * self._PLOT_SAMPLE_COUNT))
        self._plot_red.set_data(*curves.get("red", [0.0] * self._PLOT_SAMPLE_COUNT))
        self._plot_far_red.set_data(*curves.get("far_red", [0.0] * self._PLOT_SAMPLE_COUNT))

        provenance = sorted({item.get("provenance_kind", "unknown") for item in plot["metadata"].values()})
        self._provenance.text = "Spectrum: " + ", ".join(provenance)

        shared = result.get("display_legend_range")
        if shared is not None and len(shared) == 2:
            self._legend_min.text = f"{float(shared[0]):.2f}"
            self._legend_max.text = f"{float(shared[1]):.2f}"
            self._legend_unit.text = "µmol m⁻² s⁻¹"
        else:
            legend = ppfd_legend(result)
            self._legend_min.text = f"{legend['minimum']:.2f}"
            self._legend_max.text = f"{legend['maximum']:.2f}"
            self._legend_unit.text = legend["unit"]

        sample = self._sensor_state.sample(result)
        if sample is not None:
            self.update_sensor(sample)
            self.set_sensor_status("Sensor refreshed from the displayed simulation result.")
        if self.sensor_selection_enabled() and not self._viewport_sensor.enabled:
            self._viewport_sensor.set_enabled(True)
