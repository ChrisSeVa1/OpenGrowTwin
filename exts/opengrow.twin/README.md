# `opengrow.twin` Kit extension

This Kit extension provides the OGT-104 live simulation controller while the
scientific engine remains independently executable and testable.

The **OpenGrowTwin** window provides preview/final grid selection, Simulate and
Cancel actions, status/error reporting, and summary metrics. USD changes below
`/World/GrowInstallation` are debounced before an automatic preview run. Stage
reading stays on Kit's main thread; NumPy simulation runs in a worker so the
viewport remains responsive.

Launch from Kit App Template with this repository as an extension folder:

```bash
kit opengrowtwin.my_editor.kit \
  --ext-folder ~/projects/OpenGrowTwin/exts \
  --enable opengrow.twin
```
