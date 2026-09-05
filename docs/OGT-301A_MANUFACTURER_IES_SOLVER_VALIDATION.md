# OGT-301A — Manufacturer IES Solver Validation

**Status:** Step 5 complete.

This document records the deterministic-solver validation for manufacturer-backed Type-C IES photometry in OpenGrowTwin. Manufacturer optical assets remain user-supplied local inputs and are not redistributed by the public repository.

## 1. Scope

Step 5 adds a `manufacturer_ies` angular model to the deterministic photon-domain solver while preserving `generalized_lambertian` as a documented fallback.

The scientific path is:

`manufacturer radiant power × normalized spectrum s(lambda) × normalized angular distribution p(theta, phi) × 1/r^2 × receiver incidence × OpenUSD visibility → spectral irradiance → photon metrics`

The deterministic solver remains the scientific authority. RTX visualization is not used as scientific ground truth.

## 2. Orientation convention

OpenGrowTwin uses the following project convention for manufacturer Type-C profiles:

- optical axis: local `-Z`
- Type-C `C=0` reference: local `+X`
- emitter orientation matrix: local XYZ → world XYZ
- positive axial rotation: right-handed about world `+Z` for the straight-down validation case

The solver transforms world-space receiver rays into emitter-local coordinates before evaluating the manufacturer angular distribution.

## 3. Public deterministic orientation regression

A synthetic asymmetric Type-C angular profile is used in the public regression suite so orientation behavior can be tested without redistributing manufacturer data.

The regression verifies that a +90° emitter rotation moves the deliberately asymmetric C=0 lobe from world +X toward world +Y under the OpenGrowTwin convention.

Validation command:

```bash
python -m pytest -q tests/test_direct_solver.py::test_manufacturer_ies_azimuth_follows_emitter_orientation
```

Result:

```text
1 passed in 0.41s
```

Full regression result after the new orientation test:

```text
110 passed in 3.24s
```

## 4. Real manufacturer orientation sanity check

The local validator `tools/validate_manufacturer_ies_orientation.py` was run against the three selected ams OSRAM OSCONIQ P 3737 manufacturer IES profiles at 0°, 90°, 180°, and 270° axial rotations.

Selected parts:

| Channel | Part | Manufacturer IES revision |
| --- | --- | --- |
| Deep blue | `GD PUBRA1.15` | 2025-05-29 |
| Hyper red | `GH PUBRA1.25` | 2025-05-26 |
| Far red | `GF PUBRA1.25` | 2025-06-03 |

All three profiles returned:

```text
"all_quarter_turn_checks_pass": true
```

The deep-blue profile also retained a normalized solid-angle integral of exactly `1.0`; its raw manufacturer-grid integral was `1.44732841036462`, consistent with the earlier provenance validation.

For the 1 m × 1 m, 41 × 41 receiver grid at 0.6 m source height, rotating the blue profile through 0°, 90°, 180°, and 270° preserved the scalar field statistics while rotating the spatial footprint. Mean irradiance remained `0.3247527105957691` and CV remained `0.13562580858228296` for all quarter turns.

This demonstrates that the real full-azimuth Type-C profile follows emitter orientation rather than being treated as a rotationally symmetric beam.

## 5. Lambertian vs manufacturer-IES A/B validation

A controlled A/B comparison was run with:

- identical fixture geometry
- identical emitter positions
- identical radiant power
- identical manufacturer tabulated SPD
- identical receiver geometry
- identical visibility model
- only the angular model changed

The comparison changed:

```text
generalized_lambertian
        ↓
manufacturer_ies
```

Validation command:

```bash
python tools/validate_manufacturer_ies_ab.py \
  --asset-root sources/osram/extracted \
  --design demo/design.json \
  --output build/ogt-301a/manufacturer-ies-ab.json
```

### PPFD results

