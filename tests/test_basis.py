from copy import deepcopy
from pathlib import Path
import json

import numpy as np

from opengrow.physics.basis import channel_basis, reconstruct
from opengrow.physics.direct_solver import simulate_design


def test_basis_reconstructs_full_solver():
    design = json.loads((Path(__file__).parents[1] / "demo/design.json").read_text())
    basis = channel_basis(design)
    powers = [sum(e["radiant_power_w"] for e in c["emitters"]) for c in design["channels"]]
    cached = reconstruct(basis, powers)
    full = simulate_design(design)
    np.testing.assert_allclose(cached["ppfd"], full["ppfd"])
    np.testing.assert_allclose(cached["far_red"], full["far_red"])


def test_basis_channel_linearity():
    design = json.loads((Path(__file__).parents[1] / "demo/design.json").read_text())
    basis = channel_basis(design)
    one = reconstruct(basis, [10, 20, 3])
    two = reconstruct(basis, [20, 40, 6])
    np.testing.assert_allclose(two["band_ppfd"], one["band_ppfd"] * 2)
