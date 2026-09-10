#!/usr/bin/env python3
"""Run non-executing OGT-203 tool-call acceptance against a live model."""

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


CASES = (
    ("list_targets", {}, "List the approved evidence-backed plant-lighting targets."),
    (
        "get_target",
        {"target_id": "phalaenopsis_ouzounis_2015_reference"},
        "Retrieve the approved Phalaenopsis Ouzounis 2015 reference target, including its citation and limitations.",
    ),
    ("inspect_scene", {}, "Inspect and summarize the currently active OpenUSD scene."),
    (
        "get_metrics",
        {"run_id": "run_baseline"},
        "Return the deterministic solver metrics for recorded run run_baseline.",
    ),
    (
        "get_occlusion_summary",
        {"run_id": "run_candidate"},
        "Return the blocked-ray occlusion diagnostics for recorded run run_candidate.",
    ),
    (
        "run_simulation",
        {"mode": "preview"},
        "Run the deterministic solver using the current scene in preview mode.",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--api-key")
    args = parser.parse_args()

    client = ModelServiceClient(
        endpoint=args.endpoint,
        model=args.model,
        timeout_s=args.timeout_s,
        api_key=args.api_key,
    )
    report: dict = {
        "endpoint": args.endpoint,
        "model": args.model,
        "executes_tools": False,
        "health": None,
        "cases": [],
    }
    try:
        report["health"] = client.health()
        for expected_name, expected_arguments, prompt in CASES:
            record = {
                "expected_name": expected_name,
                "expected_arguments": expected_arguments,
                "prompt": prompt,
            }
            try:
                call = client.request_tool_call(prompt)
                record["actual"] = asdict(call)
                record["passed"] = (
                    call.name == expected_name
                    and call.arguments == expected_arguments
                )
            except ModelServiceError as exc:
                record["passed"] = False
                record["error"] = str(exc)
            report["cases"].append(record)
    except ModelServiceError as exc:
        report["health_error"] = str(exc)

    report["passed"] = (
        report["health"] == {"status": "ok"}
        and len(report["cases"]) == len(CASES)
        and all(case["passed"] for case in report["cases"])
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
