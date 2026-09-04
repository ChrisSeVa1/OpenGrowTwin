# OGT-301A — OSRAM Manufacturer Photometry Integration

Status: **Steps 1–4 complete; Step 5 next**

This task extends the existing OpenGrowTwin LED/scientific-source work with manufacturer-backed optical data. It does **not** reopen or redefine the acceptance criteria of the already-completed OGT-301 milestone.

## Goal

Upgrade the selected ams OSRAM horticultural LED presets from a generalized Lambertian angular approximation to manufacturer-backed angular photometry where available, while keeping the deterministic photon-domain solver authoritative and synchronizing the same manufacturer profile with the corresponding RTX/USD light.

## Locked manufacturer LED set

For OGT-301A, use the current **OSRAM OSCONIQ™ P 3737 (2W) Batwing** family for all three channels. This keeps package geometry and angular-model handling consistent and gives OpenGrowTwin a deliberately non-Lambertian manufacturer profile to validate.

| OpenGrowTwin channel | Nominal spectral role | ams OSRAM part | Manufacturer rayfile revision | Validated radiant flux in package | Angular grid | Manufacturer spectrum |
| --- | --- | --- | --- | ---: | --- | --- |
| Blue | Deep Blue, ~450 nm | `GD PUBRA1.15` | 2025-05-29 | **1.448 W** | 91 × 73 IES | 380–510 nm, 2 nm spacing, peak 446 nm |
| Red | Hyper Red | `GH PUBRA1.25` | 2025-05-26 | **1.050 W** | 91 × 73 IES | 580–780 nm, 2 nm spacing, peak 680 nm |
| Far-red | Far Red | `GF PUBRA1.25` | 2025-06-03 | **0.869 W** | 91 × 73 IES | 600–800 nm, 2 nm spacing, peak 742 nm |

### Selection note

The earlier OSLON™ Square candidates remain valid reference/fallback devices. OGT-301A intentionally standardizes the manufacturer-photometry demonstration on the P 3737 Batwing family because matched blue/red/far-red devices are available in the same package family and expose a strongly non-Lambertian angular distribution.

The nominal horticultural channel labels are retained for UI/preset compatibility, but the scientific model should use the full manufacturer-provided tabulated spectrum rather than assume a monochromatic wavelength.

Detailed numerical validation is recorded in `docs/OGT-301A_OSRAM_PHOTOMETRY_VALIDATION.md`.

## Task sequence

- [x] **1. Lock the exact three OSRAM part numbers**
  - Confirmed deep-blue, hyper-red, and far-red devices.
  - Locked exact manufacturer part numbers and OpenGrowTwin channel mapping above.

- [x] **2. Acquire IES + EULUMDAT packages for each exact part**
  - Blue `GD PUBRA1.15`: IES + EULUMDAT acquired, revision 2025-05-29.
  - Red `GH PUBRA1.25`: IES + EULUMDAT acquired, revision 2025-05-26.
  - Far-red `GF PUBRA1.25`: IES + EULUMDAT acquired, revision 2025-06-03.
  - Original manufacturer filenames and source dates preserved.
  - Do not commit the raw manufacturer archives unless redistribution rights are explicitly confirmed; prefer provenance records/retrieval instructions.

- [x] **3. Verify spectral/radiometric provenance**
  - Package-specific manufacturer radiant flux recorded: blue 1.448 W, hyper-red 1.050 W, far-red 0.869 W.
  - All IES profiles use 91 vertical angles (0–180° at 2°) and 73 horizontal angles (0–360° at 5°).
  - Numerical solid-angle integration of the IES fields reproduces manufacturer radiant flux to better than 0.05% for all three devices.
  - EULUMDAT and IES angular distributions match to rounding precision after package scaling.
  - Matching TraceProText packages provide manufacturer tabulated relative spectrum files for all three selected devices:
    - `GD_PUBRA1_15_20250529_spectrum.txt`
    - `GH_PUBRA1_25_20250526_spectrum.txt`
    - `GF_PUBRA1_25_20250603_spectrum.txt`
  - Spectrum provenance is classified as `manufacturer_tabulated_relative_spd`; do not call it a direct measured SPD unless the manufacturer documentation explicitly establishes that stronger claim.
  - Manufacturer documentation states that bundled CAD is mechanical and is not valid as optical ray-tracing geometry.
  - See `docs/OGT-301A_OSRAM_PHOTOMETRY_VALIDATION.md` for validation tables and equations.

