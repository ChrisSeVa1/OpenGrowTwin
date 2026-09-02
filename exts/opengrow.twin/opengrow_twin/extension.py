"""Kit UI and responsive orchestration for the live OpenGrowTwin stage."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
from pxr import Tf, Usd


REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = str(REPOSITORY / "src")
if SOURCE not in sys.path:
    sys.path.insert(0, SOURCE)

from opengrow.orchestration import prepare_solver_design, run_prepared_design  # noqa: E402
from opengrow.usd.live_results import set_display_mode, update_live_results  # noqa: E402
from opengrow.usd.rtx_lights import sync_rtx_lights  # noqa: E402


class OpenGrowTwinExtension(omni.ext.IExt):
    """Interactive Simulate panel with debounced live-stage updates."""

    def on_startup(self, ext_id):
        self._ext_id = ext_id
        self._run_task = None
        self._debounce_task = None
        self._stage_notice = None
        self._last_result = None
        self._baselines = {}
        self._display_mode = "current"
        settings = carb.settings.get_settings()
        self._auto_simulate = settings.get_as_bool("/exts/opengrow.twin/auto_simulate")
        self._debounce_seconds = settings.get_as_float("/exts/opengrow.twin/debounce_seconds") or 0.25
        self._build_window()
        self._stage_subscription = omni.usd.get_context().get_stage_event_stream().create_subscription_to_pop(
            self._on_stage_event, name="OpenGrowTwin stage lifecycle"
        )
        self._attach_stage_notice()
        print("[OpenGrowTwin] Interactive simulation extension ready")

    def _build_window(self):
        self._window = ui.Window("OpenGrowTwin", width=390, height=300)
        with self._window.frame:
            with ui.VStack(spacing=8, height=0):
                ui.Label("Spectral Lighting Simulation", height=24)
                ui.Label("Grid mode")
                self._mode = ui.ComboBox(0, "Preview (21 × 13)", "Final (authored grid)")
                with ui.HStack(height=34, spacing=8):
                    ui.Button("Simulate", clicked_fn=self._simulate_clicked)
                    ui.Button("Cancel", clicked_fn=self._cancel_run)
                self._comparison_button = ui.Button("Show Baseline", clicked_fn=self._toggle_comparison)
                self._status = ui.Label("Ready", word_wrap=True, height=42)
                self._metrics = ui.Label("No simulation result", word_wrap=True, height=100)

    def _selected_mode(self):
        index = self._mode.model.get_item_value_model().as_int
        return "preview" if index == 0 else "final"

    def _simulate_clicked(self):
        self._start_run(self._selected_mode(), "manual")

    def _cancel_run(self):
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
        self._set_status("Cancelled")

    def _toggle_comparison(self):
        self._display_mode = "baseline" if self._display_mode == "current" else "current"
        stage = omni.usd.get_context().get_stage()
        if stage and self._last_result:
            set_display_mode(stage, self._display_mode)
        self._comparison_button.text = "Show Current" if self._display_mode == "baseline" else "Show Baseline"

    def _on_stage_event(self, event):
        if event.type in (
            int(omni.usd.StageEventType.OPENED),
            int(omni.usd.StageEventType.CLOSED),
        ):
            self._attach_stage_notice()

    def _attach_stage_notice(self):
        if self._stage_notice is not None:
            self._stage_notice.Revoke()
            self._stage_notice = None
        stage = omni.usd.get_context().get_stage()
        if stage:
            self._stage_notice = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, stage)

    def _on_objects_changed(self, notice, sender):
        if not self._auto_simulate:
            return
        changed = list(notice.GetResyncedPaths()) + list(notice.GetChangedInfoOnlyPaths())
        if any(
            "/World/GrowInstallation" in str(path)
            and "/Results" not in str(path)
            and "/RTXLight" not in str(path)
            for path in changed
        ):
            self._schedule_debounced_preview()

    def _schedule_debounced_preview(self):
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        self._debounce_task = asyncio.ensure_future(self._debounced_preview())

    async def _debounced_preview(self):
        try:
            await asyncio.sleep(self._debounce_seconds)
            self._start_run("preview", "stage change")
        except asyncio.CancelledError:
            pass

    def _start_run(self, mode, reason):
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
        self._run_task = asyncio.ensure_future(self._run(mode, reason))

    async def _run(self, mode, reason):
        try:
            stage = omni.usd.get_context().get_stage()
            if not stage:
                raise RuntimeError("Open an OpenGrowTwin stage before simulating")
            self._set_status(f"Reading live stage ({reason})…")
            sync_rtx_lights(stage)
            design = prepare_solver_design(stage, mode)
            self._set_status(f"Simulating {mode} grid…")
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, run_prepared_design, design)
            self._last_result = result
            key = tuple(result["mode_shape"])
            baseline = self._baselines.setdefault(key, result)
            update_live_results(stage, result, baseline, self._display_mode)
            self._show_result(result, mode)
        except asyncio.CancelledError:
            self._set_status("Superseded by a newer simulation")
        except Exception as exc:
            carb.log_error(f"[OpenGrowTwin] Simulation failed: {exc}")
            self._set_status(f"Error: {exc}")

    def _show_result(self, result, mode):
        metrics = result["metrics"]
        blocked = result["blocked_ray_count"]
        total = result["total_ray_count"]
        self._set_status(f"Complete — {mode} {result['mode_shape'][0]} × {result['mode_shape'][1]}")
        self._metrics.text = (
            f"Mean PPFD: {metrics['mean_ppfd_umol_m2_s']:.2f} µmol m⁻² s⁻¹\n"
            f"Min / max: {metrics['min_ppfd_umol_m2_s']:.2f} / {metrics['max_ppfd_umol_m2_s']:.2f}\n"
            f"CV: {metrics['cv_ppfd']:.3f}    Uniformity: {metrics['uniformity_min_mean']:.3f}\n"
            f"DLI: {metrics['dli_mol_m2_day']:.3f} mol m⁻² day⁻¹\n"
            f"Far-red: {metrics['mean_far_red_umol_m2_s']:.2f} µmol m⁻² s⁻¹\n"
            f"Blocked rays: {blocked:,} / {total:,}"
        )
        print(
            f"[OpenGrowTwin] Simulation complete; mode={mode}, shape={result['mode_shape']}, "
            f"mean_ppfd={metrics['mean_ppfd_umol_m2_s']:.6f}, blocked_rays={blocked}/{total}"
        )

    def _set_status(self, text):
        if self._status:
            self._status.text = text

    def on_shutdown(self):
        self._cancel_run()
        if self._stage_notice is not None:
            self._stage_notice.Revoke()
        self._stage_notice = None
        self._stage_subscription = None
        self._window = None
        print("[OpenGrowTwin] Interactive simulation extension shutdown")
