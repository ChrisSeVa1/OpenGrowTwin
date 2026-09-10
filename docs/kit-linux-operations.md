# Linux operations guide — NVIDIA Kit + OpenGrowTwin

This guide is the operational reference for starting, stopping, validating, and troubleshooting OpenGrowTwin on a Linux NVIDIA GPU host. It assumes the Google Cloud/NVIDIA setup in [`reproduce-on-google-cloud.md`](reproduce-on-google-cloud.md) has already been completed.

## 1. Expected directory layout

The validated layout keeps NVIDIA Kit and OpenGrowTwin as separate checkouts:

```text
$HOME/projects/
├── kit-app-template/
└── OpenGrowTwin/
```

The important paths are:

```text
KIT_ROOT=$HOME/projects/kit-app-template
OGT_ROOT=$HOME/projects/OpenGrowTwin
KIT_EXE=$KIT_ROOT/_build/linux-x86_64/release/kit/kit
OGT_APP=$KIT_ROOT/_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit
OGT_EXTS=$OGT_ROOT/exts
```

Verify them before troubleshooting anything else:

```bash
test -x "$KIT_EXE" && echo "Kit executable OK"
test -f "$OGT_APP" && echo "OpenGrowTwin app OK"
test -d "$OGT_EXTS/opengrow.twin" && echo "OpenGrowTwin extension OK"
```

## 2. Build Kit

From the Kit App Template checkout:

```bash
cd "$HOME/projects/kit-app-template"
./repo.sh build
```

A successful build should leave the release tree under:

```text
_build/linux-x86_64/release/
```

If the application was not created yet, run:

```bash
./repo.sh template new
```

The OpenGrowTwin application used during validation was created with:

```text
Create: Application
Template: Kit Base Editor
Application .kit name: opengrowtwin.my_editor
Display name: OpenGrowTwin
Version: 0.1.0
Application layers: No
```

NVIDIA's current Kit App Template documentation is available at:

- https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/docs/intro.html
- https://github.com/NVIDIA-Omniverse/kit-app-template

## 3. Launch methods

### Method A — interactive repo launcher

```bash
cd "$HOME/projects/kit-app-template"
./repo.sh launch
```

Select `opengrowtwin.my_editor` when prompted.

This is convenient during development but is less explicit than the direct CLI form below.

### Method B — direct Linux CLI launch

This is the preferred reproducible launch command because every path and extension is visible:

```bash
cd "$HOME/projects/kit-app-template"

./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --ext-folder "$HOME/projects/OpenGrowTwin/exts" \
  --enable opengrow.twin
```

Expected startup markers include:

```text
[ext: opengrow.twin-0.1.0] startup
[OpenGrowTwin] Interactive simulation extension ready
[ext: opengrowtwin.my_editor-0.1.0] startup
app ready
RTX ready
```

`app ready` proves the Kit application initialized; `RTX ready` proves the RTX renderer completed initialization. Treat both as separate gates.

### Method C — direct headless validation

Headless execution is ideal for automated validators because it does not require X11:

```bash
cd "$HOME/projects/kit-app-template"

./_build/linux-x86_64/release/kit/kit \
  ./_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit \
  --no-window \
  --ext-folder "$HOME/projects/OpenGrowTwin/exts" \
  --enable opengrow.twin \
  --exec "$HOME/projects/OpenGrowTwin/tools/kit_validate_orchestration.py"
```

Replace the script after `--exec` with the validator you want to run. See [`validation-guide.md`](validation-guide.md).

## 4. Useful shell variables / command shortcuts

Rather than repeatedly typing long paths, add these to the current shell:

```bash
export OGT_ROOT="$HOME/projects/OpenGrowTwin"
export KIT_ROOT="$HOME/projects/kit-app-template"
export KIT_EXE="$KIT_ROOT/_build/linux-x86_64/release/kit/kit"
export OGT_APP="$KIT_ROOT/_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit"
```

Then launch OpenGrowTwin with:

```bash
"$KIT_EXE" "$OGT_APP" \
  --ext-folder "$OGT_ROOT/exts" \
  --enable opengrow.twin
```

For a temporary personal shell shortcut, you may define:

