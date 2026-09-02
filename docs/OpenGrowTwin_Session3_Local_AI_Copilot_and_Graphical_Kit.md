# OpenGrowTwin — Local AI Copilot, Guarded Tool Use, and Graphical Kit Validation

**Session date:** 2026-09-02  
**Project:** OpenGrowTwin  
**Purpose:** Engineering record, reproducibility guide, security record, and competition evidence  
**Status:** OGT-201 through OGT-206 **COMPLETE AND MERGED**

---

## 1. Relationship to the earlier session logs

This document continues the prior OpenGrowTwin infrastructure and science logs.

- **Day 1** established a cloud NVIDIA L4 environment, the NVIDIA driver stack,
  and a custom Kit application that reached `app ready` and `RTX ready`.
- **Day 2** established the deterministic spectral-lighting solver, OpenUSD
  result contract, geometry-aware visualization path, and headless RTX capture.
- **This session** added the constrained local open-model copilot, validated its
  tool boundary, integrated it into Kit, proved the approval/rejection flow in a
  graphical session, and added repeatable model and safety regressions.

The resulting vertical slice is:

```text
natural-language request
          ↓
local open-weight model on NVIDIA L4
          ↓
allowlisted, schema-validated tool proposal
          ↓
explicit confirmation for scene mutation
          ↓
deterministic OpenGrowTwin solver and live OpenUSD scene
          ↓
measured result returned to the model
          ↓
grounded response shown inside NVIDIA Kit
```

The language model does not calculate PPFD, DLI, photon conversion, shadowing,
or optimization values. Those quantities remain authoritative outputs of the
deterministic solver.

---

## 2. Privacy and sanitization conventions

This public reproduction record intentionally omits:

- personal names and account usernames;
- email addresses and Git author identities;
- cloud project identifiers;
- public or private IP addresses other than the loopback address;
- SSH keys, API keys, access tokens, VNC passwords, cookies, and signed URLs;
- machine-specific home-directory names;
- private repository or service credentials.

Commands use the following placeholders:

| Placeholder | Meaning |
|---|---|
| `<repo-url>` | OpenGrowTwin Git repository URL |
| `<vm-name>` | GPU VM instance name |
| `<zone>` | Cloud zone containing the VM |
| `$HOME` | Current user's home directory |
| `<vnc-password-file>` | Locally protected VNC password file on the VM |

Do not commit generated credentials, shell histories, `.env` files, VNC
password files, cloud configuration directories, or model-service secrets.

---

## 3. Session objectives

The session implemented and accepted six open-model tasks:

| Milestone | Objective | Result |
|---|---|---|
| OGT-201 | Freeze tool schemas and safety rules | Passed |
| OGT-202 | Create curated evidence records | Passed |
| OGT-203 | Run a local open-model inference service | Passed |
| OGT-204 | Implement the validated tool-execution loop | Passed |
| OGT-205 | Add and visually validate the Kit copilot panel | Passed |
| OGT-206 | Add open-model routing, grounding, and safety regressions | Passed |

The original task queue referred to Gemma as the initial candidate. The tested
implementation used **NVIDIA Nemotron 3 Nano 4B**, quantized as **Q4_K_M**, in a
local `llama.cpp` service. The architectural contract remained unchanged:
model output is untrusted until it passes deterministic tool validation.

---

## 4. Tested environment

### 4.1 Cloud GPU host

The validated environment used:

- Ubuntu 22.04 LTS;
- Google Cloud G2-class VM;
- one NVIDIA L4 GPU;
- approximately 23 GB GPU memory;
- NVIDIA driver `610.57.04`;
- NVIDIA Kit SDK `110.3.0`;
- Vulkan and NVIDIA OpenGL 4.6;
- Python project virtual environment under the OpenGrowTwin checkout.

The local model service used approximately 3,026 MiB of GPU memory during the
observed health check. A representative generation rate was approximately
77 tokens/second. Exact latency depends on prompt length, cache state, Kit/RTX
load, CPU scheduling, and quantization/runtime revisions.

