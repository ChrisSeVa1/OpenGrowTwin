# OpenGrowTwin validation and reproducibility

This document defines the minimum reproducible validation contract for the MVP.

## CPU regression gate

From the repository root with the project virtual environment active:

```bash
python -m pytest -q
```

The suite covers deterministic solver behavior, USD transforms, visibility/partial-shadow behavior, orchestration, live result updates, copilot safety/tool validation, preset handling, and live optimizer safety.

The release gate is that the complete suite passes with no failures.

## Numerical tolerance policy

OpenGrowTwin separates deterministic scientific calculations from RTX rendering.

For deterministic CPU calculations and serialized scientific metrics:

- use exact structural checks for array shapes, channel identities, prim paths, proposal schemas, and safety flags;
- use floating-point comparison tolerances already encoded by the focused tests for calculated values;
- do not require byte-identical floating-point serialization across Python/NumPy builds;
- treat differences caused only by final decimal representation as equivalent when they remain within the test tolerance;
- PPFD, DLI, CV, uniformity, and spectral-band metrics are authoritative only when produced by the deterministic photon solver.

For preview versus final-grid orchestration, the preview is intentionally lower resolution and is not expected to match the final grid point-for-point. The final-grid scientific result is the acceptance record.

For RTX:

- RTX is a visualization/synchronization layer, not the authoritative PPFD solver;
- the reproducibility requirement is a successful non-empty render-product capture from the validated OpenUSD heatmap stage;
- rendered pixels are not required to be byte-identical across driver or RTX runtime versions;
- the associated scientific metric record is taken from the OpenUSD PPFD data that is rendered.

## Deterministic optimization artifact

Generate the optimized scientific result and OpenUSD heatmap:

```bash
python -m opengrow optimize \
  data/designs/baseline.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/optimization
```

The command must produce `build/optimization/ppfd_heatmap.usda` plus the optimization result artifacts.

## L4 / Kit integration smoke test

`tools/kit_capture_heatmap.py` is executed by the generated Kit launcher with the required capture extensions enabled. The script discovers the repository root from its own location; `OPENGROW_ROOT` is only needed when the repository is intentionally mounted at a different root.

A successful smoke run must:

1. open `build/optimization/ppfd_heatmap.usda`;
2. validate 1,025 PPFD values and 1,025 display colors on `/OpenGrowTwinResults/PPFDHeatmap`;
3. author a 1280 x 720 RTX render product;
4. produce at least one non-empty EXR capture under `build/captures/`;
5. write `build/ogt-305/l4-smoke-evidence.json`.

The JSON evidence record contains only repository-relative artifact paths and scientific/render metadata. It intentionally excludes usernames, home directories, hostnames, cloud instance identifiers, credentials, tokens, and public IP addresses.

## Evidence inspection

After the Kit smoke run:

```bash
cat build/ogt-305/l4-smoke-evidence.json
ls -lh build/captures/ppfd_heatmap_rtx*.exr
```

Acceptance requires `"passed": true` and at least one capture with `size_bytes > 0`.

## Scientific scope

The MVP scientific model is deterministic direct-light spectral transport with geometry-aware binary visibility. It does not claim reflected/multi-bounce spectral transport, thermal/electrical behavior, plant-growth prediction, or a universal optimal orchid spectrum. Curated biological targets are reference treatments used as engineering targets, not universal biological optima.
