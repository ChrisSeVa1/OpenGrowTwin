# OpenGrowTwin

**An evidence-driven spectral-lighting digital twin for controlled-environment horticulture, built with OpenUSD, NVIDIA Omniverse Kit/RTX, a deterministic photon-domain solver, manufacturer optical data, and a guarded local NVIDIA Nemotron copilot.**

OpenGrowTwin is designed around one rule:

> **Rendering is not the science.**

The OpenUSD scene defines the live engineering state. A deterministic solver computes horticultural photon quantities. NVIDIA Omniverse Kit makes the scene interactive, RTX provides synchronized real-time visualization, and the local open model can inspect and propose changes only through validated tools.

## 60-second mental model

```text
                    OpenUSD live scene
            geometry • transforms • emitters
                         │
                         ▼
              deterministic adapter
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
   photon-domain solver       RTX visualization
 PPFD • DLI • spectrum       visual light/shadows
 uniformity • occlusion      manufacturer IES shape
              │                     │
              └──────────┬──────────┘
                         ▼
                 Omniverse Kit UI
       heatmap • metrics • spectrum • sensor
                         │
                         ▼
            guarded local Nemotron copilot
             allowlisted tools + approval
```

**Scientific authority:** deterministic OpenGrowTwin result arrays and OpenUSD scientific metadata.

**Visual authority:** RTX viewport presentation.

**AI authority:** none by itself. Model proposals must pass deterministic tool validation; mutating actions require explicit confirmation.

## What the application can do

Inside the custom NVIDIA Kit application, a user can:

- move or rotate spectral LED emitters and recompute the photon field from live OpenUSD transforms;
- run debounced lower-resolution previews and a 41 × 25 final simulation;
- add an obstruction and observe geometry-aware direct-light shadows in PPFD;
- switch between a simplified generalized-Lambertian model and manufacturer IES + tabulated SPD;
- view scientific PPFD, RTX LED colors, or a combined presentation;
- inspect mean/min/max PPFD, DLI, far-red, coefficient of variation, min/mean uniformity, and blocked-ray statistics;
- view active 380–800 nm spectral curves and supplier part identifiers;
- place a virtual quantum sensor on the canopy and bilinearly sample local PPFD, DLI, far-red, blue, and red contributions;
- use a local NVIDIA Nemotron 3 Nano 4B copilot through a guarded tool interface;
- require explicit user confirmation before model-proposed scene mutation.

Omniverse is not used as a decorative viewer around an offline calculation: **the live OpenUSD stage drives the scientific calculation and receives the updated scientific results.**

## Why manufacturer photometry matters

A generic beam model can materially change the engineering conclusion.

In a controlled OpenGrowTwin comparison, fixture geometry, radiant power, manufacturer spectrum, receiver geometry, and visibility were held constant while only the angular model changed:

| Metric | Simplified Lambertian | Manufacturer IES |
| --- | ---: | ---: |
| Mean PPFD | 76.5617 | 55.8179 µmol m⁻² s⁻¹ |
| Minimum PPFD | 44.9827 | 39.9454 µmol m⁻² s⁻¹ |
| Maximum PPFD | 99.7022 | 66.7023 µmol m⁻² s⁻¹ |
| PPFD CV | 0.1751 | 0.1172 |
| Min/mean uniformity | 0.5875 | 0.7156 |

Mean canopy PPFD changed by approximately **-27.1%**, while predicted min/mean uniformity improved from about **0.588 to 0.716**.

That is why OpenGrowTwin keeps angular and spectral provenance explicit instead of treating an LED as only a colored point light.

# Reproduce OpenGrowTwin

There are three useful levels of reproduction. Run them in order.

## Path 1 — CPU scientific core

Use this first even if you ultimately want Omniverse. It requires Python 3.10+ and no NVIDIA GPU.

```bash
git clone https://github.com/ChrisSeVa1/OpenGrowTwin.git
cd OpenGrowTwin

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

python -m pytest -q

python -m opengrow simulate demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/results

python -m opengrow optimize demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/optimization

python -m opengrow scene demo/design.json \
  --out demo/grow_chamber.usda
```

A validated reference environment reported:

```text
134 passed in 3.42 s
```

The current pass count can change as tests are added. A failing test is a failure; a different total on a newer commit is not automatically one.

The CPU path writes deterministic NumPy/JSON/CSV/OpenUSD data and proves the scientific core independently of rendering.

## Path 2 — Google Cloud + NVIDIA L4 + Kit/RTX

