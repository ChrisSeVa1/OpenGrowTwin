# OpenGrowTwin — Day 1 GCP, NVIDIA L4, Kit, and RTX Setup Guide

**Session date:** 2026-08-31 to 2026-09-01

**Project:** OpenGrowTwin

**Repository:** <https://github.com/ChrisSeVa1/OpenGrowTwin>

**Purpose:** Reproduction guide, engineering record, and NVIDIA GTC Berlin Golden Ticket evidence

**Outcome:** Infrastructure gate **passed**

## 1. Day 1 objective

Day 1 had one critical goal: prove that a deliberately lean Google Cloud GPU
environment could build and run a dedicated OpenGrowTwin NVIDIA Kit
application with RTX enabled.

This gate had to pass before investing the remaining competition sprint in the
scientific solver, optimization, OpenUSD data contract, and user experience.
The resulting architecture separates those responsibilities:

```text
Local or cloud CPU                    Google Cloud GPU
Python/NumPy science                  NVIDIA Kit application
simulation and optimization  ─USD─▶  OpenUSD scene and result loading
tests and numeric evidence            RTX visualization and capture
```

This separation keeps the scientific calculation reproducible without a GPU
and reserves paid L4 time for NVIDIA-specific integration and rendering.

## 2. Verified result

The completed Day 1 path was:

```text
Google Cloud Compute Engine
        ↓
g2-standard-8 in us-central1-b
        ↓
NVIDIA L4 + verified driver
        ↓
NVIDIA Kit App Template
        ↓
custom opengrowtwin.my_editor application
        ↓
headless Kit startup
        ↓
app ready + RTX ready
```

The tested deployment was:

| Component | Verified configuration |
|---|---|
| Zone | `us-central1-b` |
| Machine type | `g2-standard-8` |
| GPU | 1 × NVIDIA L4 |
| CPU / RAM | 8 vCPUs / 32 GB |
| Disk | 100 GB balanced persistent disk |
| OS | Ubuntu 22.04.5 LTS, x86-64 |
| NVIDIA driver | 610.57.04 |
| GPU memory reported | 23,034 MiB |
| Kit app | `opengrowtwin.my_editor` 0.1.0 |
| Kit result | `app ready` |
| RTX result | `RTX ready` |

The first RTX initialization took approximately 5.5 minutes, consistent with
first-run shader and cache preparation.

## 3. Why this cloud configuration was selected

The official Omniverse Development Workstation image was investigated, but its
displayed default was approximately 48 vCPUs, 180 GB RAM, an NVIDIA RTX PRO
6000, 512 GB storage, and a GRID license. The displayed continuous-use estimate
was approximately EUR 1,678 per month before applicable discounts.

That workstation is far larger than this MVP requires. OpenGrowTwin uses:

- Python/NumPy for deterministic photon-domain calculations;
- OpenUSD for the exchange contract between science and visualization;
- Kit for the application runtime and integration layer;
- NVIDIA RTX for interactive or headless visualization.

The `g2-standard-8` therefore provides a practical competition baseline: an L4
with enough memory for Kit/RTX, without paying for workstation-scale CPU, RAM,
storage, or licensing.

## 4. Preconditions

Before provisioning, install and authenticate the Google Cloud CLI on the
local workstation:

```bash
sudo snap install google-cloud-cli --classic
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

The project needs:

- Compute Engine enabled;
- global GPU quota of at least one;
- regional NVIDIA L4 quota of at least one;
- available G2/L4 capacity in the selected zone;
- permission to create Compute Engine instances.

G2 machine types already include their L4 accelerator. Do not add a separate
`--accelerator` flag to the tested `g2-standard-8` command.

## 5. Quota and capacity checks

The project initially reported:

```text
GPUS_ALL_REGIONS
limit: 0
usage: 0
```

Although the `europe-west3` regional L4 quota was already one, the global GPU
limit prevented VM creation. A request to raise `GPUS_ALL_REGIONS` to one was
submitted and approved.

After quota approval, the following European zones returned capacity errors:

- `europe-west3-a` and `europe-west3-b` — Frankfurt;
- `europe-west4-a`, `europe-west4-b`, and `europe-west4-c` — Netherlands;
- `europe-west1-c` — Belgium.

The representative failure was:

```text
ZONE_RESOURCE_POOL_EXHAUSTED
state: STOCKOUT
resource type: compute
```

This means the configuration and quotas may be valid while physical capacity
is temporarily unavailable. Because geographic latency was not critical for
the build and headless-render workflow, the fallback was `us-central1-b`
rather than a lower-tier GPU.

## 6. Provision the tested VM

Create the instance from the authenticated local workstation or Cloud Shell:

```bash
VM_NAME=opengrowtwin-gpu

