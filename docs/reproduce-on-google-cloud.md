# Reproduce OpenGrowTwin from zero on Google Cloud

This is the primary end-to-end reproduction guide for OpenGrowTwin. It is written for a developer who has never seen the project before and wants to rebuild the validated architecture without needing any internal project history.

The complete path is:

```text
Google Cloud project
  ↓
Compute Engine G2 VM + NVIDIA L4
  ↓
Ubuntu 22.04 + working NVIDIA driver
  ↓
NVIDIA Kit App Template + RTX
  ↓
OpenGrowTwin Python package + tests
  ↓
OpenUSD live application + deterministic photon solver
  ↓
local ams OSRAM IES/SPD assets (optional manufacturer mode)
  ↓
local NVIDIA Nemotron 3 Nano 4B via llama.cpp (optional)
  ↓
guarded model/tool loop + human confirmation
  ↓
full validation suite
```

## Reproducibility boundary

OpenGrowTwin source code, public fixtures, metadata, examples, and validators are in this repository. The following remain external dependencies under their own terms and are not redistributed here:

- NVIDIA Kit/Omniverse SDK components;
- NVIDIA Nemotron model weights;
- ams OSRAM IES/EULUMDAT/rayfile/spectrum archives;
- supplier datasheets and research papers.

A validated reference environment used:

| Component | Reference environment |
| --- | --- |
| Google Cloud machine | `g2-standard-8` |
| GPU | 1 × NVIDIA L4 |
| vCPU / RAM | 8 vCPU / 32 GB |
| OS | Ubuntu 22.04.5 LTS |
| Boot disk | 100 GB balanced persistent disk |
| Validated zone | `us-central1-b` |
| NVIDIA driver | 610.57.04 |
| Kit SDK used in later integration | 110.3.0 |
| Python regression at the recorded reference point | 134 passed |

Cloud capacity and upstream versions change. If you intentionally use newer software, record the actual versions you tested.

# Part A — Run the CPU scientific path first

Do this on any Linux workstation with Python 3.10+ before provisioning a GPU. It separates OpenGrowTwin issues from cloud, driver, and Kit issues.

## A1. Clone

```bash
git clone https://github.com/ChrisSeVa1/OpenGrowTwin.git
cd OpenGrowTwin
```

To reproduce a specific release or commit, check it out explicitly after cloning.

## A2. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## A3. Run tests

```bash
python -m pytest -q
```

A recorded reference environment reported:

```text
134 passed
```

A later commit may contain a different number of tests; failures matter more than matching an old total exactly.

## A4. Run the scientific CLI

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

Generate the OpenUSD scene:

```bash
python -m opengrow scene demo/design.json \
  --out demo/grow_chamber.usda
```

The CPU path proves the photon-domain calculation without RTX. Scientific PPFD, DLI, spectrum, and uniformity are never derived from rendered pixels.

# Part B — Create the Google Cloud project

## B1. Open Google Cloud

Website:

https://console.cloud.google.com/

You need a Google account with billing enabled and permission to create resources.

For a new project:

1. open Google Cloud Console;
2. use the project selector in the top navigation bar;
3. select **New Project**;
4. choose a non-sensitive project name;
5. create/select the project;
6. confirm billing is linked.

Never commit a project ID, billing account, access token, or service-account credential to this repository.

## B2. Enable Compute Engine

Direct page:

https://console.cloud.google.com/apis/library/compute.googleapis.com

Or navigate:

```text
Google Cloud Console
→ APIs & Services
→ Library
→ search "Compute Engine API"
→ Enable
```

Then open:

https://console.cloud.google.com/compute/instances

Google documentation:

https://cloud.google.com/compute/docs/instances/create-start-instance

# Part C — Check GPU quota

A valid VM configuration can still fail if the project has zero GPU quota.

Direct quota page:

https://console.cloud.google.com/iam-admin/quotas

Navigate:

```text
Google Cloud Console
→ IAM & Admin
→ Quotas & System Limits
```

For an L4/G2 deployment, check both:

- the global/all-regions GPU allowance;
- regional NVIDIA L4 quota for the region you intend to use.

The original deployment initially had:

```text
GPUS_ALL_REGIONS
limit: 0
```

That global limit had to be increased before any GPU VM could be created.

Quota approval does **not** guarantee physical GPU capacity in a zone.

Google GPU overview:

https://cloud.google.com/compute/docs/gpus/about-gpus

# Part D — Create the G2/L4 VM

