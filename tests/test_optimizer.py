import json
from pathlib import Path

import pytest
import yaml

from opengrow.optimize.optimizer import optimize_design


def test_optimizer_reaches_reference_mean_and_fraction():
    root = Path(__file__).parents[1]
    design = json.loads((root / "demo/design.json").read_text())
    target = yaml.safe_load((root / "data/targets/phalaenopsis_reference.yaml").read_text())
    result = optimize_design(design, target)
    assert result["metrics"]["mean_ppfd_umol_m2_s"] == pytest.approx(200.0)
    blue_mean = result["fields"]["band_ppfd"][0].mean()
    red_mean = result["fields"]["band_ppfd"][1].mean()
    assert blue_mean / (blue_mean + red_mean) == pytest.approx(0.40)
    assert result["metrics"]["cv_ppfd"] < 0.25


def test_optimizer_does_not_regress_baseline_uniformity():
    from opengrow.physics.direct_solver import simulate_design
    from opengrow.physics.metrics import summarize
    root = Path(__file__).parents[1]
    design = json.loads((root / "demo/design.json").read_text())
    target = yaml.safe_load((root / "data/targets/phalaenopsis_reference.yaml").read_text())
    baseline = simulate_design(design)
    baseline_metrics = summarize(baseline["ppfd"], baseline["far_red"], target["target"]["photoperiod_h"])
    result = optimize_design(design, target)
    assert result["metrics"]["cv_ppfd"] <= baseline_metrics["cv_ppfd"] + 1e-4


def test_optimizer_does_not_mutate_input():
    root = Path(__file__).parents[1]
    design = json.loads((root / "demo/design.json").read_text())
    target = yaml.safe_load((root / "data/targets/phalaenopsis_reference.yaml").read_text())
    original = json.dumps(design, sort_keys=True)
    optimize_design(design, target)
    assert json.dumps(design, sort_keys=True) == original
