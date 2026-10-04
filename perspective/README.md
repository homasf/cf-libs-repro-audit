# CF LIBS Perspective: Code S1 and Data S1

Supporting calculations for **Towards Reconstructable CF LIBS Quantification: A Perspective on Reporting, Validation, and Reproducibility**.

This folder contains the author's original nine Python scripts, complete input record, numerical outputs, tables, and original figure PDFs. The data describe hypothetical X, Y, and Z elements in a constructed plasma model. The illustrative line parameters are not real atomic transition data or experimental measurements.

## Run

From this `perspective/` folder:

```sh
python3 supplementary/code/run_all.py
python3 supplementary/code/verify_release.py
```

Use Python 3.12 or newer for the complete workflow, including the optional figure dependencies. The calculations require only the Python standard library. Optional deterministic input regeneration is tested with:

```sh
python3 supplementary/code/run_all.py --regenerate-record
```

To regenerate Figures 2, 3, 4, and S1:

```sh
python3 -m pip install -r supplementary/code/requirements.txt
python3 supplementary/code/run_all.py --figures
```

Main numerical figures are written to `figures/`, and Figure S1 to `supplementary/figures/`. Figure 1 is supplied as its original vector PDF schematic. Original dependency pins are retained.

## Contents and checks

`supplementary/` contains `code/`, `record/`, `outputs/`, `tables/`, and `figures/`. `verification/` records calculation validation and input provenance. The original scripts are unchanged; `verify_release.py` is an additional checker.

The input record was regenerated with the original supplied generator. Expected printed values were recovered from the supplied summary using the author's formatting function. All 21 line rows and 105 intensities match the supplied table.

All 76 numerical checks passed after the full baseline and all 13 scenarios were rerun. The 11 regenerated outputs are byte identical to the supplied originals, and all 666 numerical JSON values match exactly. The additional `verify_release.py` runs 105 numerical and table checks here and explicitly reports that manuscript text checks are not performed because manuscript drafts are excluded.

The original `check_manuscript.py` requires the original manuscript files and exact wording; its supplied 180 check log is historical. Use `verify_release.py` for this bundle rather than `run_all.py --check-text`.

## Repository and citation

This folder is hosted at [homasf/cf-libs-repro-audit](https://github.com/homasf/cf-libs-repro-audit/tree/main/perspective). Preserve its directory structure when downloading or running it. The repository's [MIT license](LICENSE) is included here. Cite the specific commit or archived release used for the paper, and cite the Perspective separately when its journal citation becomes available.
