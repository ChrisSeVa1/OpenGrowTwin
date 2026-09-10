# Third-party notices

OpenGrowTwin depends on or interoperates with third-party software, models, research, and manufacturer data that are **not** relicensed under this repository's Apache-2.0 license.

- **NVIDIA Omniverse, Kit, RTX, and Kit App Template** — subject to NVIDIA's applicable software/license terms. The OpenGrowTwin Apache-2.0 license applies to project-owned source code, not to NVIDIA Kit/Omniverse components downloaded or installed separately.
- **NVIDIA Nemotron 3 Nano 4B model weights** — subject to the upstream NVIDIA Nemotron Open Model License and the terms published with the selected model artifact. OpenGrowTwin does not redistribute the GGUF model weights. Reproducers must obtain the model through an authorized upstream distribution channel and review the then-current model terms.
- **llama.cpp** — used as the local model runtime and subject to its upstream open-source license. OpenGrowTwin records the validated llama.cpp revision but does not relicense that project.
- **Python dependencies** including NumPy, PyYAML, Matplotlib, Hatchling, and pytest — subject to their respective open-source licenses.
- **ams OSRAM manufacturer optical assets** used during development/validation—including IES, EULUMDAT, tabulated spectrum, rayfile, CAD, datasheet, and archive data—remain subject to the manufacturer's terms and are **not** redistributed or sublicensed by OpenGrowTwin. The public repository stores only integration code, product/file identifiers, provenance metadata, retrieval guidance, and validation results. Users who wish to reproduce manufacturer-backed simulations must obtain the corresponding source assets separately under the manufacturer's terms.
- **Other LED manufacturer specifications and spectral data** remain owned by their respective manufacturers and are not automatically covered by the OpenGrowTwin Apache-2.0 license.
- **Research publications and extracted evidence** remain subject to publisher and author rights. OpenGrowTwin stores structured evidence/target records and citations rather than redistributing full copyrighted publications.

## Repository hygiene

The repository intentionally gitignores `sources/osram/` so local manufacturer optical assets cannot be accidentally included in normal commits. Model weights, local credentials, VNC password files, cloud configuration, and other machine-specific secrets must also remain outside Git.

See the reproduction guides under `docs/` for the supported process for obtaining external dependencies without treating them as project-owned assets.
