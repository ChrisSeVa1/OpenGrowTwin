#!/usr/bin/env python3
"""Run one real, grounded OGT-204 evidence-tool conversation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opengrow.copilot import (  # noqa: E402
    ModelServiceClient,
    ToolExecutor,
    ValidatedToolLoop,
)
from opengrow.copilot.model_service import DEFAULT_ENDPOINT, DEFAULT_MODEL  # noqa: E402


PROMPT = (
    "Which publication supports the approved Phalaenopsis reference target? "
    "Give its DOI and explain one important limitation."
)
EXPECTED_TARGET = "phalaenopsis_ouzounis_2015_reference"
EXPECTED_DOI = "10.1111/ppl.12300"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key")
    args = parser.parse_args()

    client = ModelServiceClient(
        endpoint=args.endpoint,
        model=args.model,
        api_key=args.api_key,
    )
    result = ValidatedToolLoop(client, ToolExecutor()).run(PROMPT)
    answer_lower = result.answer.content.lower()
    passed = (
        result.call.name == "get_target"
        and result.call.arguments == {"target_id": EXPECTED_TARGET}
        and result.execution.output["source"]["citation"]["doi"] == EXPECTED_DOI
        and EXPECTED_DOI in result.answer.content
        and "optimal for all" not in answer_lower
        and "maximizes orchid growth" not in answer_lower
    )
    report = {
        "passed": passed,
        "prompt": PROMPT,
        "call": asdict(result.call),
        "execution": {
            "name": result.execution.name,
            "arguments": result.execution.arguments,
            "source_id": result.execution.output["source"]["source_id"],
            "doi": result.execution.output["source"]["citation"]["doi"],
        },
        "answer": asdict(result.answer),
        "executes_arbitrary_code": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
