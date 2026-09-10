from __future__ import annotations

import numpy as np

from .photons import dli_from_ppfd


def summarize(ppfd, far_red, photoperiod_h: float) -> dict[str, float]:
    field = np.asarray(ppfd, dtype=float)
    mean = float(field.mean())
    std = float(field.std())
    return {
        "mean_ppfd_umol_m2_s": mean,
        "min_ppfd_umol_m2_s": float(field.min()),
        "max_ppfd_umol_m2_s": float(field.max()),
        "uniformity_min_mean": float(field.min() / mean) if mean else 0.0,
        "cv_ppfd": float(std / mean) if mean else 0.0,
        "mean_far_red_umol_m2_s": float(np.asarray(far_red).mean()),
        "dli_mol_m2_day": float(dli_from_ppfd(mean, photoperiod_h)),
        "photoperiod_h": float(photoperiod_h),
    }
