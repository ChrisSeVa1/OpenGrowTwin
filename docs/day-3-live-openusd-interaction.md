# OpenGrowTwin — Day 3 Live OpenUSD Interaction and RTX Synchronization Guide

**Session date:** 2026-09-02

**Project:** OpenGrowTwin

**Repository:** <https://github.com/ChrisSeVa1/OpenGrowTwin>

**Milestones:** OGT-101 through OGT-106

**Status:** Product-critical interactive vertical slice passed on NVIDIA Kit 110 / L4

## 1. Relationship to Days 1 and 2

Day 1 established the GCP and NVIDIA infrastructure: a `g2-standard-8` VM
with one NVIDIA L4 could build and start the custom
`opengrowtwin.my_editor` application and reach both `app ready` and
`RTX ready`.

Day 2 established the deterministic science and offline visualization path:

```text
design.json
    → photon-domain solver and optimizer
    → NumPy arrays and metrics
    → self-contained OpenUSD PPFD mesh
    → headless RTX image
```

Day 3 converted that offline path into a live OpenUSD interaction loop:

```text
live OpenUSD stage
    → discover fixtures, emitters, sensor plane, and occluders
    → resolve world transforms and scientific attributes
    → geometry-aware photon simulation
    → update PPFD mesh and metrics in the same open stage
    → synchronize presentation-only RTX lights
```

The CPU photon solver remains authoritative for PPFD. RTX lighting is a
synchronized visual representation, not a substitute scientific measurement.

## 2. What was accomplished

### 2.1 OGT-101 — Versioned live-scene contract

The generated `demo/grow_chamber.usda` is now a complete, discoverable live
scene rather than a placeholder. Its contract is versioned as `0.3.0` and
defines:

- metres as the stage unit;
- Z as the up axis;
- a right-handed coordinate system;
- local `-Z` as the emitter-forward direction;
- one installation and fixture;
- 20 scientific emitters;
- one sensor plane with a 41 × 25 authored grid;
- one movable proxy-box occluder;
- one results container.

Entities are discovered through `opengrow:role`, not hard-coded world
coordinates. Emitters carry channel, wavelength, modeled optical radiant
power, beam exponent, enabled state, direction, and transform.

The Kit validation discovered:

| Entity | Count |
|---|---:|
| Installation | 1 |
| Fixture | 1 |
| Blue emitters at 450 nm | 8 |
| Red emitters at 660 nm | 8 |
| Far-red emitters at 730 nm | 4 |
| Sensor planes | 1 |
| Occluders | 1 |
| Results containers | 1 |

### 2.2 OGT-102 — Live USD-to-solver adapter

`opengrow.usd.stage_reader` resolves emitter position and direction in world
space and converts the open stage into the existing solver input structure.
The adapter transfers:

- channel and wavelength;
- optical radiant power;
- beam exponent and enabled state;
- emitter world position and direction;
- sensor-plane dimensions, center, orientation, and grid resolution;
- enabled proxy-box occluders.

The direct solver was generalized to separate emitter-angle falloff from
receiver-incidence cosine while preserving its original downward-emitter,
horizontal-receiver defaults.

The Kit acceptance test translated the fixture by `+0.1 m` and rotated it by
10° about X. The first emitter changed from `z = 0.6 m` to `z = 0.7 m`, and
its direction became:

```text
(0, sin(10°), -cos(10°))
= (0, 0.1736481777, -0.9848077530)
```

No edit to `design.json` was required.

### 2.3 OGT-103 — Geometry-aware visibility

The MVP implements finite emitter-to-sensor segment tests against transformed
USD cubes tagged as proxy-box occluders. For every emitter and sensor sample:

1. the segment is transformed into the oriented box frame;
2. a slab intersection test returns binary visibility;
3. only the blocked emitter contribution is removed;
4. contributions from all other emitters remain;
5. per-emitter and aggregate blocked-ray diagnostics are returned.

Moving the demo occluder into the beam produced:

| Metric | Clear | Occluded |
|---|---:|---:|
| Mean PPFD | 76.505286 | 73.554750 µmol/m²/s |
| Total rays | 20,500 | 20,500 |
| Blocked rays | 0 | 1,432 |
| Blocked-ray fraction | 0% | 6.9854% |
| Affected sensor cells | 0 | 840 of 1,025 |
| Exactly unaffected cells | 1,025 | 185 |

This demonstrates a spatially selective shadow rather than a global fixture
power reduction. General triangle-mesh intersection remains outside the MVP.

### 2.4 OGT-104 — Kit simulation orchestration

The `opengrow.twin` Kit extension now provides:

