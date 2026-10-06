#!/usr/bin/env python3
"""Write the LaTeX table bodies of Supplementary Text S1 from the numerical outputs.

Reads ../outputs/*.csv|json and ../record/* and writes ../tables/*.tex, which
supplementary.tex includes. Run after worked_examples.py,
reconstruct_record.py and seeded_defects.py (run_all.py does this).
Standard library only.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
REC = HERE.parent / "record"
TAB = HERE.parent / "tables"


def sci(value: float, digits: int = 1) -> str:
    """LaTeX scientific notation, e.g. 5.0\\times10^{7}."""
    mant, exp = f"{value:.{digits}e}".split("e")
    return f"${mant}\\times10^{{{int(exp)}}}$"


def signed(value: float, digits: int = 1) -> str:
    text = f"{abs(value):.{digits}f}"
    if float(text) == 0:
        return f"${text}$"
    return f"${'+' if value > 0 else '-'}{text}$"


def write(name: str, rows: list[str]) -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / name).write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"wrote tables/{name} ({len(rows)} rows)")


def table_s1() -> None:
    with open(OUT / "table_linewidth.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    write("tableS1_linewidth.tex",
          [f"{r['G_over_W']} & {r['L_over_W_voigt']} & {r['L_over_W_quadrature']} & "
           f"{r['Ne_overestimate_percent_uncorrected']} & {r['Ne_overestimate_percent_quadrature']}\\\\"
           for r in rows])


def table_s2() -> None:
    record = json.loads((REC / "record.json").read_text())
    with open(REC / "line_intensities.csv", newline="", encoding="utf-8") as fh:
        raw = {r["line_id"]: [r[f"replicate_{i}"] for i in range(1, record["n_replicates"] + 1)]
               for r in csv.DictReader(fh)}
    rows = []
    for ln in record["lines"]:
        line_id = ln["id"].replace("_", "\\_")
        rows.append(f"{line_id} & {ln['species']} & {ln['wavelength_nm']:.2f} & {ln['E_i_eV']:.2f} & "
                    f"{ln['E_k_eV']:.2f} & {ln['g_k']} & {sci(ln['A_ki_s-1'])} & " + " & ".join(raw[ln["id"]]) + "\\\\")
    write("tableS2_lines.tex", rows)


def table_s3() -> None:
    summ = json.loads((OUT / "summary.json").read_text())
    rows = []
    for n in summ["elements"]:
        a5 = summ["A5"][n]
        u_c = 100 * a5["u_combined"]
        u_txt = f"{u_c:.1f}" if u_c >= 1 else f"{u_c:.2f}"
        rows.append(f"{n} & {100 * a5['reference']:.3f} & {100 * summ['A4']['mole_fraction_mean'][n]:.3f} & "
                    f"{100 * a5['mean']:.3f} & {signed(a5['signed_deviation_percent'])} & {a5['rsd_percent']:.1f} & "
                    f"{100 * a5['u_repeatability_of_mean']:.3f} & {100 * a5['u_inputs_monte_carlo']:.3f} & "
                    f"{u_txt} & {100 * a5['mc_p025']:.2f}--{100 * a5['mc_p975']:.2f} & {signed(a5['zeta'], 2)}\\\\")
    write("tableS3_summary.tex", rows)


def table_s4() -> None:
    """Effect of each single perturbation on the plasma parameters and mass fractions."""
    res = json.loads((OUT / "seeded_defects.json").read_text())
    names = res["elements"]
    iv = res["monte_carlo_95_interval_ratio"]
    rows = ["-- & -- & Baseline reconstruction & 1.000 & 1.000 & 1.000 & 1.000 & 1.000\\\\",
            "-- & -- & All assigned input uncertainties (95\\% interval)$^{\\,a}$ & -- & -- & "
            + " & ".join(f"{iv[n][0]:.3f}--{iv[n][1]:.3f}" for n in names) + "\\\\", "\\midrule"]
    last_family = None
    for r in res["scenarios"]:
        if last_family is not None and r["family"] != last_family:
            rows.append("\\midrule")
        last_family = r["family"]
        label = r["label"].replace("%", "\\%")
        rows.append(f"{r['id']} & {r['checkpoint']} & {label} & {r['n_e_ratio']:.3f} & {r['temperature_ratio']:.3f} & "
                    + " & ".join(f"{r['ratio_to_baseline'][n]:.3f}" for n in names) + "\\\\")
    write("tableS4_seeded.tex", rows)


def table_s5() -> None:
    """Indicators by which each perturbation could be noticed."""
    res = json.loads((OUT / "seeded_defects.json").read_text())
    names = res["elements"]
    lo, hi = res["saha_stark_ratio_95_range"]
    s_lo, s_hi = res["residual_sd_95_range"]
    base = res["baseline"]
    rows = [f"-- & Baseline reconstruction & {base['saha_stark_ratio']:.2f} & {base['residual_sd']:.3f} & "
            + " & ".join(signed(base["zeta_vs_reference"][n], 2) for n in names) + " & --\\\\",
            f"-- & 95\\% range from the input uncertainties$^{{\\,a}}$ & {lo:.2f}--{hi:.2f} & {s_lo:.3f}--{s_hi:.3f} & -- & -- & -- & --\\\\",
            "\\midrule"]
    last_family = None
    for r in res["scenarios"]:
        if last_family is not None and r["family"] != last_family:
            rows.append("\\midrule")
        last_family = r["family"]
        flags = [k for k in "DSR" if r[f"flag_{k}"]]
        label = r["label"].replace("%", "\\%")
        rows.append(f"{r['id']} & {label} & {r['saha_stark_ratio']:.2f} & {r['residual_sd']:.3f} & "
                    + " & ".join(signed(r["zeta_vs_reference"][n], 1) for n in names)
                    + f" & {', '.join(flags) if flags else 'none'}\\\\")
    write("tableS5_indicators.tex", rows)


def main() -> None:
    table_s1()
    table_s2()
    table_s3()
    table_s4()
    table_s5()


if __name__ == "__main__":
    main()
