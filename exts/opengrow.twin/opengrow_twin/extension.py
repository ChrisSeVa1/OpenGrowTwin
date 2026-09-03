"""Kit UI and responsive orchestration for the live OpenGrowTwin stage."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
import yaml
from pxr import Tf, Usd


REPOSITORY = Path(__file__).resolve().parents[3]
SOURCE = str(REPOSITORY / "src")
if SOURCE not in sys.path:
    sys.path.insert(0, SOURCE)
for site_packages in sorted((REPOSITORY / ".venv" / "lib").glob("python*/site-packages")):
    if str(site_packages) not in sys.path:
        sys.path.append(str(site_packages))

from opengrow.optimize.live_optimizer import (  # noqa: E402
    LiveOptimizerProposal,
    apply_live_optimizer_proposal,
    propose_live_optimizer,
)
from opengrow.orchestration import prepare_solver_design, run_prepared_design  # noqa: E402
from opengrow.usd.live_results import set_display_mode, update_live_results  # noqa: E402
from opengrow.usd.rtx_lights import sync_rtx_lights  # noqa: E402
from opengrow.usd.stage_reader import discover_stage  # noqa: E402
from .copilot_panel import CopilotPanel  # noqa: E402


class OpenGrowTwinExtension(omni.ext.IExt):
    """Interactive simulation and reviewed live-stage optimization panel."""

    def on_startup(self, ext_id):
        self._ext_id = ext_id
        self._run_task = None
        self._debounce_task = None
        self._stage_notice = None
        self._last_result = None
        self._baselines = {}
        self._display_mode = "current"
        self._runs = {}
        self._run_counter = 0
        self._optimizer_proposal: LiveOptimizerProposal | None = None
        self._copilot = CopilotPanel({
            "inspect_scene": self._copilot_inspect_scene,
            "get_metrics": self._copilot_get_metrics,
            "get_occlusion_summary": self._copilot_get_occlusion_summary,
            "compare_runs": self._copilot_compare_runs,
            "run_simulation": self._copilot_run_simulation,
            "run_optimizer": self._copilot_run_optimizer,
            "set_channel_power": self._copilot_set_channel_power,
        })
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
        self._window = ui.Window("OpenGrowTwin", width=470, height=770)
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
                ui.Separator(height=4)
                ui.Label("Installation Optimizer", height=24)
                with ui.HStack(height=34, spacing=8):
                    ui.Button("Run Optimizer", clicked_fn=self._optimizer_clicked)
                    ui.Button("Apply Proposal", clicked_fn=self._apply_optimizer_clicked)
                    ui.Button("Reject", clicked_fn=self._reject_optimizer_clicked)
                self._optimizer_status = ui.Label(
                    "No optimizer proposal. Running the optimizer never changes the USD stage.",
                    word_wrap=True,
                    height=105,
                )
                self._copilot.build()

    def _selected_mode(self):
        index = self._mode.model.get_item_value_model().as_int
        return "preview" if index == 0 else "final"

    def _simulate_clicked(self):
        self._start_run(self._selected_mode(), "manual")

    def _optimizer_clicked(self):
        try:
            proposal = self._build_optimizer_proposal()
            self._optimizer_proposal = proposal
            self._show_optimizer_proposal(proposal)
        except Exception as exc:
            carb.log_error(f"[OpenGrowTwin] Optimizer proposal failed: {exc}")
            self._optimizer_status.text = f"Optimizer error: {exc}"

    def _apply_optimizer_clicked(self):
        try:
            proposal = self._optimizer_proposal
            if proposal is None:
                raise RuntimeError("Run Optimizer before applying a proposal")
            stage = self._stage()
            result = apply_live_optimizer_proposal(stage, proposal, confirmed=True)
            sync_rtx_lights(stage)
            self._optimizer_proposal = None
            self._optimizer_status.text = (
                f"Applied {result['proposal_id']} after explicit confirmation. "
                "Running final simulation…"
            )
            self._start_run("final", "optimizer applied")
        except Exception as exc:
            carb.log_error(f"[OpenGrowTwin] Optimizer apply failed: {exc}")
            self._optimizer_status.text = f"Apply error: {exc}"

    def _reject_optimizer_clicked(self):
        proposal = self._optimizer_proposal
        self._optimizer_proposal = None
        if proposal is None:
            self._optimizer_status.text = "No optimizer proposal to reject."
        else:
            self._optimizer_status.text = (
                f"Rejected {proposal.proposal_id}. Scene unchanged."
            )

    def _target_record(self):
        path = REPOSITORY / "data" / "targets" / "phalaenopsis_reference.yaml"
        target = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(target, dict):
            raise RuntimeError("approved optimizer target must be a mapping")
        return target

    def _build_optimizer_proposal(self):
        stage = self._stage()
        target = self._target_record()
        design = prepare_solver_design(stage, "final")
        return propose_live_optimizer(
            design,
            target,
            fixture_path="/World/GrowInstallation/Fixtures/Fixture_01",
        )

    def _show_optimizer_proposal(self, proposal):
        powers = ", ".join(
            f"{item['channel_id']}={item['after_total_radiant_power_w']:.3f} W"
            for item in proposal.channel_changes
        )
        mean_ppfd = proposal.predicted_metrics["mean_ppfd_umol_m2_s"]
        cv = proposal.predicted_metrics["cv_ppfd"]
        self._optimizer_status.text = (
            f"Proposal {proposal.proposal_id} — NO SCENE CHANGE YET\n"
            f"Fixture height: {proposal.before_fixture_height_m:.3f} → {proposal.after_fixture_height_m:.3f} m\n"
            f"Channel totals: {powers}\n"
            f"Predicted mean PPFD: {mean_ppfd:.2f}; CV: {cv:.3f}\n"
            "Review these exact values, then click Apply Proposal or Reject."
        )
        print(
            "[OpenGrowTwin] Optimizer proposal "
            + json.dumps(proposal.to_dict(), sort_keys=True)
        )

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
            self._optimizer_proposal = None
            self._attach_stage_notice()

    def _attach_stage_notice(self):
        if self._stage_notice is not None:
            self._stage_notice.Revoke()
            self._stage_notice = None
        stage = omni.usd.get_context().get_stage()
        if stage:
            self._stage_notice = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, stage)

    def _on_objects_changed(self, notice, sender):
        changed = list(notice.GetResyncedPaths()) + list(notice.GetChangedInfoOnlyPaths())
        relevant = any(
            "/World/GrowInstallation" in str(path)
            and "/Results" not in str(path)
            and "/RTXLight" not in str(path)
            for path in changed
        )
        if relevant and self._optimizer_proposal is not None:
            self._optimizer_proposal = None
            if self._optimizer_status:
                self._optimizer_status.text = (
                    "Optimizer proposal invalidated because the live scene changed. Run Optimizer again."
                )
        if self._auto_simulate and relevant:
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
            self._record_run(result, mode)
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

    def _stage(self):
        stage = omni.usd.get_context().get_stage()
        if not stage:
            raise RuntimeError("Open an OpenGrowTwin stage first")
        return stage

    def _record_run(self, result, mode):
        self._run_counter += 1
        run_id = f"run_{self._run_counter:04d}"
        self._runs[run_id] = {"mode": mode, "result": result}
        while len(self._runs) > 20:
            self._runs.pop(next(iter(self._runs)))
        return run_id

    def _run_record(self, run_id):
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise ValueError(f"unknown recorded run {run_id!r}") from exc

    def _copilot_inspect_scene(self):
        discovered = discover_stage(self._stage())
        entities = discovered["entities"]
        channel_power = {}
        for emitter in entities["emitter"]:
            if emitter["enabled"]:
                channel = emitter["channel"]
                channel_power[channel] = channel_power.get(channel, 0.0) + emitter["radiant_power_w"]
        return {
            "schema_version": discovered["schema_version"],
            "entity_counts": {name: len(records) for name, records in entities.items()},
            "enabled_channel_power_w": channel_power,
            "recorded_run_ids": list(self._runs),
            "pending_optimizer_proposal_id": (
                self._optimizer_proposal.proposal_id if self._optimizer_proposal else None
            ),
        }

    def _copilot_get_metrics(self, run_id):
        record = self._run_record(run_id)
        return {
            "run_id": run_id,
            "mode": record["mode"],
            "mode_shape": record["result"]["mode_shape"],
            "metrics": record["result"]["metrics"],
        }

    def _copilot_get_occlusion_summary(self, run_id):
        result = self._run_record(run_id)["result"]
        blocked = int(result["blocked_ray_count"])
        total = int(result["total_ray_count"])
        return {
            "run_id": run_id,
            "blocked_ray_count": blocked,
            "total_ray_count": total,
            "blocked_fraction": blocked / total if total else 0.0,
        }

    def _copilot_compare_runs(self, baseline_run_id, candidate_run_id):
        baseline = self._run_record(baseline_run_id)["result"]["metrics"]
        candidate = self._run_record(candidate_run_id)["result"]["metrics"]
        common = sorted(set(baseline) & set(candidate))
        return {
            "baseline_run_id": baseline_run_id,
            "candidate_run_id": candidate_run_id,
            "metric_deltas": {
                name: float(candidate[name]) - float(baseline[name])
                for name in common
                if isinstance(baseline[name], (int, float))
                and isinstance(candidate[name], (int, float))
            },
        }

    def _copilot_run_simulation(self, mode):
        stage = self._stage()
        sync_rtx_lights(stage)
        design = prepare_solver_design(stage, mode)
        result = run_prepared_design(design)
        self._last_result = result
        run_id = self._record_run(result, mode)
        key = tuple(result["mode_shape"])
        baseline = self._baselines.setdefault(key, result)
        update_live_results(stage, result, baseline, self._display_mode)
        self._show_result(result, mode)
        return {
            "run_id": run_id,
            "mode": mode,
            "mode_shape": result["mode_shape"],
            "metrics": result["metrics"],
            "blocked_ray_count": result["blocked_ray_count"],
            "total_ray_count": result["total_ray_count"],
        }

    def _copilot_run_optimizer(self, objective):
        if objective != "target_uniformity_power":
            raise ValueError(f"unsupported optimizer objective {objective!r}")
        proposal = self._build_optimizer_proposal()
        self._optimizer_proposal = proposal
        self._show_optimizer_proposal(proposal)
        return proposal.to_dict()

    def _copilot_set_channel_power(self, fixture_id, channel_id, radiant_power_w):
        stage = self._stage()
        discovered = discover_stage(stage)
        fixtures = [
            item for item in discovered["entities"]["fixture"]
            if item["path"].rsplit("/", 1)[-1].lower() == fixture_id.lower()
        ]
        if len(fixtures) != 1:
            raise ValueError(f"fixture {fixture_id!r} did not resolve uniquely")
        prefix = fixtures[0]["path"] + "/"
        emitters = [
            item for item in discovered["entities"]["emitter"]
            if item["path"].startswith(prefix) and item["channel"] == channel_id
        ]
        if not emitters:
            raise ValueError(f"fixture {fixture_id!r} has no {channel_id!r} emitters")
        before = sum(item["radiant_power_w"] for item in emitters)
        per_emitter = float(radiant_power_w) / len(emitters)
        for emitter in emitters:
            attribute = stage.GetPrimAtPath(emitter["path"]).GetAttribute("opengrow:radiantPowerW")
            if not attribute:
                raise ValueError(f"{emitter['path']}: missing opengrow:radiantPowerW")
            attribute.Set(per_emitter)
        sync_rtx_lights(stage)
        return {
            "fixture_id": fixture_id,
            "channel_id": channel_id,
            "before_total_radiant_power_w": before,
            "after_total_radiant_power_w": float(radiant_power_w),
            "emitter_count": len(emitters),
            "per_emitter_radiant_power_w": per_emitter,
            "scene_changed": True,
            "simulation_required": True,
        }

    def _set_status(self, text):
        if self._status:
            self._status.text = text

    def on_shutdown(self):
        self._copilot.shutdown()
        self._cancel_run()
        if self._stage_notice is not None:
            self._stage_notice.Revoke()
        self._stage_notice = None
        self._stage_subscription = None
        self._optimizer_proposal = None
        self._window = None
        print("[OpenGrowTwin] Interactive simulation extension shutdown")
