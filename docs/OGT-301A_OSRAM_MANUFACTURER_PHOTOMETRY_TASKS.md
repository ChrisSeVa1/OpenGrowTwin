# OGT-301A — OSRAM Manufacturer Photometry Integration

Status: **Steps 1–3 complete; Step 4 next**

This task extends the existing OpenGrowTwin LED/scientific-source work with manufacturer-backed optical data. It does **not** reopen or redefine the acceptance criteria of the already-completed OGT-301 milestone.

## Goal

Upgrade the selected ams OSRAM horticultural LED presets from a generalized Lambertian angular approximation to manufacturer-backed angular photometry where available, while keeping the deterministic photon-domain solver authoritative and synchronizing the same manufacturer profile with the corresponding RTX/USD light.

## Locked manufacturer LED set

For OGT-301A, use the current **OSRAM OSCONIQ™ P 3737 (2W) Batwing** family for all three channels. This keeps package geometry and angular-model handling consistent and gives OpenGrowTwin a deliberately non-Lambertian manufacturer profile to validate.

| OpenGrowTwin channel | Nominal spectral role | ams OSRAM part | Manufacturer rayfile revision | Validated radiant flux in package | Angular grid |
| --- | --- | --- | --- | ---: | --- |
| Blue | Deep Blue, ~450 nm | `GD PUBRA1.15` | 2025-05-29 | **1.448 W** | 91 × 73 IES |
| Red | Hyper Red, ~660 nm | `GH PUBRA1.25` | 2025-05-26 | **1.050 W** | 91 × 73 IES |
| Far-red | Far Red, ~730 nm | `GF PUBRA1.25` | 2025-06-03 | **0.869 W** | 91 × 73 IES |

### Selection note

The earlier OSLON™ Square candidates remain valid reference/fallback devices, including `GD CSSRM3.14` deep blue and `GH CSSRM6.24` hyper red. OGT-301A intentionally standardizes the manufacturer-photometry demonstration on the P 3737 Batwing family because matched blue/red/far-red devices are available in the same package family and expose a strongly non-Lambertian angular distribution.

Detailed numerical validation is recorded in `docs/OGT-301A_OSRAM_PHOTOMETRY_VALIDATION.md`.

## Task sequence

- [x] **1. Lock the exact three OSRAM part numbers**
  - Confirmed deep-blue (~450 nm), hyper-red (~660 nm), and far-red (~730 nm) devices.
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
  - The six IES/EULUMDAT archives do not themselves supply machine-readable SPD data; spectral provenance therefore remains separate and must not be labeled measured unless a separate manufacturer spectrum file is acquired.
  - Manufacturer documentation states that bundled CAD is mechanical and is not valid as optical ray-tracing geometry.
  - See `docs/OGT-301A_OSRAM_PHOTOMETRY_VALIDATION.md` for the validation tables and equations.

- [ ] **4. Implement a generic IES parser**
  - Parse LM-63 metadata, vertical angles, horizontal angles, and intensity samples.
  - Expose a normalized angular field `I(theta, phi)` / `p(theta, phi)` suitable for deterministic interpolation.
  - Compute and retain the raw solid-angle integral as a validation metric.
  - Add bilinear interpolation with periodic azimuth handling.
  - Add parser validation for malformed/unsupported profiles.
  - Preserve manufacturer metadata and source provenance.
  - Prefer synthetic/open regression fixtures; do not require redistribution of proprietary manufacturer archives.

- [ ] **5. Add `manufacturer_ies` angular model to the deterministic solver**
  - Use interpolated `I(theta, phi)` instead of the current generalized Lambertian model when a validated manufacturer IES profile is available.
  - Keep `generalized_lambertian` as a documented fallback.
  - Normalize angular shape independently and apply authoritative `radiant_flux_w` from LED metadata.
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
  - Display manufacturer, part number, channel, wavelength, radiant/photon source data, angular model, IES source, EULUMDAT source, spectrum provenance, and limitations.
  - Add a photometry view for angular intensity distribution where practical.
  - Clearly distinguish:
    - spatial distribution: PPFD `[µmol·m⁻²·s⁻¹]`
    - spectral distribution
    - angular distribution / photometry

- [ ] **9. Run and extend regression coverage**
  - Run the full existing OpenGrowTwin regression suite.
  - Add tests for IES parsing, interpolation, normalization, fallback behavior, provenance, RTX/scientific synchronization, and deterministic A/B results.
  - Ensure existing OGT-101…206 behavior remains unchanged unless intentionally extended.

- [ ] **10. Capture reproducible evidence for README/demo**
  - Document the complete pipeline:

    `manufacturer optical file → OpenUSD asset → deterministic solver → RTX visualization → PPFD heatmap`

  - Capture at least one clear Lambertian-vs-manufacturer comparison.
  - Include provenance and limitations in the README/demo evidence.
  - Keep the work reproducible with exact source filenames, commands, environment details, and validation outputs.

## MVP scope boundary

For the Golden Ticket submission, prioritize **IES-based manufacturer angular photometry**. Full ingestion of large TracePro / ASAP / Speos / TM-25 raysets is out of scope unless it becomes trivial after the IES path is complete.

Recommended MVP hierarchy:

1. generalized Lambertian fallback
2. manufacturer IES / EULUMDAT angular photometry
3. full near-field rayset ingestion — post-MVP / roadmap

## Scientific architecture reminder

The intended model remains:

`manufacturer spectral/radiometric source + I(theta, phi) + 1/r^2 + receiver incidence + OpenUSD visibility → PPFD`

For implementation, normalize the manufacturer angular field to a unit-solid-angle distribution `p(theta, phi)` and then apply the authoritative manufacturer `radiant_flux_w`. Spectral provenance remains independent of angular provenance.