| Metric | Generalized Lambertian | Manufacturer IES |
| --- | ---: | ---: |
| Mean PPFD | 76.5617 | 55.8179 |
| Minimum PPFD | 44.9827 | 39.9454 |
| Maximum PPFD | 99.7022 | 66.7023 |
| Standard deviation | 13.4067 | 6.5399 |
| CV | 0.17511 | 0.11716 |
| Min/mean uniformity | 0.58754 | 0.71564 |

Derived comparison:

- mean PPFD change: approximately **-27.1%**
- maximum PPFD change: approximately **-33.1%**
- minimum PPFD change: approximately **-11.2%**
- CV improvement: approximately **33.1% lower**
- min/mean uniformity: **0.588 → 0.716**

The mean absolute PPFD difference was `20.743736454662965 µmol/m²/s`, equal to `27.09415828083905%` of the Lambertian mean.

### Far-red 700–750 nm results

| Metric | Generalized Lambertian | Manufacturer IES |
| --- | ---: | ---: |
| Mean far-red | 7.5940 | 5.7153 |
| Minimum far-red | 4.3415 | 3.8034 |
| Maximum far-red | 9.8562 | 7.0305 |
| CV | 0.18132 | 0.13763 |
| Min/mean uniformity | 0.57170 | 0.66548 |

The far-red field shows the same qualitative redistribution pattern.

## 6. Interpretation

The manufacturer batwing profile redistributes more emitted power toward larger off-axis angles than the simplified generalized-Lambertian approximation. For the finite 1.0 m × 0.6 m receiver used in this A/B test, less emitted flux is intercepted by the modeled canopy area, so mean PPFD is lower while the field becomes flatter.

The result does **not** mean that manufacturer IES photometry universally reduces PPFD by 27%. The magnitude depends on fixture arrangement, source height, receiver extent, emitted power, and the selected manufacturer optical profile.

The engineering conclusion is that realistic manufacturer angular photometry can materially change predicted horticultural-lighting performance even when fixture geometry and emitted radiant power are unchanged.

For the Golden Ticket demonstration, the strongest concise result is:

> Replacing the simplified angular model with manufacturer IES photometry changed predicted mean PPFD by approximately 27% and improved predicted min/mean uniformity from 0.588 to 0.716, without changing fixture geometry or emitted radiant power.

This is a concrete reason for OpenGrowTwin to exist as an engineering simulation workflow rather than merely as an Omniverse visualization.

## 7. Scientific and licensing boundaries

OpenGrowTwin currently models direct illumination plus geometry-aware visibility. This validation does not include:

- multi-bounce or interreflection transport
- canopy interception or leaf-level radiative transfer
- thermal behavior
- wall-plug electrical efficiency unless separately provided
- biological growth or yield prediction

Reporting bands are:

- PPFD: 400–700 nm
- far-red: >700–750 nm

Manufacturer IES, EULUMDAT, spectrum, rayset, CAD, and archive files are not redistributed by OpenGrowTwin. `sources/osram/` remains gitignored. Users supply manufacturer assets separately under the manufacturer terms.

## 8. Step 5 acceptance

**PASS**

- [x] manufacturer Type-C IES path added to deterministic solver
- [x] angular shape normalized independently of authoritative radiant power
- [x] manufacturer tabulated SPD used for photon conversion when available
- [x] inverse-square attenuation retained
- [x] receiver incidence retained
- [x] OpenUSD geometry visibility retained
- [x] full emitter orientation retained from OpenUSD
- [x] Type-C azimuth orientation regression passes
- [x] real blue/red/far-red quarter-turn checks pass
- [x] generalized-Lambertian fallback retained
- [x] real OSRAM A/B comparison captured
- [x] full regression suite passes: 110 tests
- [x] manufacturer assets remain excluded from the public repository

## 9. Next gate

Proceed to Step 6: attach the same manufacturer IES profile to the corresponding RTX/USD light while preserving the existing OpenGrowTwin rule that RTX is visualization and the deterministic solver is the scientific authority.