The tested full-stack environment used:

```text
Google Cloud Compute Engine
→ g2-standard-8
→ 1 × NVIDIA L4
→ Ubuntu 22.04
→ NVIDIA driver
→ NVIDIA Kit App Template
→ custom opengrowtwin.my_editor
→ OpenGrowTwin extension
→ OpenUSD + RTX
```

The complete from-zero guide starts at the Google Cloud Console and covers project creation, Compute Engine API enablement, GPU quota, Console and CLI VM creation, driver installation, Kit bootstrap, application creation, direct Linux CLI launch, graphical access, manufacturer data, local AI, and validation:

**[`docs/reproduce-on-google-cloud.md`](docs/reproduce-on-google-cloud.md)**

For day-to-day Linux operation, including direct Kit commands, headless validators, Xorg/Openbox/x11vnc, SSH tunneling, shortcuts, and shutdown:

**[`docs/kit-linux-operations.md`](docs/kit-linux-operations.md)**

## Path 3 — Manufacturer optics + local AI + complete validation

To reproduce the full reference configuration:

1. obtain the exact ams OSRAM optical assets using [`docs/manufacturer-optical-data.md`](docs/manufacturer-optical-data.md);
2. start NVIDIA Nemotron 3 Nano 4B through the pinned CUDA-enabled `llama.cpp` runtime using [`docs/local-ai-copilot.md`](docs/local-ai-copilot.md);
3. run the layered scientific/Kit/RTX/manufacturer/model/safety checks in [`docs/validation-guide.md`](docs/validation-guide.md).

## Google Cloud reference environment

| Component | Value |
| --- | --- |
| Machine | `g2-standard-8` |
| GPU | 1 × NVIDIA L4 |
| CPU / RAM | 8 vCPU / 32 GB |
| OS | Ubuntu 22.04.5 LTS |
| Disk | 100 GB `pd-balanced` |
| Validated zone | `us-central1-b` |
| NVIDIA driver in reference environment | 610.57.04 |
| Kit SDK in later integration | 110.3.0 |

GPU quota and physical capacity are separate concerns. A correctly configured project can still receive `ZONE_RESOURCE_POOL_EXHAUSTED` if a zone has no available G2/L4 capacity.

## Launch OpenGrowTwin from Linux CLI

Once Kit and OpenGrowTwin are installed:

```bash
export OGT_ROOT="$HOME/projects/OpenGrowTwin"
export KIT_ROOT="$HOME/projects/kit-app-template"
export KIT_EXE="$KIT_ROOT/_build/linux-x86_64/release/kit/kit"
export OGT_APP="$KIT_ROOT/_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit"

"$KIT_EXE" "$OGT_APP" \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin
```

A valid startup should include:

```text
[ext: opengrow.twin-0.1.0] startup
[OpenGrowTwin] Interactive simulation extension ready
app ready
RTX ready
```