### 4.2 Service boundary

The model server listened only on:

```text
127.0.0.1:8080
```

This loopback binding is important. The development server reported that CORS
allowed all origins and no API key was set; exposing that configuration on a
public interface would be unsafe. Network firewall rules are not a substitute
for the loopback bind in this workflow.

---

## 5. OGT-201 — Frozen tool contract and deterministic safety

### 5.1 Design rule

The model is allowed to choose among declared tools, but it cannot execute
arbitrary Python, shell commands, paths, modules, or dynamically named
functions.

The boundary enforces:

- an explicit tool allowlist;
- JSON-schema-shaped arguments;
- rejection of unknown tools and arguments;
- enum or approved-identifier validation;
- numeric bounds with explicit units;
- separation of read-only and mutating tools;
- confirmation tokens bound to exact mutation arguments;
- one-time consumption and expiry of confirmation tokens;
- no arbitrary-code execution path.

### 5.2 Mutation lifecycle

```text
model proposes exact mutation
          ↓
application validates name, identifiers, types, units, and bounds
          ↓
application creates confirmation bound to those exact arguments
          ↓
user confirms or rejects
          ↓
confirmed call executes once; rejected call does not mutate
```

Changing the arguments after confirmation invalidates the token. Reusing a
consumed token or using an expired token is also rejected.

### 5.3 Security acceptance evidence

The deterministic OGT-206 safety suite later exercised this OGT-201 contract:

| Case | Expected rejection | Result |
|---|---|---|
| Arbitrary tool such as `run_python` | Unknown tool | Passed |
| Path traversal as a target identifier | Not an approved identifier | Passed |
| Out-of-range radiant power | Outside authored bounds | Passed |
| Mutation without confirmation | Missing confirmation token | Passed |
| Arguments changed after confirmation | Token does not match mutation | Passed |
| Replayed confirmation | Valid unused token required | Passed |
| Expired confirmation | Token expired | Passed |

---

## 6. OGT-202 — Curated evidence records

The copilot receives approved structured evidence instead of unrestricted
filesystem or web access. Evidence records connect exposed targets and claims
to bundled source identifiers, conditions, and limitations.

The validated Phalaenopsis reference lookup returned:

- DOI: `10.1111/ppl.12300`;
- publication year: 2015;
- limitation: the study did not establish a universal spectral optimum across
  cultivars; responses varied by cultivar, response variable, and harvest.

This limitation is part of the grounded answer contract. A published treatment
is represented as a reference environment, not promoted to a universal plant
recipe.

---

## 7. OGT-203 — Local Nemotron service

### 7.1 Runtime architecture

The selected model ran through `llama.cpp` as an OpenAI-compatible local chat
completion service. The repository launcher is:

```text
tools/run_nemotron_service.sh
```

The launcher must retain its executable bit in Git:

```bash
chmod +x tools/run_nemotron_service.sh
git update-index --chmod=+x tools/run_nemotron_service.sh
```

Verify the tracked mode with:

```bash
git ls-files -s tools/run_nemotron_service.sh
```

The mode should be `100755`.

### 7.2 Start and verify the service

On the GPU VM:

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate
tools/run_nemotron_service.sh
```

Keep the service terminal open. In a second VM terminal:

```bash
curl -sS http://127.0.0.1:8080/health
echo

sudo ss -ltnp 'sport = :8080'
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

Expected health response:

```json
{"status":"ok"}
```

Only one server may bind port 8080. If a second launch reports `couldn't bind
HTTP server socket`, inspect the existing listener first. A healthy existing
`llama-server` should be reused rather than started twice.

### 7.3 Service availability failure

The client error:

```text
model service request failed: <urlopen error [Errno 111] Connection refused>
```

means no service accepted a connection on the configured address. It is not a
Kit renderer failure. Confirm `/health`, the listener, and the server process
before debugging tool calling.

---

## 8. OGT-204 — Validated model/tool loop

