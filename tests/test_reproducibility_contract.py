from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_SCRIPT = ROOT / "tools" / "kit_capture_heatmap.py"
VALIDATION_DOC = ROOT / "docs" / "validation.md"


def test_rtx_capture_has_no_machine_specific_home_fallback():
    text = CAPTURE_SCRIPT.read_text(encoding="utf-8")
    assert "/home/" not in text
    assert "Path(__file__).resolve().parents[1]" in text
    assert "build/ogt-305/l4-smoke-evidence.json" in text


def test_validation_contract_documents_authoritative_solver_and_rtx_smoke_gate():
    text = VALIDATION_DOC.read_text(encoding="utf-8")
    assert "deterministic photon solver" in text
    assert "RTX is a visualization/synchronization layer" in text
    assert '"passed": true' in text
    assert "size_bytes > 0" in text
