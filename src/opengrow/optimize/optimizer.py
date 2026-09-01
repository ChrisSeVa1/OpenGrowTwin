"""Bounded, deterministic optimizer over channel power and fixture height."""

from __future__ import annotations

from copy import deepcopy

import numpy as np

from opengrow.physics.basis import channel_basis, design_at_height, reconstruct
from opengrow.physics.metrics import summarize


def _desired_par_contributions(target: dict, wavelengths: np.ndarray) -> np.ndarray:
    mean_target = float(target["target"]["mean_ppfd_umol_m2_s"])
    fractions = target["photon_fraction"]
    desired = np.zeros(len(wavelengths), dtype=float)
    for index, wavelength in enumerate(wavelengths):
        if 400 <= wavelength < 500:
            desired[index] = mean_target * float(fractions.get("blue_400_500", 0.0))
        elif 500 <= wavelength < 600:
            desired[index] = mean_target * float(fractions.get("green_500_600", 0.0))
        elif 600 <= wavelength <= 700:
            desired[index] = mean_target * float(fractions.get("red_600_700", 0.0))
    if not np.isclose(desired.sum(), mean_target):
        raise ValueError("target PAR photon fractions must sum to 1.0")
    return desired


def _channel_bounds(channel: dict) -> tuple[float, float]:
    bounds = channel.get("radiant_power_bounds_w", {})
    return float(bounds.get("min", 0.0)), float(
        bounds.get("max", sum(e["radiant_power_w"] for e in channel["emitters"]) * 10.0)
    )


def _set_channel_total_power(channel: dict, total_power_w: float) -> None:
    current = np.asarray([emitter["radiant_power_w"] for emitter in channel["emitters"]], dtype=float)
    weights = current / current.sum() if current.sum() else np.full(len(current), 1.0 / len(current))
    for emitter, power in zip(channel["emitters"], weights * total_power_w, strict=True):
        emitter["radiant_power_w"] = float(power)


def optimize_design(design: dict, target: dict, candidate_heights_m=None) -> dict:
    """Select height and bounded radiant powers using exact cached linear bases.

    At each height, channel powers reproduce the requested mean photon
    contributions where bounds permit. The selected candidate minimizes PPFD
    coefficient of variation, with target error as the primary penalty.
    """
    if candidate_heights_m is None:
        candidate_heights_m = design.get("optimization", {}).get(
            "candidate_heights_m", [0.4, 0.5, 0.6, 0.7, 0.8]
        )
    photoperiod = float(target["target"]["photoperiod_h"])
    power_weight = float(design.get("optimization", {}).get("radiant_power_weight", 0.35))
    par_power_capacity = sum(
        _channel_bounds(channel)[1]
        for channel in design["channels"]
        if 400 <= float(channel["wavelength_nm"]) <= 700
    )
    candidates = []
    for height in candidate_heights_m:
        candidate_design = design_at_height(design, float(height))
        basis = channel_basis(candidate_design)
        desired_means = _desired_par_contributions(target, basis["wavelengths_nm"])
        basis_means = basis["photon_per_radiant_w"].mean(axis=(1, 2))
        powers = np.zeros(len(candidate_design["channels"]), dtype=float)
        clipped = []
        for index, channel in enumerate(candidate_design["channels"]):
            low, high = _channel_bounds(channel)
            if desired_means[index] > 0:
                requested = desired_means[index] / basis_means[index]
            else:
                requested = sum(e["radiant_power_w"] for e in channel["emitters"])
            powers[index] = np.clip(requested, low, high)
            clipped.append(not np.isclose(powers[index], requested))
        fields = reconstruct(basis, powers)
        metrics = summarize(fields["ppfd"], fields["far_red"], photoperiod)
        target_error = abs(metrics["mean_ppfd_umol_m2_s"] - target["target"]["mean_ppfd_umol_m2_s"])
        par_power = float(powers[(basis["wavelengths_nm"] >= 400) & (basis["wavelengths_nm"] <= 700)].sum())
        target_error_fraction = target_error / target["target"]["mean_ppfd_umol_m2_s"]
        radiant_power_penalty = par_power / par_power_capacity
        score = target_error_fraction + metrics["cv_ppfd"] + power_weight * radiant_power_penalty
        candidates.append({
            "height_m": float(height),
            "powers_w": powers,
            "metrics": metrics,
            "score": float(score),
            "target_error_fraction": float(target_error_fraction),
            "radiant_power_penalty": float(radiant_power_penalty),
            "par_radiant_power_w": par_power,
            "clipped": clipped,
            "basis": basis,
            "fields": fields,
            "design": candidate_design,
        })
    best = min(candidates, key=lambda item: item["score"])
    optimized = deepcopy(best["design"])
    for channel, power in zip(optimized["channels"], best["powers_w"], strict=True):
        _set_channel_total_power(channel, float(power))
    return {
        "design": optimized,
        "height_m": best["height_m"],
        "channel_ids": best["basis"]["channel_ids"],
        "channel_radiant_power_w": best["powers_w"],
        "metrics": best["metrics"],
        "fields": best["fields"],
        "candidate_summary": [
            {
                "height_m": item["height_m"],
                "score": item["score"],
                "target_error_fraction": item["target_error_fraction"],
                "cv_ppfd": item["metrics"]["cv_ppfd"],
                "par_radiant_power_w": item["par_radiant_power_w"],
                "radiant_power_penalty": item["radiant_power_penalty"],
                "radiant_power_weight": power_weight,
                "mean_ppfd_umol_m2_s": item["metrics"]["mean_ppfd_umol_m2_s"],
                "channel_radiant_power_w": item["powers_w"].tolist(),
                "power_bound_active": item["clipped"],
            }
            for item in candidates
        ],
    }