### 8.1 Loop behavior

The model client sends:

- the system safety policy;
- compact scene or evidence context;
- the frozen tool schemas;
- a user request.

It then requires a clean tool-call finish, validates the returned name and
arguments, executes only the approved operation, returns the deterministic
result to the model, and requests a grounded final answer.

### 8.2 Reproduce the approved evidence lookup

With the local service running:

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate
python tools/validate_tool_loop.py
```

The observed successful run contained:

```json
{
  "call": {
    "name": "get_target",
    "arguments": {
      "target_id": "phalaenopsis_ouzounis_2015_reference"
    }
  },
  "execution": {
    "doi": "10.1111/ppl.12300"
  },
  "executes_arbitrary_code": false,
  "passed": true
}
```

### 8.3 Tool-routing nondeterminism encountered

During development, the same exact mutation prompt occasionally returned a
generic `propose_configuration` call instead of the intended
`set_channel_power` call. Another attempt reported that the model did not
finish with a tool call, even though a raw request later returned a valid
`tool_calls` response.

The final prompt/schema contract produced the required exact call:

```json
{
  "name": "set_channel_power",
  "arguments": {
    "fixture_id": "fixture_01",
    "channel_id": "blue",
    "radiant_power_w": 4.5
  }
}
```

This is why OGT-206 includes repeated routing regressions instead of treating a
single successful generation as sufficient acceptance evidence.

---

## 9. OGT-205 — Guarded Kit copilot panel

### 9.1 UI behavior

The OpenGrowTwin Kit panel exposes:

- a prompt field;
- Ask and Clear controls;
- model/tool status;
- a grounded response area;
- an exact proposed mutation;
- **Confirm exact change** and **Reject** controls.

Read-only tools may execute automatically. Mutations remain proposals until the
user confirms the exact change.

### 9.2 Headless acceptance

The guarded headless acceptance produced:

```json
{
  "before_total_blue_w": 18.0,
  "after_total_blue_w": 4.5,
  "mutation_before_confirmation": false,
  "confirmation_consumed": true,
  "arbitrary_code_execution": false,
  "proposal": {
    "name": "set_channel_power",
    "arguments": {
      "fixture_id": "fixture_01",
      "channel_id": "blue",
      "radiant_power_w": 4.5
    }
  },
  "mean_ppfd_after": 52.446328240084085,
  "grounded_answer": "The total blue-channel radiant power of fixture_01 is now 4.5 watts."
}
```

The central safety evidence is `mutation_before_confirmation: false`. The
change occurred only after confirmation, and the confirmation was consumed.

### 9.3 Kit-Python dependency issue

Kit uses its own Python environment. Installing PyYAML in the project's normal
`.venv` does not make `import yaml` available inside Kit.

An initial attempt to install through `omni.kit.pipapi` also failed because the
Kit Python environment did not contain `pip`:

```text
ModuleNotFoundError: No module named 'pip'
```

The robust integration principle is to avoid runtime package installation in
acceptance scripts. Bundle or expose required data through Kit-compatible code,
or declare/package Python dependencies with the extension build. Do not assume
the project virtual environment and Kit Python share packages.

---

## 10. Graphical Kit access on a headless NVIDIA L4 VM

The final visual check required a real X server backed by the NVIDIA GPU. A
software-only X server may display UI, but it does not prove the same graphical
path as NVIDIA Xorg/OpenGL.

### 10.1 Required packages

Install the minimal desktop and verification tools using the distribution
package manager:

```bash
sudo apt-get update
sudo apt-get install -y \
  openbox \
  x11vnc \
  xterm \
  dbus-x11 \
  x11-xserver-utils \
  mesa-utils \
  xfonts-base \
  nvidia-xconfig
