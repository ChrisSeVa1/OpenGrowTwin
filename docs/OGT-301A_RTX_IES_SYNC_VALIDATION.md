# OGT-301A Step 6 — Manufacturer IES / RTX Synchronization Validation

## Status

**PASS — headless Kit validation complete; graphical viewport evidence remains the final Step 6 gate.**

This step extends the existing OGT-106 scientific/RTX synchronization layer so
manufacturer-provided IES distributions can drive NVIDIA RTX presentation while
the deterministic OpenGrowTwin solver remains the scientific authority.

The raw ams OSRAM optical assets are **not** committed to this repository. The
validators expect user-supplied files under `sources/osram/extracted/`, which is
gitignored.

## Architecture

```text
Authoritative OpenUSD scientific emitter
             |
             +-- transform / power / enabled state
             |
             +-- manufacturer IES --> deterministic solver --> PPFD / far-red
             |
             +-- manufacturer IES --> UsdLux.ShapingAPI --> RTX presentation
```

RTX remains explicitly presentation-only. Rendered pixels are not used as a
scientific PPFD measurement.

## Environment

Validated on the project NVIDIA Omniverse Kit environment:

- Kit SDK 110.3.0
- NVIDIA L4 GPU environment
- OpenUSD/PXR version bundled with Kit
- `opengrow.twin-0.1.0`

The installed Kit API was probed directly. `UsdLux.ShapingAPI` exposes:

- `CreateShapingIesFileAttr`
- `CreateShapingIesNormalizeAttr`
- `CreateShapingIesAngleScaleAttr`
- matching getter methods

This avoids assuming API names from another OpenUSD release.

## Implementation boundary

`src/opengrow/usd/rtx_lights.py` remains the synchronization boundary created by
OGT-106. Step 6 extends that path rather than introducing a second lighting
system.

For a channel with a supplied IES path, the child `UsdLux.DiskLight` receives:

- manufacturer IES via `UsdLux.ShapingAPI`;
- IES normalization enabled;
- IES angle scale `1.0`;
- the pre-existing approximate display color and visual intensity mapping;
- `opengrow:visualOnly = true`;
- `opengrow:scientificSourcePath` pointing to the authoritative emitter.

## Tracked validators

### 1. IES binding validator

`tools/kit_validate_manufacturer_ies_rtx.py`

This opens `demo/grow_chamber.usda`, loads the local manufacturer files, calls
`sync_rtx_lights`, then reads the authored USD attributes back from the stage.

Validated results:

```text
scientific_emitter_count: 20
light_count: 20
ies_channel_count: 3
manufacturer_ies_light_count: 20
PASS: 20 scientific emitters synchronized to RTX
PASS: all 20 RTX lights carry manufacturer IES shaping
PASS: RTX lights remain explicitly visualOnly
```

For every one of the 20 child RTX lights the validator observed:

```text
shaping:ies:file       = expected local manufacturer file
shaping:ies:normalize  = true
shaping:ies:angleScale = 1.0
opengrow:visualOnly    = true
opengrow:scientificSourcePath = matching parent scientific emitter
```

The three locally supplied IES revisions used in this acceptance run were:

- `GD_PUBRA1_15_20250529.ies` — blue
- `GH_PUBRA1_25_20250526.ies` — red
- `GF_PUBRA1_25_20250603.ies` — far-red

These filenames are recorded for reproducibility; the files themselves are not
redistributed.

### 2. Shared-transform validator

`tools/kit_validate_manufacturer_ies_transform_sync.py`

The validator uses `/World/GrowInstallation/Fixtures/Fixture_01/Emitters/Blue_01`
and its child `RTXLight`.

It performs the following sequence:

1. read the baseline world orientation through OpenGrowTwin stage discovery;
2. independently read the scientific emitter world transform;
3. independently read the inherited RTX child world transform;
4. author a +90 degree local-Z rotation on the scientific emitter;
5. rediscover the scientific orientation;
6. confirm the RTX child inherits exactly the same new world orientation;
7. confirm the manufacturer IES remains attached;
8. evaluate the real manufacturer IES field on a square sensor grid centered on
   the emitter optical axis;
9. verify the computed field rotates by the expected quarter turn.

Validated output:

```text
baseline_science_equals_emitter_world: PASS
baseline_rtx_inherits_emitter_world: PASS
rotated_science_equals_emitter_world: PASS
rotated_rtx_inherits_emitter_world: PASS
rotation_matrix_max_abs_error: 1.6081226496766364e-16
scientific_orientation_is_exact_plus90Z: PASS
rtx_ies_survives_transform_edit: PASS
field_rotation_max_abs_error: 5.551115123125783e-16
field_rotation_error_fraction_of_peak: 1.2578094529619454e-15
scientific_ies_field_rotates_with_usd_transform: PASS
PASS: scientific solver and RTX share authoritative OpenUSD transform
```

The post-rotation scientific and RTX orientation matrices were identical to
floating-point precision:

```text
[[ 2.220446049250313e-16, -1.0, 0.0],
 [ 1.0,  2.220446049250313e-16, 0.0],
 [ 0.0,  0.0, 1.0]]
```

## Important validation detail

A first transform-field check incorrectly compared an emitter-offset field with
`np.rot90()` about the canopy-grid center. That is not the same physical
operation as rotating an IES distribution about the emitter optical axis.

The final validator therefore centers its square validation grid directly under
the selected emitter. With the physical and array rotation centers aligned, the
quarter-turn comparison agrees to approximately `1.26e-15` of peak field.

No solver change was required.

## CPU regression

After the Step 6 IES synchronization implementation:

```text
112 passed in 3.20s
```

This confirms the manufacturer RTX integration did not regress the deterministic
solver, existing OpenUSD scene contract, copilot safety controls, or previous
manufacturer-photometry tests.

## Scientific authority and limitations

The deterministic solver remains the source of scientific PPFD, DLI, spectral,
and uniformity values. RTX is a synchronized visual representation only.

The current scientific transport still models direct illumination plus explicit
occlusion. This validation does not claim:

- calibrated PPFD from rendered pixels;
- multi-bounce optical transport;
- canopy interception or plant-growth prediction;
- thermal or electrical efficiency modeling;
- that manufacturer IES orientation conventions are universal beyond the
  OpenGrowTwin Type-C mapping validated for this project.

## Step 6 acceptance state

Headless engineering acceptance is complete:

- [x] installed Kit `UsdLux.ShapingAPI` verified directly;
- [x] 20/20 RTX lights receive the correct manufacturer IES mapping;
- [x] IES normalization and angle scale verified by reading authored USD back;
- [x] RTX remains `opengrow:visualOnly = true`;
- [x] scientific and RTX world orientations are identical before and after an
  authoritative emitter rotation;
- [x] real manufacturer-IES scientific field rotates consistently with the same
  OpenUSD edit;
- [x] full CPU suite passes: 112 tests;
- [ ] capture graphical RTX viewport evidence showing the IES-shaped lighting
  responding to the same live OpenUSD transform edit.

Once the graphical evidence is captured, Step 6 can be marked complete and the
branch can proceed to PR/merge.