For a headless validator:

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/kit_validate_orchestration.py"
```

## Manufacturer optical data

The manufacturer-backed fixture uses the ams OSRAM OSCONIQ™ P 3737 (2W) Batwing family:

| Channel | Part | Manufacturer spectrum | Peak | Angular model |
| --- | --- | --- | ---: | --- |
| Blue | `GD PUBRA1.15` | 380–510 nm | 446 nm | Type-C IES |
| Red | `GH PUBRA1.25` | 580–780 nm | 680 nm | Type-C IES |
| Far-red | `GF PUBRA1.25` | 600–800 nm | 742 nm | Type-C IES |

OpenGrowTwin expects the local, gitignored six-file bundle under:

```text
sources/osram/extracted/
```

The repository deliberately does **not** redistribute supplier IES, EULUMDAT, rayfile, or spectrum archives.

See:

**[`docs/manufacturer-optical-data.md`](docs/manufacturer-optical-data.md)**

## Scientific model

The current model includes:

- inverse-square attenuation;
- receiver incidence;
- generalized-Lambertian or manufacturer Type-C angular distribution;
- monochromatic fallback or tabulated relative spectrum;
- OpenUSD-derived emitter position and orientation;
- finite-segment geometry-aware direct-light occlusion;
- PPFD over 400–700 nm;
- far-red 700–750 nm reported separately;
- DLI, mean/min/max PPFD, CV, and min/mean uniformity.

It deliberately does **not** claim:

- reflected or multi-bounce spectral radiometry;
- detailed canopy interception or leaf physiology;
- thermal simulation;
- LED junction-temperature effects;
- wall-plug electrical efficiency unless separately modeled;
- plant-growth, flowering, or yield prediction;
- measured agreement with a physical grow chamber;
- a universal optimal spectrum.

The bundled Phalaenopsis configuration is a published **reference treatment**, not a universal recipe.

## OpenUSD scene contract

The generated live stage uses metres, Z-up, and namespaced `opengrow:*` metadata.

```text
/World/GrowInstallation
├── Fixtures
│   └── Fixture_01
│       └── Emitters
├── SensorPlane
├── Occluders
└── Results
```

Roles and scientific attributes are discovered from the stage. Fixture edits therefore change solver input without editing `design.json`.

Exact PPFD values are written into OpenUSD primvars such as:

```text
primvars:opengrow:ppfd
```

Display colors are visualization; the scalar field remains available separately.

## RTX boundary

Each scientific emitter has synchronized presentation state for RTX. The same authoritative emitter power/transform can therefore change both the photon-domain result and the RTX viewport appearance.

RTX intensity is explicitly treated as visual-only and is never presented as PPFD.

In manufacturer mode, local IES data can drive USD/RTX light shaping while the deterministic solver independently uses the normalized manufacturer angular distribution.

## Local NVIDIA Nemotron copilot

The validated local AI runtime uses:

| Field | Value |
| --- | --- |
| Model | NVIDIA Nemotron 3 Nano 4B |
| Quantization | Q4_K_M |
| Runtime | CUDA-enabled `llama.cpp` |
| llama.cpp commit | `7798007a29a90e3053e799394da48cf53a2f8e0f` |
| Context | 8,192 |
| Endpoint | `127.0.0.1:8080` |
| Observed model VRAM | ~3 GB |

The tool boundary rejects arbitrary function names, arbitrary paths, and out-of-range mutations. Confirmation tokens are bound to exact arguments, one-use, and expiring.

A validated live-model regression reported:

```text
routing: 8/8 passed
grounding: 2/2 passed
deterministic adversarial safety: 7/7 passed
```

See:

**[`docs/local-ai-copilot.md`](docs/local-ai-copilot.md)**

## Reproducibility

A useful reproduction report should record:

```text
OpenGrowTwin commit/tag
OS + kernel
GPU
NVIDIA driver
Kit SDK/template revision
Python version
pytest pass count
manufacturer asset revision(s), if used
llama.cpp commit, if used
model name/quantization/SHA-256, if used
which acceptance layers were run
known deviations from the reference environment
```

Do not publish cloud project IDs, credentials, tokens, API keys, personal usernames, or private infrastructure addresses.

## Project layout

```text
OpenGrowTwin/
├── src/opengrow/
│   ├── physics/          photon conversion, direct solver, visibility, photometry, spectra
│   ├── usd/              scene contract, stage adapter, live results, RTX synchronization
│   └── copilot/          evidence, tool contracts, model/tool execution boundary
├── exts/opengrow.twin/   NVIDIA Kit extension and UI
├── data/                 project-owned LED/evidence/target metadata
├── demo/                 deterministic demonstration configuration / OpenUSD scene
├── tests/                analytical and regression tests
├── tools/                CPU/Kit/model/manufacturer validators and launch helpers
└── docs/                 maintained public documentation
```

## Documentation

Start with [`docs/README.md`](docs/README.md).

- [`docs/architecture.md`](docs/architecture.md) — architecture and scientific/RTX/AI authority boundaries
- [`docs/reproduce-on-google-cloud.md`](docs/reproduce-on-google-cloud.md) — from Google Cloud Console to L4, driver, Kit, RTX, and OpenGrowTwin
- [`docs/kit-linux-operations.md`](docs/kit-linux-operations.md) — Linux CLI launch, graphical cloud access, shortcuts, and troubleshooting
- [`docs/manufacturer-optical-data.md`](docs/manufacturer-optical-data.md) — supplier pages, optical downloads, local asset layout, and validation
- [`docs/local-ai-copilot.md`](docs/local-ai-copilot.md) — pinned `llama.cpp` + Nemotron runtime, security boundary, and live validators
- [`docs/validation-guide.md`](docs/validation-guide.md) — layered CPU/Kit/RTX/manufacturer/model/safety acceptance suite

## License and external data

OpenGrowTwin code is licensed under Apache-2.0.

NVIDIA software/model artifacts, ams OSRAM manufacturer data, research literature, and other dependencies retain their respective terms. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Raw manufacturer optical assets and model weights are intentionally not committed.