```bash
alias ogt-kit='"$KIT_EXE" "$OGT_APP" --ext-folder "$OGT_ROOT/exts" --enable opengrow.twin'
```

Because shell aliases do not reliably expand nested variables in every quoting arrangement, a small shell function is safer:

```bash
ogt-kit() {
  "$KIT_EXE" "$OGT_APP" \
    --ext-folder "$OGT_ROOT/exts" \
    --enable opengrow.twin "$@"
}
```

Now:

```bash
ogt-kit
ogt-kit --no-window
```

These shortcuts are convenience only; the full commands remain the reproducibility reference.

## 5. Start the project Python environment

OpenGrowTwin's normal Python dependencies are separate from Kit Python:

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate
python -m pytest -q
```

Important: installing a package in `.venv` does **not** make it available inside Kit's embedded Python runtime. Do not debug a Kit `ModuleNotFoundError` by repeatedly installing into the project virtual environment.

## 6. Make the development extension visible to Kit

The preferred launch method passes the repository extension folder directly:

```text
--ext-folder $HOME/projects/OpenGrowTwin/exts
--enable opengrow.twin
```

The original development environment also used a machine-local symlink into the Kit release `exts` directory. That method works, but the explicit `--ext-folder` launch is easier for another developer to reproduce and does not modify the Kit build tree.

If you intentionally use the symlink approach:

```bash
ln -s \
  "$HOME/projects/OpenGrowTwin/exts/opengrow.twin" \
  "$HOME/projects/kit-app-template/_build/linux-x86_64/release/exts/opengrow.twin"
```

Do not commit machine-local symlinks as project source.

## 7. Graphical Kit on a headless Google Cloud GPU VM

A headless G2 VM has a GPU but no desktop session. The validated graphical path used:

```text
NVIDIA L4
  ↓
NVIDIA Xorg :1
  ↓
Openbox
  ↓
x11vnc bound to 127.0.0.1:5901
  ↓
SSH tunnel
  ↓
local VNC client
```

The VNC port is never opened publicly.

### 7.1 Install the minimal graphical packages

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
command -v glxinfo
```

### 7.2 Identify the GPU bus

```bash
nvidia-smi
lspci | grep -i nvidia
```

The validated VM used PCI bus `PCI:0:3:0`, but **do not copy that value blindly**. Use the value from your machine.

### 7.3 Generate NVIDIA Xorg configuration

Example using the validated bus:

```bash
sudo nvidia-xconfig \
  --allow-empty-initial-configuration \
  --virtual=1920x1080 \
  --busid=PCI:0:3:0
```

Back up `/etc/X11/xorg.conf` before manual edits.

A key lesson from the tested environment: `UseDisplayDevice "None"` conflicted with the virtual display. The working configuration used an emulated connected display (`DFP-0`) and `AllowEmptyInitialConfiguration`.

### 7.4 Start Xorg

For a temporary session:

```bash
sudo systemd-run \
  --unit=opengrow-xorg \
  /usr/bin/Xorg :1 \
  -config /etc/X11/xorg.conf \
  -noreset \
  -nolisten tcp \
  -ac
```

Validate GPU-backed OpenGL:

```bash
DISPLAY=:1 glxinfo -B
DISPLAY=:1 xrandr
```

Success requires output equivalent to:

```text
direct rendering: Yes
OpenGL vendor string: NVIDIA Corporation
OpenGL renderer string: NVIDIA L4/PCIe/SSE2
```

A UI displayed through software rendering does not prove the NVIDIA graphical path.

### 7.5 Start Openbox

In a persistent terminal/session:

```bash
DISPLAY=:1 dbus-run-session -- openbox-session
```

### 7.6 Configure x11vnc

Create a password interactively; never store the password in documentation or Git:

```bash
mkdir -p "$HOME/.vnc"
x11vnc -storepasswd "$HOME/.vnc/passwd"
chmod 600 "$HOME/.vnc/passwd"
```

Start VNC on loopback only:

```bash
x11vnc \
  -display :1 \
  -rfbauth "$HOME/.vnc/passwd" \
  -rfbport 5901 \
  -localhost \
  -forever \
  -shared
```

Confirm:

```bash
ss -ltnp | grep ':5901'
```

The listener should resolve to loopback, not `0.0.0.0`.

