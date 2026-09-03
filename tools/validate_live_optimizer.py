#!/usr/bin/env python3
"""Emit a deterministic OGT-302 proposal validation artifact."""

from __future__ import annotations

import json
from pathlib import Path

from opengrow.optimize.live_optimizer import build_optimizer_proposal, load_reference_target


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = "/World/GrowInstallation/Fixtures/Fixture_01"


def main() -> int:
    design = json.loads((ROOT / "demo" / "design.json").read_text(encoding="utf-8"))
    labels = {"blue": "Blue", "red": "Red", "far_red": "FarRed"}
    for channel in design["channels"]:
        for index, emitter in enumerate(channel["emitters"], start=1):
            emitter["source_path"] = (
                f"{FIXTURE_PATH}/Emitters/{labels[channel['id']]}_{index:02d}"
            )
    proposal = build_optimizer_proposal(
        design,
        load_reference_target(),
        fixture_path=FIXTURE_PATH,
        current_fixture_height_m=0.6,
    )
    artifact = {
        "task": "OGT-302",
        "validation": "live OpenUSD optimizer proposal bridge",
        "passed": (
            proposal["status"] == "proposal_only"
            and proposal["requires_explicit_confirmation"] is True
            and proposal["scene_changed"] is False
            and abs(proposal["predicted_metrics"]["mean_ppfd_umol_m2_s"] - 200.0) < 1e-9
        ),
        "proposal_id": proposal["proposal_id"],
        "target_id": proposal["target_id"],
        "fixture_path": proposal["fixture_path"],
        "before_fixture_height_m": proposal["before_fixture_height_m"],
        "after_fixture_height_m": proposal["after_fixture_height_m"],
        "channel_totals_w": {
            item["channel_id"]: {
                "before": item["before_total_radiant_power_w"],
                "after": item["after_total_radiant_power_w"],
            }
            for item in proposal["channel_changes"]
        },
        "predicted_metrics": proposal["predicted_metrics"],
        "mutation_before_confirmation": proposal["scene_changed"],
        "explicit_confirmation_required": proposal["requires_explicit_confirmation"],
    }
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0 if artifact["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
