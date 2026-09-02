# OGT-205 — Local Nemotron Copilot Panel

## Status

Complete. Backend and graphical acceptance passed on the OpenGrowTwin GCP
NVIDIA L4 VM on 2026-09-02.

## Delivered interaction

The existing OpenGrowTwin Kit window now contains a local Nemotron copilot
section. A user can ask about:

- the active OpenUSD scene;
- approved evidence targets;
- recorded solver metrics and occlusion;
- comparisons between recorded runs;
- bounded deterministic simulations;
- an exact fixture-channel radiant-power change.

Read-only calls execute after deterministic contract validation. Mutating calls
stop at a visible proposal containing the exact arguments. The user must choose
**Confirm exact change** or **Reject**. Confirmation tokens are short-lived,
single-use, and bound to the exact tool name and arguments.

Nemotron never receives arbitrary Python, shell execution, file paths, or
unrestricted USD prim paths.

## Headless acceptance

Run the loopback model service separately, then execute:

```bash
cd ~/projects/kit-app-template
./repo.sh launch -- \
  --no-window \
  --exec ~/projects/OpenGrowTwin/tools/kit_validate_copilot_panel.py
```

Observed acceptance:

```json
{
  "after_total_blue_w": 4.5,
  "arbitrary_code_execution": false,
  "before_total_blue_w": 18.0,
  "confirmation_consumed": true,
  "grounded_answer": "The total blue-channel radiant power of fixture_01 is now 4.5 watts.",
  "mean_ppfd_after": 52.446328240084085,
  "mutation_before_confirmation": false,
  "proposal": {
    "arguments": {
      "channel_id": "blue",
      "fixture_id": "fixture_01",
      "radiant_power_w": 4.5
    },
    "name": "set_channel_power"
  }
}
```

This validates that the model proposed the exact unsigned mutation, no USD
attribute changed before confirmation, the application consumed confirmation,
the RTX presentation synchronized, the deterministic solver consumed the
updated scene, and the final answer was grounded in tool output.

The acceptance stage is opened in memory and is not saved over the demo asset.

## Regression result

```text
79 passed in 2.30s
```

## Runtime notes

The llama.cpp service remains loopback-only at `127.0.0.1:8080`. The Kit
Python runtime does not ship with pip or PyYAML, so the extension exposes the
project virtual environment's pure-Python dependencies to Kit. No system-wide
package mutation is required.

## Graphical acceptance

A GPU-backed Xorg display on the L4 was viewed through a localhost-only VNC
server over an SSH tunnel. The Kit window rendered the simulation controls,
metrics, copilot input, grounded answer, and confirmation controls.

The confirmed 4.5 W request completed, refreshed the solver results, and
displayed a grounded response. A subsequent 5.0 W proposal was rejected; the
panel reported that no scene change occurred, identified
`set_channel_power` as the rejected tool, disabled the mutation buttons, and
retained the previous mean PPFD of 31.08 µmol m⁻² s⁻¹.

Both visual confirmation branches passed.