- [x] **4. Implement a generic IES parser and tabulated-SPD ingestion**
  - Added `src/opengrow/physics/photometry.py`.
  - Parses LM-63 `TILT=NONE` Type-C metadata, vertical angles, horizontal angles, multiplier, and intensity field.
  - Preserves raw angular semantics without assuming candela or W/sr.
  - Computes solid-angle integral and unit-solid-angle normalization.
  - Adds bilinear interpolation with periodic azimuth handling.
  - Rejects malformed, tilted, and unsupported non-Type-C profiles.
  - Added synthetic/open regression fixtures in `tests/test_photometry.py`.
  - Added `tools/validate_manufacturer_optics.py` for provenance-safe validation against user-supplied manufacturer files.
  - Added `src/opengrow/physics/spectrum.py` and `tests/test_spectrum.py` to ingest/normalize manufacturer tabulated relative spectra without bundling third-party rayfiles.
  - Band integration interpolates arbitrary wavelength boundaries before trapezoidal quadrature.
  - OGT reporting bands are explicit in the validator: PAR 400–700 nm and far-red 700–750 nm.
  - Validation on the GCP L4 development VM: **105 tests passed in 2.65 s**.
  - Manufacturer-asset validation results:
    - Blue: IES integral 1.447328410 W vs 1.448 W authoritative flux; peak 446 nm; PAR photon flux 5.378530073 µmol/s.
    - Hyper-red: IES integral 1.049828031 W vs 1.050 W authoritative flux; peak 680 nm; PAR 5.801436375 µmol/s; far-red 700–750 nm 0.099459200 µmol/s.
    - Far-red: IES integral 0.868967978 W vs 0.869 W authoritative flux; peak 742 nm; PAR 0.232539530 µmol/s; far-red 700–750 nm 4.169875674 µmol/s.
  - `sources/osram/` is gitignored so manufacturer assets remain local and are not redistributed in the public repository.

- [ ] **5. Add `manufacturer_ies` angular model to the deterministic solver**
  - Use interpolated `p(theta, phi)` instead of the current generalized Lambertian model when a validated manufacturer IES profile is available.
  - Keep `generalized_lambertian` as a documented fallback.
  - Normalize angular shape independently and apply authoritative `radiant_flux_w` from LED metadata.
  - Use normalized manufacturer spectral distribution `s(lambda)` for wavelength-resolved photon conversion.
  - Maintain inverse-square attenuation, receiver incidence angle, and OpenUSD geometry visibility.

- [ ] **6. Attach the same manufacturer IES profile to the RTX/USD light**
  - Bind the official IES asset through the USD light shaping API.
  - Keep the RTX light synchronized with the authoritative scientific emitter state.
  - Preserve the existing distinction: RTX is visualization; deterministic OpenGrowTwin results remain the scientific truth.

- [ ] **7. Validate A/B behavior: Lambertian vs manufacturer IES**
  - Run the same fixture geometry and power through both angular models.
  - Compare PPFD heatmaps, mean/min/max PPFD, CV, min/mean uniformity, DLI, and footprint shape.
  - For batwing devices, explicitly verify that the manufacturer profile produces the expected off-axis redistribution.
  - Save reproducible comparison artifacts.

- [ ] **8. Add photometry + provenance UI in Kit**
  - Display manufacturer, part number, channel role, spectral peak/range, radiant/photon source data, angular model, IES source, EULUMDAT source, spectrum provenance, and limitations.
  - Add a photometry view for angular intensity distribution where practical.
  - Clearly distinguish spatial PPFD, spectral distribution, and angular distribution.

- [ ] **9. Run and extend regression coverage**
  - Run the full existing OpenGrowTwin regression suite.
  - Add tests for IES parsing, interpolation, normalization, spectrum normalization, fallback behavior, provenance, RTX/scientific synchronization, and deterministic A/B results.
  - Ensure existing OGT-101…206 behavior remains unchanged unless intentionally extended.

- [ ] **10. Capture reproducible evidence for README/demo**
  - Document the complete pipeline:

    `manufacturer optical file → OpenUSD asset → deterministic solver → RTX visualization → PPFD heatmap`

  - Capture at least one clear Lambertian-vs-manufacturer comparison.
  - Include provenance and limitations in README/demo evidence.
  - Keep the work reproducible with exact source filenames, commands, environment details, and validation outputs.

## MVP scope boundary

For the Golden Ticket submission, prioritize **IES-based manufacturer angular photometry plus manufacturer tabulated spectra**. Full ingestion of large TracePro / ASAP / Speos / TM-25 raysets remains out of scope.

Recommended MVP hierarchy:

1. generalized Lambertian + monochromatic fallback
2. manufacturer IES angular photometry + manufacturer tabulated SPD
3. full near-field rayset ingestion — post-MVP / roadmap

## Scientific architecture reminder

The intended model is:

`manufacturer radiant flux × normalized spectrum s(lambda) × normalized angular distribution p(theta, phi) × 1/r^2 × receiver incidence × OpenUSD visibility → spectral irradiance → photon metrics`

Angular provenance and spectral provenance remain separate. RTX visualization must not replace the deterministic photon-domain calculation.