gcloud compute instances create "$VM_NAME" \
  --zone=us-central1-b \
  --machine-type=g2-standard-8 \
  --maintenance-policy=TERMINATE \
  --image-project=ubuntu-os-cloud \
  --image-family=ubuntu-2204-lts \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-balanced \
  --network=default
```

Expected instance summary:

```text
NAME: opengrowtwin-gpu
ZONE: us-central1-b
MACHINE_TYPE: g2-standard-8
STATUS: RUNNING
```

Connect to it:

```bash
gcloud compute ssh "$VM_NAME" --zone=us-central1-b
```

## 7. Verify the host and NVIDIA stack

Inspect the base system:

```bash
hostnamectl
df -h /
lspci | grep -i nvidia
```

The tested VM reported Ubuntu 22.04.5, kernel `6.8.0-1066-gcp`, x86-64, and
the NVIDIA device on PCIe. The standard Ubuntu image exposed the hardware but
did not initially provide a working `nvidia-smi`; the NVIDIA driver still had
to be installed.

After driver installation, verify the actual runtime rather than relying only
on the PCIe device:

```bash
nvidia-smi
```

The verified session reported:

```text
NVIDIA-SMI 610.57.04
GPU 0: NVIDIA L4
Memory: 23034 MiB
```

Do not proceed to Kit until `nvidia-smi` succeeds.

## 8. Bootstrap NVIDIA Kit App Template

On the VM, clone NVIDIA's Kit App Template into the project workspace:

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/NVIDIA-Omniverse/kit-app-template.git
cd kit-app-template
```

Bootstrap Packman and verify the repository toolchain:

```bash
./repo.sh --help
```

In the tested session this initialized Repo Tool / `repoman` 2.9.3 and exposed
the required commands, including `build`, `launch`, `test`, `template`, `usd`,
and `package`.

The Kit template remains governed by NVIDIA's own software terms. The
Apache-2.0 license in OpenGrowTwin applies to entrant-owned project code, not
to NVIDIA Kit or the template repository.

## 9. Create the dedicated OpenGrowTwin Kit app

From `~/projects/kit-app-template`, start the template wizard:

```bash
./repo.sh template new
```

Use these selections:

```text
Create: Application
Template: Kit Base Editor
Application .kit name: opengrowtwin.my_editor
Display name: OpenGrowTwin
Version: 0.1.0
Application layers: No
```

The wizard should create:

```text
source/apps/opengrowtwin.my_editor.kit
```

This gives the project its own Kit application identity rather than modifying
an undifferentiated sample app.

## 10. Build and run the infrastructure smoke test

Build the application:

```bash
cd ~/projects/kit-app-template
./repo.sh build
```

Launch through the repository tool and select `opengrowtwin.my_editor`:

```bash
./repo.sh launch
```

For a headless cloud session, window-related warnings such as these are
expected:

```text
Cannot setup ExternalDragDrop without a default window
Hotkeys cannot be setup without a default window
```

They are not success criteria and should not be ignored blindly. The run only
passes when the same log subsequently contains both:

```text
app ready
RTX ready
```

The verified Day 1 log contained:

```text
[15.294s] app ready
[328.696s] RTX ready
```

## 11. Acceptance checklist

| Gate | Result in tested session | How to verify |
|---|---:|---|
| Global and regional GPU quota | Pass | GCP quota page or CLI |
| G2/L4 instance provisioned | Pass | `gcloud compute instances describe` |
| Ubuntu host available | Pass | `hostnamectl` |
| NVIDIA device visible | Pass | `lspci` |
| Driver and L4 runtime valid | Pass | `nvidia-smi` |
| Kit template bootstrapped | Pass | `./repo.sh --help` |
| Dedicated app scaffolded | Pass | application `.kit` file exists |
| Application builds | Pass | `./repo.sh build` exits successfully |
| Kit runtime starts | Pass | log contains `app ready` |
| RTX initializes | **Pass** | log contains `RTX ready` |

