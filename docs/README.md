# OpenGrowTwin documentation

This directory contains the maintained documentation for reproducing, operating, understanding, and validating OpenGrowTwin.

## Start here

| Goal | Guide |
| --- | --- |
| Understand the project and run the CPU scientific core | [`../README.md`](../README.md) |
| Understand the architecture and authority boundaries | [`architecture.md`](architecture.md) |
| Rebuild the complete Google Cloud + NVIDIA L4 + Kit + RTX stack | [`reproduce-on-google-cloud.md`](reproduce-on-google-cloud.md) |
| Launch and operate Kit from Linux, including graphical cloud access | [`kit-linux-operations.md`](kit-linux-operations.md) |
| Obtain and validate the ams OSRAM manufacturer optical data | [`manufacturer-optical-data.md`](manufacturer-optical-data.md) |
| Reproduce the local NVIDIA Nemotron copilot and guarded tool loop | [`local-ai-copilot.md`](local-ai-copilot.md) |
| Run the validation suite and understand what each check proves | [`validation-guide.md`](validation-guide.md) |

## Recommended order for a new developer

```text
README
  ↓
CPU scientific core
  ↓
architecture
  ↓
Google Cloud + NVIDIA L4
  ↓
Kit build and Linux launch
  ↓
OpenGrowTwin live OpenUSD scene
  ↓
manufacturer IES/SPD assets (optional)
  ↓
local Nemotron service (optional)
  ↓
full validation
```

Run the CPU path first even if your final goal is Omniverse. That separates project-level problems from GPU, cloud, driver, and Kit problems and proves the deterministic scientific core independently of rendering.

## Reproducibility boundary

The repository redistributes OpenGrowTwin source code, public metadata, examples, and test fixtures. It intentionally does **not** redistribute:

- NVIDIA Kit/Omniverse SDK components;
- NVIDIA Nemotron model weights;
- ams OSRAM IES/EULUMDAT/rayfile/spectrum archives;
- copyrighted research papers or supplier datasheets.

The guides explain where external dependencies come from, how they are used, and how to verify that the expected assets are present. Always follow upstream license and download terms.

## Documentation policy

Public documentation is organized by **task and subsystem**, not by development chronology. Internal sprint notes, submission material, milestone task queues, and one-off acceptance logs are intentionally not part of the maintained documentation set.

Validation details that remain useful to users are consolidated into [`validation-guide.md`](validation-guide.md), while supplier-specific retrieval and provenance rules live in [`manufacturer-optical-data.md`](manufacturer-optical-data.md).
