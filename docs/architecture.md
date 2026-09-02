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

## Current assumptions

- Direct light only; no reflections or occlusion.
- Downward point emitters with an axisymmetric cosine-power distribution.
- Monochromatic channel approximations at 450, 660, and 730 nm.
- PPFD integrates channels from 400 through 700 nm; far-red is separate.
- Sensor plane is horizontal and expressed in metres.

Every approximation is explicit so it can later be replaced by measured spectral power distributions, extended emitters, ray-traced validation, and canopy geometry without changing the result boundary.
