from copy import deepcopy
from pathlib import Path

import pytest

from opengrow.led_presets import LedPresetError, LedPresetLibrary, validate_led_preset


ROOT = Path(__file__).resolve().parents[1] / "data" / "leds"


def test_library_loads_three_verified_osram_channels():
    library = LedPresetLibrary(ROOT)
    records = library.list_presets()
    assert len(records) == 3
    assert {record["channel"] for record in records} == {"blue", "hyper_red", "far_red"}
    assert {record["wavelength_nm"] for record in records} == {450, 660, 730}
    assert all(record["manufacturer"] == "ams OSRAM" for record in records)
    assert all(record["product_family"] == "OSCONIQ P 3737" for record in records)
    assert all(record["provenance_status"] == "manufacturer_family_verified" for record in records)


def test_far_red_is_excluded_from_ppfd():
    record = LedPresetLibrary(ROOT).get_preset("mvp_farred_730")
    assert record["wavelength_nm"] == 730
    assert record["included_in_ppfd"] is False


def test_blue_and_hyper_red_are_included_in_ppfd():
    library = LedPresetLibrary(ROOT)
    assert library.get_preset("mvp_blue_450")["included_in_ppfd"] is True
    assert library.get_preset("mvp_hyperred_660")["included_in_ppfd"] is True


def test_rejects_wrong_channel_wavelength():
    record = LedPresetLibrary(ROOT).get_preset("mvp_blue_450")
    record["wavelength_nm"] = 451
    with pytest.raises(LedPresetError, match="unexpected nominal wavelength"):
        validate_led_preset(record)


def test_rejects_unknown_channel():
    record = LedPresetLibrary(ROOT).get_preset("mvp_blue_450")
    record["channel"] = "ultraviolet"
    with pytest.raises(LedPresetError, match="unknown LED channel"):
        validate_led_preset(record)


def test_rejects_electrical_power_as_radiant_power():
    record = LedPresetLibrary(ROOT).get_preset("mvp_blue_450")
    record["simulation_assumptions"]["manufacturer_electrical_power_used_as_radiant_power"] = True
    with pytest.raises(LedPresetError, match="electrical power"):
        validate_led_preset(record)


def test_rejects_non_official_provenance_source():
    record = LedPresetLibrary(ROOT).get_preset("mvp_blue_450")
    record["provenance"]["source_url"] = "https://example.invalid/product"
    with pytest.raises(LedPresetError, match="official ams OSRAM"):
        validate_led_preset(record)


def test_get_preset_returns_copy():
    library = LedPresetLibrary(ROOT)
    first = library.get_preset("mvp_blue_450")
    first["wavelength_nm"] = 999
    assert library.get_preset("mvp_blue_450")["wavelength_nm"] == 450
