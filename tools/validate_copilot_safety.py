#!/usr/bin/env python3
"""OGT-206 deterministic adversarial regressions for the copilot boundary."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opengrow.copilot.contracts import (  # noqa: E402
    ConfirmationStore,
    ContractError,
    validate_tool_call,
)


BASE = {
    "fixture_id": "fixture_01",
    "channel_id": "blue",
    "radiant_power_w": 4.5,
}


def expect_rejected(case_id, operation, contains):
    try:
        operation()
    except (ContractError, ValueError) as exc:
        message = str(exc)
        return {
            "id": case_id,
            "passed": contains in message,
            "error": message,
            "expected_error_contains": contains,
        }
    return {
        "id": case_id,
        "passed": False,
        "error": "operation was unexpectedly accepted",
        "expected_error_contains": contains,
    }


def main() -> int:
    cases = [
        expect_rejected(
            "arbitrary-tool",
            lambda: validate_tool_call("run_python", {"code": "print('unsafe')"}),
            "unknown tool",
        ),
        expect_rejected(
            "target-path-traversal",
            lambda: validate_tool_call(
                "get_target", {"target_id": "../../private/target.yaml"}
            ),
            "approved identifier",
        ),
        expect_rejected(
            "channel-power-out-of-bounds",
            lambda: validate_tool_call(
                "set_channel_power",
                {**BASE, "radiant_power_w": 1000.0, "confirmation_token": "x" * 32},
            ),
            "bounds",
        ),
        expect_rejected(
            "missing-confirmation",
            lambda: validate_tool_call("set_channel_power", BASE),
            "confirmation_token",
        ),
    ]

    changed_store = ConfirmationStore()
    changed_token = changed_store.issue("set_channel_power", BASE)
    cases.append(expect_rejected(
        "changed-confirmed-arguments",
        lambda: changed_store.consume(
            "set_channel_power",
            {**BASE, "radiant_power_w": 5.0, "confirmation_token": changed_token},
        ),
        "does not match",
    ))

    replay_store = ConfirmationStore()
    replay_token = replay_store.issue("set_channel_power", BASE)
    confirmed = {**BASE, "confirmation_token": replay_token}
    replay_store.consume("set_channel_power", confirmed)
    cases.append(expect_rejected(
        "confirmation-replay",
        lambda: replay_store.consume("set_channel_power", confirmed),
        "valid unused",
    ))

    now = [100.0]
    expired_store = ConfirmationStore(ttl_s=5.0, clock=lambda: now[0])
    expired_token = expired_store.issue("set_channel_power", BASE)
    now[0] = 106.0
    cases.append(expect_rejected(
        "expired-confirmation",
        lambda: expired_store.consume(
            "set_channel_power", {**BASE, "confirmation_token": expired_token}
        ),
        "expired",
    ))

    report = {
        "milestone": "OGT-206",
        "kind": "deterministic-safety",
        "executes_arbitrary_code": False,
        "cases": cases,
        "passed": all(case["passed"] for case in cases),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
