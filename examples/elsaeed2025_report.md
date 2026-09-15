# CF-LIBS/LIPS reproducibility-audit report

**Source verification:** AI cross-check against the supplied publication on 2026-09-15; author source verification pending
**Unresolved missing inputs:** []
**Recorded conflicts:** [{"quantity": "test electron density", "printed": "1.54382e17 cm^-3", "alternative": "1.54382e16 cm^-3", "basis": "Alternative inferred only from empirical inversion; not a corrected measurement."}]

**Audited publication:** Calibration-free picosecond LIPS for quantifying heavy metals in soils near Egyptian industrial sites
**DOI:** 10.1038/s41598-025-04395-5  |  **Record transcribed by:** Homa Saeidfirozeh on 2026-07-29

This report tests only whether the published numerical chain can be reconstructed from the printed values supplied in the audit record. It does not assess raw data, true concentrations or author intent, and a FAIL is a reproducibility finding, not an allegation.

## Summary

- PASS: 5
- FAIL: 8
- NOT_INVERTIBLE: 4
- NOT_REPORTED: 5
- INFO: 3

## Findings

| Checkpoint | Check | Status | Detail |
|---|---|---|---|
| A5 | `validation:Cd:Ne-based` | **FAIL** | delta = -6.61% lies OUTSIDE the stated ±1.0% interval |
| A5 | `validation:Cd:Te-based` | **FAIL** | delta = +8.88% lies OUTSIDE the stated ±1.0% interval |
| A5 | `validation:Zn:Ne-based` | **FAIL** | delta = -5.77% lies OUTSIDE the stated ±1.0% interval |
| A5 | `validation:Zn:Te-based` | **FAIL** | delta = -4.59% lies OUTSIDE the stated ±1.0% interval |
| A5 | `validation:Fe:Ne-based` | **PASS** | delta = -0.65% lies within the stated ±1.0% interval |
| A5 | `validation:Fe:Te-based` | **PASS** | delta = -0.65% lies within the stated ±1.0% interval |
| A5 | `validation:Ni:Ne-based` | **PASS** | delta = +0.23% lies within the stated ±1.0% interval |
| A5 | `validation:Ni:Te-based` | **PASS** | delta = +0.23% lies within the stated ±1.0% interval |
| A1 | `stark:S1-P1` | **FAIL** | printed FWHM gives 1.15x the comparison N_e; an effective W_s of 0.0438 nm would be required instead of the printed 0.0381 nm |
| A1 | `stark:S1-Ptest` | **FAIL** | printed FWHM gives 1.15x the comparison N_e; an effective W_s of 0.0437 nm would be required instead of the printed 0.0381 nm |
| A1 | `instrument:width` | **INFO** | Resolution width ~ 0.0086 nm at R = 75000 |
| A1 | `instrument:correction:S1-P1` | **INFO** | quadrature instrumental correction changes the FWHM by 0.16%; the Voigt scenario changes it by 0.34%. These assume different profile models; neither is a measured correction. |
| A1 | `instrument:correction:S1-Ptest` | **INFO** | quadrature instrumental correction changes the FWHM by 0.20%; the Voigt scenario changes it by 0.44%. These assume different profile models; neither is a measured correction. |
| A2 | `scale:Cd` | **FAIL** | exponent inferred from this comparison is 10^16 (gives 65.02866972477065), but the article states 10^17; this does not establish the physical density |
| A2 | `scale:Zn` | **FAIL** | exponent inferred from this comparison is 10^16 (gives 136.94603804511928), but the article states 10^17; this does not establish the physical density |
| A4 | `equation:Fe:Ne` | **NOT_INVERTIBLE** | printed slope is 0.0 — equation returns a constant and cannot be inverted for concentration; moreover the constant 1.566 does not equal the operative test value 1.54382 |
| A4 | `equation:Ni:Ne` | **NOT_INVERTIBLE** | printed slope is 0.0 — equation returns a constant and cannot be inverted for concentration; moreover the constant 1.563 does not equal the operative test value 1.54382 |
| A4 | `equation:Fe:Te` | **NOT_INVERTIBLE** | printed slope is 0.0 — equation returns a constant and cannot be inverted for concentration; moreover the constant 9118.16 does not equal the operative test value 9136.3 |
| A4 | `equation:Ni:Te` | **NOT_INVERTIBLE** | printed slope is 0.0 — equation returns a constant and cannot be inverted for concentration; moreover the constant 9118.16 does not equal the operative test value 9136.3 |
| A4 | `equation:Cd:Ne` | **PASS** | inversion gives 65.029, compatible with the printed estimate 65.02 by the declared comparison rule |
| A3 | `qualitative:lte_check_reported` | **NOT_REPORTED** | explicit LTE check (e.g. McWhirter with inputs): not fully specified in the supplied record |
| A3 | `qualitative:optical_thinness_or_self_absorption_reported` | **NOT_REPORTED** | optical-thinness / self-absorption diagnostic for analytical lines: not fully specified in the supplied record |
| A2 | `qualitative:atomic_data_provenance_reported` | **NOT_REPORTED** | atomic/broadening-data source, version and access date: not fully specified in the supplied record |
| A1 | `qualitative:instrumental_width_reported` | **NOT_REPORTED** | numerical instrumental width / line-shape treatment: not fully specified in the supplied record |
| A4 | `qualitative:full_precision_coefficients_available` | **NOT_REPORTED** | full-precision coefficients or machine-actionable record: not fully specified in the supplied record |

