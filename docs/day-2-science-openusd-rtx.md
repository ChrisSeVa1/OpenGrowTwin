# OpenGrowTwin — Day 2 Science, OpenUSD, and Headless RTX Guide

**Session date:** 2026-09-01  
**Project:** OpenGrowTwin  
**Repository:** <https://github.com/ChrisSeVa1/OpenGrowTwin>  
**Purpose:** Engineering record, reproduction guide, and competition evidence

## 1. Relationship to the Day 1 log

This document continues the Day 1 GCP and NVIDIA Omniverse setup log. Day 1
proved the infrastructure path: a Google Cloud G2 VM with an NVIDIA L4 could
start the custom `opengrowtwin.my_editor` Kit application and reach both
`app ready` and `RTX ready`.

Day 2 moved beyond infrastructure and completed the first end-to-end vertical
slice:

```text
design.json + reference treatment
              ↓
deterministic photon solver and optimizer
              ↓
numeric arrays + metrics + comparison plots
              ↓
self-contained OpenUSD PPFD mesh
              ↓
headless NVIDIA RTX render product
              ↓
PNG and EXR evidence images
```

The scientific calculation remains independent of RTX. NumPy/CSV values are
authoritative; the RTX image is the visualization and integration proof.

## 2. What was accomplished

### 2.1 Repository and reproducible Python package

- Established the public `OpenGrowTwin` repository.
- Added an installable Python package with a `src/` layout and CLI.
- Added Apache-2.0 licensing and third-party notices.
- Added deterministic demo inputs for a horticultural lighting installation.
- Added 17 passing automated tests covering photon conversion, the direct
  solver, basis maps, optimization, heatmaps, CLI outputs, and OpenUSD export.

### 2.2 Photon-domain simulation

The CPU-side solver now supports:

- monochromatic radiant-energy to photon-flux conversion;
- 450 nm blue, 660 nm red, and 730 nm far-red channels;
- multiple point emitters;
- cosine beam falloff and inverse-square attenuation;
- PPFD over 400–700 nm;
- far-red photon flux reported separately;
- DLI, minimum, maximum, mean, coefficient of variation, and
  minimum-to-mean uniformity;
- cached per-channel basis maps and exact linear reconstruction.

The current direct-light model does **not** yet include reflections, canopy
interception, thermal effects, LED wall-plug efficiency, or plant-growth
prediction.

### 2.3 Multi-emitter reference fixture

The demo design contains:

- a 1.0 m × 0.6 m receiver plane;
- a 41 × 25 measurement grid (1,025 samples);
- eight blue emitters at 450 nm;
- eight red emitters at 660 nm;
- four supplemental far-red emitters at 730 nm;
- candidate fixture heights from 0.4 m through 0.8 m.

The target is the bundled `phalaenopsis_ouzounis_2015_reference` treatment:

- mean PPFD: approximately 200 µmol/m²/s;
- photoperiod: 14 hours;
- photon fraction: 40% blue and 60% red.

This is treated as a published reference environment, not as a universal
optimal orchid spectrum.

### 2.4 Installation optimization

The optimizer evaluates fixture height and bounded channel radiant powers.
Its objective balances:

1. mean-PPFD target error;
2. spatial PPFD coefficient of variation;
3. a documented radiant-power penalty.

The verified optimized result was:

| Metric | Baseline | Optimized |
|---|---:|---:|
| Mean PPFD | 76.505 µmol/m²/s | 200.000 µmol/m²/s |
| Minimum PPFD | 44.967 µmol/m²/s | 117.504 µmol/m²/s |
| Maximum PPFD | 99.631 µmol/m²/s | 260.454 µmol/m²/s |
| PPFD CV | 0.17508 | 0.17508 |
| Minimum/mean uniformity | 0.58777 | 0.58752 |
| DLI at 14 h | 3.856 mol/m²/day | 10.080 mol/m²/day |
| Mean far-red | 8.664 µmol/m²/s | 8.664 µmol/m²/s |

Selected installation parameters:

- fixture height: 0.6 m;
- blue radiant power: 46.428 W;
- red radiant power: 47.483 W;
- far-red radiant power: 3.000 W.

These are modeled optical radiant powers, not electrical input powers.

### 2.5 OpenUSD result contract

Optimization creates `build/optimization/ppfd_heatmap.usda`, containing:

- one OpenUSD mesh with 1,025 vertices and 960 quad faces;
- exact scalar PPFD values in `primvars:opengrow:ppfd`;
- visualization colors in `primvars:displayColor`;
- topology and grid metadata;
- namespaced summary metrics.

Kit validated the loaded stage with:

```text
[OpenGrowTwin] Stage valid; PPFD=1025, colors=1025,
range=(117.504, 260.454)
```

