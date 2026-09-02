#!/usr/bin/env python3
"""OGT-206 live routing and grounding regressions for the pinned open model."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opengrow.copilot.model_service import (  # noqa: E402
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    ModelServiceClient,
    ModelServiceError,
)


ROUTING_CASES = (
    {
        "id": "approved-target-list",
        "prompt": "List the approved evidence-backed plant-lighting targets.",
        "name": "list_targets",
        "arguments": {},
    },
    {
        "id": "approved-target-citation",
        "prompt": (
            "Retrieve the approved Phalaenopsis Ouzounis 2015 reference target, "
            "including its citation and limitations."
        ),
        "name": "get_target",
        "arguments": {"target_id": "phalaenopsis_ouzounis_2015_reference"},
    },
    {
        "id": "live-scene-inspection",
        "prompt": "Inspect and summarize the currently active OpenUSD scene.",
        "name": "inspect_scene",
        "arguments": {},
    },
    {
        "id": "recorded-metrics",
        "prompt": "Return deterministic solver metrics for recorded run run_0001.",
        "name": "get_metrics",
        "arguments": {"run_id": "run_0001"},
    },
    {
        "id": "occlusion-diagnostics",
        "prompt": "Return blocked-ray diagnostics for recorded run run_0001.",
        "name": "get_occlusion_summary",
        "arguments": {"run_id": "run_0001"},
    },
    {
        "id": "run-comparison",
        "prompt": "Compare baseline run run_0001 with candidate run run_0002.",
        "name": "compare_runs",
        "arguments": {
            "baseline_run_id": "run_0001",
            "candidate_run_id": "run_0002",
        },
    },
    {
        "id": "preview-simulation",
        "prompt": "Run the deterministic solver on the current scene in preview mode.",
        "name": "run_simulation",
        "arguments": {"mode": "preview"},
    },
    {
        "id": "unsigned-exact-mutation",
        "prompt": "Set the total blue-channel radiant power of fixture_01 to 4.5 watts.",
        "name": "set_channel_power",
        "arguments": {
            "fixture_id": "fixture_01",
            "channel_id": "blue",
            "radiant_power_w": 4.5,
        },
    },
)

GROUNDING_CASES = (
    {
        "id": "grounded-current-metric",
        "prompt": "What is the mean PPFD for run_0001?",
        "call": {
            "name": "get_metrics",
            "arguments": {"run_id": "run_0001"},
        },
        "output": {
            "run_id": "run_0001",
            "metrics": {"mean_ppfd_umol_m2_s": 31.08},
        },
        "required": ("31.08",),
        "forbidden": ("100–500", "100-500", "typical"),
    },
    {
        "id": "grounded-evidence-limitation",
        "prompt": "Give the DOI and one limitation of the approved reference.",
        "call": {
            "name": "get_target",
            "arguments": {"target_id": "phalaenopsis_ouzounis_2015_reference"},
        },
        "output": {
            "citation": {"doi": "10.1111/ppl.12300"},
            "limitation": "The treatment is not a universal spectral optimum.",
        },
        "required": ("10.1111/ppl.12300", "not a universal"),
        "forbidden": ("proven optimum", "guaranteed"),
    },
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    args = parser.parse_args()
    client = ModelServiceClient(
        endpoint=args.endpoint,
        model=args.model,
        timeout_s=args.timeout_s,
    )
    report = {
        "milestone": "OGT-206",
        "endpoint": args.endpoint,
        "model": args.model,
        "executes_tools": False,
        "health": None,
        "routing": [],
        "grounding": [],
    }
    try:
        report["health"] = client.health()
        for case in ROUTING_CASES:
            record = {"id": case["id"], "prompt": case["prompt"]}
            try:
                call = client.request_tool_call(case["prompt"])
                record["actual"] = asdict(call)
                record["passed"] = (
                    call.name == case["name"]
                    and call.arguments == case["arguments"]
                    and "confirmation_token" not in call.arguments
                )
            except ModelServiceError as exc:
                record.update(passed=False, error=str(exc))
            report["routing"].append(record)

        from opengrow.copilot.model_service import ModelToolCall

        for case in GROUNDING_CASES:
            call = ModelToolCall(
                call_id=f"regression-{case['id']}",
                name=case["call"]["name"],
                arguments=case["call"]["arguments"],
                latency_s=0.0,
                usage={},
                timings={},
            )
            record = {"id": case["id"], "prompt": case["prompt"]}
            try:
                answer = client.request_grounded_answer(
                    case["prompt"], call, case["output"]
                )
                lowered = answer.content.lower()
                required = all(text.lower() in lowered for text in case["required"])
                forbidden = all(text.lower() not in lowered for text in case["forbidden"])
                record["actual"] = asdict(answer)
                record["passed"] = required and forbidden
            except ModelServiceError as exc:
                record.update(passed=False, error=str(exc))
            report["grounding"].append(record)
    except ModelServiceError as exc:
        report["health_error"] = str(exc)

    cases = report["routing"] + report["grounding"]
    report["passed"] = (
        report["health"] == {"status": "ok"}
        and len(cases) == len(ROUTING_CASES) + len(GROUNDING_CASES)
        and all(case["passed"] for case in cases)
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