```

Verify:

```bash
command -v Xorg
command -v openbox-session
command -v x11vnc
command -v xterm
command -v glxinfo
```

### 10.2 NVIDIA Xorg configuration

First identify the GPU PCI bus using `nvidia-smi` or `lspci`. Generate the base
configuration with the matching bus ID:

```bash
sudo nvidia-xconfig \
  --allow-empty-initial-configuration \
  --virtual=1920x1080 \
  --busid=PCI:0:3:0
```

For the tested driver, `UseDisplayDevice "None"` was incompatible with a
virtual display and caused:

```text
UseDisplayDevice "None" is not supported with virtual display
Failed to select a display subsystem
no screens found
```

The working `Device` and `Screen` intent was:

```text
Section "Device"
    Identifier "Device0"
    Driver "nvidia"
    BusID "PCI:0:3:0"
EndSection

Section "Screen"
    Identifier "Screen0"
    Device "Device0"
    Monitor "Monitor0"
    DefaultDepth 24
    Option "AllowEmptyInitialConfiguration" "True"
    Option "UseDisplayDevice" "DFP-0"
    Option "ConnectedMonitor" "DFP-0"
    SubSection "Display"
        Depth 24
        Virtual 1920 1080
    EndSubSection
EndSection
```

Back up `/etc/X11/xorg.conf` before editing it. GPU bus IDs and connector names
are environment-specific; do not copy them blindly to a different VM.

### 10.3 Start Xorg and verify GPU acceleration

For a temporary validation session:

```bash
sudo systemd-run \
  --unit=opengrow-xorg \
  /usr/bin/Xorg :1 \
  -config /etc/X11/xorg.conf \
  -noreset \
  -nolisten tcp \
  -ac
```

Verify:

```bash
systemctl status opengrow-xorg --no-pager
DISPLAY=:1 glxinfo -B
DISPLAY=:1 xrandr
```

The acceptance output must show:

```text
direct rendering: Yes
OpenGL vendor string: NVIDIA Corporation
OpenGL renderer string: NVIDIA L4/PCIe/SSE2
OpenGL core profile version string: 4.6.0 NVIDIA ...
```

In the tested session, Xorg exposed a 1920 × 1080 virtual screen and an emulated
connected display. The active mode initially appeared at 1024 × 768 within the
larger framebuffer; `xrandr` can select 1920 × 1080 if required.

### 10.4 Start Openbox and x11vnc

Create the VNC password interactively on the VM; never paste it into a shared
log or commit it:

```bash
mkdir -p "$HOME/.vnc"
x11vnc -storepasswd "$HOME/.vnc/passwd"
chmod 600 "$HOME/.vnc/passwd"
```

Start a minimal desktop and loopback-only VNC service. The exact service wrapper
may vary; the essential process commands are:

```bash
DISPLAY=:1 dbus-run-session -- openbox-session

x11vnc \
  -display :1 \
  -rfbauth "$HOME/.vnc/passwd" \
  -rfbport 5901 \
  -localhost \
  -forever \
  -shared
```

Run these in persistent terminals or user services. Confirm the VNC listener is
bound to loopback, not a public interface:

```bash
ss -ltnp | grep ':5901'
```

### 10.5 Create the SSH tunnel from the local workstation

Run this on the local workstation, not inside the VM:

```bash
gcloud compute ssh <vm-name> \
  --zone=<zone> \
  -- \
  -N \
  -L 5901:127.0.0.1:5901
```

Keep the tunnel terminal open. Connect a VNC client to:

```text
vnc://127.0.0.1:5901
```

The VNC port does not need to be opened in the cloud firewall because traffic
travels through SSH.

### 10.6 Clipboard and keyboard caveats

VNC clipboard behavior depends on both the client and terminal emulator.
Common terminal shortcuts are:

- copy: `Ctrl+Shift+C`;
- paste: `Ctrl+Shift+V`;
- X11 selection paste: middle mouse button.

If the local and remote keyboard layouts differ, characters such as `~` may not
map correctly. Use absolute paths instead of `~` as a temporary workaround and
set a matching layout with `setxkbmap` when needed. Avoid pasting multiline
commands until clipboard behavior is verified with harmless text.

---

## 11. Make the development extension visible to Kit

The custom Kit application declared a dependency on `opengrow.twin`, but the
dependency solver initially reported that no package was available. The app's
extension search folders were:

```text
${app}/../exts
${app}/../extscache
```

For the local development build, expose the repository extension at the build
search path:

```bash
ln -s \
  "$HOME/projects/OpenGrowTwin/exts/opengrow.twin" \
  "$HOME/projects/kit-app-template/_build/linux-x86_64/release/exts/opengrow.twin"
