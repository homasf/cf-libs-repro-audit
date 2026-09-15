"""Regenerate the earlier soil-only tables from printed values.

Running ``python -m libs_repro_audit`` prints, in order:

  * Table 1  - recalculated signed relative deviations (checkpoint A5)
  * Table 2  - Ca I 646.257 nm Stark/linewidth consistency check (A1/A2)
  * the electron-density scale check, Eqs. (3)-(4) (A2/A4)
  * the Fe/Ni zero-slope invertibility audit (A4)

and writes CSV copies of Tables 1-2 to ``output/``.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .audit import (
    LinearEquation,
    effective_stark_width,
    instrumental_fwhm,
    load_printed_values,
    ne_scale_check,
    quadrature_corrected_fwhm,
    signed_relative_deviation,
    stark_ne,
)


def table1_rows(data: dict) -> list[dict]:
    rows = []
    for element, vals in data["validation_table"]["elements"].items():
        rows.append(
            {
                "element": element,
                "icp_oes_ppm": vals["icp_oes"],
                "ne_estimate_ppm": vals["ne_estimate"],
                "delta_ne_percent": round(
                    signed_relative_deviation(vals["ne_estimate"], vals["icp_oes"]), 2
                ),
                "te_estimate_ppm": vals["te_estimate"],
                "delta_te_percent": round(
                    signed_relative_deviation(vals["te_estimate"], vals["icp_oes"]), 2
                ),
            }
        )
    return rows


def table2_rows(data: dict) -> list[dict]:
    stark = data["stark"]
    rows = []
    for sample, s in stark["samples"].items():
        ne_calc = stark_ne(s["fwhm_nm"], stark["w_s_nm"],
                           stark["normalization_exponent"]) / 1e16
        ratio = ne_calc / s["ne_comparison_1e16"]
        rows.append(
            {
                "sample": sample,
                "fwhm_nm": s["fwhm_nm"],
                "ne_calc_1e16_cm-3": round(ne_calc, 2),
                "ne_comparison_1e16_cm-3": s["ne_comparison_1e16"],
                "ratio_R": round(ratio, 2),
                "w_s_effective_nm": round(
                    effective_stark_width(
                        s["fwhm_nm"], s["ne_comparison_1e16"] * 1e16
                    ),
                    4,
                ),
            }
        )
    return rows


def _print_table(title: str, rows: list[dict]) -> None:
    print(f"\n=== {title} ===")
    if not rows:
        print("(empty)")
        return
    headers = list(rows[0].keys())
    widths = [
        max(len(h), *(len(str(r[h])) for r in rows)) for h in headers
    ]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    for r in rows:
        print("  ".join(str(r[h]).ljust(w) for h, w in zip(headers, widths)))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(output_dir: str = "output") -> None:
    data = load_printed_values()
    out = Path(output_dir)

    # --- A5: Table 1 ---------------------------------------------------
    t1 = table1_rows(data)
    _print_table("Table 1: recalculated signed relative deviations (A5)", t1)
    _write_csv(out / "table1_signed_deviations.csv", t1)
    band = data["validation_table"]["stated_agreement_interval_percent"]
    outside = [
        r["element"]
        for r in t1
        if abs(r["delta_ne_percent"]) > band or abs(r["delta_te_percent"]) > band
    ]
    print(f"Elements outside the stated +/-{band}% interval: {', '.join(outside)}")

    # --- A1/A2: Table 2 -------------------------------------------------
    t2 = table2_rows(data)
    _print_table("Table 2: Ca I 646.257 nm linewidth consistency (A1/A2)", t2)
    _write_csv(out / "table2_linewidth_check.csv", t2)

    instr = data["instrument"]
    w_inst = instrumental_fwhm(
        instr["diagnostic_wavelength_nm"], instr["conditioned_resolving_power"]
    )
    fwhm0 = data["stark"]["samples"]["S1-P1"]["fwhm_nm"]
    fwhm_corr = quadrature_corrected_fwhm(fwhm0, w_inst)
    change = (fwhm0 - fwhm_corr) / fwhm0 * 100
    print(
        f"Instrumental FWHM at R={instr['conditioned_resolving_power']}: "
        f"{w_inst:.4f} nm; quadrature correction changes the displayed "
        f"FWHM by {change:.2f}%. This assumes Gaussian widths; it is not a universal bound."
    )

    # --- A2/A4: electron-density scale check, Eqs. (3)-(4) ---------------
    print("\n=== Electron-density scale check (A2/A4) ===")
    ne = data["test_sample"]["ne_printed"]["value"]
    for element in ("Cd", "Zn"):
        coeffs = data["ne_concentration_equations"]["S1"][element]
        eq = LinearEquation(coeffs["a"], coeffs["b"])
        scales = ne_scale_check(eq, ne)
        printed = data["validation_table"]["elements"][element]["ne_estimate"]
        print(
            f"{element}: C(1e16 scale) = {scales[16]:.2f} ppm "
            f"(printed estimate {printed} ppm); "
            f"C(1e17 scale) = {scales[17]:.1f} ppm (does not reproduce table)"
        )

    # --- A4: Fe/Ni invertibility audit -----------------------------------
    print("\n=== Fe/Ni invertibility audit (A4) ===")
    for element in ("Fe", "Ni"):
        coeffs = data["ne_concentration_equations"]["S1"][element]
        eq = LinearEquation(coeffs["a"], coeffs["b"])
        status = "invertible" if eq.invertible else "NOT invertible (zero slope)"
        print(
            f"{element} (S1, N_e eq.): a={coeffs['a']}, b={coeffs['b']} -> {status}; "
            f"constant {coeffs['a']} vs test mantissa under the inferred 1e16 normalization "
            f"{data['test_sample']['ne_printed']['value']}"
        )
    te_const = data["te_concentration_equations"]["S1"]["Fe"]["a"]
    te_test = data["test_sample"]["te_reported_K"]
    print(
        f"T_e eq. constant {te_const} K vs reported test-sample "
        f"temperature {te_test} K"
    )

    print(f"\nCSV outputs written to {out.resolve()}/")


if __name__ == "__main__":  # pragma: no cover
    main()

