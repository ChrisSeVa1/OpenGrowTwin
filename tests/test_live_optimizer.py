import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from opengrow.optimize.live_optimizer import (
    LiveOptimizerError,
    apply_optimizer_proposal,
    build_optimizer_proposal,
)


FIXTURE_PATH = "/World/GrowInstallation/Fixtures/Fixture_01"


def _live_design():
    root = Path(__file__).parents[1]
    design = json.loads((root / "demo/design.json").read_text())
    counters = {}
    for channel in design["channels"]:
        counters[channel["id"]] = 0
        label = {"blue": "Blue", "red": "Red", "far_red": "FarRed"}[channel["id"]]
        for emitter in channel["emitters"]:
            counters[channel["id"]] += 1
            emitter["source_path"] = f"{FIXTURE_PATH}/Emitters/{label}_{counters[channel['id']]:02d}"
    return design


def _target():
    root = Path(__file__).parents[1]
    return yaml.safe_load((root / "data/targets/phalaenopsis_reference.yaml").read_text())


class FakeAttribute:
    def __init__(self, value):
        self.value = value

    def Get(self):
        return self.value

    def Set(self, value):
        self.value = value
        return True


class FakePrim:
    def __init__(self, attributes):
        self.attributes = attributes

    def GetAttribute(self, name):
        return self.attributes.get(name)

    def __bool__(self):
        return True


class FakeStage:
    def __init__(self, proposal):
        self.prims = {
            proposal["fixture_path"]: FakePrim({
                "xformOp:translate": FakeAttribute((0.0, 0.0, proposal["before_fixture_height_m"]))
            })
        }
        for channel in proposal["channel_changes"]:
            for emitter in channel["emitters"]:
                self.prims[emitter["path"]] = FakePrim({
                    "opengrow:radiantPowerW": FakeAttribute(emitter["before_radiant_power_w"])
                })

    def GetPrimAtPath(self, path):
        return self.prims.get(path)


def test_live_optimizer_proposal_is_non_mutating_and_reaches_target():
    design = _live_design()
    original = json.dumps(design, sort_keys=True)
    proposal = build_optimizer_proposal(
        design,
        _target(),
        fixture_path=FIXTURE_PATH,
        current_fixture_height_m=0.6,
    )
    assert json.dumps(design, sort_keys=True) == original
    assert proposal["status"] == "proposal_only"
    assert proposal["scene_changed"] is False
    assert proposal["requires_explicit_confirmation"] is True
    assert proposal["proposal_id"].startswith("opt_")
    assert proposal["predicted_metrics"]["mean_ppfd_umol_m2_s"] == pytest.approx(200.0)
    assert [item["channel_id"] for item in proposal["channel_changes"]] == ["blue", "red", "far_red"]


def test_live_optimizer_proposal_is_deterministic():
    kwargs = dict(
        design=_live_design(),
        target=_target(),
        fixture_path=FIXTURE_PATH,
        current_fixture_height_m=0.6,
    )
    first = build_optimizer_proposal(**kwargs)
    second = build_optimizer_proposal(**kwargs)
    assert first["proposal_id"] == second["proposal_id"]
    assert first == second


def test_live_optimizer_rejects_emitter_outside_fixture():
    design = _live_design()
    design["channels"][0]["emitters"][0]["source_path"] = "/World/Other/Emitter"
    with pytest.raises(LiveOptimizerError, match="fixture-local"):
        build_optimizer_proposal(
            design,
            _target(),
            fixture_path=FIXTURE_PATH,
            current_fixture_height_m=0.6,
        )


def test_apply_optimizer_proposal_changes_exact_reviewed_values():
    proposal = build_optimizer_proposal(
        _live_design(),
        _target(),
        fixture_path=FIXTURE_PATH,
        current_fixture_height_m=0.6,
    )
    stage = FakeStage(proposal)
    result = apply_optimizer_proposal(stage, proposal)
    assert result["scene_changed"] is True
    assert result["simulation_required"] is True
    assert result["emitter_updates"] == 20
    translation = stage.GetPrimAtPath(FIXTURE_PATH).GetAttribute("xformOp:translate").Get()
    assert translation[2] == pytest.approx(proposal["after_fixture_height_m"])
    for channel in proposal["channel_changes"]:
        for emitter in channel["emitters"]:
            actual = stage.GetPrimAtPath(emitter["path"]).GetAttribute("opengrow:radiantPowerW").Get()
            assert actual == pytest.approx(emitter["after_radiant_power_w"])


def test_apply_optimizer_proposal_rejects_stale_scene_without_mutation():
    proposal = build_optimizer_proposal(
        _live_design(),
        _target(),
        fixture_path=FIXTURE_PATH,
        current_fixture_height_m=0.6,
    )
    stage = FakeStage(proposal)
    first_emitter = proposal["channel_changes"][0]["emitters"][0]
    stage.GetPrimAtPath(first_emitter["path"]).GetAttribute("opengrow:radiantPowerW").Set(99.0)
    before_translation = stage.GetPrimAtPath(FIXTURE_PATH).GetAttribute("xformOp:translate").Get()
    with pytest.raises(LiveOptimizerError, match="changed since proposal creation"):
        apply_optimizer_proposal(stage, proposal)
    assert stage.GetPrimAtPath(FIXTURE_PATH).GetAttribute("xformOp:translate").Get() == before_translation


def test_apply_optimizer_proposal_rejects_unreviewed_record():
    proposal = build_optimizer_proposal(
        _live_design(),
        _target(),
        fixture_path=FIXTURE_PATH,
        current_fixture_height_m=0.6,
    )
    proposal = deepcopy(proposal)
    proposal["status"] = "applied"
    with pytest.raises(LiveOptimizerError, match="proposal_only"):
        apply_optimizer_proposal(FakeStage(proposal), proposal)
