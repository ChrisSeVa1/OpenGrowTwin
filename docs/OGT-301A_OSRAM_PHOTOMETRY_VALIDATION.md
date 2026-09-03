# OGT-301A — OSRAM Photometry Validation

**Status:** Step 2 complete; Step 3 scientific/radiometric validation complete for the three selected manufacturer packages.

This document records direct inspection and numerical validation of the ams OSRAM rayfile packages selected for OpenGrowTwin. It is an engineering evidence record for OGT-301A and does not replace the original manufacturer documentation.

## 1. Validated manufacturer files

| Channel | Part | IES package | EULUMDAT package |
| --- | --- | --- | --- |
| Deep blue | `GD PUBRA1.15` | `rayfile_GD_PUBRA1_15_20250529_IES.zip` | `rayfile_GD_PUBRA1_15_20250529_EULUMDAT.zip` |
| Hyper red | `GH PUBRA1.25` | `rayfile_GH_PUBRA1_25_20250526_IES.zip` | `rayfile_GH_PUBRA1_25_20250526_EULUMDAT.zip` |
| Far red | `GF PUBRA1.25` | `rayfile_GF_PUBRA1_25_20250603_IES.zip` | `rayfile_GF_PUBRA1_25_20250603_EULUMDAT.zip` |

Each package contains manufacturer documentation plus mechanical CAD. The CAD is explicitly documented by ams OSRAM as mechanical data and not as optical ray-tracing geometry.

## 2. Manufacturer documentation values

Direct extraction from the included `*_info.pdf` files gives:

| Part | Documented radiant flux | Virtual focus relative to package origin |
| --- | ---: | --- |
| `GD PUBRA1.15` | **1.448 W** | `(-0.005, +0.007, -0.119) mm` |
| `GH PUBRA1.25` | **1.050 W** | `(+0.001, +0.004, -0.005) mm` |
| `GF PUBRA1.25` | **0.869 W** | `(+0.044, -0.037, -0.026) mm` |

The included documentation labels Section 3 as **Radiant Intensity** and supplies the corresponding radiant flux. It also states that rayfile wavelengths are set to the peak emission wavelength for several software-specific exports and that typical radiometric spectra are supplied in formats available in other rayfile packages.

For OpenGrowTwin, these package-specific radiant-flux values are preferred over older planning values when modeling these exact manufacturer rayfile revisions.

## 3. IES structure

All three IES files use the same angular grid:

- LM-63 header: `IESNA:LM-63-2002`
- photometric type field: `1`
- units type field: `2`
- vertical angles: **91 samples**, `0° … 180°` in `2°` increments
- horizontal angles: **73 samples**, `0° … 360°` in `5°` increments
- total angular values: **6,643** per file
- multiplier: `1`

The profiles are full azimuthal fields rather than rotationally symmetric one-dimensional beam curves. This is important for the P 3737 batwing optics.

### IES numeric header values

| Part | LM-63 second numeric field | Input watts field | Intensity-grid maximum |
| --- | ---: | ---: | ---: |
| `GD PUBRA1.15` | 1.448 | 1.981 | 0.401038 |
| `GH PUBRA1.25` | 1.050 | 1.316 | 0.269005 |
| `GF PUBRA1.25` | 0.869 | 1.190 | 0.221278 |

The LM-63 container normally uses photometric terminology. For these OSRAM files, numerical validation below demonstrates that the angular values are being used consistently with the package's radiometric flux, so OpenGrowTwin must preserve the manufacturer-package interpretation rather than relabeling the values as ordinary visible-light candela.

## 4. Solid-angle integration of IES profiles

For each IES file, the angular field was integrated numerically using

\[
\Phi = \int_0^{2\pi}\int_0^{\pi} I(\theta,\phi)\sin\theta\,d\theta\,d\phi
\]

with the supplied 2° × 5° sampling grid and trapezoidal integration. The duplicate `360°` azimuth plane is treated as the periodic endpoint.

| Part | Manufacturer radiant flux | Numerical IES integral | Ratio integral / documented flux | Difference |
| --- | ---: | ---: | ---: | ---: |
| `GD PUBRA1.15` | 1.448 W | **1.447328 W** | 0.999536 | -0.0464% |
| `GH PUBRA1.25` | 1.050 W | **1.049828 W** | 0.999836 | -0.0164% |
| `GF PUBRA1.25` | 0.869 W | **0.868968 W** | 0.999963 | -0.0037% |

### Conclusion

The agreement is substantially better than 0.05% for all three files. Therefore, for these exact OSRAM packages, the IES angular grids are numerically consistent with a physical angular radiant-intensity field whose solid-angle integral equals the documented radiant flux.

This resolves the earlier ambiguity sufficiently for the OpenGrowTwin scientific path: we can treat the manufacturer IES values as the package's radiometric angular intensity data, while still recording that they are carried inside an LM-63 container whose conventional field names are photometric.

