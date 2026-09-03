import numpy as np
import pytest

from opengrow.physics.spectrum import parse_spectrum_text


def test_parse_and_normalize_tabulated_spectrum():
    spectrum = parse_spectrum_text("400 0\n450 1\n500 0\n", source="test_spectrum.txt")
    density = spectrum.normalized_density()
    area = np.trapz(density, spectrum.wavelengths_nm)
    assert area == pytest.approx(1.0)
    assert spectrum.peak_wavelength_nm == pytest.approx(450.0)
    assert spectrum.source == "test_spectrum.txt"
    assert spectrum.provenance_kind == "manufacturer_tabulated_relative_spd"


def test_radiant_spectral_density_preserves_total_flux():
    spectrum = parse_spectrum_text("400 0\n450 1\n500 0\n")
    spectral_flux = spectrum.radiant_spectral_density(1.448)
    assert np.trapz(spectral_flux, spectrum.wavelengths_nm) == pytest.approx(1.448)


def test_photon_flux_per_watt_uses_full_spectrum():
    spectrum = parse_spectrum_text("449 1\n450 1\n451 1\n")
    result = spectrum.photon_flux_per_watt_umol_s()
    # A narrow distribution around 450 nm should approach the monochromatic
    # conversion of one watt at 450 nm (~3.7617 µmol/s).
    assert result == pytest.approx(3.7617, rel=2e-3)


def test_band_fraction_and_validation():
    spectrum = parse_spectrum_text("400 0\n450 1\n500 0\n550 0\n")
    assert 0.0 < spectrum.fraction_in_band(400, 500) <= 1.0
    with pytest.raises(ValueError, match="non-negative"):
        parse_spectrum_text("400 1\n450 -1\n")
    with pytest.raises(ValueError, match="strictly increasing"):
        parse_spectrum_text("450 1\n400 1\n")
