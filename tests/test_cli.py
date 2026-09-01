import json

from opengrow.cli import simulate


def test_cli_result_contract(tmp_path):
    from pathlib import Path
    root = Path(__file__).parents[1]
    result = simulate(root / "demo/design.json", root / "data/targets/phalaenopsis_reference.yaml", tmp_path)
    assert result["shape"] == [13, 21]
    assert result["wavelengths_nm"] == [450.0, 660.0, 730.0]
    assert (tmp_path / "ppfd.npy").exists()
    assert json.loads((tmp_path / "metrics.json").read_text())["dli_mol_m2_day"] > 0
