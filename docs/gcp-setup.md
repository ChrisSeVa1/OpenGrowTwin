# Google Cloud and NVIDIA Kit status

The Day 1 infrastructure gate has been passed on a Google Cloud G2 instance with one NVIDIA L4, 8 vCPUs, and 32 GB RAM.

Validated path:

1. Provision a G2/L4 VM in a zone with capacity.
2. Confirm the L4 is visible and install/verify the NVIDIA driver with `nvidia-smi`.
3. Clone and bootstrap NVIDIA Kit App Template.
4. Create the dedicated OpenGrowTwin Kit Base Editor application.
5. Start Kit headlessly.
6. Confirm both `app ready` and `RTX ready` in the Kit log.

G2 machine types already include the L4; a separate accelerator attachment is not required. Capacity errors encountered in European zones were stock limitations, not configuration failures. Expected headless warnings about ExternalDragDrop and hotkeys are non-fatal when Kit subsequently reports readiness.

The detailed chronological setup log remains project evidence and will be distilled further as the reproducible deployment scripts are added.
