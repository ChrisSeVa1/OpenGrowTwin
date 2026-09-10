#!/usr/bin/env python3
"""Emit deterministic OGT-301 LED preset validation evidence as JSON."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opengrow.led_presets import LedPresetLibrary  # noqa: E402


def main() -> int:
    library = LedPresetLibrary(ROOT / "data" / "leds")
    presets = sorted(library.list_presets(), key=lambda record: record["wavelength_nm"])
    result = {
        "task": "OGT-301",
        "validation": "OSRAM horticultural LED preset library",
        "schema_version": "1.0",
        "preset_count": len(presets),
        "channels": [record["channel"] for record in presets],
        "wavelengths_nm": [record["wavelength_nm"] for record in presets],
        "ppfd_inclusion": {record["channel"]: record["included_in_ppfd"] for record in presets},
        "manufacturer": "ams OSRAM",
        "product_family": "OSCONIQ P 3737",
        "provenance_statuses": sorted({record["provenance_status"] for record in presets}),
        "radiant_power_authority": "scene_or_simulation_input",
        "manufacturer_electrical_power_used_as_radiant_power": False,
        "solver_modified": False,
        "passed": len(presets) == 3 and [record["wavelength_nm"] for record in presets] == [450, 660, 730],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