## Numerical values, sources and comparison rules

### validation:Cd:Ne-based
```json
{
  "method_value": 65.02,
  "reference_value": 69.62,
  "delta_percent": -6.60729675380639,
  "tolerance_percent": 1.0,
  "units": "ppm",
  "source": "Table 6 of the audited article",
  "tolerance_source": "article states approximately +/-1% agreement with ICP-OES for all four elements"
}
```

### validation:Cd:Te-based
```json
{
  "method_value": 75.8,
  "reference_value": 69.62,
  "delta_percent": 8.876759551852905,
  "tolerance_percent": 1.0,
  "units": "ppm",
  "source": "Table 6",
  "tolerance_source": "article states approximately +/-1% agreement with ICP-OES for all four elements"
}
```

### validation:Zn:Ne-based
```json
{
  "method_value": 136.94,
  "reference_value": 145.33,
  "delta_percent": -5.773068189637387,
  "tolerance_percent": 1.0,
  "units": "ppm",
  "source": "Table 6",
  "tolerance_source": "article states approximately +/-1% agreement with ICP-OES for all four elements"
}
```

### validation:Zn:Te-based
```json
{
  "method_value": 138.66,
  "reference_value": 145.33,
  "delta_percent": -4.589554806302908,
  "tolerance_percent": 1.0,
  "units": "ppm",
  "source": "Table 6",
  "tolerance_source": "article states approximately +/-1% agreement with ICP-OES for all four elements"
}
```

### validation:Fe:Ne-based
```json
{
  "method_value": 61.27,
  "reference_value": 61.67,
  "delta_percent": -0.6486135884546759,
  "tolerance_percent": 1.0,
  "units": "ppm",
  "source": "Table 6",
  "tolerance_source": "article states approximately +/-1% agreement with ICP-OES for all four elements"
}
```

### validation:Fe:Te-based
```json
{
  "method_value": 61.27,
  "reference_value": 61.67,
  "delta_percent": -0.6486135884546759,
  "tolerance_percent": 1.0,
  "units": "ppm",
  "source": "Table 6",
  "tolerance_source": "article states approximately +/-1% agreement with ICP-OES for all four elements"
}
```

### validation:Ni:Ne-based
```json
{
  "method_value": 149.87,
  "reference_value": 149.53,
  "delta_percent": 0.2273791212465749,
  "tolerance_percent": 1.0,
  "units": "ppm",
  "source": "Table 6",
  "tolerance_source": "article states approximately +/-1% agreement with ICP-OES for all four elements"
}
```

### validation:Ni:Te-based
```json
{
  "method_value": 149.87,
  "reference_value": 149.53,
  "delta_percent": 0.2273791212465749,
  "tolerance_percent": 1.0,
  "units": "ppm",
  "source": "Table 6",
  "tolerance_source": "article states approximately +/-1% agreement with ICP-OES for all four elements"
}
```

### stark:S1-P1
```json
{
  "fwhm_nm": 0.15322,
  "w_s_nm": 0.0381,
  "ne_calc": 2.0107611548556428e+16,
  "ne_comparison": 1.75e+16,
  "ratio": 1.1490063742032244,
  "w_s_effective_nm": 0.043777142857142855,
  "ratio_tolerance": 0.01,
  "tolerance_basis": "Analyst numerical screen, 1% relative; intentionally coarser than printed precision. Not an experimental uncertainty.",
  "source": "FWHM and W_s printed in the audited article; comparison value plotted there"
}
```

### stark:S1-Ptest
```json
{
  "fwhm_nm": 0.13493,
  "w_s_nm": 0.0381,
  "ne_calc": 1.7707349081364828e+16,
  "ne_comparison": 1.54382e+16,
  "ratio": 1.146982749372649,
  "w_s_effective_nm": 0.04370004275109793,
  "ratio_tolerance": 0.01,
  "tolerance_basis": "Analyst numerical screen, 1% relative; intentionally coarser than printed precision. Not an experimental uncertainty.",
  "source": "article prints 1.54382e17 cm-3; 1e16 is inferred from the printed inversion, not independently measured here"
}
```

### instrument:width
```json
{
  "instrumental_fwhm_nm": 0.00861676,
  "source": "conditioned resolving power stated in the audited article",
  "assumption": "lambda/R treated as a Gaussian FWHM for scenarios only"
}
```