```

Then ensure the app manifest includes:

```toml
[dependencies]
"opengrow.twin" = {}
```

The symlink is environment staging, not a portable repository artifact. A
cleaner long-term solution is to add the OpenGrowTwin extension directory as an
explicit configured search path or package the extension as part of the Kit
application build.

Launch the graphical app on the GPU-backed display:

```bash
cd "$HOME/projects/kit-app-template"
DISPLAY=:1 ./repo.sh launch
```

Successful startup includes:

```text
[ext: opengrow.twin-0.1.0] startup
[OpenGrowTwin] Interactive simulation extension ready
[ext: opengrowtwin.my_editor-0.1.0] startup
app ready
RTX ready
```

---

## 12. Final graphical acceptance procedure

### 12.1 Preconditions

Before opening the copilot panel:

1. the local Nemotron service responds to `/health`;
2. Xorg `:1` reports NVIDIA direct rendering;
3. Openbox and loopback-only x11vnc are running;
4. the SSH tunnel and VNC client are connected;
5. the Kit app loaded `opengrow.twin` and reached `RTX ready`.

### 12.2 Confirm path

In the OpenGrowTwin panel, enter:

```text
Set the total blue-channel radiant power of fixture_01 to 4.5 watts.
```

Select **Ask**. Verify that the UI presents an exact
`set_channel_power` proposal and does not mutate immediately. Select
**Confirm exact change**.

The observed visual result showed:

- the correct `set_channel_power` proposal;
- a grounded statement that the fixture blue-channel total was 4.5 W;
- the scene and simulation recomputed after confirmation;
- mean PPFD displayed at approximately 31.08 µmol/m²/s in that graphical run.

The graphical value differs from the standalone headless acceptance value
because the live staged scene and simulation configuration were different.
Acceptance depends on the guarded transition and internally consistent
recomputation, not equality between unrelated scene states.

### 12.3 Reject path

Submit a second bounded proposal, for example:

```text
Set the total blue-channel radiant power of fixture_01 to 5.0 watts.
```

Select **Reject**. The observed panel reported:

```text
Proposal rejected — no scene change occurred.
Rejected proposed tool: set_channel_power
```

The existing heatmap and approximately 31.08 µmol/m²/s mean PPFD remained in
place. This visually proved that rejection does not mutate the scene.

---

## 13. Expected warnings and actionable errors

### 13.1 Usually non-blocking in this workflow

- **ECC enabled on the L4:** informational for this validation.
- **Audio device unavailable:** Kit falls back to a null audio streamer; the
  lighting workflow does not require audio.
- **Hydra source already registered:** observed without blocking RTX readiness.
- **Different OpenUSD build imported before the asset converter:** avoid mixing
  converters and host USD bindings in production, but it did not block this
  visual validation.
- **Missing `primvars:displayColor:indices`:** warning observed for the current
  PPFD heatmap; investigate for clean logs, but the heatmap remained visible.

### 13.2 Actionable failures and their causes

| Symptom | Cause | Resolution |
|---|---|---|
| `Permission denied` launching model service | Script lacked executable bit | Set and commit mode `100755` |
| `Connection refused` from copilot | Model server not listening | Start/reuse service; verify `/health` and port 8080 |
| `couldn't bind ... port: 8080` | A model server already owns the port | Reuse it or deliberately stop it before restart |
| `model did not finish with a tool call` | Model response did not satisfy client contract | Inspect raw response; improve schemas/prompt; rerun regressions |
| `No module named 'yaml'` in Kit | Kit Python differs from project `.venv` | Package dependency for Kit or remove runtime dependency |
| `No module named 'pip'` in `pipapi` | Kit runtime lacks pip bootstrap | Do not install dependencies during acceptance startup |
| `no screens found` from Xorg | `UseDisplayDevice None` conflicted with virtual display | Use an emulated connected DFP and matching display device |
| Dependency solver cannot find `opengrow.twin` | Extension absent from Kit build search path | Add dependency and expose extension in release `exts` path |
| Git commit reports unknown author | Repository has no Git identity | Configure repository-local `user.name` and `user.email`; do not publish them in logs |

