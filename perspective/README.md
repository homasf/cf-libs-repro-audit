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

## What the code does, step by step

1. **Read the supplied record.** The default run uses `record/record.json`, `record/line_intensities.csv`, and `record/reported_values.json` inside `supplementary/`. These describe hypothetical X, Y, and Z elements, 21 spectral lines, five intensity replicates, assigned uncertainties, and expected printed results. The calculation starts from saved integrated intensities and linewidths.

2. **Recalculate the worked examples.** `worked_examples.py` demonstrates linewidth correction, temperature and density conventions, concentration conversion, sensitivity, and reference comparisons. It writes example results and runs 24 checks.

3. **Reconstruct the composition.** `reconstruct_record.py` uses `cflibs_chain.py` to correct the linewidth, calculate electron density, and fit Boltzmann points to estimate temperature and relative populations. Saha balance supplies missing charge stages. The populations are normalized to mole fractions and converted to mass fractions for each replicate.

4. **Propagate uncertainty.** A Monte Carlo calculation with 200,000 draws varies the assigned physical and atomic inputs. Each input draw is shared across all five replicates, while replicate intensity scatter is combined separately. The output includes standard uncertainties, percentile intervals, signed deviations, and comparison scores. A second calculation with 20,000 draws uses another seed as a consistency check.

5. **Test deliberate changes.** `seeded_defects.py` introduces 13 individual perturbations, including linewidth and density conventions, intensity conventions, and concentration basis. Each scenario uses 20,000 uncertainty draws. The code checks whether density agreement, Boltzmann fit scatter, and reference compatibility reveal the resulting changes.

6. **Write the results and tables.** Detailed results go to JSON files; replicate and scenario comparisons go to CSV files in `supplementary/outputs/`. `make_tables.py` generates the five supplementary LaTeX table bodies in `supplementary/tables/`. The default run performs 76 numerical checks.

7. **Run the separate consistency checker.** Run `verify_release.py` after the calculations. Its 105 checks compare the packaged numerical values and table relationships. It writes `check_log_release.txt` and preserves the original historical text check log.

The `--figures` option additionally redraws Figures 2, 3, 4, and S1. Figure 1 is supplied as its original schematic. The `--regenerate-record` option recreates the constructed inputs from the saved seed and checks them against the shipped files.

These scripts run locally without an AI service or API key. They demonstrate reproducibility and sensitivity of the constructed calculations. The checks do not establish experimental accuracy or validate a real plasma model.

## Repository and citation

This folder is hosted at [homasf/cf-libs-repro-audit](https://github.com/homasf/cf-libs-repro-audit/tree/main/perspective). Preserve its directory structure when downloading or running it. The repository's [MIT license](LICENSE) is included here. Cite the specific commit or archived release used for the paper, and cite the Perspective separately when its journal citation becomes available.
