# Code S2 and Data S2: three published CF-LIBS records

Version 1.0.0. Software author: Homa Saeidfirozeh.

These files accompany Supplementary Text S2 of *Towards Reconstructable CF-LIBS Quantification: A Perspective on Reporting, Validation, and Reproducibility*. They supply selected calculations transcribed from three original studies. The constructed examples are distributed separately as [Code S1](https://github.com/homasf/cf-libs-repro-audit/tree/main/perspective).

## Run

```bash
python3 published_case_checks.py
```

Use Python 3.10 or later. No third-party dependencies are needed. Inputs and outputs are beside the script. The script writes `published_case_results.json` and three CSV files, and fails if its 20 numerical checks do not pass.

| Case | Calculations regenerated | Limits |
| --- | --- | --- |
| El-Saeed et al., Scientific Reports (2025) | Signed deviations for Cd, Zn, Fe and Ni in Table 6 | No new calibration fit or complete composition reconstruction |
| Fayyaz et al., Metals (2023) | Experimental/theoretical Fe I and Cu I central intensity ratios | A ratio check does not independently prove optical thinness; composition inputs are incomplete |
| Aldakheel et al., Arabian Journal of Chemistry (2024) | McWhirter threshold, Stark arithmetic using the whole fitted width, sum of 23 printed concentrations | No instrument-corrected Stark width or absolute-concentration closure is reconstructed |

The input JSON records the DOI, table/section locations, units and adopted conventions. Expected rounded values are check targets, not measured inputs or uncertainties. The actual source values remain explicit. No raw spectra are reprocessed, omitted inputs inferred, or true sample concentrations established.

Data S2 comprises the input JSON and recalculated JSON/CSV outputs. Code S2 is `published_case_checks.py`. `Supplementary_Text_S2.tex` and `.pdf` provide the accompanying explanation and Tables S6–S7.

## Sources

- El-Saeed et al. (2025): https://doi.org/10.1038/s41598-025-04395-5, Table 6.
- Fayyaz et al. (2023): https://doi.org/10.3390/met13071188, Table 1 and Equation (1).
- Aldakheel et al. (2024): https://doi.org/10.1016/j.arabjc.2024.105941, Table 1, Sections 3.2 and 3.5, Tables 3a and 3b.

## Archive and citation

```bash
python3 build_archive.py
```

This produces a deterministic versioned ZIP and SHA256 checksum under `dist/`. The versioned archive is supplied in the separate [published-records-v1.0.0 release](https://github.com/homasf/cf-libs-repro-audit/releases/tag/published-records-v1.0.0). `CITATION.cff` identifies this component. Cite the GitHub repository or this versioned release together with the original studies; no DOI has been assigned to Code S2/Data S2. The Code S1 DOI identifies only the constructed package.

MIT License for the supplied code. Published sources retain their own terms and are credited above.
