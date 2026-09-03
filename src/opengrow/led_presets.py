"""Validated manufacturer-backed horticultural LED preset records."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


class LedPresetError(ValueError):
    """An LED preset failed deterministic validation."""


EXPECTED_CHANNELS = {
    "blue": {"wavelength_nm": 450, "reporting_band": "blue_400_500", "included_in_ppfd": True},
    "hyper_red": {"wavelength_nm": 660, "reporting_band": "red_600_700", "included_in_ppfd": True},
    "far_red": {"wavelength_nm": 730, "reporting_band": "far_red_700_800", "included_in_ppfd": False},
}


def _require(record: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [key for key in keys if key not in record]
    if missing:
        raise LedPresetError(f"{label} missing required fields: {', '.join(missing)}")


def validate_led_preset(record: dict[str, Any]) -> None:
    _require(
        record,
        (
            "schema_version", "id", "manufacturer", "product_family", "application",
            "channel", "wavelength_nm", "spectrum_representation", "reporting_band",
            "included_in_ppfd", "manufacturer_data", "simulation_assumptions",
            "provenance", "provenance_status", "limitations",
        ),
        "LED preset",
    )
    if record["schema_version"] != "1.0":
        raise LedPresetError("unsupported LED preset schema version")
    if record["manufacturer"] != "ams OSRAM" or record["product_family"] != "OSCONIQ P 3737":
        raise LedPresetError("OGT-301 presets must identify the verified ams OSRAM OSCONIQ P 3737 family")
    if record["application"] != "horticulture":
        raise LedPresetError("LED preset application must be horticulture")
    channel = record["channel"]
    if channel not in EXPECTED_CHANNELS:
        raise LedPresetError(f"unknown LED channel {channel!r}")
    expected = EXPECTED_CHANNELS[channel]
    if record["wavelength_nm"] != expected["wavelength_nm"]:
        raise LedPresetError(f"unexpected nominal wavelength for channel {channel!r}")
    if record["reporting_band"] != expected["reporting_band"]:
        raise LedPresetError(f"unexpected reporting band for channel {channel!r}")
    if record["included_in_ppfd"] is not expected["included_in_ppfd"]:
        raise LedPresetError(f"incorrect PPFD inclusion for channel {channel!r}")
    if record["spectrum_representation"] != "monochromatic_approximation":
        raise LedPresetError("MVP LED presets must explicitly use the monochromatic approximation")

    manufacturer_data = record["manufacturer_data"]
    _require(manufacturer_data, ("scope", "spectral_identity_only"), "manufacturer_data")
    if manufacturer_data["scope"] != "product_family" or manufacturer_data["spectral_identity_only"] is not True:
        raise LedPresetError("manufacturer data must be limited to product-family spectral identity")

    assumptions = record["simulation_assumptions"]
    _require(
        assumptions,
        ("wavelength_model", "radiant_power_source", "manufacturer_electrical_power_used_as_radiant_power"),
        "simulation_assumptions",
    )
    if assumptions["radiant_power_source"] != "scene_or_simulation_input":
        raise LedPresetError("simulation radiant power must come from scene or simulation input")
    if assumptions["manufacturer_electrical_power_used_as_radiant_power"] is not False:
        raise LedPresetError("manufacturer electrical power must never be silently used as radiant power")

    provenance = record["provenance"]
    _require(provenance, ("manufacturer", "source_type", "source_url", "retrieved_utc_date", "supported_claim"), "provenance")
    if provenance["manufacturer"] != record["manufacturer"]:
        raise LedPresetError("provenance manufacturer does not match preset manufacturer")
    if not str(provenance["source_url"]).startswith("https://ams-osram.com/"):
        raise LedPresetError("preset provenance must use an official ams OSRAM source")
    if record["provenance_status"] != "manufacturer_family_verified":
        raise LedPresetError("LED preset provenance is not manufacturer-family verified")
    if not isinstance(record["limitations"], list) or not record["limitations"]:
        raise LedPresetError("LED preset must declare limitations")


def load_led_preset(path: Path) -> dict[str, Any]:
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedPresetError(f"cannot load LED preset {path}") from exc
    if not isinstance(record, dict):
        raise LedPresetError(f"LED preset {path} must contain an object")
    validate_led_preset(record)
    return record


class LedPresetLibrary:
    """Load the complete validated OpenGrowTwin LED preset library."""

    def __init__(self, root: Path | None = None):
        if root is None:
            root = Path(__file__).resolve().parents[2] / "data" / "leds"
        self._root = Path(root)
        self._records: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._root.is_dir():
            raise LedPresetError(f"LED preset root does not exist: {self._root}")
        for path in sorted(self._root.glob("*.json")):
            record = load_led_preset(path)
            preset_id = record["id"]
            if preset_id in self._records:
                raise LedPresetError(f"duplicate LED preset identifier {preset_id!r}")
            self._records[preset_id] = record
        if not self._records:
            raise LedPresetError("no LED presets found")
        channels = {record["channel"] for record in self._records.values()}
        missing = set(EXPECTED_CHANNELS) - channels
        if missing:
            raise LedPresetError(f"LED preset library missing required channels: {', '.join(sorted(missing))}")

    def list_presets(self) -> list[dict[str, Any]]:
        return [deepcopy(record) for record in self._records.values()]

    def get_preset(self, preset_id: str) -> dict[str, Any]:
        if preset_id not in self._records:
            raise LedPresetError(f"unknown LED preset {preset_id!r}")
        return deepcopy(self._records[preset_id])
