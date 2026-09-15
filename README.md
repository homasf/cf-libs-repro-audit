# CF-LIBS Reproducibility Audit

Selected executable calculations for reconstructing printed CF-LIBS/LIPS results.
This is an unreleased revision accompanying *Reconstructable CF-LIBS quantification:
a reporting framework with worked literature examples*, by Homa Saeidfirozeh,
Petr Kubelík, Jan Suchánek and Martin Ferus. Software author: Homa Saeidfirozeh.

## Scope and installation

The generic engine checks selected linewidth, parameter, empirical inversion,
validation and reporting operations. The multi-case module adds an unweighted
Boltzmann line-table fit, mass–mole conversion and a MESBP composition-distance
comparison. It does not process raw spectra, implement a complete CF-LIBS closure
pipeline, or rerun the iterative MESBP algorithm.

```bash
git clone https://github.com/homasf/cf-libs-repro-audit.git
cd cf-libs-repro-audit
python -m pip install -e ".[dev]"
python -m pytest -q
cf-libs-audit --worked-example -o audit_report.html
python -m libs_repro_audit.cases --output output/case_results.json
python scripts/make_validation_figure.py
```

Bundled records are labelled **AI source cross-check; author verification pending**.
Outputs from them are preliminary. Follow AGENT_GUIDE.md before assigning a human
verification stamp. Local tests do not establish source verification or experimental
validity. PyPI availability and an archival DOI are not claimed for this revision.

The earlier commands `python -m libs_repro_audit` and
`python scripts/make_figure2.py` remain available for soil-only outputs.

## Results and comparison rules

| Status | Interpretation |
|---|---|
| PASS | The declared numerical rule is met; physical validity is not established. |
| FAIL | The declared rule is not met; experimental cause is not determined. |
| NOT_INVERTIBLE | The printed linear relation has zero slope. |
| NOT_REPORTED | The record explicitly marks an item absent. |
| NOT_ASSESSED | No check was supplied for this checkpoint. |
| REPORTED | A diagnostic is marked present; adequacy is not assessed. |
| INFO | Arithmetic or a scenario without a supported binary rule. |

Markdown and HTML retain values, sources, assumptions, tolerances, missing inputs,
conflicts and verification status. The manuscript further distinguishes numerical
reconstruction, uncertainty-interval compatibility, conditional scenarios and
missing inputs. Neither representation is a composite score for a paper.

`--strict` returns nonzero for failed, absent or non-invertible checks and for
unverified records. A non-strict zero exit means a report was generated, not that
all checks passed. Invalid input returns code 2.

## Numerical safeguards

- Reject non-finite, boolean and physically invalid numeric inputs.
- Convert McWhirter temperature in eV to K before using the K prefactor.
- Distinguish Gaussian quadrature and Voigt instrument-response scenarios;
  neither is a universal correction bound.
- Require explicit rounding bounds or tolerances for inverse comparisons.
  Nonzero slope alone proves invertibility, not reproduction.
- Preserve conflicting density scales; the soil lower scale is an inference.
- Keep numerical rounding, analyst screening and measurement uncertainty separate.
- State the SD/mean assumptions behind plant RA and RSD checks. A necessary bound
  does not demonstrate attainability for an integer replicate count.
- Normalize mass–mole conversions only over the stated element set.

## Files and sources

`src/libs_repro_audit/case_studies.json` contains the five cases, source locations
and DOI identifiers. `cases.py` computes their results. `audit.py` contains kernels;
`engine.py` runs generic records; `tests/` verifies known answers, domains, rounding,
round trips and reporting provenance. SCIENTIFIC_REVIEW.md describes this revision.

Source papers: [soil](https://doi.org/10.1038/s41598-025-04395-5),
[alloy](https://doi.org/10.3390/met13071188),
[plant](https://doi.org/10.1016/j.arabjc.2024.105941),
[MESBP](https://doi.org/10.1039/D2JA00218C),
[mass–mole](https://doi.org/10.1039/D4JA00028E).

## Extraction, citation and license

`cf-libs-audit-extract` drafts unverified records from plain text. It requires
configured service credentials and is not invoked by tests. Human source
verification is required before a record is labelled verified; see AGENT_GUIDE.md.
Cite software separately from the article using CITATION.cff. Mint a DOI for the
accepted archival release; do not substitute a placeholder. MIT License.