## 5. IES ↔ EULUMDAT cross-validation

The corresponding EULUMDAT files contain:

- **72 C planes**, `0° … 355°` in `5°` increments;
- **91 gamma angles**, `0° … 180°` in `2°` increments;
- **6,552** angular values.

The EULUMDAT angular arrays were converted to the IES physical scale using the package radiant-flux factor and compared sample-for-sample against the first 72 IES azimuth planes (`0° … 355°`).

| Part | Max absolute IES↔LDT difference | Mean absolute difference | Difference relative to IES peak |
| --- | ---: | ---: | ---: |
| `GD PUBRA1.15` | 1.192e-6 | 2.461e-7 | 2.97e-6 |
| `GH PUBRA1.25` | 1.000e-6 | 2.167e-7 | 3.72e-6 |
| `GF PUBRA1.25` | 9.010e-7 | 2.028e-7 | 4.07e-6 |

Representative deep-blue check:

```text
IES(C=0°, gamma=0°)          = 0.226079
EULUMDAT scaled equivalent   = 0.226079136
```

The differences are at rounding precision. The IES and EULUMDAT packages therefore encode the same manufacturer angular distribution.

### OGT-301A decision

Use **IES as the canonical runtime angular profile** because:

1. RTX/UsdLux can consume IES directly;
2. the deterministic solver can parse the same 91 × 73 field;
3. EULUMDAT independently validates the angular data and can remain a provenance/cross-check source.

## 6. Scientific normalization policy

Even though the raw IES fields integrate correctly, OpenGrowTwin should maintain a clean separation between source flux and angular shape.

For a parsed manufacturer profile:

\[
p(\theta,\phi) = \frac{I(\theta,\phi)}{\int I\,d\Omega}
\]

so that

\[
\int p(\theta,\phi)d\Omega = 1.
\]

Then the scientific solver uses

\[
I_e(\theta,\phi)=\Phi_e\,p(\theta,\phi)
\]

where `Phi_e` is the authoritative manufacturer radiant flux stored in the LED asset metadata.

This normalization has three advantages:

- it makes the solver's unit contract explicit;
- it keeps angular shape independent of drive scaling or future calibrated flux values;
- it prevents accidental dependence on LM-63 field naming conventions.

The parser should still retain the raw IES integral and original header fields for provenance and validation.

## 7. Spectrum provenance boundary

These six IES/EULUMDAT packages provide angular distribution plus the included manufacturer information/CAD. They do **not** provide a machine-readable spectral curve in the IES or EULUMDAT archive itself.

Therefore OGT-301A must not claim that these six files contain measured SPD data. Until a separate manufacturer spectrum file is acquired, the existing narrowband spectral representation must remain explicitly classified according to its actual provenance, e.g. `monochromatic_approximation` or another separately supported source.

Angular provenance and spectral provenance are separate fields.

## 8. Mechanical CAD limitation

The manufacturer information files state that the supplied CAD is intended for mechanical-component design and is **not valid for optical ray-tracing calculations**.

OpenGrowTwin may use the STEP/IGES/SolidWorks package geometry for visualization and placement, but it must not treat that geometry as the optical model responsible for the manufacturer batwing distribution. The IES distribution is the authoritative far-field angular optical representation for this MVP.

## 9. Acceptance result for Steps 2 and 3

### Step 2 — Acquire manufacturer packages

**PASS**

- [x] Blue IES
- [x] Blue EULUMDAT
- [x] Hyper-red IES
- [x] Hyper-red EULUMDAT
- [x] Far-red IES
- [x] Far-red EULUMDAT

### Step 3 — Verify radiometric provenance and semantics

**PASS for angular/radiometric data**

- [x] Manufacturer radiant flux recorded for all three exact rayfile revisions.
- [x] IES angular grids numerically integrate to the documented radiant flux.
- [x] EULUMDAT and IES distributions agree to rounding precision.
- [x] Mechanical CAD limitation documented.
- [x] Spectral provenance kept separate; no unsupported measured-SPD claim.

## 10. Next implementation gate — Step 4

Implement a generic pure-Python/NumPy LM-63 parser with an `AngularDistribution` abstraction.

Minimum acceptance criteria:

```text
parse IES
  ↓
validate 91 × 73 angular grid
  ↓
retain raw manufacturer intensity field
  ↓
compute solid-angle integral
  ↓
normalize to p(theta, phi)
  ↓
bilinear sample(theta, phi), periodic in phi
  ↓
assert integral(p) ≈ 1
```

Required regression fixtures should avoid redistributing the proprietary OSRAM archives unless their redistribution terms are explicitly confirmed. Prefer small synthetic LM-63 fixtures plus hashes/provenance instructions for manufacturer-file validation.