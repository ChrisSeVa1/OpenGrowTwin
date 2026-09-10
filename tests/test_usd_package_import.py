"""Regression coverage for Kit's intentionally small Python environment."""

from __future__ import annotations

import builtins
import importlib
import sys


def test_stage_reader_import_does_not_require_matplotlib(monkeypatch):
    original_import = builtins.__import__

    def import_without_matplotlib(name, *args, **kwargs):
        if name == "matplotlib" or name.startswith("matplotlib."):
            raise ModuleNotFoundError("simulated Kit environment: no matplotlib")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_matplotlib)
    for name in list(sys.modules):
        if name == "opengrow.usd" or name.startswith("opengrow.usd."):
            sys.modules.pop(name)

    module = importlib.import_module("opengrow.usd.stage_reader")
    assert callable(module.discover_stage)
