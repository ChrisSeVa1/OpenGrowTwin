# OpenGrowTwin architecture

OpenGrowTwin separates scientific computation, scene state, visualization, and AI assistance so that each layer can be tested independently.

## Authority model

```text
OpenUSD live scene
  geometry • transforms • emitter state • occluders
        │
        ▼
USD → solver adapter
        │
        ▼
deterministic photon-domain solver
  PPFD • DLI • spectrum • uniformity • occlusion
        │
        ├──────────────► OpenUSD result prims + heatmap
        │
        └──────────────► metrics / arrays / validation artifacts

same authoritative emitter state
        │
        └──────────────► RTX visualization

validated scene + result tools
        │
        └──────────────► local Nemotron copilot
                         proposals only; guarded mutations
```

The responsibilities are deliberately different:

1. **OpenUSD** is the authoritative live scene and engineering-state layer.
2. **The deterministic Python/NumPy solver** is authoritative for horticultural photon quantities.
3. **NVIDIA RTX** is authoritative only for visual presentation.
4. **The local language model** has no scientific authority by itself; it can only inspect or propose actions through validated tools.

## Repository boundaries

| Path | Responsibility |
| --- | --- |
| `src/opengrow/physics/` | photon conversion, direct transport, photometry, spectra, metrics, visibility |
| `src/opengrow/usd/` | scene contract, stage reading, live results, RTX synchronization |
| `src/opengrow/optimize/` | bounded lighting optimization |
| `src/opengrow/copilot/` | evidence store, tool schemas, model-service client, guarded execution |
| `src/opengrow/manufacturer_profiles.py` | local supplier-profile resolution without redistributing vendor files |
| `exts/opengrow.twin/` | NVIDIA Kit extension and UI |
| `data/` | project-owned targets, evidence metadata, and generic LED metadata |
| `demo/` | deterministic example design and OpenUSD scene |
| `tools/` | validation and runtime helper scripts |
| `tests/` | deterministic unit/regression tests |

## Live OpenUSD scene contract

The live stage is the authoritative source for installation geometry and emitter state. `design.json` is a deterministic bootstrap input; `opengrow scene` converts it into `demo/grow_chamber.usda`, after which interactive simulation reads the open stage.

The scene uses metres, Z-up, a right-handed coordinate system, and local `-Z` as the emitter-forward direction.

Entities are discovered through `opengrow:role` metadata instead of fixed world coordinates.

| Role | Required state |
| --- | --- |
| `fixture` | ID and transform |
| `emitter` | channel, spectral/radiant state, enabled state, transform/orientation |
| `sensorPlane` | ID, dimensions, grid resolution, transform |
| `occluder` | ID, enabled state, transform, proxy geometry |
| `results` | result meshes and metric metadata |

## OpenUSD → scientific solver adapter

`opengrow.usd.stage_reader` resolves live emitter positions and directions in world space and translates stage state into the solver input model.

The adapter transfers:

- emitter world position and orientation;
- channel identity;
- radiant power;
- wavelength/spectrum state;
- optical angular model;
- enabled state;
- sensor-plane geometry and sampling grid;
- enabled occluders.

A fixture translation or rotation therefore changes the scientific calculation without editing `design.json`.

## Photon-domain solver

The solver models direct light from each emitter to each sensor sample.

The current transport includes:

- inverse-square attenuation;
- emission-angle distribution;
- receiver-incidence cosine;
- generalized-Lambertian angular models;
- manufacturer Type-C IES angular distributions when local supplier assets are available;
- monochromatic fallback spectra;
- tabulated relative manufacturer spectra;
- geometry-aware direct-light visibility against transformed proxy-box occluders.

The scientific path computes:

- PPFD over 400–700 nm;
- far-red photon flux over 700–750 nm;
- DLI from PPFD and photoperiod;
- mean/min/max PPFD;
- coefficient of variation;
- minimum/mean uniformity;
- blocked-ray diagnostics;
- channel/spectral contributions used by the virtual sensor and UI.