### 2.6 Headless RTX proof

The capture tool opens the generated USDA stage, validates its scientific
primvars, authors a top-down camera, dome light, render settings, raster render
product, and `LdrColor` render variable, then captures through RTX without an
X11/GLFW window.

The GCP L4 session reached:

```text
app ready
[OpenGrowTwin] Stage valid; PPFD=1025, colors=1025,
range=(117.504, 260.454)
[OpenGrowTwin] Render product authored:
/Render/OpenGrowTwinProduct; camera=/OpenGrowTwinResults/CaptureCamera,
vars=1, resolution=1280x720
RTX ready
[OpenGrowTwin] Starting headless RTX render product
```

The renderer produced two non-empty images:

```text
build/captures/ppfd_heatmap_rtx1_LdrColor.png  822748 bytes
build/captures/ppfd_heatmap_rtx1_LdrColor.exr  748816 bytes
```

This proves that Kit loaded the generated OpenUSD result and NVIDIA RTX
rendered its spatial display colors on the L4 in a headless session.

## 3. CPU reproduction guide

### 3.1 Clone and install

```bash
git clone https://github.com/ChrisSeVa1/OpenGrowTwin.git
cd OpenGrowTwin

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

### 3.2 Run validation

```bash
python -m pytest -q
```

Expected result for this session:

```text
17 passed
```

### 3.3 Run the baseline simulation

```bash
python -m opengrow simulate demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/results
```

Expected outputs:

```text
build/results/
├── band_ppfd.npy
├── metrics.json
├── ppfd.npy
├── result.json
└── spectral_irradiance.npy
```

### 3.4 Run optimization and OpenUSD export

```bash
python -m opengrow optimize demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/optimization
```

Expected outputs include:

```text
build/optimization/
├── band_ppfd_optimized.npy
├── comparison.json
├── optimized_design.json
├── ppfd_baseline.csv
├── ppfd_baseline.png
├── ppfd_comparison.png
├── ppfd_heatmap.usda
├── ppfd_optimized.csv
├── ppfd_optimized.npy
└── ppfd_optimized.png
```

The command must appear only once at the shell prompt. Accidentally pasting a
second `python -m opengrow optimize ...` after the first command causes
`unrecognized arguments` because the shell passes the duplicate text to the
same process.

## 4. GPU/Kit reproduction guide

### 4.1 Preconditions

- Google Cloud G2 VM with one NVIDIA L4;
- Ubuntu 22.04;
- NVIDIA driver verified using `nvidia-smi`;
- NVIDIA Kit App Template built under `~/projects/kit-app-template`;
- application `opengrowtwin.my_editor` available in the release build;
- OpenGrowTwin cloned under `~/projects/OpenGrowTwin`;
- CPU optimization completed so `ppfd_heatmap.usda` exists.

The tested VM was:

- instance: `opengrow-gpu`;
- zone: `us-central1-b`;
- machine class: `g2-standard-8`;
- GPU: one NVIDIA L4;
- RAM: 32 GB.

### 4.2 Synchronize and generate results

```bash
cd ~/projects/OpenGrowTwin
git pull
source .venv/bin/activate

python -m pytest -q
python -m opengrow optimize demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/optimization
```

### 4.3 Launch headless RTX capture

```bash
cd ~/projects/kit-app-template

./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --no-window \
  --enable omni.kit.capture.viewport \
  --enable omni.graph \
  --enable omni.graph.nodes \
  --enable omni.graph.examples.cpp \
  --exec ~/projects/OpenGrowTwin/tools/kit_capture_heatmap.py
```

### 4.4 Verify capture files

Do not rely only on `Capture outputs`. Kit 110 can write the image correctly
while returning an empty output manifest.

```bash
find ~/projects/OpenGrowTwin/build/captures \
  -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %s bytes %p\n'
```

Success requires a non-empty PNG or EXR file. The EXR is the archival linear
render; the PNG is the convenient human-readable preview.

## 5. Copy evidence from the VM

Run these commands on the local workstation, not inside `opengrow-gpu`.

```bash
sudo snap install google-cloud-cli --classic
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
mkdir -p ~/Downloads/OpenGrowTwin
```

Copy the PNG:

```bash
gcloud compute scp \
  --zone=us-central1-b \
  chris_sevilla_v_de@opengrow-gpu:/home/chris_sevilla_v_de/projects/OpenGrowTwin/build/captures/ppfd_heatmap_rtx1_LdrColor.png \
  ~/Downloads/OpenGrowTwin/
```

Copy the EXR:

```bash
gcloud compute scp \
  --zone=us-central1-b \
  chris_sevilla_v_de@opengrow-gpu:/home/chris_sevilla_v_de/projects/OpenGrowTwin/build/captures/ppfd_heatmap_rtx1_LdrColor.exr \
  ~/Downloads/OpenGrowTwin/