Official Google G-series guide:

https://cloud.google.com/compute/docs/gpus/create-gpu-vm-g-series

You can use the Console or CLI.

## D1. Console method

Open:

https://console.cloud.google.com/compute/instancesAdd

Or navigate:

```text
Google Cloud Console
→ Compute Engine
→ VM instances
→ Create instance
```

Use approximately:

| Setting | Value |
| --- | --- |
| Name | `opengrowtwin-gpu` |
| Machine | `g2-standard-8` |
| GPU | 1 × NVIDIA L4 |
| OS | Ubuntu 22.04 LTS |
| Disk | 100 GB balanced persistent disk |
| Maintenance policy | terminate |

The validated environment used `us-central1-b`. That is a reference, not a guarantee that the zone always has stock.

Several European G2 zones were correctly configured but temporarily returned:

```text
ZONE_RESOURCE_POOL_EXHAUSTED
```

That is a capacity problem, not necessarily a quota or configuration problem.

## D2. CLI method

On Ubuntu, install the CLI if needed:

```bash
sudo snap install google-cloud-cli --classic
```

Authenticate:

```bash
gcloud auth login
gcloud config set project <project-id>
```

Create:

```bash
export VM_NAME=opengrowtwin-gpu
export ZONE=us-central1-b

gcloud compute instances create "$VM_NAME" \
  --zone="$ZONE" \
  --machine-type=g2-standard-8 \
  --maintenance-policy=TERMINATE \
  --image-project=ubuntu-os-cloud \
  --image-family=ubuntu-2204-lts \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-balanced \
  --network=default
```

The tested `g2-standard-8` configuration already includes the L4 accelerator; the successful command did not add a separate `--accelerator` argument.

Connect:

```bash
gcloud compute ssh "$VM_NAME" --zone="$ZONE"
```

# Part E — Verify the VM and NVIDIA driver

## E1. Inspect the host

```bash
hostnamectl
df -h /
lspci | grep -i nvidia
```

Seeing an NVIDIA PCI device does not prove the driver is usable.

## E2. Check the driver

```bash
nvidia-smi
```

If it identifies the NVIDIA L4, record the driver version and continue.

If not, use Google's maintained installation instructions:

https://cloud.google.com/compute/docs/gpus/install-drivers-gpu

For Ubuntu 22.04, update APT first:

```bash
sudo apt-get update
```

One supported route is to install a matching GCP NVIDIA kernel-module/driver pair. Available package versions vary with the Ubuntu repository, so confirm the current package names before installation rather than hard-coding an obsolete driver number.

After installation, reboot if required:

```bash
sudo reboot
```

Reconnect, then verify:

```bash
nvidia-smi
```

The recorded reference environment used driver `610.57.04`. A newer compatible driver can be valid, but should be recorded as a deviation from the reference environment.

Do not proceed to Kit until `nvidia-smi` works.

# Part F — Install development tools

```bash
sudo apt-get update
sudo apt-get install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  cmake \
  curl \
  ca-certificates
```

Create a common workspace:

```bash
mkdir -p "$HOME/projects"
```

# Part G — Bootstrap NVIDIA Kit App Template

Official repository:

https://github.com/NVIDIA-Omniverse/kit-app-template

Documentation:

https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/docs/intro.html

## G1. Clone

```bash
cd "$HOME/projects"
git clone https://github.com/NVIDIA-Omniverse/kit-app-template.git
cd kit-app-template
```

## G2. Bootstrap repository tooling

```bash
./repo.sh --help
```

Internet access is required for NVIDIA dependencies.

## G3. Create the OpenGrowTwin Kit application

```bash
./repo.sh template new
```

The reference application used:

```text
Create: Application
Template: Kit Base Editor
Application .kit name: opengrowtwin.my_editor
Display name: OpenGrowTwin
Version: 0.1.0
Application layers: No
```

Expected application definition:

```text
source/apps/opengrowtwin.my_editor.kit
```

## G4. Build

```bash
./repo.sh build
```

## G5. First launch

```bash
./repo.sh launch
```

Select `opengrowtwin.my_editor`.

The Kit/RTX gate passes only when the log reaches both:

```text
app ready
RTX ready
```

The first RTX initialization can take several minutes while shaders and caches are prepared.

For explicit Linux CLI launch commands, headless validators, graphical access, and operator shortcuts, see [`kit-linux-operations.md`](kit-linux-operations.md).

# Part H — Clone OpenGrowTwin on the VM

