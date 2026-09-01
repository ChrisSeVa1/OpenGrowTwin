# Architecture

OpenGrowTwin keeps three responsibilities separate:

1. The Python/NumPy engine computes photon-domain quantities deterministically.
2. A stable file contract (`design.json` to `result.json` plus NumPy arrays) isolates the scientific engine from Kit's Python environment.
3. OpenUSD/Omniverse/RTX provides scene interaction and visualizes solver output; it is not the scientific measurement engine.

This enables local CPU development while scarce GCP L4 time is reserved for Kit, RTX, and final capture.

## Current assumptions

- Direct light only; no reflections or occlusion.
- Downward point emitters with an axisymmetric cosine-power distribution.
- Monochromatic channel approximations at 450, 660, and 730 nm.
- PPFD integrates channels from 400 through 700 nm; far-red is separate.
- Sensor plane is horizontal and expressed in metres.

Every approximation is explicit so it can later be replaced by measured spectral power distributions, extended emitters, ray-traced validation, and canopy geometry without changing the result boundary.