### instrument:correction:S1-P1
```json
{
  "change_percent": 0.15825989565464743,
  "voigt_change_percent": 0.33999936243042156,
  "voigt_lorentzian_fwhm_nm": 0.1526990529768841
}
```

### instrument:correction:S1-Ptest
```json
{
  "change_percent": 0.20411946596588848,
  "voigt_change_percent": 0.43830131232099795,
  "voigt_lorentzian_fwhm_nm": 0.13433860003928527
}
```

### scale:Cd
```json
{
  "per_exponent_ppm": {
    "16": 65.02866972477065,
    "17": 4048.5091743119265
  },
  "printed_estimate": 65.02,
  "matching_exponents": [
    16
  ],
  "comparison_details": {
    "16": {
      "rounding_interval": [
        64.87458793177584,
        65.18279569892472
      ],
      "comparison_basis": "declared rounding intervals"
    },
    "17": {
      "rounding_interval": [
        4047.7712483875594,
        4049.2473118279568
      ],
      "comparison_basis": "declared rounding intervals"
    }
  },
  "source": "S1 Cd Ne-concentration equation, Table 4; test-sample Ne stated as 1.54382e17"
}
```

### scale:Zn
```json
{
  "per_exponent_ppm": {
    "16": 136.94603804511928,
    "17": 736.2808954837597
  },
  "printed_estimate": 136.94,
  "matching_exponents": [
    16
  ],
  "comparison_details": {
    "16": {
      "rounding_interval": [
        136.9213017879095,
        136.97077536935188
      ],
      "comparison_basis": "declared rounding intervals"
    },
    "17": {
      "rounding_interval": [
        736.241292298402,
        736.3205003774399
      ],
      "comparison_basis": "declared rounding intervals"
    }
  },
  "source": "S1 Zn Ne-concentration equation, Table 4"
}
```

### equation:Fe:Ne
```json
{
  "analyte": "Fe",
  "parameter": "Ne",
  "a": 1.566,
  "b": 0.0,
  "operative_value": 1.54382,
  "source": "S1 Fe: Ne = (1.566 + 0.0*C) x 1e16"
}
```

### equation:Ni:Ne
```json
{
  "analyte": "Ni",
  "parameter": "Ne",
  "a": 1.563,
  "b": 0.0,
  "operative_value": 1.54382,
  "source": "S1 Ni: Ne = (1.563 + 0.0*C) x 1e16"
}
```

### equation:Fe:Te
```json
{
  "analyte": "Fe",
  "parameter": "Te",
  "a": 9118.16,
  "b": 0.0,
  "operative_value": 9136.3,
  "source": "S1 Fe/Ni: Te = 9118.16 + 0.0*C; reported test-sample Te = 9136.3 K"
}
```

### equation:Ni:Te
```json
{
  "analyte": "Ni",
  "parameter": "Te",
  "a": 9118.16,
  "b": 0.0,
  "operative_value": 9136.3,
  "source": "El-Saeed Table 5, S1 Ni; validation paragraph for temperature"
}
```

### equation:Cd:Ne
```json
{
  "analyte": "Cd",
  "parameter": "Ne",
  "a": 1.317,
  "b": 0.003488,
  "operative_value": 1.54382,
  "printed_estimate": 65.02,
  "source": "S1 Cd equation: compatible with the printed estimate under the declared rounding intervals",
  "rounding": {
    "a_halfwidth": 0.0005,
    "b_halfwidth": 5e-07,
    "y_halfwidth": 5e-06,
    "estimate_halfwidth": 0.005
  },
  "inverted_concentration": 65.02866972477065,
  "rounding_interval": [
    64.87458793177584,
    65.18279569892472
  ],
  "comparison_basis": "declared rounding intervals"
}
```

### qualitative:lte_check_reported
```json
{
  "source": "Population-model discussion: no numerical LTE diagnostic located in supplied PDF."
}
```

### qualitative:optical_thinness_or_self_absorption_reported
```json
{
  "source": "Ca I 646.257 nm described as free of self-absorption; no quantitative diagnostic located."
}
```

### qualitative:atomic_data_provenance_reported
```json
{
  "source": "Atomic-data sources are cited, but a complete reproducible broadening-data record is not supplied. False means incomplete, not wholly absent."
}
```

### qualitative:instrumental_width_reported
```json
{
  "source": "Resolving power and profile discussion supplied; measured response at diagnostic line and numerical separated Stark width not supplied."
}
```

### qualitative:full_precision_coefficients_available
```json
{
  "source": "Tables 4 and 5 print S1 Fe/Ni slopes as 0.0."
}
```


## Interpretation guide

PASS: the declared numerical comparison rule is met; physical validity is not established. FAIL: it does not; possible explanations include typographical errors, rounding, unreported full-precision coefficients or an undocumented calculation pathway — any of which the authors could resolve by clarification. NOT_INVERTIBLE: a printed equation cannot be used as described. NOT_REPORTED: a minimum reporting item (Table 3 of the framework paper) is absent from the printed record.
