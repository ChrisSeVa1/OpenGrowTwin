# OpenGrowTwin

OpenGrowTwin is an evidence-driven spectral-lighting digital twin for controlled-environment horticulture. It combines an auditable photon-domain solver with OpenUSD/NVIDIA Omniverse visualization.

The MVP deliberately separates the science from rendering:

- `opengrow` computes spectral photon flux, PPFD, DLI, spatial uniformity, and far-red photon flux.
- OpenUSD/Omniverse consumes the result files and displays the chamber and heatmap.
- Biological targets are traceable reference treatments, not universal growth optima.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
opengrow simulate demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/results

opengrow optimize demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/optimization

opengrow scene demo/design.json --out demo/grow_chamber.usda
```

The command writes `ppfd.npy`, `band_ppfd.npy`, `spectral_irradiance.npy`, `metrics.json`, and `result.json`.

The optimizer caches per-channel photon basis maps at candidate fixture heights,
uses their exact linear superposition to select bounded radiant powers, and
writes a reproducible baseline/optimized comparison. It optimizes the lighting
installation to reproduce a reference environment—not plant growth.

The height objective balances target error, PPFD coefficient of variation, and
a documented radiant-power penalty. Electrical consumption is not claimed
until LED wall-plug efficiencies are added from traceable manufacturer data.
Candidate selection rejects avoidable regressions in baseline PPFD uniformity.

The demo fixture uses sixteen interleaved PAR emitters (eight blue and eight
red) plus four supplemental far-red emitters over a 41 × 25 sensor grid.
Optimization also writes baseline and optimized PNG heatmaps with one shared
absolute color scale, plus CSV grids for inspection and later OpenUSD import.
The PNG colors are explanatory only; NumPy/CSV values remain authoritative.

The same command writes `ppfd_heatmap.usda`: a self-contained OpenUSD mesh
with exact PPFD values in `primvars:opengrow:ppfd`, display colors in
`primvars:displayColor`, quad topology, grid dimensions, and namespaced
summary metrics. Kit can sublayer or reference this result without importing
the solver into its Python environment.

The `scene` command authors the OGT-101 live-stage contract. The stage is
Z-up, uses metres, and identifies fixtures, emitters, sensor planes,
occluders, and results with `opengrow:role`. Emitters carry wavelength,
radiant power, beam exponent, enabled state, and a local `-Z` emission
direction. Fixture transforms therefore provide the authoritative movable
state for the next solver adapter rather than hard-coded world coordinates.

Inside Kit, validate discovery and world-transform extraction with:

```bash
./repo.sh --exec tools/kit_validate_live_scene.py demo/grow_chamber.usda
```

The OGT-102 adapter groups the discovered world-space emitters into the
existing solver channel model. It also transfers the sensor-plane dimensions,
resolution, center, and orientation. The direct solver accepts emitter
direction and receiver orientation while retaining the original downward-light
defaults. Validate live fixture translation and rotation propagation in Kit:

```bash
./repo.sh --exec tools/kit_validate_usd_solver_input.py
```

OGT-103 adds finite emitter-to-sensor visibility segments against transformed
USD `Cube` prims tagged as `opengrow:occluderShape = "box"`. Contributions are
masked per emitter, preserving partial shadows from the remaining emitters.
The solver returns binary visibility fields and per-emitter blocked-ray
diagnostics. Validate a parked and beam-intersecting occluder in Kit with:

```bash
./repo.sh --exec tools/kit_validate_occlusion.py
```

## Headless Kit/RTX capture

After generating `build/optimization/ppfd_heatmap.usda` on the GPU VM, run
`tools/kit_capture_heatmap.py` through the OpenGrowTwin Kit launcher using
`--exec`. It opens the result layer, validates the PPFD and display-color
primvars, creates a top-down camera and a 1280 × 720 USD render product, then
uses Kit's capture extension to write an RTX image under `build/captures/`.
This path does not create a GLFW viewport window and is suitable for a VM with
no X display.

## Scientific scope

The current solver models direct light from point emitters with cosine beam falloff and inverse-square attenuation. Reflections, canopy interception, thermal effects, plant growth, and spectral rendering validation are outside the MVP. Far-red (730 nm) is reported separately and is not included in 400–700 nm PPFD.

The bundled Phalaenopsis target reproduces a published reference treatment of approximately 200 µmol/m²/s for 14 hours/day with a 40% blue / 60% red photon fraction. It is not presented as an optimal orchid spectrum.

## Project layout

- `src/opengrow/physics/` — photon conversion, direct solver, and metrics
- `data/` — LED metadata and evidence-based targets
- `demo/` — deterministic example design and OpenUSD placeholder scene
- `tests/` — analytical scientific validation
- `exts/opengrow.twin/` — Omniverse Kit integration boundary
- `docs/` — architecture and GCP/Kit reproducibility notes

Detailed engineering records:

- [`docs/gcp-setup.md`](docs/gcp-setup.md) — Day 1 GCP/L4 and Kit infrastructure gate
- [`docs/day-2-science-openusd-rtx.md`](docs/day-2-science-openusd-rtx.md) — tested solver, optimization, OpenUSD, and headless RTX reproduction guide

## License

OpenGrowTwin code is licensed under Apache-2.0. NVIDIA software, manufacturer data, research literature, and other dependencies retain their respective terms; see `THIRD_PARTY_NOTICES.md`.
