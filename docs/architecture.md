# Architecture

OpenGrowTwin keeps three responsibilities separate:

1. The Python/NumPy engine computes photon-domain quantities deterministically.
2. Stable result files (`result.json` plus NumPy arrays) isolate the scientific engine from Kit's Python environment.
3. OpenUSD/Omniverse/RTX provides scene interaction and visualizes solver output; it is not the scientific measurement engine.

This enables local CPU development while scarce GCP L4 time is reserved for Kit, RTX, and final capture.

## Live OpenUSD scene contract (OGT-101)

The live stage is the authoritative source for installation geometry and
emitter state. `design.json` remains a deterministic bootstrap input, but the
`opengrow scene` command converts it into `demo/grow_chamber.usda`; subsequent
interactive simulations read the open stage rather than the JSON file.

The contract is versioned as `0.3.0`, uses metres, is Z-up and right-handed,
and defines local `-Z` as the emitter forward direction. Entities are
discovered by `opengrow:role`, never by fixed paths:

| Role | Required state |
|---|---|
| `fixture` | ID and transform |
| `emitter` | channel, wavelength, radiant power, beam exponent, enabled state, direction and transform |
| `sensorPlane` | ID, dimensions, grid resolution and transform |
| `occluder` | ID, enabled state, transform and boundable geometry |
| `results` | result-layer relationship or asset metadata |

`opengrow.usd.stage_reader.discover_stage()` resolves emitter positions and
directions in world space inside Kit. This is the input boundary for OGT-102.

## Live stage to solver adapter (OGT-102)

`stage_to_solver_design()` converts the open stage into the deterministic
solver model. It groups enabled emitters by channel and transfers wavelength,
radiant power, beam exponent, world position, and world direction. It also
transfers the selected sensor plane's dimensions, grid resolution, world
center, and local U/V axes.

The direct solver's backward-compatible default remains a horizontal receiver
and downward-facing emitters. Live-stage inputs can additionally provide
oriented emitters and an oriented planar sensor grid. Emission-angle and
receiver-incidence terms are evaluated separately, so rotating a fixture has a
physical effect rather than merely moving its visualization.

## Geometry-aware visibility (OGT-103)

The MVP uses transformed USD cubes tagged as `box` occluder proxies. Their
world center, oriented axes, and half extents are passed into the CPU solver.
For each emitter and sensor sample, a finite segment-versus-oriented-box test
produces a binary visibility value. Only that emitter's blocked contribution
is removed, so other fixtures and channels continue illuminating the same
sample. Per-emitter and aggregate blocked-ray counts make the shadow result
auditable. General triangle-mesh intersection remains outside the MVP path.

## Kit simulation orchestration (OGT-104)

The `opengrow.twin` extension reads USD state on Kit's main thread, then runs
the prepared NumPy design through a background executor. The panel exposes a
manual Simulate action and preview/final grid selection. OpenUSD object-change
notices are debounced before automatic preview simulation, preventing drag
operations from queuing a run for every intermediate transform. Errors and
completion metrics are surfaced in the same panel and in the Kit log.

## In-stage results (OGT-105)

Every completed run updates two meshes below the existing `Results` prim:
`BaselinePPFDHeatmap` and `CurrentPPFDHeatmap`. Exact PPFD remains a vertex
primvar; display colors are derived from a fixed scale established by the
matching-resolution baseline. Visibility switching provides an immediate
comparison without reopening or replacing the stage. Namespaced attributes
store the full metric summary alongside the current scientific field.

## Scientific and RTX light synchronization (OGT-106)

Scientific emitter attributes remain the single source of truth. A child RTX
`DiskLight` inherits each emitter's world transform, while synchronization
derives enabled intensity, an approximate channel color, and wavelength
metadata. RTX intensity uses a documented presentation scale of 500 intensity
units per modeled radiant watt. It makes the scene legible but is never treated
as a calibrated optical quantity; PPFD continues to come only from the photon
solver.

## Current assumptions

- Direct light only; no reflections or occlusion.
- Downward point emitters with an axisymmetric cosine-power distribution.
- Monochromatic channel approximations at 450, 660, and 730 nm.
- PPFD integrates channels from 400 through 700 nm; far-red is separate.
- Sensor plane is horizontal and expressed in metres.

Every approximation is explicit so it can later be replaced by measured spectral power distributions, extended emitters, ray-traced validation, and canopy geometry without changing the result boundary.