- a **Simulate** action;
- preview and final grid modes;
- a **Cancel** action;
- debounced automatic preview after relevant stage changes;
- main-thread USD extraction;
- background NumPy simulation;
- status, error, and metric reporting in the panel and log.

Result prim changes and RTX-light synchronization changes are excluded from
the automatic simulation trigger, preventing feedback loops.

The verified modes were:

| Mode | Grid | Rays | Mean PPFD |
|---|---:|---:|---:|
| Preview | 21 × 13 | 5,460 | 75.359773 µmol/m²/s |
| Final | 41 × 25 | 20,500 | 76.505286 µmol/m²/s |

The preview mean differed from the final mean by `1.4973%`, within the 2%
acceptance threshold for the bundled fixture.

### 2.5 OGT-105 — Live in-stage heatmaps and metrics

Completed simulations author two meshes below the existing results prim:

```text
/World/GrowInstallation/Results/BaselinePPFDHeatmap
/World/GrowInstallation/Results/CurrentPPFDHeatmap
```

Both meshes contain:

- exact vertex values in `primvars:opengrow:ppfd`;
- vertex colors in `primvars:displayColor`;
- grid dimensions and units;
- fixed legend limits derived from the matching-resolution baseline;
- mean, minimum, maximum, CV, minimum/mean uniformity, DLI, mean far-red,
  and blocked-ray metadata.

The meshes are updated without reopening or replacing the stage. A 2 mm
display-only offset prevents depth flicker above the scientific sensor plane.
The panel can switch between baseline and current visibility.

The verified full-grid update contained 1,025 PPFD values and colors. With
the occluder inserted, the live result reported:

| Quantity | Value |
|---|---:|
| Baseline mean PPFD | 76.505286 µmol/m²/s |
| Current mean PPFD | 73.554750 µmol/m²/s |
| Fixed legend minimum | 44.967477 µmol/m²/s |
| Fixed legend maximum | 99.630661 µmol/m²/s |
| Current DLI at 14 h | 3.707159 mol/m²/day |
| Current mean far-red | 8.278320 µmol/m²/s |

### 2.6 OGT-106 — Scientific/RTX emitter synchronization

Each scientific emitter owns a child RTX `DiskLight`. The authoritative
attributes remain on the emitter:

- `opengrow:radiantPowerW`;
- `opengrow:wavelengthNm`;
- `opengrow:enabled`;
- emitter and parent fixture transforms.

Synchronization derives:

- an approximate channel display color;
- RTX enabled intensity;
- inherited spatial transform;
- wavelength and relative-power metadata;
- a source-path link back to the scientific emitter.

The visual mapping uses `500 RTX intensity units` per modeled optical radiant
watt and is explicitly marked `opengrow:visualOnly = true`. It is an exposure
choice for a legible viewport and is not a calibrated radiometric conversion.

Doubling Blue_01 from 2.25 W to 4.5 W produced:

| Quantity | Baseline | Updated |
|---|---:|---:|
| Modeled optical radiant power | 2.25 W | 4.50 W |
| RTX intensity | 1,125 | 2,250 |
| Full-grid mean PPFD | 76.505286 | 79.861929 µmol/m²/s |

The same authoritative power edit therefore changed both RTX appearance and
the scientific result.

## 3. Repository changes

The main implementation boundaries are:

| Path | Responsibility |
|---|---|
| `src/opengrow/usd/scene_contract.py` | Portable USDA scene generation and schema constants |
| `src/opengrow/usd/stage_reader.py` | Kit-side discovery and USD-to-solver conversion |
| `src/opengrow/physics/visibility.py` | Finite segment/oriented-box visibility |
| `src/opengrow/physics/direct_solver.py` | Direction-aware photon calculation and occlusion diagnostics |
| `src/opengrow/orchestration.py` | Preview/final preparation and simulation orchestration |
| `src/opengrow/usd/live_results.py` | In-stage PPFD meshes, fixed colors, metrics, and comparison visibility |
| `src/opengrow/usd/rtx_lights.py` | Scientific-emitter to RTX-light synchronization |
| `exts/opengrow.twin/` | Interactive Kit extension and panel |
| `tools/kit_validate_*.py` | Headless Kit acceptance scripts |

The verified GitHub commit sequence is:

| Commit | Purpose |
|---|---|
| `5f68d17` | Implement OGT-101 scene contract |
| `a0fe08f` | Decouple Kit stage reading from Matplotlib |
| `f6b1773` | Implement OGT-102 live USD solver adapter |
| `cc64f81` | Implement OGT-103 geometry-aware visibility |
| `ff85aaa` | Implement OGT-104 Kit simulation orchestration |
| `374493c` | Implement OGT-105 live-stage heatmaps |
| `dd0bdbc` | Correct live USD child-prim authoring for USD 25.11 |
| `5da3336` | Implement OGT-106 RTX emitter synchronization |