## Geometry-aware occlusion

For every emitter-to-sensor sample, OpenGrowTwin can perform a finite segment-versus-oriented-box intersection test against enabled OpenUSD occluder proxies.

Only the blocked emitter contribution is removed. Other emitters can continue illuminating the same sensor sample, producing spatially selective partial shadows rather than a global power reduction.

General triangle-mesh ray intersection, diffuse reflection, and multi-bounce transport remain outside the current direct-light model.

## Manufacturer optics

OpenGrowTwin supports a public fallback model with no proprietary data and an optional local manufacturer mode.

For the current ams OSRAM reference set, the project uses:

- Type-C IES for angular redistribution;
- tabulated relative spectra for wavelength-resolved photon conversion;
- supplier part/revision metadata for provenance.

Raw manufacturer assets remain outside Git under `sources/osram/`, which is ignored by the repository.

Angular and spectral provenance are intentionally separate. An IES profile does not by itself define the spectrum, and a spectrum does not define the angular distribution.

## Live result state

Completed simulations update OpenUSD result meshes under the scene's `Results` hierarchy.

Exact PPFD values are retained in scientific primvars such as:

```text
primvars:opengrow:ppfd
```

Display colors are derived visualization. The numeric scalar field remains separate and is used by metrics, baseline/current switching, and virtual-sensor sampling.

The live application supports lower-resolution preview runs and explicit 41 × 25 final runs.

## RTX synchronization

Each scientific emitter has synchronized presentation state for RTX.

The same authoritative emitter transform and power state can therefore change:

- the deterministic photon-domain result; and
- the RTX viewport appearance.

RTX intensity uses a presentation scale for a legible viewport and is explicitly treated as visual-only. It is never converted into or labeled as PPFD.

When local manufacturer IES files are available, the same supplier angular profile can also shape the corresponding USD/RTX light while the deterministic solver independently evaluates the scientific angular distribution.

## Virtual quantum sensor

The UI can sample a point on the canopy/sensor plane from an already-computed scientific result.

The virtual sensor:

- stores a world-space point;
- bilinearly interpolates the current scientific field;
- reports local PPFD;
- reports DLI using the active photoperiod;
- reports far-red and channel contributions when available;
- updates when the displayed result changes or the scene is recomputed.

It does not launch a separate ray trace for each click.

## Local AI copilot

The local NVIDIA Nemotron model is served through CUDA-enabled `llama.cpp` on a loopback endpoint.

The model sees compact structured context and declared tool schemas rather than unrestricted Python, shell, filesystem, or USD access.

The guarded execution path is:

```text
model proposal
  ↓
schema + identifier + bounds validation
  ↓
read-only execution
      OR
exact mutation proposal
  ↓
explicit user confirmation
  ↓
scene mutation + deterministic recomputation
```

The model does not calculate PPFD, DLI, occlusion, or optimization results itself.

## Scientific limitations

The current model deliberately does **not** claim:

- diffuse or multi-bounce spectral radiometry;
- detailed arbitrary-mesh optical transport;
- detailed canopy interception or leaf scattering;
- fluorescence;
- thermal or CFD simulation;
- LED junction-temperature behavior;
- wall-plug electrical efficiency unless separately supplied;
- biological growth, flowering, or yield prediction;
- measured calibration against a physical chamber;
- a universal optimal plant spectrum.

The bundled Phalaenopsis configuration is a published reference treatment, not a universal growth recipe.

## Design principle

OpenGrowTwin is structured so that future improvements—measured spectra, additional luminaire formats, mesh-level optical transport, reflections, thermal models, new crop targets, or different open models—can be added without changing the core authority boundary:

> **OpenUSD defines the live engineering state; the deterministic solver defines the scientific result; RTX visualizes it; AI operates only through guarded tools.**
