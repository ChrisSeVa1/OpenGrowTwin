# OGT-301A — OSRAM Manufacturer Photometry Integration

Status: **Step 1 complete; Step 2 next**

This task extends the existing OpenGrowTwin LED/scientific-source work with manufacturer-backed optical data. It does **not** reopen or redefine the acceptance criteria of the already-completed OGT-301 milestone.

## Goal

Upgrade the selected ams OSRAM horticultural LED presets from a generalized Lambertian angular approximation to manufacturer-backed angular photometry where available, while keeping the deterministic photon-domain solver authoritative and synchronizing the same manufacturer profile with the corresponding RTX/USD light.

## Locked manufacturer LED set

For OGT-301A, use the current **OSRAM OSCONIQ™ P 3737 (2W) Batwing** family for all three channels. This keeps package geometry and angular-model handling consistent and gives OpenGrowTwin a deliberately non-Lambertian manufacturer profile to validate.

| OpenGrowTwin channel | Nominal spectral role | ams OSRAM part | Full production ordering variant | Manufacturer-listed photon/radiant data | Beam |
| --- | --- | --- | --- | --- | --- |
| Blue | Deep Blue, ~450 nm | `GD PUBRA1.15` | `GD PUBRA1.15-T1T4-24-1-D` / Q65115A3136 | ΦP = 5.10…5.90 µmol/s @ 700 mA | 140° batwing |
| Red | Hyper Red, ~660 nm | `GH PUBRA1.25` | `GH PUBRA1.25-T4U1-1-1-D` / Q65115A3134 | ΦP = 5.70…6.30 µmol/s @ 700 mA; typical ΦE ≈ 1050 mW | 140° batwing |
| Far-red | Far Red, ~730 nm | `GF PUBRA1.25` | `GF PUBRA1.25-T1T3-1-1-D` / Q65115A3135 | ΦP = 5.10…5.70 µmol/s @ 700 mA; typical ΦE ≈ 862 mW | 140° batwing |

### Selection note

The earlier OSLON™ Square candidates remain valid reference/fallback devices, including `GD CSSRM3.14` deep blue and `GH CSSRM6.24` hyper red. OGT-301A intentionally standardizes the manufacturer-photometry demonstration on the newer P 3737 Batwing family because matched blue/red/far-red devices are available in the same package family and expose a strongly non-Lambertian angular distribution. The already-uploaded `GD PUBRA1.15` IES/EULUMDAT package therefore becomes the first reference asset.

## Task sequence

- [x] **1. Lock the exact three OSRAM part numbers**
  - Confirmed deep-blue (~450 nm), hyper-red (~660 nm), and far-red (~730 nm) devices.
  - Locked exact manufacturer part numbers and OpenGrowTwin channel mapping above.
  - First reference asset: `GD PUBRA1.15` manufacturer IES/EULUMDAT package dated 2025-05-29.

- [ ] **2. Acquire IES + EULUMDAT packages for each exact part**
  - Download the official ams OSRAM IES package for each LED.
  - Download the matching EULUMDAT package as an independent photometric cross-check.
  - Preserve original filenames and source dates.
  - Blue `GD PUBRA1.15`: IES + EULUMDAT already acquired for the working session; copy into the repository only if redistribution/licensing is appropriate, otherwise store a provenance manifest and retrieval instructions.
  - Red `GH PUBRA1.25`: acquire IES + EULUMDAT.
  - Far-red `GF PUBRA1.25`: acquire IES + EULUMDAT.

- [ ] **3. Verify spectral/radiometric provenance**
  - Record manufacturer radiant-flux / photon-flux / wavelength data used by the scientific model.
  - Classify spectrum provenance explicitly, e.g. `measured_csv`, `digitized_datasheet`, `parameterized_gaussian`, or `monochromatic_approximation`.
  - Do not interpret LM-63 values as ordinary candela for photon calculations until the OSRAM encoding is validated.
  - Document known limitations and assumptions.

- [ ] **4. Implement a generic IES parser**
  - Parse LM-63 metadata, vertical angles, horizontal angles, and intensity samples.
  - Expose a normalized angular field `I(theta, phi)` suitable for deterministic interpolation.
  - Add parser validation for malformed/unsupported profiles.
  - Preserve manufacturer metadata and source provenance.

- [ ] **5. Add `manufacturer_ies` angular model to the deterministic solver**
  - Use interpolated `I(theta, phi)` instead of the current generalized Lambertian model when a validated manufacturer IES profile is available.
  - Keep `generalized_lambertian` as a documented fallback.
  - Keep spectral/radiometric normalization separate from angular-shape data.
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
  - Add tests for IES parsing, interpolation, fallback behavior, provenance, RTX/scientific synchronization, and deterministic A/B results.
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

The manufacturer IES profile supplies the **angular shape**. Spectral/radiometric data supplies the energy/photon normalization. These must remain separate to avoid treating standard photometric file values as direct photon-domain truth without validation.
