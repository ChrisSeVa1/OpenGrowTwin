from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

from .physics.direct_solver import simulate_design
from .physics.metrics import summarize
from .optimize.optimizer import optimize_design
from .visualization.heatmap import render_comparison
from .usd.heatmap import write_heatmap_usda
from .usd.scene_contract import write_live_scene_usda


def simulate(design_path: Path, target_path: Path | None, out_dir: Path) -> dict:
    design = json.loads(design_path.read_text(encoding="utf-8"))
    target = yaml.safe_load(target_path.read_text(encoding="utf-8")) if target_path else None
    result = simulate_design(design)
    photoperiod = target["target"]["photoperiod_h"] if target else design.get("photoperiod_h", 14.0)
    metrics = summarize(result["ppfd"], result["far_red"], photoperiod)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "ppfd.npy", result["ppfd"])
    np.save(out_dir / "band_ppfd.npy", result["band_ppfd"])
    np.save(out_dir / "spectral_irradiance.npy", result["spectral_irradiance"])
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    contract = {
        "schema_version": "0.1.0",
        "design": str(design_path),
        "target": str(target_path) if target_path else None,
        "wavelengths_nm": result["wavelengths_nm"].tolist(),
        "shape": list(result["ppfd"].shape),
        "metrics": metrics,
        "assets": {"ppfd": "ppfd.npy", "band_ppfd": "band_ppfd.npy", "spectral_irradiance": "spectral_irradiance.npy"},
    }
    (out_dir / "result.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return contract


def optimize(design_path: Path, target_path: Path, out_dir: Path) -> dict:
    design = json.loads(design_path.read_text(encoding="utf-8"))
    target = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    baseline_result = simulate_design(design)
    baseline_metrics = summarize(
        baseline_result["ppfd"], baseline_result["far_red"], target["target"]["photoperiod_h"]
    )
    optimized = optimize_design(design, target)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "ppfd_optimized.npy", optimized["fields"]["ppfd"])
    np.save(out_dir / "band_ppfd_optimized.npy", optimized["fields"]["band_ppfd"])
    heatmap_assets = render_comparison(
        baseline_result["ppfd"], optimized["fields"]["ppfd"], design["grid"], out_dir
    )
    usd_asset = write_heatmap_usda(
        optimized["fields"]["ppfd"], design["grid"], optimized["metrics"],
        out_dir / "ppfd_heatmap.usda",
    )
    (out_dir / "optimized_design.json").write_text(
        json.dumps(optimized["design"], indent=2) + "\n", encoding="utf-8"
    )
    comparison = {
        "schema_version": "0.1.0",
        "reference_treatment": target["id"],
        "claim": "installation optimization to reproduce a published photon environment",
        "baseline": baseline_metrics,
        "optimized": optimized["metrics"],
        "selected_height_m": optimized["height_m"],
        "channel_ids": optimized["channel_ids"],
        "channel_radiant_power_w": optimized["channel_radiant_power_w"].tolist(),
        "candidate_summary": optimized["candidate_summary"],
        "assets": {
            "optimized_design": "optimized_design.json",
            "ppfd": "ppfd_optimized.npy",
            "band_ppfd": "band_ppfd_optimized.npy",
            **heatmap_assets,
            "openusd_heatmap": usd_asset["path"],
        },
        "openusd": usd_asset,
    }
    (out_dir / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    return comparison


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="opengrow")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("simulate", help="run a deterministic direct-light simulation")
    command.add_argument("design", type=Path)
    command.add_argument("--target", type=Path)
    command.add_argument("--out", type=Path, required=True)
    optimize_command = subparsers.add_parser("optimize", help="optimize channel powers and fixture height")
    optimize_command.add_argument("design", type=Path)
    optimize_command.add_argument("--target", type=Path, required=True)
    optimize_command.add_argument("--out", type=Path, required=True)
    scene_command = subparsers.add_parser("scene", help="author the authoritative live OpenUSD scene")
    scene_command.add_argument("design", type=Path)
    scene_command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "simulate":
        contract = simulate(args.design, args.target, args.out)
        print(json.dumps(contract["metrics"], indent=2))
    elif args.command == "optimize":
        comparison = optimize(args.design, args.target, args.out)
        print(json.dumps({
            "selected_height_m": comparison["selected_height_m"],
            "channel_radiant_power_w": comparison["channel_radiant_power_w"],
            "baseline": comparison["baseline"],
            "optimized": comparison["optimized"],
        }, indent=2))
    elif args.command == "scene":
        design = json.loads(args.design.read_text(encoding="utf-8"))
        contract = write_live_scene_usda(design, args.out)
        print(json.dumps(contract, indent=2))
    return 0
