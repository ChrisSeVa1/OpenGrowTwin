import pytest

from opengrow.physics.photons import dli_from_ppfd, irradiance_to_photon_flux


@pytest.mark.parametrize(("wavelength", "expected"), [(450, 3.761706), (660, 5.517169), (730, 6.102323)])
def test_monochromatic_conversion(wavelength, expected):
    assert irradiance_to_photon_flux(1.0, wavelength) == pytest.approx(expected, abs=1e-6)


def test_reference_dli():
    assert dli_from_ppfd(200, 14) == pytest.approx(10.08)
