# OpenGrowTwin validation guide

OpenGrowTwin should be validated in layers. A screenshot is useful presentation evidence, but it is not a substitute for independent scientific, OpenUSD, RTX, manufacturer-data, AI-routing, and mutation-safety checks.

Recommended order:

```text
Python/unit tests
  ↓
CPU scientific CLI
  ↓
OpenUSD scene contract
  ↓
Kit live-scene / occlusion / orchestration
  ↓
RTX synchronization
  ↓
manufacturer optics (when local assets exist)
  ↓
local model service
  ↓
model routing + grounded tool loop
  ↓
deterministic safety regressions
  ↓
graphical confirm/reject acceptance
```

## 1. Environment preparation

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate
```

If you are not on the GPU VM, the CPU sections still apply.

## 2. Full Python regression suite

```bash
python -m pytest -q
```

A recorded reference environment reported:

```text
134 passed
```

The current count can change as tests are added. A failing test matters; matching an old total exactly is not required on a newer commit.

### What this proves

- photon-conversion/math tests execute;
- deterministic solver regressions pass;
- spectrum/photometry parsing tests pass;
- Python-side OpenUSD contracts pass;
- copilot contract/safety unit tests pass;
- public manufacturer-photometry fixtures behave as expected.

### What it does not prove

- a real L4 is present;
- Kit starts;
- RTX starts;
- proprietary supplier files are present;
- the real local Nemotron model routes correctly;
- the graphical UI behaves correctly.

## 3. CPU scientific smoke test

Simulation:

```bash
python -m opengrow simulate demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/results
```

Optimization:

```bash
python -m opengrow optimize demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/optimization
```

Scene generation:

```bash
python -m opengrow scene demo/design.json \
  --out demo/grow_chamber.usda
```

Inspect outputs rather than checking only the exit code:

```bash
find build/results build/optimization -maxdepth 2 -type f -print 2>/dev/null | sort
ls -lh demo/grow_chamber.usda
```

## 4. Google Cloud/NVIDIA infrastructure gates

On the GPU VM:

```bash
hostnamectl
lspci | grep -i nvidia
nvidia-smi
```

The reference architecture used one NVIDIA L4. `lspci` alone is insufficient; `nvidia-smi` must work.

Build/launch Kit as documented in [`kit-linux-operations.md`](kit-linux-operations.md). A successful NVIDIA application gate requires both:

```text
app ready
RTX ready
```

## 5. Common headless Kit invocation

```bash
export OGT_ROOT="$HOME/projects/OpenGrowTwin"
export KIT_ROOT="$HOME/projects/kit-app-template"
export KIT_EXE="$KIT_ROOT/_build/linux-x86_64/release/kit/kit"
export OGT_APP="$KIT_ROOT/_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit"
```

Pattern:

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/<validator>.py"
```

## 6. OpenUSD live-scene contract

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --exec "$OGT_ROOT/tools/kit_validate_live_scene.py"
```

Current validator success marker:

```text
[OpenGrowTwin] OGT-101 live scene contract valid
```

The identifier is retained in the validator output for traceability. The check proves that the application can discover the installation, fixture, emitter, sensor, occluder, and result roles rather than relying on hard-coded world coordinates.

## 7. OpenUSD → solver adapter

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --exec "$OGT_ROOT/tools/kit_validate_usd_solver_input.py"
```

Current success marker:

```text
[OpenGrowTwin] OGT-102 USD-to-solver adapter valid
```

The check translates and rotates the fixture and verifies that the generated scientific emitter state changes without editing `design.json`.

## 8. Geometry-aware occlusion

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --exec "$OGT_ROOT/tools/kit_validate_occlusion.py"
```

Current success marker:

```text
[OpenGrowTwin] OGT-103 geometry-aware visibility valid
```

A reference case produced 1,432 blocked emitter→sensor rays out of 20,500 and affected 840 of 1,025 sensor cells. The purpose is to prove a spatially selective photon shadow rather than a global power reduction.

## 9. Kit simulation orchestration

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/kit_validate_orchestration.py"
```

Current success marker:

```text
[OpenGrowTwin] OGT-104 Kit orchestration valid
```

This validates preview/final preparation and the live simulation path inside Kit.

## 10. Live in-stage result update

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/kit_validate_live_results.py"
```

Current success marker:

```text
[OpenGrowTwin] OGT-105 live heatmap update valid
```

This proves that the application writes exact PPFD values and display colors into the open stage instead of requiring a stage reload.

## 11. Scientific emitter ↔ RTX synchronization

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/kit_validate_rtx_sync.py"
```

Current success marker:

```text
[OpenGrowTwin] OGT-106 RTX/scientific emitter synchronization valid
```

The principle is: one authoritative channel/transform state changes both the deterministic scientific result and the presentation-only RTX light. RTX intensity is not relabeled as PPFD.

## 12. Headless RTX heatmap capture

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --enable omni.kit.capture.viewport \
  --enable omni.graph \
  --enable omni.graph.nodes \
  --enable omni.graph.examples.cpp \
  --exec "$OGT_ROOT/tools/kit_capture_heatmap.py"
```

Then verify actual files:

```bash
find "$OGT_ROOT/build/captures" \
  -type f \
  -printf '%TY-%Tm-%Td %TH:%TM:%TS %s bytes %p\n'
