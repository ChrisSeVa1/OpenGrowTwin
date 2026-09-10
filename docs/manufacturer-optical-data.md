# Reproduce the ams OSRAM manufacturer optical-data path

OpenGrowTwin can run with a public fallback optical model, while the manufacturer-backed configuration uses angular photometry and tabulated spectra for three ams OSRAM OSCONIQ™ P 3737 (2W) Batwing devices.

The raw manufacturer assets are **not** committed to this repository. This guide explains how another developer can locate the supplier pages, identify the correct devices, obtain the available optical-simulation downloads, extract the required IES/spectrum files locally, and verify that OpenGrowTwin recognizes them.

## 1. Exact devices used

| OpenGrowTwin channel | ams OSRAM part | Spectral role | Expected IES revision | Validated spectrum peak |
| --- | --- | --- | --- | ---: |
| Blue | `GD PUBRA1.15` | Deep Blue | 2025-05-29 | 446 nm |
| Red | `GH PUBRA1.25` | Hyper Red | 2025-05-26 | 680 nm |
| Far-red | `GF PUBRA1.25` | Far Red | 2025-06-03 | 742 nm |

Current official product pages:

- Blue — https://ams-osram.com/products/leds/color-leds/osram-osconiq-p-3737-2w-gd-pubra1-15
- Red — https://ams-osram.com/products/leds/color-leds/osram-osconiq-p-3737-2w-gh-pubra1-25
- Far-red — https://ams-osram.com/products/leds/color-leds/osram-osconiq-p-3737-2w-gf-pubra1-25

If a product URL changes, start at https://ams-osram.com/ and search the exact part number including punctuation, for example `GD PUBRA1.15`.

## 2. What to download from the supplier site

On each product page:

1. Confirm that the page title contains the exact part number.
2. Review the **Details / Parameters** section to confirm the emission family and beam-angle information.
3. Open **Downloads** and obtain the current datasheet for provenance/reference.
4. Under **Resources**, open **Optical Simulation**.
5. Download the optical-simulation packages offered for the exact device. Depending on the supplier page/revision, these may be exposed as IES, EULUMDAT, rayfile, or TracePro-text packages/folders.
6. Preserve the manufacturer filenames and archive revision/date. Do not rename the original ZIP archives until after you have recorded what was downloaded.

The reference set used by OpenGrowTwin included IES and EULUMDAT angular data plus a TraceProText package containing a tabulated relative spectrum.

### Why several formats exist

- **IES / LM-63**: angular intensity/flux distribution. OpenGrowTwin's manufacturer angular model uses Type-C IES.
- **EULUMDAT**: another photometry-distribution format; it can be used as an independent cross-check of the angular distribution.
- **TraceProText / rayfile package**: the reference packages included tabulated manufacturer relative spectral data used by OpenGrowTwin's wavelength-resolved photon conversion.
- **CAD**: mechanical CAD is useful for package geometry but should not automatically be treated as optical ray-tracing geometry.

The public OpenGrowTwin implementation does not require redistribution of any supplier file.

## 3. Local directory expected by OpenGrowTwin

Create this gitignored directory in the repository checkout:

```bash
cd "$HOME/projects/OpenGrowTwin"
mkdir -p sources/osram/extracted
```

The resolver in `src/opengrow/manufacturer_profiles.py` expects exactly six files in that directory:

```text
sources/osram/extracted/
├── GD_PUBRA1_15_20250529.ies
├── GD_PUBRA1_15_20250529_spectrum.txt
├── GH_PUBRA1_25_20250526.ies
├── GH_PUBRA1_25_20250526_spectrum.txt
├── GF_PUBRA1_25_20250603.ies
└── GF_PUBRA1_25_20250603_spectrum.txt
```

The six names are part of the current reference profile contract. If ams OSRAM publishes a newer revision, do **not** silently rename the newer data to look like the reference revision. Either reproduce the recorded set or update provenance and rerun the full validation suite for the newer revision.

## 4. Extract the archives

Keep original downloads outside Git-tracked paths. For example:

```bash
mkdir -p "$HOME/Downloads/osram-optics"
mkdir -p "$HOME/projects/OpenGrowTwin/sources/osram/extracted"
```

Inspect an archive before extracting it:

```bash
unzip -l /path/to/archive.zip
```

Extract into a temporary supplier-data directory:

```bash
mkdir -p "$HOME/Downloads/osram-optics/work"
unzip /path/to/archive.zip -d "$HOME/Downloads/osram-optics/work"
```

Locate candidate files:

```bash
find "$HOME/Downloads/osram-optics/work" -type f \
  \( -iname '*.ies' -o -iname '*.ldt' -o -iname '*spectrum*.txt' \) \
  -print
```

Copy only the six required files into `sources/osram/extracted/`, using the canonical filenames shown above.

Example:

```bash
cp /actual/extracted/path/to/blue.ies \
  "$HOME/projects/OpenGrowTwin/sources/osram/extracted/GD_PUBRA1_15_20250529.ies"
```

Repeat for the matching spectrum and the red/far-red devices.

## 5. How to identify the correct spectrum file

The reference TraceProText packages contained relative-spectrum text tables. Expected wavelength ranges and peaks are:

| Device | Reference wavelength coverage | Spacing | Reference peak |
| --- | --- | --- | ---: |
| `GD PUBRA1.15` | 380–510 nm | 2 nm | 446 nm |
| `GH PUBRA1.25` | 580–780 nm | 2 nm | 680 nm |
| `GF PUBRA1.25` | 600–800 nm | 2 nm | 742 nm |