## 4. CPU reproduction

### 4.1 Clone and install

```bash
git clone https://github.com/ChrisSeVa1/OpenGrowTwin.git
cd OpenGrowTwin
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

### 4.2 Run the complete automated suite

```bash
python -m pytest -q
```

At the end of OGT-106, the expected result is:

```text
39 passed
```

### 4.3 Regenerate the live scene

```bash
python -m opengrow scene \
  demo/design.json \
  --out demo/grow_chamber.usda
```

Expected contract summary:

```json
{
  "schema_version": "0.3.0",
  "fixture_count": 1,
  "emitter_count": 20,
  "sensor_plane_count": 1,
  "occluder_count": 1
}
```

### 4.4 Confirm the scientific baseline

```bash
python -m opengrow simulate demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/results
```

The baseline mean PPFD should be approximately:

```text
76.505285549336 µmol/m²/s
```

## 5. GPU/Kit reproduction

### 5.1 Preconditions

- Ubuntu 22.04 GCP VM;
- instance `opengrow-gpu` in `us-central1-b`;
- `g2-standard-8` with one NVIDIA L4;
- NVIDIA driver verified with `nvidia-smi`;
- Kit App Template built under `~/projects/kit-app-template`;
- `opengrowtwin.my_editor.kit` present in the release build;
- OpenGrowTwin cloned under `~/projects/OpenGrowTwin`.

Synchronize and test:

```bash
cd ~/projects/OpenGrowTwin
git pull
source .venv/bin/activate
python -m pytest -q
```

### 5.2 Common Kit invocation

Run commands from:

```bash
cd ~/projects/kit-app-template
```

The common executable and application paths are:

```text
./_build/linux-x86_64/release/kit/kit
./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit
```

Do not substitute similar-looking directory names. A wrong application path
fails immediately with `File doesn't exist`.

### 5.3 OGT-101 — Validate the scene contract

```bash
./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --no-window \
  --exec ~/projects/OpenGrowTwin/tools/kit_validate_live_scene.py
```

Success marker:

```text
[OpenGrowTwin] OGT-101 live scene contract valid
```

### 5.4 OGT-102 — Validate the USD-to-solver adapter

```bash
./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --no-window \
  --exec ~/projects/OpenGrowTwin/tools/kit_validate_usd_solver_input.py
```

Success marker:

```text
[OpenGrowTwin] OGT-102 USD-to-solver adapter valid
```

### 5.5 OGT-103 — Validate occlusion

```bash
./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --no-window \
  --exec ~/projects/OpenGrowTwin/tools/kit_validate_occlusion.py
```

Success marker:

```text
[OpenGrowTwin] OGT-103 geometry-aware visibility valid
```

### 5.6 OGT-104 — Validate the Kit extension and orchestration

```bash
./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --no-window \
  --ext-folder ~/projects/OpenGrowTwin/exts \
  --enable opengrow.twin \
  --exec ~/projects/OpenGrowTwin/tools/kit_validate_orchestration.py
```

Success marker:

```text
[OpenGrowTwin] OGT-104 Kit orchestration valid
```

### 5.7 OGT-105 — Validate live in-stage results

```bash
./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --no-window \
  --ext-folder ~/projects/OpenGrowTwin/exts \
  --enable opengrow.twin \
  --exec ~/projects/OpenGrowTwin/tools/kit_validate_live_results.py
```

Success marker:

```text
[OpenGrowTwin] OGT-105 live heatmap update valid
```

### 5.8 OGT-106 — Validate RTX/scientific synchronization

```bash
./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --no-window \
  --ext-folder ~/projects/OpenGrowTwin/exts \
  --enable opengrow.twin \
  --exec ~/projects/OpenGrowTwin/tools/kit_validate_rtx_sync.py
```

Success marker:

```text
[OpenGrowTwin] OGT-106 RTX/scientific emitter synchronization valid
```

Each verified session also reached `RTX ready` after its acceptance output.

## 6. Interactive application launch

Launch the app with the repository extension folder enabled:

```bash
cd ~/projects/kit-app-template

./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --ext-folder ~/projects/OpenGrowTwin/exts \
  --enable opengrow.twin
```

Open:

```text
~/projects/OpenGrowTwin/demo/grow_chamber.usda
```

The **OpenGrowTwin** panel provides:

- preview or final grid selection;
- **Simulate** and **Cancel**;
- baseline/current visibility switching;
- status and errors;
- PPFD, CV, uniformity, DLI, far-red, and blocked-ray metrics.

