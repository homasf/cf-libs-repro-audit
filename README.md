# CF-LIBS Reproducibility Audit

[![audit-checks](https://github.com/homasf/cf-libs-repro-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/homasf/cf-libs-repro-audit/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![version](https://img.shields.io/badge/version-2.0.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)

**CF-LIBS Reproducibility Audit** is an executable A1–A5 audit engine for
checking whether quantitative claims in a published calibration-free
LIBS/LIPS study can be reconstructed from the values printed in the article.

**Software author:** Homa Saeidfirozeh  
**Version:** 2.0.0  
**Package metadata date:** 7 July 2026 (no tagged general audit release exists at this date)  
**Repository:** `homasf/cf-libs-repro-audit`

## Chemosensors Perspective support

Code S1 and Data S1 for *Towards Reconstructable CF LIBS Quantification: A Perspective on Reporting, Validation, and Reproducibility* have their own fixed version, `perspective-v1.0.0`.

Use the [Perspective only archive](https://github.com/homasf/cf-libs-repro-audit/releases/download/perspective-v1.0.0/CF_LIBS_Perspective_CodeS1_v1.0.0.zip) and its [version specific release](https://github.com/homasf/cf-libs-repro-audit/releases/tag/perspective-v1.0.0). The release snapshot contains only the constructed Perspective material. It excludes the separate legacy named study audit documented below and excludes repository history.

The [`perspective/`](perspective/) development folder mirrors that material. Run:

```bash
cd perspective
python3 supplementary/code/run_all.py
python3 supplementary/code/restore_figures.py
python3 supplementary/code/verify_release.py
```

The five final manuscript figures are fixed raster artwork in PDF wrappers, with provenance and hashes. Restoration copies the exact supplied assets. Optional numerical diagnostic plots are drawn separately and do not overwrite the manuscript figures. See the [Perspective README](perspective/README.md).

The general audit engine below is separate software. Its named example and any related manuscript are not part of Code S1 and are not cited as evidence by the Perspective. The earlier README article description is not a statement of publication or submission status. If a related manuscript is submitted or under review, its authors should disclose its actual status and relationship to the editor.

## Scope

The software reads a machine-actionable JSON record containing values
transcribed from a publication and reruns deterministic checks associated
with five checkpoints:

- **A1 — Linewidth provenance:** printed FWHM, Stark-width and instrumental-width checks.
- **A2 — Plasma-parameter consistency:** units, normalizations and powers of ten.
- **A3 — Plasma-model reporting:** LTE, optical-thinness/self-absorption, atomic-data provenance and related reporting flags.
- **A4 — Concentration inversion:** invertibility and consistency of printed empirical equations.
- **A5 — Validation:** signed relative deviations from independent comparison values and stated tolerances.

The engine returns `PASS`, `FAIL`, `NOT_INVERTIBLE`, `NOT_REPORTED`,
`REPORTED` and `INFO` results, with the arithmetic shown in Markdown or HTML.

**No raw spectra are used and no new measurements are made.** A failure means
that a claim is not reproducible from the values as printed; it is not an
assessment of author intent, experimental misconduct or the true sample
concentrations.

## Legacy audit worked example

The bundled record audits El-Saeed et al., *Scientific Reports* 15 (2025)
19949. From printed values only, the repository regenerates:

| Paper item | Checkpoint | Implementation/output |
|---|---|---|
| Table 1 — signed relative deviations versus ICP-OES | A5 | `report.table1_rows`, `output/table1_signed_deviations.csv` |
| Figure 2 — deviation chart with the stated ±1% band | A5 | `scripts/make_figure2.py` |
| Table 2 — Ca I 646.257 nm linewidth/Stark check | A1/A2 | `report.table2_rows`, `output/table2_linewidth_check.csv` |
| Instrumental-width upper bound at $R=75{,}000$ | A1 | `audit.instrumental_fwhm`, `audit.quadrature_corrected_fwhm` |
| Electron-density exponent check | A2/A4 | `audit.ne_scale_check` |
| Fe/Ni zero-slope equation audit | A4 | `audit.LinearEquation` |

## Installation

From PyPI, after the release is published:

```bash
python -m pip install cf-libs-repro-audit
```

For development from GitHub:

```bash
git clone https://github.com/homasf/cf-libs-repro-audit.git
cd cf-libs-repro-audit
python -m pip install -e ".[dev]"
```

## Use

Audit the bundled worked example:

```bash
cf-libs-audit --worked-example
```

Write a styled HTML report:

```bash
cf-libs-audit --worked-example -o audit_report.html
```

Audit another paper:

```bash
cp examples/template.json mypaper.json
# Transcribe and verify the paper's printed values in mypaper.json.
cf-libs-audit mypaper.json -o mypaper_report.html
```

Use strict mode in continuous integration:

```bash
cf-libs-audit mypaper.json --strict
```

Regenerate the manuscript tables and numerical checks:

```bash
python -m libs_repro_audit
```

Regenerate Figure 2:

```bash
python scripts/make_figure2.py
```

Run the test suite:

```bash
python -m pytest -v
```

## Repository structure

- `data/printed_values.json` — printed numerical inputs for the worked example.
- `examples/template.json` — paper-independent audit-record template.
- `examples/elsaeed2025_scirep.json` — verified worked-example record.
- `src/libs_repro_audit/audit.py` — deterministic numerical functions.
- `src/libs_repro_audit/engine.py` — general A1–A5 audit engine.
- `src/libs_repro_audit/cli.py` — `cf-libs-audit` command-line interface.
- `tests/` — assertions for the numerical results used in the article.
- `.github/workflows/ci.yml` — tests on Python 3.9 and 3.12.
- `perspective/` — Code S1 and Data S1 for the Chemosensors Perspective.
- `.github/workflows/perspective.yml` — numerical and consistency checks for the Perspective support.

## AI-assisted extraction

`cf-libs-audit-extract` can draft an audit record from a plain-text paper
export. The draft is always stamped `UNVERIFIED`. A human must check every
value against the publication before the deterministic audit is run. The
language model performs transcription only; it never determines the audit
verdict. This optional command requires a compatible chat completion endpoint,
model, and key configured by the user; no provider is selected by default.
The audit engine and the Perspective calculation scripts run without an AI
service. See `AGENT_GUIDE.md` for configuration and verification instructions.

## Citation

The software author is **Homa Saeidfirozeh**. Use GitHub's **Cite this
repository** control or the archived Zenodo DOI after it is minted. The
machine-readable software metadata are in `CITATION.cff`.

The Perspective package is cited separately using its own fixed version and release metadata. The legacy audit software metadata do not describe the Perspective Code S1 package.

## License

MIT License. See `LICENSE`.