```

A valid integration run should produce a non-empty PNG and/or EXR artifact.

## 13. Manufacturer optical bundle availability

Follow [`manufacturer-optical-data.md`](manufacturer-optical-data.md) first.

Quick check:

```bash
python - <<'PY'
from opengrow.manufacturer_profiles import manufacturer_bundle_available, default_asset_root
print(default_asset_root())
print(manufacturer_bundle_available())
PY
```

Expected when manufacturer mode is configured:

```text
True
```

## 14. Manufacturer optical-data validation

```bash
python tools/validate_manufacturer_optics.py
python tools/validate_manufacturer_ies_ab.py
```

A controlled reference comparison held geometry, radiant power, manufacturer SPD, receiver geometry, and visibility constant while changing only the angular model:

| Metric | Simplified Lambertian | Manufacturer IES |
| --- | ---: | ---: |
| Mean PPFD | 76.5617 | 55.8179 µmol m⁻² s⁻¹ |
| Minimum PPFD | 44.9827 | 39.9454 µmol m⁻² s⁻¹ |
| Maximum PPFD | 99.7022 | 66.7023 µmol m⁻² s⁻¹ |
| PPFD CV | 0.1751 | 0.1172 |
| Min/mean uniformity | 0.5875 | 0.7156 |

The point of the A/B test is to prove that the supplier angular distribution materially changes the engineering prediction.

## 15. Manufacturer IES ↔ RTX checks

With the local IES assets present:

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/kit_validate_manufacturer_ies_rtx.py"
```

Transform synchronization:

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/kit_validate_manufacturer_ies_transform_sync.py"
```

These checks prove that the same local IES profile can be used for RTX shaping while the deterministic solver remains the scientific authority.

## 16. Local model service health

Start the service as documented in [`local-ai-copilot.md`](local-ai-copilot.md), then:

```bash
curl -sS http://127.0.0.1:8080/health
echo
sudo ss -ltnp 'sport = :8080'
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

Required security property: the development service remains loopback-only unless a separate hardened deployment is deliberately designed.

## 17. Real model-service routing validation

```bash
python tools/validate_model_service.py
```

This uses the real model but does not grant arbitrary execution.

## 18. Real model → tool → result validation

```bash
python tools/validate_tool_loop.py
```

This validates a real tool-call round trip with the approved evidence store.

## 19. Open-model routing + grounding regressions

```bash
mkdir -p build/open-model-regressions
python tools/validate_open_model_regressions.py \
  | tee build/open-model-regressions/routing-grounding.json
```

A validated reference run reported:

```text
overall passed: True
routing: 8/8 passed
grounding: 2/2 passed
```

Because this test calls the real local model, it is slower and less deterministic than pure unit tests. That is why OpenGrowTwin also has deterministic schema validation and does not trust model output directly.

## 20. Deterministic adversarial safety suite

```bash
python tools/validate_copilot_safety.py \
  | tee build/open-model-regressions/safety.json
```

The safety suite verifies rejection of cases including:

- unknown/arbitrary tool names;
- path traversal as an identifier;
- out-of-range radiant power;
- mutation without confirmation;
- arguments changed after confirmation;
- replayed confirmation token;
- expired confirmation token.

A validated reference run passed all seven adversarial cases and reported `executes_arbitrary_code: false` for the tool-executor architecture.

## 21. Kit copilot panel acceptance

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/kit_validate_copilot_panel.py"
```

The key property is:

```text
mutation_before_confirmation: false
```

The model may propose an exact bounded change; execution must not occur until confirmation.

## 22. Graphical confirm/reject acceptance

For the strongest human-visible safety proof:

1. start the local model service;
2. start the NVIDIA Xorg/Openbox/VNC graphical path;
3. launch OpenGrowTwin on `DISPLAY=:1`;
4. ask for a bounded channel-power mutation;
5. verify the proposal appears without scene mutation;
6. click **Confirm exact change**;
7. verify the scene and deterministic result recompute;
8. ask for a second bounded change;
9. click **Reject**;
10. verify no scene change occurs.

## 23. Virtual sensor and live UI checks

Verify:

- optical-model selection changes the actual scientific path;
- spectrum graph updates to the active profile;
- PPFD legend is bound to the displayed field;
- baseline/current switching changes heatmap, metrics, and sensor coherently;
- sensor position remains fixed in world space across recomputation;
- bilinear local PPFD/DLI/far-red/channel values come from the displayed scientific result;
- fixture edits trigger the expected live recomputation.

## 24. Reproduction report

Record:

```text
OpenGrowTwin commit/tag:
OS + kernel:
Cloud machine type/zone (non-sensitive):
GPU:
NVIDIA driver:
Kit SDK/template revision:
Python version:
pytest pass count:
manufacturer asset revision(s), if used:
llama.cpp commit, if used:
model name/quantization/SHA-256, if used:
app ready: yes/no
RTX ready: yes/no
manufacturer validation: pass/fail/not run
model routing: pass/fail/not run
safety suite: pass/fail
confirm/reject UI: pass/fail/not run
known deviations from reference environment:
```

Do not include project IDs, private IPs, credentials, tokens, personal usernames, or API keys in a public reproduction report.