The gate is not passed merely because the VM exists or because `lspci` finds
an NVIDIA device. Both Kit and RTX readiness are required.

## 12. Troubleshooting and decisions

### Global GPU quota is zero

**Symptom:** `GPUS_ALL_REGIONS limit: 0`.

**Resolution:** request a global GPU quota of at least one. Regional L4 quota
alone is insufficient.

### G2 reports `STOCKOUT`

**Symptom:** `ZONE_RESOURCE_POOL_EXHAUSTED` even though quota is available.

**Resolution:** try another G2-supported zone. This is a capacity condition,
not evidence that the machine command or quota is wrong.

### `nvidia-smi` is unavailable

**Symptom:** the L4 appears in `lspci`, but the driver utility is missing or
cannot communicate with the GPU.

**Resolution:** install a compatible NVIDIA driver, reboot if required, and do
not continue until `nvidia-smi` identifies the L4.

### Headless window warnings

**Symptom:** drag-and-drop or hotkey warnings refer to a missing default
window.

**Resolution:** for the headless smoke test, judge the run by later `app ready`
and `RTX ready` messages. A window-dependent exception or a missing readiness
message is still a failure.

### First RTX startup appears stalled

The verified first initialization took roughly 329 seconds. Allow time for
shader/cache preparation before terminating the first run. Later runs should
benefit from the populated cache.

## 13. Cost-control workflow

GPU compute is billed while the VM is running. Keep CPU-side development,
tests, documentation, and most OpenUSD authoring local, and start the L4 only
for Kit/RTX work.

Stop the VM:

```bash
VM_NAME=opengrowtwin-gpu
gcloud compute instances stop "$VM_NAME" --zone=us-central1-b
```

Restart it:

```bash
gcloud compute instances start "$VM_NAME" --zone=us-central1-b
```

Stopping the instance does not delete its persistent boot disk. Review current
Google Cloud pricing and disk/IP charges before treating a stopped VM as
cost-free.

## 14. What Day 1 proves—and what it does not

Day 1 supports the following competition claims:

- OpenGrowTwin has a dedicated NVIDIA Kit application;
- the application builds and starts on a Google Cloud NVIDIA L4;
- the NVIDIA driver, Vulkan/RTX stack, and Kit runtime reach readiness in a
  headless cloud environment;
- the project can use a smaller, task-appropriate G2 instance instead of a
  workstation-scale marketplace image;
- quota, regional stock, and headless-runtime risks were tested early rather
  than deferred to submission day.

Day 1 alone does **not** prove:

- correct PPFD, DLI, or spectral calculations;
- successful OpenUSD result exchange;
- rendering of scientific output;
- an interactive application workflow;
- biological validity or measured agreement with a physical chamber;
- production deployment or end-user streaming.

Those scientific and integration claims begin with the
[Day 2 science, OpenUSD, and headless RTX guide](day-2-science-openusd-rtx.md).

## 15. Competition-facing narrative

Day 1 retired the largest infrastructure uncertainty in the seven-day MVP:
whether OpenGrowTwin could run a custom NVIDIA Kit/RTX application on an
affordable, on-demand cloud GPU. The answer was yes.

The result also validated the project's central engineering decision. Numeric
horticultural-lighting results can remain deterministic, testable, and
portable in Python, while OpenUSD provides a transparent bridge into Kit and
RTX. This makes the entry accessible to CPU-only contributors and still uses
NVIDIA technology for the visualization and digital-twin layer where it adds
the most value.

## 16. Evidence to preserve

For the final submission or audit trail, retain:

- the G2 machine-type description;
- global and regional quota confirmation;
- representative European `STOCKOUT` output;
- the successful instance creation record;
- `hostnamectl`, disk, and `lspci` output;
- the successful `nvidia-smi` output;
- Kit template bootstrap output;
- the `opengrowtwin.my_editor` creation record;
- the build result;
- the log lines containing `app ready` and `RTX ready`.

Together, these establish the reproducible infrastructure chain. The Day 2
guide adds the scientific outputs, OpenUSD validation, and non-empty PNG/EXR
RTX renders that complete the first end-to-end vertical slice.
