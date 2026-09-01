from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

from .physics.direct_solver import simulate_design
from .physics.metrics import summarize


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="opengrow")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("simulate", help="run a deterministic direct-light simulation")
    command.add_argument("design", type=Path)
    command.add_argument("--target", type=Path)
    command.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "simulate":
        contract = simulate(args.design, args.target, args.out)
        print(json.dumps(contract["metrics"], indent=2))
    return 0