---

## 14. OGT-206 — Open-model and safety regressions

### 14.1 Live open-model regression suite

With the model service running:

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate

python tools/validate_open_model_regressions.py \
  | tee build/ogt-206/open-model-regressions.json
```

The accepted report contained:

```text
overall passed: True
routing: 8/8 passed
grounding: 2/2 passed
```

This suite exercises actual model routing and grounded-response behavior. It
therefore requires the local inference service and may take longer than the
normal deterministic unit tests.

### 14.2 Deterministic safety suite

Run:

```bash
python tools/validate_copilot_safety.py \
  | tee build/ogt-206/copilot-safety-regressions.json
```

Accepted summary:

```json
{
  "kind": "deterministic-safety",
  "milestone": "OGT-206",
  "executes_arbitrary_code": false,
  "passed": true
}
```

All seven adversarial cases passed.

### 14.3 Full unit suite

Run:

```bash
python -m pytest -q
```

Expected result for the merged session state:

```text
79 passed
```

The observed runtime varied from about 2.3 to 3.9 seconds across runs.

---

## 15. Clean reproduction from a fresh checkout

### 15.1 CPU/project setup

```bash
git clone <repo-url> "$HOME/projects/OpenGrowTwin"
cd "$HOME/projects/OpenGrowTwin"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

