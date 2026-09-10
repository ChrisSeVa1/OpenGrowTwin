import json

from opengrow.cli import simulate


def test_cli_result_contract(tmp_path):
    from pathlib import Path
    root = Path(__file__).parents[1]
    result = simulate(root / "demo/design.json", root / "data/targets/phalaenopsis_reference.yaml", tmp_path)
    assert result["shape"] == [25, 41]
    assert result["wavelengths_nm"] == [450.0, 660.0, 730.0]
    assert (tmp_path / "ppfd.npy").exists()
    assert json.loads((tmp_path / "metrics.json").read_text())["dli_mol_m2_day"] > 0


def test_optimize_writes_visual_assets(tmp_path):
    from pathlib import Path
    from opengrow.cli import optimize
    root = Path(__file__).parents[1]
    result = optimize(root / "demo/design.json", root / "data/targets/phalaenopsis_reference.yaml", tmp_path)
    for name in ("ppfd_baseline.png", "ppfd_optimized.png", "ppfd_comparison.png",
                 "ppfd_baseline.csv", "ppfd_optimized.csv", "ppfd_heatmap.usda"):
        assert (tmp_path / name).stat().st_size > 0
    assert result["assets"]["comparison_heatmap"] == "ppfd_comparison.png"
    assert result["openusd"]["vertex_count"] == 41 * 25
    assert result["openusd"]["face_count"] == 40 * 24
