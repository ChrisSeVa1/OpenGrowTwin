# Phalaenopsis Ouzounis 2015 evidence package

This approved MVP package represents the 40% blue / 60% red treatment from
Ouzounis et al., *Physiologia Plantarum* 154(2), 314-327 (2015), DOI
`10.1111/ppl.12300`.

It is a reference lighting environment, not a universal orchid optimum. The
OpenGrowTwin mapping reproduces selected PPFD, photoperiod, and blue/red photon
fraction conditions with 450 nm and 660 nm narrowband approximations. It does
not recreate the original LED spectral distribution, background daylight,
greenhouse environment, or biological response.

`source.yaml` contains publication and experiment facts. `target.yaml` maps
approved source fields to the deterministic simulator. `claims.yaml` defines
the statements the copilot may make and the claims it must not make.