```bash
cd "$HOME/projects"
git clone https://github.com/ChrisSeVa1/OpenGrowTwin.git
cd OpenGrowTwin

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest -q
```

Regenerate the demo stage:

```bash
python -m opengrow scene demo/design.json --out demo/grow_chamber.usda
```

# Part I — Launch OpenGrowTwin directly from Linux CLI

Set convenient variables:

```bash
export OGT_ROOT="$HOME/projects/OpenGrowTwin"
export KIT_ROOT="$HOME/projects/kit-app-template"
export KIT_EXE="$KIT_ROOT/_build/linux-x86_64/release/kit/kit"
export OGT_APP="$KIT_ROOT/_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit"
```

Launch:

```bash
"$KIT_EXE" "$OGT_APP" \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin
```

Expected startup markers:

```text
[ext: opengrow.twin-0.1.0] startup
[OpenGrowTwin] Interactive simulation extension ready
app ready
RTX ready
```

Headless example:

```bash
"$KIT_EXE" "$OGT_APP" \
  --no-window \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin \
  --exec "$OGT_ROOT/tools/kit_validate_orchestration.py"
```

The OpenUSD scene is authoritative for fixture transforms and emitter state. The deterministic solver reads that state, computes photon-domain results, and writes PPFD/metrics back to the open stage. RTX synchronizes visual lights from the same source state but is not the scientific calculator.

# Part J — Optional manufacturer-backed ams OSRAM mode

OpenGrowTwin works with its generic optical fallback without proprietary supplier assets.

To reproduce manufacturer-backed optical behavior, follow:

[`manufacturer-optical-data.md`](manufacturer-optical-data.md)

That guide covers:

- exact ams OSRAM part numbers;
- official supplier product pages;
- where to find **Downloads → Resources → Optical Simulation**;
- IES, EULUMDAT, and TraceProText roles;
- the six local filenames expected by the resolver;
- the gitignored `sources/osram/extracted/` directory;
- manufacturer-vs-Lambertian validation.

Do not commit raw supplier packages.

# Part K — Optional local NVIDIA Nemotron copilot

Follow:

[`local-ai-copilot.md`](local-ai-copilot.md)

The validated AI path is:

```text
NVIDIA Nemotron 3 Nano 4B Q4_K_M
  ↓
CUDA-enabled llama.cpp
  ↓
127.0.0.1:8080
  ↓
allowlisted tool schemas
  ↓
deterministic validation
  ↓
explicit confirmation for mutation
  ↓
OpenUSD scene + deterministic photon solver
```

The model does not calculate PPFD/DLI and has no arbitrary-code tool.

# Part L — Graphical access to a headless cloud VM

A headless GCP GPU VM can host a temporary NVIDIA-backed graphical session for interactive Kit work.

The tested approach uses:

```text
NVIDIA Xorg :1
  ↓
Openbox
  ↓
loopback-only x11vnc
  ↓
SSH tunnel
  ↓
local VNC client
```

Use [`kit-linux-operations.md`](kit-linux-operations.md) for the detailed procedure.

Important security rules:

- keep VNC bound to loopback;
- tunnel it through SSH;
- do not open port 5901 publicly;
- store VNC credentials outside Git;
- do not publish cloud project IDs, private addresses, or local credentials.

# Part M — Validate the complete system

Use [`validation-guide.md`](validation-guide.md).

The validation sequence covers:

1. Python/unit tests;
2. CPU scientific CLI;
3. OpenUSD scene contract;
4. USD-to-solver adapter;
5. geometry-aware occlusion;
6. Kit simulation orchestration;
7. live PPFD result updates;
8. RTX synchronization;
9. optional manufacturer optical validation;
10. optional local-model routing and grounded tool use;
11. deterministic safety checks;
12. graphical confirm/reject behavior.

# Part N — Cost control

Stop the VM whenever GPU work is finished:

```bash
gcloud compute instances stop "$VM_NAME" --zone="$ZONE"
```

Stopping Kit, Xorg, VNC, or the model service does **not** stop Compute Engine billing. Persistent disks and retained network resources may continue to incur charges.

Restart when needed:

```bash
gcloud compute instances start "$VM_NAME" --zone="$ZONE"
```

# Part O — Reproduction report template

Record at least:

```text
OpenGrowTwin commit/tag:
OS + kernel:
Google Cloud machine type:
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

Do not include project IDs, credentials, API keys, tokens, personal usernames, or private infrastructure addresses in a public reproduction report.