python -m pytest -q
```

### 15.2 Model setup

Install/build the repository-pinned `llama.cpp` revision and obtain the exact
repository-documented Nemotron GGUF model through its authorized distribution
channel. Verify the recorded checksum before use. Model files are intentionally
not embedded in this log.

Start and validate:

```bash
cd "$HOME/projects/OpenGrowTwin"
tools/run_nemotron_service.sh
```

In another terminal:

```bash
curl -sS http://127.0.0.1:8080/health
python tools/validate_tool_loop.py
python tools/validate_open_model_regressions.py
python tools/validate_copilot_safety.py
```

### 15.3 Headless Kit acceptance

Use the repository's Kit validation script with the custom application build.
The precise launch command depends on the local Kit App Template layout. The
important conditions are:

- the OpenGrowTwin repository `src/` directory is importable;
- the `opengrow.twin` extension is discoverable;
- required validation script arguments are passed through Kit;
- Kit reaches `app ready` and `RTX ready`;
- the validation JSON reports no pre-confirmation mutation and no arbitrary
  code execution.

### 15.4 Graphical acceptance

Follow Sections 10–12. Capture evidence of:

1. NVIDIA-backed graphical Kit;
2. the live spectral simulation and PPFD heatmap;
3. a model-generated exact mutation proposal;
4. unchanged state before confirmation;
5. recomputation after confirmation;
6. unchanged state after rejection.

---

## 16. Shutdown and cost control

Stop the graphical validation services after capturing evidence:

```bash
systemctl --user stop opengrow-vnc opengrow-openbox
sudo systemctl stop opengrow-xorg
```

Stop Kit and the model server with `Ctrl+C` in their owning terminals. Stop the
local SSH tunnel with `Ctrl+C` on the workstation.

Verify that no unintended listener or GPU process remains:

```bash
ss -ltnp | grep -E ':5901|:8080' || true
nvidia-smi
```

Then stop the GPU VM from the local workstation:

```bash
gcloud compute instances stop <vm-name> --zone=<zone>
```

Stopping the VM is the decisive cost-control step. Stopping Kit, Xorg, VNC, or
the model process alone does not stop VM billing.

---

## 17. Security properties demonstrated

The session demonstrated the following properties with automated or visual
evidence:

- the model endpoint remained loopback-only;
- the model could call only declared tools;
- arbitrary tool names were rejected;
- identifiers could not be replaced with arbitrary paths;
- numeric mutations were bounded;
- a mutation could not execute without confirmation;
- confirmation was bound to the exact arguments;
- confirmation tokens were one-use and expiring;
- rejecting a proposal produced no scene change;
- deterministic solver outputs, not model prose, defined PPFD results;
- approved evidence included citation and limitation information;
- regression artifacts recorded pass/fail results without credentials.

`executes_arbitrary_code: false` is an architectural assertion backed by the
allowlist and adversarial regression suite; it does not mean the surrounding
Kit application or Python runtime is a general-purpose security sandbox.

---

## 18. Known limitations

1. **Small quantized model.** A 4B Q4 model can route incorrectly or fail to
   finish with a tool call. Regression coverage and deterministic validation
   are required.
2. **Development service configuration.** The tested `llama.cpp` server had no
   API key and permissive CORS. It is acceptable only while bound to loopback.
3. **Temporary desktop services.** The Xorg/Openbox/x11vnc setup was created for
   visual acceptance, not hardened as a permanent multi-user service.
4. **Kit dependency isolation.** Project-venv packages are not automatically
   available to Kit Python.
5. **Development symlink.** The extension was exposed to the Kit release build
   through a machine-local symlink. Packaging/search-path automation remains
   desirable.
6. **Direct-light scientific scope.** The solver's previously documented
   exclusions still apply, including absent biological prediction and limited
   optical transport compared with a full plant/facility model.
7. **Reference target scope.** A cited treatment is not a universal crop
   optimum.
8. **Visual warnings.** The missing display-color indices warning should be
   cleaned up before a polished submission recording even though it did not
   block the accepted result.

---

## 19. Repository completion state

At the end of the session:

- OGT-205 was merged through its reviewed pull request;
- OGT-206 was merged through its reviewed pull request;
- the main branch included the graphical acceptance documentation and both
  regression scripts;
- the full suite reported `79 passed`;
- live open-model routing reported `8/8` passed;
- grounded-response checks reported `2/2` passed;
- deterministic adversarial safety checks reported `7/7` passed.

Generated regression JSON under `build/ogt-206/` is evidence output. Whether it
is committed or regenerated should follow the repository's artifact policy;
the validator scripts and reproduction instructions are the durable source of
truth.

---

## 20. Final acceptance checklist

- [x] Tool schemas and mutation policy frozen
- [x] Unknown tools and arbitrary paths rejected
- [x] Numeric bounds enforced
- [x] Exact, one-use, expiring confirmation enforced
- [x] Approved citation-bearing evidence exposed
- [x] Local Nemotron service healthy on loopback
- [x] Valid read-only model → tool → result → answer loop
- [x] Exact `set_channel_power` routing demonstrated
- [x] No arbitrary-code execution path in the tool executor
- [x] Headless guarded Kit acceptance passed
- [x] NVIDIA-backed Xorg/OpenGL display verified
- [x] OpenGrowTwin panel visible in graphical Kit
- [x] Confirm path mutated only after approval
- [x] Reject path produced no scene change
- [x] Open-model routing regressions passed 8/8
- [x] Grounding regressions passed 2/2
- [x] Deterministic safety regressions passed 7/7
- [x] Full Python test suite passed 79/79
- [x] OGT-201 through OGT-206 merged

The OpenGrowTwin MVP now has a reproducible, locally hosted open-model copilot
that is visibly integrated into NVIDIA Kit, operates through a deterministic
allowlisted tool boundary, requires explicit approval for scene mutation, and
reports measured lighting results without replacing the scientific solver.
