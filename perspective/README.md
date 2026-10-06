# Code S1 for the CF LIBS Perspective

Constructed examples and reporting record accompanying *Towards Reconstructable CF LIBS Quantification: A Perspective on Reporting, Validation, and Reproducibility* by Homa Saeidfirozeh, Petr Kubelík, Jan Suchánek, and Martin Ferus.

**Software author:** Homa Saeidfirozeh. **Version:** 1.0.0. **Date:** 6 October 2026. **Tag:** `perspective-v1.0.0`.

This release snapshot contains only the constructed material accompanying this Perspective. All numerical data are hypothetical. No published study is assessed by this package. The separate older audit software and its example records are excluded from this snapshot and the attached Code S1 archive. The repository history is not part of the archive.

Download the [fixed Code S1 archive](https://github.com/homasf/cf-libs-repro-audit/releases/download/perspective-v1.0.0/CF_LIBS_Perspective_CodeS1_v1.0.0.zip) or see the [version specific release](https://github.com/homasf/cf-libs-repro-audit/releases/tag/perspective-v1.0.0). Cite the software using `CITATION.cff` or `CITATION.bib`. Version 1.0.0 is specific to this Perspective package, independent of version numbers used by other software. A DOI has not yet been issued.

## Run the numerical examples

From the extracted archive root:

```bash
python3 supplementary/code/run_all.py
python3 supplementary/code/restore_figures.py
python3 supplementary/code/verify_release.py
```

The calculations, table production, figure restoration, and checks require only the Python standard library. They were verified with Python 3.12.14. Running the Monte Carlo calculations takes several minutes.

To regenerate the inputs from their saved seed and verify that they match the supplied input files, use:

```bash
python3 supplementary/code/run_all.py --regenerate-record --figures
python3 supplementary/code/verify_release.py
```

## What the calculations do

1. `make_record.py` constructs 21 line entries for hypothetical elements X, Y, and Z and five replicate intensity records using the saved seed. These are simulated inputs, with no experimental measurements.
2. `worked_examples.py` evaluates the five checkpoints: linewidth decomposition, plasma parameters, model consistency, composition basis, and reference comparison.
3. `reconstruct_record.py` reads the record and replicate intensities, obtains electron density and temperature, combines neutral and singly ionized populations, and converts mole fractions into mass fractions. It propagates the assigned input uncertainties using 200,000 Monte Carlo draws.
4. `seeded_defects.py` applies nine convention or reporting slips and four legitimate input perturbations to the same record. It compares their effects with input uncertainty intervals and with density, scatter, and reference indicators.
5. `make_tables.py` turns the numerical outputs into the five supplementary LaTeX table bodies.
6. `verify_release.py` checks the packaged numerical values and table entries, and separately verifies the identities of the fixed figure files. It does not read manuscript prose, citations, or a bibliography. It does not establish physical validity or experimental accuracy.

There are 76 checks inside the calculation scripts, 105 additional numerical and table checks, and 15 figure file integrity checks. The last group checks ten supplied PDF/PNG asset hashes and five restored PDF copies. See `verification/VALIDATION.md` for results and limits.

## The manuscript figures

The five final manuscript figures are fixed raster artwork in PDF wrappers. They were recovered losslessly from the author supplied final PDFs, preserving the embedded pixels and Figure 1 transparency. Their PDF and PNG assets, SHA256 hashes, and provenance are in `supplementary/figure_assets/`.

`restore_figures.py` and the `--figures` option verify and copy these assets to `supplementary/figures/`. They restore the exact supplied files and do not redraw the artwork. Figure 1 is a schematic rather than a numerical plot. The original editable drawing sources were not supplied; this release cannot recreate the graphical design from numerical inputs.

Optional diagnostic plots are drawn directly from the numerical results in a separate directory. Their graphical design differs from the final manuscript artwork, and they never overwrite it:

```bash
python3 -m pip install -r supplementary/code/requirements.txt
python3 supplementary/code/run_all.py --diagnostic-plots
```

These plots use NumPy 2.3.5, Matplotlib 3.10.8, and the bundled DejaVu Sans font. They are written to `supplementary/diagnostic_figures/`. The supplied artwork's original software versions are unknown; these pins describe only the verified diagnostic plotting environment.

## Files

| Path | Contents |
| --- | --- |
| `supplementary/code/` | Calculation, table, restoration, diagnostic plotting, and verification scripts |
| `supplementary/record/` | Constructed JSON inputs and five replicate intensities |
| `supplementary/outputs/` | Expected numerical outputs and check logs |
| `supplementary/tables/` | Five supplementary LaTeX table bodies |
| `supplementary/figure_assets/` | Fixed manuscript PDF and PNG artwork, provenance, and hashes |
| `supplementary/figures/` | Restored fixed manuscript PDFs |
| `verification/` | Validation evidence and provenance |

The article and supplementary prose are distributed separately from this code release. This package intentionally has no manuscript text checker requiring absent source files. Numerical checks, file checks, and author review of prose have different scopes.

## Archiving

The GitHub release attaches the fixed Code S1 ZIP and its SHA256 checksum. `.zenodo.json` provides metadata for manual archival deposition. Deposit this clean ZIP, rather than the general repository homepage or another branch, and then cite the version specific DOI issued for the deposition. Do not describe an unissued DOI as available.

## License

MIT License. See `LICENSE`.