The intended interaction is:

1. run the clear baseline;
2. translate or rotate `Fixture_01`, or move `Occluder_01` into the beam;
3. wait for the debounced preview or press **Simulate**;
4. observe updated metrics and PPFD colors;
5. switch between baseline and current;
6. select the final grid before capturing evidence.

The headless acceptance suite verifies the underlying controller, stage
mutation, result contract, and synchronization. A polished interactive
screen/video capture remains a later submission task.

## 7. Troubleshooting record

### 7.1 Kit did not include Matplotlib

Initial OGT-101 validation failed while importing `opengrow.usd.stage_reader`
because `opengrow/usd/__init__.py` eagerly imported the Matplotlib heatmap
module.

Resolution:

- make the USD package initializer dependency-free;
- expose the old heatmap helper through a lazy import;
- add a regression test that blocks Matplotlib and imports the stage reader.

Do not install Matplotlib into Kit merely to read a stage. The scientific
virtual environment may contain it, but the Kit-side discovery path does not
require it.

### 7.2 Child prim definition failed under USD 25.11

Initial OGT-105 validation reported:

```text
Failed to define UsdPrim
</World/GrowInstallation/Results/BaselinePPFDHeatmap>
```

The parent and child `UsdStage.Define` calls were wrapped in one
`Sdf.ChangeBlock`. Parent composition was deferred, so USD 25.11 could not
resolve the parent when defining the child.

Resolution:

- do not batch stage-level parent/child `Define` calls in that change block;
- allow normal USD composition between definitions.

### 7.3 Result writes must not trigger simulation loops

Live-result and RTX-light changes generate USD notices. The extension filters
`/Results` and `/RTXLight` paths from its automatic simulation trigger so an
output update cannot recursively start another run.

### 7.4 Use the exact release paths

The tested paths are exactly:

```text
./_build/linux-x86_64/release/kit/kit
./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit
```

If Kit reports that the application file does not exist, inspect the typed
path before rebuilding or changing dependencies.

## 8. What the evidence proves

The OGT-101 through OGT-106 evidence proves that:

- Kit can discover the live horticultural scene through a versioned contract;
- fixture translation and rotation propagate into solver inputs;
- proxy geometry selectively blocks finite emitter-to-sensor rays;
- the solver preserves partial illumination from unblocked emitters;
- the Kit extension supports preview/final orchestration without importing
  Matplotlib;
- PPFD fields and metrics update in the same open stage;
- baseline/current heatmaps share a fixed comparison scale;
- one scientific emitter state drives both photon calculation and RTX light;
- every GPU acceptance run can coexist with RTX initialization on the L4.

It does **not** prove:

- measured agreement with a physical fixture or quantum sensor;
- accuracy for arbitrary triangle-mesh occluders;
- reflected-light, canopy-interception, or thermal accuracy;
- that RTX intensity is a calibrated radiometric quantity;
- biological optimality or plant-growth prediction;
- production-scale performance or multi-user collaboration;
- completion of the local open-model integration.

## 9. Competition-facing narrative

The product-critical interaction is now concrete:

> An engineer moves a spectral fixture or obstruction in an NVIDIA
> Omniverse/OpenUSD grow-space twin. OpenGrowTwin resolves the live geometry,
> recomputes auditable PPFD and far-red exposure, updates the spatial heatmap
> and metrics, and synchronizes RTX appearance from the same emitter state.

The result uses NVIDIA technology where it adds genuine value:

1. **OpenUSD** is the authoritative, editable installation state.
2. **Kit** orchestrates the interactive application and live result contract.
3. **RTX** communicates fixture state, obstruction, and spatial context.
4. **The deterministic photon solver** retains scientific auditability.

## 10. Recommended next milestone

The product-critical OpenUSD/Kit/RTX vertical slice is complete. The next
milestone is the guarded open-model path:

1. OGT-201 — freeze open-model tool schemas and safety rules;
2. OGT-202 — create curated evidence records;
3. OGT-203 — run the selected local open-model inference service;
4. OGT-204 — implement the validated tool-execution loop;
5. OGT-205 — add the Copilot panel;
6. OGT-206 — execute open-model regression scenarios.

The model should explain and operate the deterministic twin through narrow,
allowlisted tools. It must not replace the solver, invent biological claims,
or receive arbitrary code/file execution.

## 11. Cost-control reminder

Stop the G2 VM when Kit/RTX work is finished:

```bash
gcloud compute instances stop opengrow-gpu --zone=us-central1-b
```

Documentation, schemas, evidence records, tool validation, and most open-model
integration work can be developed without leaving the L4 VM running.