Do not infer the spectrum merely from the LED's marketing color or nominal wavelength. The purpose of manufacturer mode is to use the tabulated relative spectral distribution rather than monochromatic spikes.

OpenGrowTwin labels this provenance as:

```text
manufacturer_tabulated_relative_spd
```

That wording is deliberate. Do not upgrade the claim to “direct measured SPD” unless supplier documentation explicitly establishes that measurement provenance.

## 6. Check that Git will not publish supplier assets

Before continuing:

```bash
cd "$HOME/projects/OpenGrowTwin"
git status --short
```

The supplier files under `sources/osram/` should not appear as staged/tracked files. Confirm ignore behavior:

```bash
git check-ignore -v sources/osram/extracted/GD_PUBRA1_15_20250529.ies
```

If Git does not report an ignore rule, stop and fix `.gitignore` before continuing.

## 7. Verify the bundle programmatically

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate
```

Quick check:

```bash
python - <<'PY'
from opengrow.manufacturer_profiles import manufacturer_bundle_available, default_asset_root
print("asset root:", default_asset_root())
print("bundle available:", manufacturer_bundle_available())
PY
```

Expected:

```text
bundle available: True
```

If it is `False`, compare the actual files with the exact six names in Section 3.

## 8. Run manufacturer validation

Run the Python tests first:

```bash
python -m pytest -q
```

Then:

```bash
python tools/validate_manufacturer_optics.py
python tools/validate_manufacturer_ies_ab.py
```

The recorded reference data established:

- IES profiles used 91 vertical angles and 73 horizontal angles;
- numerical solid-angle integration reproduced package radiant flux to better than 0.05% for the three selected devices;
- EULUMDAT and IES angular distributions agreed to rounding precision after scaling;
- spectrum peaks resolved at approximately 446 nm, 680 nm, and 742 nm;
- manufacturer angular profiles produced materially different canopy predictions from the simplified generalized-Lambertian model.

A controlled reference comparison held geometry, radiant power, manufacturer spectrum, receiver geometry, and visibility constant while changing only the angular model:

| Metric | Simplified Lambertian | Manufacturer IES |
| --- | ---: | ---: |
| Mean PPFD | 76.5617 | 55.8179 µmol m⁻² s⁻¹ |
| Minimum PPFD | 44.9827 | 39.9454 µmol m⁻² s⁻¹ |
| Maximum PPFD | 99.7022 | 66.7023 µmol m⁻² s⁻¹ |
| PPFD CV | 0.1751 | 0.1172 |
| Min/mean uniformity | 0.5875 | 0.7156 |

This is why the supplier-data path matters: manufacturer photometry changes the predicted photon field, not only how the light looks in RTX.

## 9. Verify manufacturer mode inside Kit

With the complete six-file bundle present, launch Kit using [`kit-linux-operations.md`](kit-linux-operations.md).

In the OpenGrowTwin panel:

1. select **Manufacturer IES + SPD**;
2. confirm all three part identifiers are shown;
3. confirm the spectrum plot shows loaded tabulated curves rather than idealized spikes;
4. run a 41 × 25 final simulation;
5. switch to **Simplified / Lambertian**;
6. rerun and verify that heatmap/metrics differ;
7. return to manufacturer mode and verify RTX IES shaping remains synchronized with the same authoritative emitter transform.

If the six-file bundle is incomplete, the application must not pretend manufacturer mode is active. The intended behavior is an explicit fallback state.

## 10. RTX synchronization validation

Manufacturer IES influences two distinct paths:

```text
local IES + SPD
    ├── deterministic scientific solver → PPFD/DLI/spectrum/uniformity
    └── USD/RTX shaping                → visual light distribution
```

The deterministic solver remains authoritative. RTX is presentation and interaction, not the source of PPFD.

Headless checks:

- `tools/kit_validate_manufacturer_ies_rtx.py`
- `tools/kit_validate_manufacturer_ies_transform_sync.py`

## 11. If the supplier website changes

Supplier websites and revisions change over time. A reproducible update process is:

1. search the exact part number on the official ams OSRAM domain;
2. record the product page URL and retrieval date;
3. record the datasheet revision;
4. record the optical-simulation archive filename and revision/date;
5. preserve the original archive locally;
6. extract into a clean working directory;
7. compare IES grid dimensions, integrated radiant flux, and spectrum peak/range against the current reference values;
8. if adopting a new revision, update provenance and rerun the full CPU + Kit manufacturer validation.

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `manufacturer_bundle_available()` is `False` | missing/misnamed file | compare all six expected filenames |
| manufacturer mode falls back to Lambertian | incomplete local bundle | inspect `sources/osram/extracted/` |
| IES parser rejects profile | unsupported/malformed profile or wrong file | confirm LM-63 Type-C `TILT=NONE` asset from exact part |
| spectrum peak is wrong | wrong device/revision/text file | check part number and tabulated wavelength range |
| values differ after supplier update | new optical revision | treat as a new dataset and revalidate |
| Git shows supplier files | ignore rules not active | stop, fix `.gitignore`, unstage without deleting local source data |
| RTX shape changes but PPFD does not | visual IES path active but scientific manufacturer profile not loaded | verify six-file bundle and active optical-model state |

## 13. Provenance rule

For every supplier-backed result, retain enough information for another engineer to answer:

- Which manufacturer?
- Which exact part number?
- Which product family?
- Which optical-file revision?
- Which local filename?
- Which spectral provenance classification?
- Which validation proved the file was parsed and normalized correctly?

That provenance is more useful than simply saying “OSRAM data was used.”
