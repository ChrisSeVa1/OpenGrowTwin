# OpenGrowTwin

OpenGrowTwin is an evidence-driven spectral-lighting digital twin for controlled-environment horticulture. It combines an auditable photon-domain solver with OpenUSD/NVIDIA Omniverse visualization.

The MVP deliberately separates the science from rendering:

- `opengrow` computes spectral photon flux, PPFD, DLI, spatial uniformity, and far-red photon flux.
- OpenUSD/Omniverse consumes the result files and displays the chamber and heatmap.
- Biological targets are traceable reference treatments, not universal growth optima.

## Quick start

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
opengrow simulate demo/design.json \
  --target data/targets/phalaenopsis_reference.yaml \
  --out build/results
```

The command writes `ppfd.npy`, `band_ppfd.npy`, `spectral_irradiance.npy`, `metrics.json`, and `result.json`.

## Scientific scope

The current solver models direct light from point emitters with cosine beam falloff and inverse-square attenuation. Reflections, canopy interception, thermal effects, plant growth, and spectral rendering validation are outside the MVP. Far-red (730 nm) is reported separately and is not included in 400–700 nm PPFD.

The bundled Phalaenopsis target reproduces a published reference treatment of approximately 200 µmol/m²/s for 14 hours/day with a 40% blue / 60% red photon fraction. It is not presented as an optimal orchid spectrum.

## Project layout

- `src/opengrow/physics/` — photon conversion, direct solver, and metrics
- `data/` — LED metadata and evidence-based targets
- `demo/` — deterministic example design and OpenUSD placeholder scene
- `tests/` — analytical scientific validation
- `exts/opengrow.twin/` — Omniverse Kit integration boundary
- `docs/` — architecture and GCP/Kit reproducibility notes

## License

OpenGrowTwin code is licensed under Apache-2.0. NVIDIA software, manufacturer data, research literature, and other dependencies retain their respective terms; see `THIRD_PARTY_NOTICES.md`.
