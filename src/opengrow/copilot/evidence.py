"""Approved, citation-bearing evidence records exposed to the copilot."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .contracts import TARGET_IDS


class EvidenceError(ValueError):
    """An evidence package failed deterministic validation."""


def _resolve(record: dict, dotted_path: str) -> Any:
    value: Any = record
    for segment in dotted_path.split("."):
        if not isinstance(value, dict) or segment not in value:
            raise EvidenceError(f"unknown evidence field {dotted_path!r}")
        value = value[segment]
    return value


def _load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise EvidenceError(f"cannot load evidence file {path}") from exc
    if not isinstance(data, dict):
        raise EvidenceError(f"evidence file {path} must contain an object")
    return data


def _require(record: dict, keys: tuple[str, ...], label: str) -> None:
    missing = [key for key in keys if key not in record]
    if missing:
        raise EvidenceError(f"{label} missing required fields: {', '.join(missing)}")


def _validate_package(source: dict, target: dict, claims: dict) -> None:
    _require(source, ("schema_version", "source_id", "approval_status", "citation", "experiment", "source_limitations"), "source")
    _require(target, ("schema_version", "target_id", "approval_status", "source_id", "target", "photon_fraction", "claim_boundary"), "target")
    _require(claims, ("schema_version", "source_id", "target_id", "approved_claims", "prohibited_claims"), "claims")

    if source["schema_version"] != "1.0" or target["schema_version"] != "1.0" or claims["schema_version"] != "1.0":
        raise EvidenceError("unsupported evidence schema version")
    if source["approval_status"] != "approved" or target["approval_status"] != "approved":
        raise EvidenceError("copilot may load only approved evidence")
    if target["target_id"] not in TARGET_IDS:
        raise EvidenceError("target is not in the OGT-201 approved identifier allowlist")
    if target["source_id"] != source["source_id"] or claims["source_id"] != source["source_id"]:
        raise EvidenceError("evidence package source identifiers do not match")
    if claims["target_id"] != target["target_id"]:
        raise EvidenceError("claims target identifier does not match")

    citation = source["citation"]
    _require(citation, ("title", "authors", "journal", "year", "doi", "url"), "citation")
    if not isinstance(citation["authors"], list) or not citation["authors"]:
        raise EvidenceError("citation requires at least one author")

    linked_values = (
        target["target"]["mean_ppfd_umol_m2_s"],
        target["target"]["photoperiod_h"],
        target["photon_fraction"]["blue_400_500"],
        target["photon_fraction"]["red_600_700"],
    )
    for linked in linked_values:
        _require(linked, ("value", "source_field"), "target value")
        if linked["value"] != _resolve(source, linked["source_field"]):
            raise EvidenceError(f"target value does not match {linked['source_field']}")

    mean_ppfd = float(target["target"]["mean_ppfd_umol_m2_s"]["value"])
    photoperiod_h = float(target["target"]["photoperiod_h"]["value"])
    dli = target["target"]["derived_dli_mol_m2_d"]
    _require(dli, ("value", "derivation", "authority"), "derived DLI")
    expected_dli = mean_ppfd * photoperiod_h * 0.0036
    if abs(float(dli["value"]) - expected_dli) > 1e-9:
        raise EvidenceError("derived DLI is inconsistent with PPFD and photoperiod")
    if dli["authority"] != "deterministic_calculation":
        raise EvidenceError("derived DLI must be labeled as deterministic calculation")

    blue = float(target["photon_fraction"]["blue_400_500"]["value"])
    red = float(target["photon_fraction"]["red_600_700"]["value"])
    if not 0.0 <= blue <= 1.0 or not 0.0 <= red <= 1.0 or abs(blue + red - 1.0) > 1e-12:
        raise EvidenceError("blue and red photon fractions must be bounded and sum to one")

    boundary = target["claim_boundary"]
    if boundary.get("classification") != "published_reference_treatment":
        raise EvidenceError("target must be classified as a published reference treatment")
    for field in ("optimization_claim", "biological_prediction", "universal_recommendation"):
        if boundary.get(field) is not False:
            raise EvidenceError(f"claim boundary {field} must be false")

    approved_claims = claims["approved_claims"]
    prohibited_claims = claims["prohibited_claims"]
    if not isinstance(approved_claims, list) or not approved_claims:
        raise EvidenceError("at least one approved claim is required")
    if not isinstance(prohibited_claims, list) or not prohibited_claims:
        raise EvidenceError("at least one prohibited claim is required")
    claim_ids: set[str] = set()
    for claim in approved_claims:
        _require(claim, ("claim_id", "statement", "evidence_fields"), "approved claim")
        if claim["claim_id"] in claim_ids:
            raise EvidenceError(f"duplicate claim identifier {claim['claim_id']!r}")
        claim_ids.add(claim["claim_id"])
        if not claim["statement"].strip() or not claim["evidence_fields"]:
            raise EvidenceError("approved claims require a statement and evidence fields")
        for field in claim["evidence_fields"]:
            _resolve(source, field)


class ApprovedEvidenceStore:
    """Load and expose only deterministic, approved evidence packages."""

    def __init__(self, evidence_root: Path | None = None):
        if evidence_root is None:
            evidence_root = Path(__file__).resolve().parents[3] / "data" / "evidence"
        self._root = Path(evidence_root)
        self._records: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self._root.is_dir():
            raise EvidenceError(f"evidence root does not exist: {self._root}")
        for directory in sorted(path for path in self._root.iterdir() if path.is_dir()):
            source = _load_yaml(directory / "source.yaml")
            target = _load_yaml(directory / "target.yaml")
            claims = _load_yaml(directory / "claims.yaml")
            _validate_package(source, target, claims)
            target_id = target["target_id"]
            if target_id in self._records:
                raise EvidenceError(f"duplicate target identifier {target_id!r}")
            self._records[target_id] = {"source": source, "target": target, "claims": claims}
        if not self._records:
            raise EvidenceError("no approved evidence packages found")

    def list_targets(self) -> list[dict]:
        return [
            {
                "target_id": target_id,
                "display_name": record["target"]["display_name"],
                "species": record["target"]["scope"]["species"],
                "classification": record["target"]["claim_boundary"]["classification"],
                "source_id": record["source"]["source_id"],
                "doi": record["source"]["citation"]["doi"],
            }
            for target_id, record in self._records.items()
        ]

    def get_target(self, target_id: str) -> dict:
        if target_id not in TARGET_IDS or target_id not in self._records:
            raise EvidenceError(f"unknown or unapproved target {target_id!r}")
        return deepcopy(self._records[target_id])
