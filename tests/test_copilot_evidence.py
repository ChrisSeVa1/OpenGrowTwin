from copy import deepcopy
from pathlib import Path
import shutil

import pytest
import yaml

from opengrow.copilot.evidence import ApprovedEvidenceStore, EvidenceError


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "evidence" / "phalaenopsis_ouzounis_2015"
TARGET_ID = "phalaenopsis_ouzounis_2015_reference"


def _copy_package(tmp_path: Path) -> Path:
    root = tmp_path / "evidence"
    shutil.copytree(PACKAGE, root / PACKAGE.name)
    return root


def _rewrite(path: Path, update) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    update(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_lists_one_citation_bearing_approved_target():
    targets = ApprovedEvidenceStore().list_targets()
    assert targets == [{
        "target_id": TARGET_ID,
        "display_name": "Phalaenopsis 2015 B40/R60 reference",
        "species": "Phalaenopsis",
        "classification": "published_reference_treatment",
        "source_id": "ouzounis_2015_ppl_12300",
        "doi": "10.1111/ppl.12300",
    }]


def test_target_exposes_source_target_claims_and_limitations():
    record = ApprovedEvidenceStore().get_target(TARGET_ID)
    assert record["target"]["target"]["derived_dli_mol_m2_d"]["value"] == 10.08
    assert record["source"]["experiment"]["conditions"]["background_daylight"] is True
    assert record["target"]["claim_boundary"]["universal_recommendation"] is False
    assert len(record["claims"]["approved_claims"]) == 3
    assert len(record["claims"]["prohibited_claims"]) == 5


def test_get_target_returns_a_defensive_copy():
    store = ApprovedEvidenceStore()
    first = store.get_target(TARGET_ID)
    first["source"]["citation"]["doi"] = "changed"
    assert store.get_target(TARGET_ID)["source"]["citation"]["doi"] == "10.1111/ppl.12300"


def test_unapproved_package_is_rejected(tmp_path):
    root = _copy_package(tmp_path)
    _rewrite(root / PACKAGE.name / "target.yaml", lambda data: data.update(approval_status="candidate"))
    with pytest.raises(EvidenceError, match="only approved evidence"):
        ApprovedEvidenceStore(root)


def test_target_value_must_match_its_source_field(tmp_path):
    root = _copy_package(tmp_path)
    def alter(data):
        data["target"]["mean_ppfd_umol_m2_s"]["value"] = 250
    _rewrite(root / PACKAGE.name / "target.yaml", alter)
    with pytest.raises(EvidenceError, match="does not match"):
        ApprovedEvidenceStore(root)


def test_derived_dli_is_recomputed_and_validated(tmp_path):
    root = _copy_package(tmp_path)
    def alter(data):
        data["target"]["derived_dli_mol_m2_d"]["value"] = 9.9
    _rewrite(root / PACKAGE.name / "target.yaml", alter)
    with pytest.raises(EvidenceError, match="derived DLI"):
        ApprovedEvidenceStore(root)


def test_universal_optimization_claim_is_rejected(tmp_path):
    root = _copy_package(tmp_path)
    def alter(data):
        data["claim_boundary"]["universal_recommendation"] = True
    _rewrite(root / PACKAGE.name / "target.yaml", alter)
    with pytest.raises(EvidenceError, match="universal_recommendation"):
        ApprovedEvidenceStore(root)


def test_claim_must_resolve_to_a_source_field(tmp_path):
    root = _copy_package(tmp_path)
    def alter(data):
        data["approved_claims"][0]["evidence_fields"] = ["experiment.imaginary_result"]
    _rewrite(root / PACKAGE.name / "claims.yaml", alter)
    with pytest.raises(EvidenceError, match="unknown evidence field"):
        ApprovedEvidenceStore(root)


def test_unknown_target_is_not_exposed():
    with pytest.raises(EvidenceError, match="unknown or unapproved"):
        ApprovedEvidenceStore().get_target("../../unreviewed.yaml")