```

Add `--tunnel-through-iap` if the VM has no external IP. If the copy command is
run inside the VM, it merely copies the remote file back onto that VM.

Open the PNG locally:

```bash
xdg-open ~/Downloads/OpenGrowTwin/ppfd_heatmap_rtx1_LdrColor.png
```

## 6. Inspect the EXR on Ubuntu

Blender can open EXR directly in its Image Editor. For command-line inspection
and conversion, install OpenImageIO:

```bash
sudo apt update
sudo apt install openimageio-tools
```

Inspect metadata:

```bash
oiiotool --info -v \
  ~/Downloads/OpenGrowTwin/ppfd_heatmap_rtx1_LdrColor.exr
```

Create an sRGB PNG preview:

```bash
oiiotool \
  ~/Downloads/OpenGrowTwin/ppfd_heatmap_rtx1_LdrColor.exr \
  --colorconvert linear sRGB \
  -o ~/Downloads/OpenGrowTwin/ppfd_heatmap_rtx_from_exr.png
```

## 7. Troubleshooting record

### 7.1 `usdchecker` was not present

`./repo.sh usd --help` exposes schema/plugin tooling, not a USD validation
command, and no `usdchecker` executable was found in `_build`. The practical
validation path became: open the stage in Kit, inspect the required prim and
attributes, then render it.

### 7.2 GLFW and `IWindowing` failures

Creating a viewport window on a VM without an X display produced GLFW errors,
`IWindowing` failures, and a `NoneType.get_event_key()` exception. The correct
headless architecture is a USD render product, not `create_viewport_window()`.

### 7.3 Incomplete render product

An initial product containing only a camera and resolution was not accepted by
Hydra. The fix added:

- `productType = "raster"`;
- a product name;
- an ordered `LdrColor` render variable;
- active render settings metadata;
- a synchronization delay before capture.

### 7.4 Kit metadata type mismatch

Kit 110 expects `renderSettingsPrimPath` as a string. Passing an `Sdf.Path`
raised:

```text
Expected type 'string'
```

### 7.5 Empty capture output manifest

Kit wrote valid PNG and EXR files but `CaptureExtension.get_outputs()` returned
`[]`. The capture script now waits for asynchronous writes and scans the output
directory. File existence and non-zero size are the reliable success check for
this Kit build.

### 7.6 `gcloud compute scp` authentication scopes

Running `gcloud compute scp` inside the VM used the VM service account and
failed with insufficient authentication scopes. Running the command from an
authenticated local workstation succeeded.

## 8. What the evidence proves

The Day 2 result supports these claims:

- the deterministic solver produces auditable photon-domain results;
- the optimizer can reproduce the selected reference mean PPFD within floating
  point precision while reporting spatial uniformity and radiant-power tradeoffs;
- exact PPFD samples and visualization colors are exported into OpenUSD;
- Kit successfully reads all 1,025 PPFD and color samples;
- NVIDIA RTX on an L4 renders the generated OpenUSD heatmap headlessly;
- the same repository connects local/CPU development with GPU/Kit validation.

It does **not** yet prove:

- that the modeled treatment is biologically optimal;
- measured agreement with a physical grow chamber;
- reflected-light or canopy accuracy;
- electrical energy consumption;
- a complete interactive Kit user interface;
- arbitrary luminaire photometry or a full TracePro replacement.

## 9. Competition-facing narrative

OpenGrowTwin demonstrates a credible separation of concerns:

1. **Science layer:** deterministic, tested, inspectable Python/NumPy models.
2. **Exchange layer:** self-contained OpenUSD containing both geometry and
   domain-specific PPFD attributes.
3. **NVIDIA layer:** Kit and RTX consume and visualize known-good scientific
   results on an NVIDIA L4.

This separation makes the project reproducible without a GPU while reserving
scarce GPU time for the work that genuinely requires NVIDIA rendering.

## 10. Recommended next milestone

The next vertical slice should turn the verified heatmap into a competition
demo:

- add a chamber and orchid/canopy context around the receiver plane;
- add a legend with units and the 117.504–260.454 µmol/m²/s range;
- show baseline and optimized metrics in the Kit extension;
- add controls for height and channel power;
- rerun the solver/optimizer and reload results from the extension;
- capture a polished screenshot and short demonstration video;
- preserve numeric result files alongside all visual evidence.

## 11. Cost-control reminder

Stop the G2 VM when RTX work is finished:

```bash
gcloud compute instances stop opengrow-gpu --zone=us-central1-b
```

The CPU solver, tests, optimization logic, documentation, and most OpenUSD
authoring can continue locally while the GPU VM is stopped.