### 7.7 Tunnel VNC from the workstation

Run this on your **local workstation**, not on the VM:

```bash
gcloud compute ssh <vm-name> \
  --zone=<zone> \
  -- \
  -N \
  -L 5901:127.0.0.1:5901
```

Keep that terminal open and connect your VNC client to:

```text
127.0.0.1:5901
```

No Google Cloud firewall rule for port 5901 is required.

### 7.8 Launch Kit on the graphical display

```bash
cd "$HOME/projects/kit-app-template"
DISPLAY=:1 ./repo.sh launch
```

Or explicitly:

```bash
DISPLAY=:1 \
"$HOME/projects/kit-app-template/_build/linux-x86_64/release/kit/kit" \
"$HOME/projects/kit-app-template/_build/linux-x86_64/release/apps/opengrowtwin.my_editor.kit" \
  --ext-folder "$HOME/projects/OpenGrowTwin/exts" \
  --enable opengrow.twin
```

## 8. Starting the local Nemotron service beside Kit

Use a separate terminal on the GPU VM:

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate
tools/run_nemotron_service.sh
```

Verify before launching/using the copilot UI:

```bash
curl -sS http://127.0.0.1:8080/health
echo
sudo ss -ltnp 'sport = :8080'
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

The tested model service occupied roughly 3 GB of L4 VRAM, leaving enough capacity for the validated Kit/RTX workflow.

## 9. Stop everything cleanly

Stop Kit and the model server with `Ctrl+C` in their owning terminals.

If you created persistent graphical services in your environment, the tested service names were:

```bash
systemctl --user stop opengrow-vnc opengrow-openbox 2>/dev/null || true
sudo systemctl stop opengrow-xorg 2>/dev/null || true
```

For a `systemd-run` temporary Xorg unit:

```bash
sudo systemctl stop opengrow-xorg
```

Verify no unintended listeners remain:

```bash
ss -ltnp | grep -E ':5901|:8080' || true
nvidia-smi
```

Then stop the VM from the workstation:

```bash
gcloud compute instances stop <vm-name> --zone=<zone>
```

Stopping the VM—not merely closing Kit—is the action that stops Compute Engine VM usage charges. Persistent disks and other retained resources can still incur charges.

## 10. Common failures

| Symptom | Likely cause | Check/fix |
| --- | --- | --- |
| `File doesn't exist` for the app | wrong `_build/.../apps` path | verify `OGT_APP` with `test -f` |
| dependency solver cannot find `opengrow.twin` | extension folder not visible | add `--ext-folder "$OGT_ROOT/exts" --enable opengrow.twin` |
| `No module named yaml` inside Kit | project `.venv` and Kit Python are separate | package/remove the Kit runtime dependency; do not install only into `.venv` |
| `Connection refused` from copilot | model service not listening | check `/health` and port 8080 |
| `couldn't bind ... 8080` | another model server already owns the port | inspect listener and reuse/stop it deliberately |
| `no screens found` | Xorg/device/display mismatch | verify NVIDIA bus, xorg.conf and emulated display |
| OpenGL vendor is Mesa | software rendering | fix NVIDIA Xorg before claiming graphical GPU validation |
| VNC works but Kit has no RTX | graphical access alone does not establish renderer readiness | check Kit log for `RTX ready` |
| first RTX startup seems frozen | shader/cache initialization | allow the first run to finish; the validated first startup took several minutes |

## 11. Minimal operator cheat sheet

On the VM:

```bash
# GPU
nvidia-smi

# project tests
cd "$HOME/projects/OpenGrowTwin" && source .venv/bin/activate && python -m pytest -q

# model
cd "$HOME/projects/OpenGrowTwin" && tools/run_nemotron_service.sh

# graphical Kit
cd "$HOME/projects/kit-app-template" && DISPLAY=:1 ./repo.sh launch

# model health
curl -sS http://127.0.0.1:8080/health && echo
```

On the local workstation:

```bash
# VNC tunnel
gcloud compute ssh <vm-name> --zone=<zone> -- -N -L 5901:127.0.0.1:5901

# stop VM when done
gcloud compute instances stop <vm-name> --zone=<zone>
```

For exact scientific and AI acceptance tests, continue with [`validation-guide.md`](validation-guide.md).
