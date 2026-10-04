#!/usr/bin/env python3
"""Consistency check between the text and the numerical outputs.

Author-side quality control. For every constructed number that is quoted in
the article (main.tex) or in Supplementary Text S1 (supplementary.tex), this
script recomputes the value from the files in ../outputs/ and ../record/,
formats it as it is printed, and confirms that the formatted string occurs in
the text. It also checks that every citation key resolves, that every
reference is cited, that figure files exist, and that the hard-coded
cross-references between the two documents point to the intended items.

Run after run_all.py:

    python3 check_manuscript.py

main.tex and references.bib are expected one level above the supplementary
folder; if they are absent, only the supplement is checked.
Standard library only.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPP_DIR = HERE.parent
PKG = SUPP_DIR.parent
OUT = SUPP_DIR / "outputs"
REC = SUPP_DIR / "record"

SUPP = (SUPP_DIR / "supplementary.tex").read_text(encoding="utf-8")
HAVE_MAIN = (PKG / "main.tex").exists() and (PKG / "references.bib").exists()
MAIN = (PKG / "main.tex").read_text(encoding="utf-8") if HAVE_MAIN else ""
BIB = (PKG / "references.bib").read_text(encoding="utf-8") if HAVE_MAIN else ""
SUPP_BIB = (SUPP_DIR / "references_supplement.bib").read_text(encoding="utf-8")

results: list[tuple[bool, str]] = []


def check(name: str, cond: bool) -> None:
    results.append((bool(cond), name))


def has(text: str, needle: str, where: str, what: str) -> None:
    check(f"{where}: {what} -> '{needle}'", needle in text)


def sci(value: float, digits: int = 2) -> str:
    mant, exp = f"{value:.{digits}e}".split("e")
    return f"{mant}\\times10^{{{int(exp)}}}"


def pct(ratio: float) -> str:
    """Rounded percentage change of a ratio to the baseline, without sign."""
    return f"{abs(100 * (ratio - 1)):.0f}"


def entries(bib: str) -> dict:
    return {m.group(1): m.group(0).strip() for m in re.finditer(r"@\w+\{([^,]+),.*?\n\}", bib, re.S)}


def env_number(text: str, env: str, label: str) -> int:
    """Position (1-based) of the environment that carries a label."""
    blocks = re.findall(rf"\\begin\{{{env}\}}.*?\\end\{{{env}\}}", text, re.S)
    for i, block in enumerate(blocks, start=1):
        if f"\\label{{{label}}}" in block:
            return i
    return -1


def main_checks(ex: dict, summ: dict, seeded: dict, scen: dict) -> None:
    names = summ["elements"]

    # ------------------------------------------------------------ A1
    a1 = {round(r["G_over_W"], 1): r for r in ex["A1"]["table"]}
    has(MAIN, f"overestimates $\\Ne$ by {a1[0.4]['ne_bias_uncorrected_percent']:.0f}\\%", "main A1", "uncorrected at G/W=0.4")
    has(MAIN, f"still overestimates it by {a1[0.4]['ne_bias_quadrature_percent']:.0f}\\%", "main A1", "quadrature at G/W=0.4")
    has(MAIN, f"reach {a1[0.8]['ne_bias_uncorrected_percent']:.0f}\\% and {a1[0.8]['ne_bias_quadrature_percent']:.0f}\\%", "main A1", "G/W=0.8")
    li = ex["A1"]["lorentzian_instrument"]["G_over_W_0.4"]
    has(MAIN, f"rise to {li['ne_bias_uncorrected_percent']:.0f}\\% and {li['ne_bias_quadrature_percent']:.0f}\\%", "main A1", "Lorentzian instrumental profile")
    record = json.loads((REC / "record.json").read_text())
    st = record["stark_line"]
    has(MAIN, f"$G/W={st['instrument_gaussian_fwhm_nm'] / st['observed_fwhm_nm']:.2f}$", "main A1", "G/W of the record")

    # ------------------------------------------------------------ A2
    a2 = ex["A2"]
    has(MAIN, f"{a2['kelvin_per_eV']:,.1f}~K", "main A2", "kelvin per eV")
    has(MAIN, f"${sci(a2['saha_prefactor_cm-3_K-1.5'])}\\,\\cmc\\,\\mathrm{{K}}^{{-3/2}}$", "main A2", "Saha prefactor (K)")
    has(MAIN, f"${sci(a2['saha_prefactor_cm-3_eV-1.5'])}\\,\\cmc\\,\\mathrm{{eV}}^{{-3/2}}$", "main A2", "Saha prefactor (eV)")
    sens = ex["A4_sensitivity"]
    has(MAIN, f"by a factor of {sens['Saha_factor_for_T_plus_5pct_Eion_6eV']:.1f} to {sens['Saha_factor_for_T_plus_5pct_Eion_9eV']:.1f}", "main A2", "Saha factor for +5% T")
    check("main A2: sensitivities -3.5 to -7 and 8.5 to 12",
          round(sens["dln_n_dlnT_Ek_3eV"], 1) == -3.5 and round(sens["dln_n_dlnT_Ek_6eV"]) == -7
          and round(sens["dln_Saha_dlnT_Eion_6eV"], 1) == 8.5 and round(sens["dln_Saha_dlnT_Eion_9eV"]) == 12
          and "$-3.5$ to $-7$" in MAIN and "8.5 to 12" in MAIN)

    # ------------------------------------------------------------ A3
    a3 = ex["A3"]
    has(MAIN, f"${sci(a3['threshold_cm3'])}\\,\\cmc$", "main A3", "McWhirter threshold")
    has(MAIN, f"${sci(a3['threshold_with_eV_inserted_cm3'])}\\,\\cmc$", "main A3", "threshold with eV inserted")
    has(MAIN, f"lower by a factor of {a3['ratio']:.0f}", "main A3", "ratio")
    has(MAIN, f"inserting the same temperature as {a3['temperature_eV']:.4f}", "main A3", "temperature in eV")

    # ------------------------------------------------------------ A4
    with open(OUT / "table_basis.csv", newline="", encoding="utf-8") as fh:
        basis = list(csv.DictReader(fh))
    for r in basis:
        row = (f"{r['element']} & {float(r['molar_mass_g_mol']):g}" if not r["material"].startswith("Constructed")
               else f"{r['element']} & {float(r['molar_mass_g_mol']):.1f}")
        row += f" & {r['mass_percent']} & {r['mole_percent']} & {float(r['reported_over_true_if_unconverted']):.2f}\\\\"
        has(MAIN, row, "main Table 2", f"{r['material'].split(' ')[0]} {r['element']}")
    low = ex["A4_lowering"]
    has(MAIN, f"gives {low['electrons_only']['lowering_eV']:.2f}--{low['electrons_and_singly_charged_ions']['lowering_eV']:.2f}~eV", "main A4", "ionization-energy lowering")
    check("main A4: lowering raises the Saha ratio by about 10%",
          1.07 < low["electrons_only"]["saha_ratio_factor"] < low["electrons_and_singly_charged_ions"]["saha_ratio_factor"] < 1.12
          and "raises the Saha ratio by about 10\\%" in MAIN)
    clo = ex["A4_closure"]
    has(MAIN, f"add up to {clo['detected_total_mass_percent']:.1f}\\% of the dry mass", "main A4", "detected total")
    has(MAIN, f"returns {clo['subset_normalized_percent']['K']:.0f}\\% for an element that is present at "
              f"{clo['whole_sample_mg_per_kg']['K'] / 1e4:.1f}\\%", "main A4", "subset K")
    inv = ex["A4_inverse"]
    has(MAIN, f"this factor is {inv['amplification']:.0f}", "main A4", "amplification")
    lo, hi = inv["rel_spread_from_one_digit_slope_percent"]
    has(MAIN, f"$-{abs(lo):.0f}\\%$ to $+{hi:.0f}\\%$", "main A4", "one-digit slope spread")
    has(MAIN, f"becomes {100 * inv['rel_uncertainty_C']:.0f}\\% in concentration", "main A4", "amplified uncertainty")

    # ------------------------------------------------------------ A5 generic
    a5 = ex["A5"]
    has(MAIN, f"mean of {a5['mean']:.1f} and a standard deviation of {a5['sd']:.2f} (RSD {a5['rsd_percent']:.1f}\\%)", "main A5", "replicates")
    has(MAIN, f"reference value of {a5['reference']:.1f} that has a standard uncertainty of {a5['u_reference']:.2f}", "main A5", "reference")
    has(MAIN, f"$\\delta=+{a5['signed_deviation_percent']:.1f}\\%$", "main A5", "deviation")
    has(MAIN, f"$0.60/\\sqrt{{5}}={a5['u_repeatability_of_mean']:.2f}$", "main A5", "standard deviation of the mean")
    has(MAIN, f"$\\zeta={a5['zeta_repeatability_only']:.1f}$", "main A5", "zeta with repeatability only")
    has(MAIN, f"of the result ({a5['u_full_assumed']:.2f}), $\\zeta={a5['zeta_full_uncertainty']:.1f}$", "main A5", "zeta with the full uncertainty")

    # ------------------------------------------------------------ record
    reported = json.loads((REC / "reported_values.json").read_text())
    det, mcb = reported["deterministic"], reported["monte_carlo_based"]
    has(MAIN, f"$T={det['A2_temperature_K']['value']:.0f}$~K (standard deviation of the five replicates, "
              f"{det['A2_temperature_replicate_sd_K']['value']:.0f}~K)", "main record", "temperature")
    has(MAIN, f"$\\Ne={summ['A1']['n_e_cm3'] / 1e17:.2f}\\times10^{{17}}\\,\\cmc$, and mass fractions", "main record", "electron density")
    w = summ["A4"]["mass_fraction_mean"]
    has(MAIN, "mass fractions of " + ", ".join(f"{100 * w[n]:.2f}\\%" for n in names[:2]) + f", and {100 * w[names[2]]:.2f}\\%", "main record", "mass fractions")
    r5 = summ["A5"]
    has(MAIN, "RSDs are " + ", ".join(f"{r5[n]['rsd_percent']:.1f}\\%" for n in names[:2]) + f", and {r5[names[2]]['rsd_percent']:.1f}\\%", "main record", "RSDs")
    mc = summ["monte_carlo"]
    has(MAIN, f"uncertainties of {mcb['A2_temperature_propagated_u_K']['value']:.0f}~K for $T$ and {mc['n_e_rel_sd_percent']:.0f}\\% for $\\Ne$", "main record", "propagated u(T) and u(Ne)")
    has(MAIN, f"uncertainties of {r5['X']['u_combined_rel_percent']:.0f}\\%, {r5['Y']['u_combined_rel_percent']:.1f}\\%, and {r5['Z']['u_combined_rel_percent']:.1f}\\%", "main record", "combined uncertainties")
    check("main record: SD of the replicate temperatures is about five times smaller than u(T)",
          round(mc["temperature_K_sd"] / summ["A2"]["temperature_K_sd"]) == 5 and "about five times smaller" in MAIN)
    check("main record: combined uncertainty of X is nine times the replicate RSD",
          round(r5["X"]["u_combined_rel_percent"] / r5["X"]["rsd_percent"]) == 9 and "nine times the replicate RSD" in MAIN)
    has(MAIN, f"95\\% interval from {100 * r5['X']['mc_p025']:.1f}\\% to {100 * r5['X']['mc_p975']:.1f}\\%", "main record", "95% interval of X")
    has(MAIN, f"a repeatability of {r5['X']['rsd_percent']:.1f}\\% coexists with a combined standard uncertainty of {r5['X']['u_combined_rel_percent']:.0f}\\%", "main A5", "pointer to the record")

    def count(d: dict) -> int:
        return sum(1 if "value" in v else len(v) for v in d.values())

    check("main record: 18 deterministic and 7 Monte Carlo-based reported values",
          count(det) == 18 and count(mcb) == 7 and "its 18 deterministic reported values" in MAIN
          and "its 7 Monte Carlo-based values" in MAIN)
    check("main record: 21 lines, 5 replicates, 3% noise", len(record["lines"]) == 21 and record["n_replicates"] == 5
          and record["generation"]["intensity_rel_sd"] == 0.03
          and "generated 21 line intensities in five replicates with 3\\% relative Gaussian noise" in MAIN)
    sx = summ["A3"]["saha_ion_to_neutral_replicate_1"]["X"]
    check("main record: about 90% of X is ionized", 0.88 < sx / (1 + sx) < 0.92 and "about 90\\% of X is ionized" in MAIN)

    # ------------------------------------------------------------ scenarios
    slips = [r for r in seeded["scenarios"] if r["family"] == "slip"]
    check("main scenarios: 13 perturbations, 9 slips", len(seeded["scenarios"]) == 13 and len(slips) == 9
          and "applied 13 single perturbations" in MAIN and "Nine represent convention or reporting slips" in MAIN)
    x = {k: v["ratio_to_baseline"]["X"] for k, v in scen.items()}
    has(MAIN, f"which is {0.05 * summ['A2']['temperature_K_mean'] / mc['temperature_K_sd']:.1f} times the standard uncertainty propagated here", "main scenarios", "U1 in units of u(T)")
    check("main scenarios: U4 changes the composition by less than 1%",
          all(abs(v - 1) < 0.01 for v in scen["U4"]["ratio_to_baseline"].values())
          and "it changes the composition by less than 1\\% here" in MAIN)
    has(MAIN, f"by factors of {x['C5']:.2f} (C5) and {x['C6']:.1f} (C6)", "main scenarios", "C5 and C6")
    has(MAIN, f"lowers X by {pct(x['C3'])}\\% (C3), and the reverse slip raises it by {pct(x['C4'])}\\% (C4)", "main scenarios", "C3 and C4")
    has(MAIN, f"multiplies X by {x['C8']:.1f} (C8)", "main scenarios", "C8")
    check("main scenarios: C9 doubles X and reduces Z to less than a third",
          round(x["C9"]) == 2 and scen["C9"]["ratio_to_baseline"]["Z"] < 1 / 3
          and "doubles X and reduces Z to less than a third (C9)" in MAIN)
    has(MAIN, f"lowers X by {pct(x['C1'])}\\% and {pct(x['C2'])}\\%", "main scenarios", "C1 and C2")
    has(MAIN, f"(C7) lowers it by {pct(x['C7'])}\\%", "main scenarios", "C7")
    has(MAIN, f"U1 raises X by {pct(x['U1'])}\\% and U2 by {pct(x['U2'])}\\%", "main scenarios", "U1 and U2")
    out = [r["id"] for r in slips if r["outside_95_interval"]["X"]]
    lo_x, hi_x = seeded["monte_carlo_95_interval_ratio"]["X"]
    check("main scenarios: six of nine slips move X outside the 95% interval (C3-C6, C8, C9)",
          out == ["C3", "C4", "C5", "C6", "C8", "C9"]
          and "six of the nine slips (C3--C6, C8, and C9) move X outside the 95\\% interval" in MAIN
          and "six of nine seeded convention slips shift a minor element outside the 95\\% interval" in MAIN)
    has(MAIN, f"extends from {lo_x:.2f} to {hi_x:.2f} times the baseline value", "main scenarios", "95% interval of X as a ratio")
    uncs = [r for r in seeded["scenarios"] if r["family"] == "uncertainty"]
    check("main scenarios: no comparison scenario leaves the 95% interval",
          not any(any(r["outside_95_interval"].values()) for r in uncs)
          and "whereas none of the four comparison scenarios does" in MAIN)
    y_out = [r["id"] for r in seeded["scenarios"] if abs(r["ratio_to_baseline"]["Y"] - 1) >= 0.05]
    check("main scenarios: Y within 5% in 11 of 13; exceptions C6 and C8",
          y_out == ["C6", "C8"] and "within 5\\% of its baseline value in 11 of them; the exceptions are C6 and C8" in MAIN
          and "the major element moved by less than 5\\% in all but two" in MAIN)
    check("main conclusions: X changes by factors between 0.2 and 6 in the six large slips",
          round(min(x[k] for k in out), 1) == 0.2 and round(max(x[k] for k in out)) == 6
          and "by factors between 0.2 and 6" in MAIN)

    # ------------------------------------------------------------ indicators
    lo95, hi95 = seeded["saha_stark_ratio_95_range"]
    has(MAIN, f"the ratio is {seeded['baseline']['saha_stark_ratio']:.2f}, but the input uncertainties alone give it a 95\\% range of {lo95:.2f}--{hi95:.2f}", "main indicators", "density ratio and its range")
    has(MAIN, f"({scen['C5']['saha_stark_ratio']:.2f} and {scen['C6']['saha_stark_ratio']:.1f})", "main indicators", "tenfold slips")
    has(MAIN, f"({scen['C3']['saha_stark_ratio']:.2f} and {scen['C4']['saha_stark_ratio']:.2f})", "main indicators", "twofold slips")
    s_lo, s_hi = seeded["residual_sd_95_range"]
    has(MAIN, f"In the baseline, it is {seeded['baseline']['residual_sd']:.2f} and reflects the intensity noise alone", "main indicators", "baseline scatter")
    has(MAIN, f"would produce a scatter of {s_lo:.2f}--{s_hi:.2f}", "main indicators", "range of the scatter")
    has(MAIN, f"the scatter rises to {scen['C7']['residual_sd']:.2f}, above this range", "main indicators", "scatter under C7")
    flagged_d = [r["id"] for r in slips if r["flag_D"]]
    flagged_s = [r["id"] for r in slips if r["flag_S"]]
    flagged_r = [r["id"] for r in slips if r["flag_R"]]
    flagged_any = [r["id"] for r in slips if r["flagged_by_any"]]
    rep_slips = [r["id"] for r in slips if r["flag_R_repeatability_only"]]
    rep_uncs = [r["id"] for r in uncs if r["flag_R_repeatability_only"]]
    check("main indicators: with repeatability only, all nine slips and U1-U3 exceed |zeta| = 2",
          len(rep_slips) == 9 and rep_uncs == ["U1", "U2", "U3"]
          and "every slip exceeds $|\\zeta|=2$, but so do the comparison scenarios U1--U3" in MAIN)
    check("main indicators: no comparison scenario is flagged by any indicator",
          not any(r["flagged_by_any"] for r in uncs))
    check("main indicators: density ratio flags C3-C6, scatter flags C7 only",
          flagged_d == ["C3", "C4", "C5", "C6"] and flagged_s == ["C7"])
    check("main indicators: five slips flagged by the reference, four pass, C4 among them",
          flagged_r == ["C3", "C5", "C6", "C8", "C9"] and "Five slips give $|\\zeta|>2$" in MAIN and "The other four pass" in MAIN)
    has(MAIN, f"X is {pct(x['C4'])}\\% too high but $\\zeta={scen['C4']['zeta_vs_reference']['X']:.1f}$", "main indicators", "C4 passes")
    check("main indicators: seven of nine flagged, C1 and C2 escape all three",
          len(flagged_any) == 7 and set(r["id"] for r in slips) - set(flagged_any) == {"C1", "C2"}
          and "flag seven of the nine slips" in MAIN and "the two linewidth slips escape all three" in MAIN)
    check("main indicators: C8 and C9 keep the baseline values of both internal indicators",
          all(abs(scen[k]["saha_stark_ratio"] - seeded["baseline"]["saha_stark_ratio"]) < 1e-9
              and abs(scen[k]["residual_sd_ratio"] - 1) < 1e-9 for k in ("C8", "C9"))
          and "both keep their baseline values" in MAIN)

    # ------------------------------------------------------------ citations, files, cross-references
    keys = set(entries(BIB))
    cited = {k.strip() for c in re.findall(r"\\cite\{([^}]*)\}", MAIN) for k in c.split(",")}
    check(f"main: all {len(cited)} citation keys resolve", cited <= keys)
    check(f"main: every one of the {len(keys)} bibliography entries is cited", keys <= cited)
    for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", MAIN):
        check(f"main: figure file {fig} exists", (PKG / fig).exists())
    labels = set(re.findall(r"\\label\{([^}]+)\}", MAIN))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", MAIN))
    check("main: every \\ref has a \\label", refs <= labels)
    abstract = re.search(r"\\abstract\{(.*?)\}\n\n\\keyword", MAIN, re.S).group(1)
    n_words = len(abstract.replace("---", " ").split())
    check(f"main: abstract has {n_words} words (limit 200)", n_words <= 200)
    n_kw = len(re.search(r"\\keyword\{(.*?)\}", MAIN, re.S).group(1).split(";"))
    check(f"main: {n_kw} keywords (3 to 10)", 3 <= n_kw <= 10)
    for item in ("Table~S1", "Table~S2", "Table~S3", "Table~S4", "Tables~S4 and~S5", "Table~S5", "Figure~S1",
                 "Data~S1", "Code~S1", "Supplementary Text~S1"):
        check(f"main: cites {item.replace('~', ' ')}", item in MAIN)

    # hard-coded references from the supplement to the main text
    eq = {lab: env_number(MAIN, "equation", lab) for lab in
          ("eq:boltzmann", "eq:saha", "eq:closure", "eq:stark", "eq:voigt", "eq:mcwhirter", "eq:massmole", "eq:delta", "eq:zeta")}
    check("cross-reference: supplement's Equations (1)-(9) match the main text",
          [eq[k] for k in ("eq:boltzmann", "eq:saha", "eq:closure", "eq:stark", "eq:voigt", "eq:mcwhirter", "eq:massmole", "eq:delta", "eq:zeta")]
          == list(range(1, 10)))
    check("cross-reference: Table 2 is the basis table and Table 4 the reporting record",
          env_number(MAIN, "table", "tab:basis") == 2 and env_number(MAIN, "table", "tab:record") == 4)
    check("cross-reference: Figure 2 is the linewidth figure and Figure 4 the perturbation figure",
          env_number(MAIN, "figure", "fig:linewidth") == 2 and env_number(MAIN, "figure", "fig:sensitivity") == 4)
    sections = re.findall(r"\\(section|subsection)\{[^}]*\}(?:\\label\{([^}]+)\})?", MAIN)
    sec = sub = 0
    number = {}
    for kind, lab in sections:
        if kind == "section":
            sec, sub = sec + 1, 0
        else:
            sub += 1
        if lab:
            number[lab] = f"{sec}.{sub}" if kind == "subsection" else f"{sec}"
    check("cross-reference: Section 3.5 is the validation checkpoint", number.get("sec:a5") == "3.5" and "Section~3.5" in SUPP)


def supplement_checks(ex: dict, summ: dict, seeded: dict, scen: dict) -> None:
    names = summ["elements"]
    near = ex["A1"]["near_resolution"]
    has(SUPP, f"$\\Delta\\lambda_{{\\mathrm{{S}}}}={near['lorentz_fwhm_nm']:.3f}$~nm", "supp A1", "near-resolution Stark width")
    has(SUPP, f"by a factor of {near['density_overestimate_factor_if_uncorrected']:.1f}", "supp A1", "uncorrected factor")
    has(SUPP, f"by a factor of {near['density_overestimate_factor_if_quadrature']:.1f}", "supp A1", "quadrature factor")
    li = ex["A1"]["lorentzian_instrument"]["G_over_W_0.4"]
    has(SUPP, f"by {li['ne_bias_uncorrected_percent']:.0f}\\%, and the quadrature-subtracted width by {li['ne_bias_quadrature_percent']:.0f}\\%", "supp A1", "Lorentzian instrumental profile")
    appr = ex["A1"]["approximation_check"]
    check("supp A1: approximation accuracy better than 0.03%", appr["max_relative_deviation_percent"] < 0.03
          and "to better than 0.03\\%" in SUPP)
    has(SUPP, f"an exact inversion gives {appr['record_point']['lorentz_fwhm_exact_nm']:.5f}~nm where Equation~(\\ref{{eq:inverse}}) gives "
              f"{appr['record_point']['lorentz_fwhm_approximation_nm']:.5f}~nm", "supp A1", "exact inversion at the record point")

    a2 = ex["A2"]
    has(SUPP, f"$\\kB T={a2['kT_eV']:.4f}$~eV", "supp A2", "kT")
    has(SUPP, f"$-{abs(a2['slope_ln_per_eV']):.4f}$~eV$^{{-1}}$", "supp A2", "ln slope")
    has(SUPP, f"$-{abs(a2['slope_log10_per_eV']):.4f}$~eV$^{{-1}}$", "supp A2", "log10 slope")
    has(SUPP, f"{a2['temperature_if_log10_slope_read_as_ln_K']:,.0f}~K", "supp A2", "log10 slip temperature")
    has(SUPP, f"${sci(a2['saha_prefactor_cm-3_K-1.5'])}\\,\\cmc\\,\\mathrm{{K}}^{{-3/2}}$", "supp A2", "Saha prefactor (K)")
    has(SUPP, f"${sci(a2['saha_prefactor_cm-3_eV-1.5'])}\\,\\cmc\\,\\mathrm{{eV}}^{{-3/2}}$", "supp A2", "Saha prefactor (eV)")
    has(SUPP, f"={sci(a2['saha_prefactor_ratio'])}$", "supp A2", "ratio of the prefactors")
    sens = ex["A4_sensitivity"]
    has(SUPP, "factors of " + ", ".join(f"{sens[f'Saha_factor_for_T_plus_5pct_Eion_{e}eV']:.2f}" for e in (6, 7, 8))
        + f", and {sens['Saha_factor_for_T_plus_5pct_Eion_9eV']:.2f}", "supp A2", "exact Saha factors")
    a3 = ex["A3"]
    has(SUPP, f"${sci(a3['threshold_cm3'])}\\,\\cmc$", "supp A3", "threshold")
    has(SUPP, f"${sci(a3['threshold_with_eV_inserted_cm3'])}\\,\\cmc$", "supp A3", "threshold with eV inserted")
    has(SUPP, f"={a3['ratio']:.1f}$", "supp A3", "ratio")

    low = ex["A4_lowering"]
    e1, e2 = low["electrons_only"], low["electrons_and_singly_charged_ions"]
    has(SUPP, f"$\\lambda_{{\\mathrm{{D}}}}={e1['debye_length_nm']:.1f}$ and {e2['debye_length_nm']:.1f}~nm", "supp A4", "Debye lengths")
    has(SUPP, f"$\\Delta E_{{\\mathrm{{ion}}}}={e1['lowering_eV']:.3f}$ and {e2['lowering_eV']:.3f}~eV", "supp A4", "lowering")
    has(SUPP, f"by factors of {e1['saha_ratio_factor']:.2f} and {e2['saha_ratio_factor']:.2f}", "supp A4", "Saha factors of the lowering")
    clo = ex["A4_closure"]
    has(SUPP, f"add up to {clo['detected_total_mg_per_kg']:,.0f}~mg~kg$^{{-1}}$, or {clo['detected_total_mass_percent']:.2f}\\% of the dry mass", "supp A4", "detected total")
    sub = clo["subset_normalized_percent"]
    has(SUPP, "returns " + ", ".join(f"{sub[k]:.1f}\\% {k}" for k in ("K", "Ca", "Mg", "P", "S")) + f", and {sub['Fe']:.1f}\\% Fe", "supp A4", "subset fractions")
    has(SUPP, f"mass fractions, {clo['scale_factor_subset_to_whole']:.4f},", "supp A4", "scale factor")
    inv = ex["A4_inverse"]
    has(SUPP, f"$a={inv['a']:.2f}$, $b={inv['b']:.3f}$ per mass percent, and $C={inv['C']:.1f}\\%$, $y={inv['y']:.2f}$", "supp A4", "inverse relation")
    has(SUPP, f"between {inv['C_if_slope_rounded_up']:.2f}\\% and {inv['C_if_slope_rounded_down']:.2f}\\%", "supp A4", "C range")
    a5 = ex["A5"]
    has(SUPP, ", ".join(f"{v:.1f}" for v in a5["replicates"][:4]) + f", and {a5['replicates'][4]:.1f}", "supp A5", "replicates")
    has(SUPP, f"mean of {a5['mean']:.1f}, a standard deviation of {a5['sd']:.2f}, and a relative standard deviation (RSD) of {a5['rsd_percent']:.1f}\\%", "supp A5", "statistics")
    has(SUPP, f"$\\zeta={a5['zeta_repeatability_only']:.1f}$; with a relative standard uncertainty of 6\\% of the result ({a5['u_full_assumed']:.2f}), $\\zeta={a5['zeta_full_uncertainty']:.1f}$", "supp A5", "zeta values")

    # record
    record = json.loads((REC / "record.json").read_text())
    st = record["stark_line"]
    has(SUPP, f"$\\omega={st['stark_parameter_nm']:.4f}$~nm (HWHM)", "supp record", "Stark parameter")
    has(SUPP, f"observed width of {st['observed_fwhm_nm']:.5f}~nm", "supp record", "stored observed width")
    line = next(ln for ln in record["lines"] if ln["id"] == st["line_id"])
    has(SUPP, f"is {st['line_id'].replace('_', chr(92) + '_')} ({line['wavelength_nm']:.2f}~nm)", "supp record", "diagnostic line")
    has(SUPP, f"seed {record['generation']['seed']}", "supp record", "noise seed")
    ref = record["reference"]
    has(SUPP, "standard uncertainties of " + ", ".join(f"{100 * ref['standard_uncertainty'][n]:.2f}" for n in names[:2])
        + f", and {100 * ref['standard_uncertainty'][names[2]]:.2f} percentage points", "supp record", "reference uncertainties")
    a1s = summ["A1"]
    has(SUPP, f"$\\Delta\\lambda_{{\\mathrm{{S}}}}={a1s['stark_fwhm_nm']:.4f}$~nm and", "supp record", "Stark width")
    has(SUPP, f"${a1s['n_e_if_width_uncorrected_cm3'] / 1e17:.2f}\\times10^{{17}}\\,\\cmc$", "supp record", "uncorrected density")
    has(SUPP, f"${a1s['n_e_if_quadrature_cm3'] / 1e17:.2f}\\times10^{{17}}\\,\\cmc$", "supp record", "quadrature density")
    reported = json.loads((REC / "reported_values.json").read_text())
    det, mcb = reported["deterministic"], reported["monte_carlo_based"]
    has(SUPP, f"The temperature is {det['A2_temperature_K']['value']:.0f}~K, with a standard deviation of {det['A2_temperature_replicate_sd_K']['value']:.0f}~K", "supp record", "temperature")
    has(SUPP, f"is ${det['A3_mcwhirter_threshold_1e15_cm3']['value']:.2f}\\times10^{{15}}\\,\\cmc$, a factor of {summ['A3']['ne_over_threshold']:.0f} below", "supp record", "McWhirter threshold")
    ratios = summ["A3"]["ne_saha_over_ne_stark_replicates"]
    has(SUPP, f"{summ['A3']['ne_saha_over_ne_stark_mean']:.2f} times the Stark value on average ({min(ratios):.2f} to {max(ratios):.2f}", "supp record", "Saha/Stark")
    has(SUPP, f"slope corresponds to {round(summ['A2']['temperature_K_replicates'][0], -1):.0f}~K", "supp record", "replicate-1 temperature")

    def count(d: dict) -> int:
        return sum(1 if "value" in v else len(v) for v in d.values())

    check("supp record: 25 reported values (18 deterministic, 7 Monte Carlo-based)",
          count(det) == 18 and count(mcb) == 7 and "contains 25 values. The 18 deterministic values" in SUPP and "The 7 values" in SUPP)
    mc = summ["monte_carlo"]
    cfg = record["uncertainty_budget"]["monte_carlo"]
    has(SUPP, f"with {cfg['draws']:,} draws", "supp MC", "number of draws")
    has(SUPP, f"uncertainties of {mcb['A2_temperature_propagated_u_K']['value']:.0f}~K ({mc['temperature_rel_sd_percent']:.1f}\\%) for the temperature and {mc['n_e_rel_sd_percent']:.0f}\\% for the electron density", "supp MC", "u(T), u(Ne)")
    chk = mc["independent_seed_check"]
    worst = max(abs(v - 1) for v in chk["sd_ratio_to_documented_seed"].values())
    check("supp MC: independent seed reproduces u_in within 1.1%", worst <= 0.0115
          and f"{chk['draws']:,} draws reproduces the three values of $u_{{\\mathrm{{in}}}}$ within 1.1\\%" in SUPP)
    r5 = summ["A5"]
    has(SUPP, f"its mean is {100 * r5['X']['mc_mean']:.2f}\\%, its median {100 * r5['X']['mc_p50']:.2f}\\%, and its 95\\% interval extends from "
              f"{100 * r5['X']['mc_p025']:.2f}\\% to {100 * r5['X']['mc_p975']:.2f}\\%", "supp MC", "skewed distribution of X")
    dev = cfg["check_deviates"]
    has(SUPP, f"the first three deviates are $-{abs(dev[0]):.6f}$, {dev[1]:.6f}, and {dev[2]:.6f}", "supp MC", "check deviates of the generator")
    has(SUPP, f"random.Random({cfg['seed']}).random()", "supp MC", "generator call")
    has(SUPP, f"uncertainty is {r5['X']['u_combined_rel_percent']:.0f}\\%, compared with a replicate RSD of {r5['X']['rsd_percent']:.1f}\\% and a deviation from the reference of $-{abs(r5['X']['signed_deviation_percent']):.1f}\\%$", "supp MC", "X summary")

    # scenarios
    w = summ["A4"]["mass_fraction_mean"]
    has(SUPP, "baseline value (" + ", ".join(f"{100 * w[n]:.3f}\\%" for n in names[:2]) + f", and {100 * w[names[2]]:.3f}\\%)", "supp scenarios", "baseline mass fractions")
    has(SUPP, f"corresponds to {0.05 * summ['A2']['temperature_K_mean'] / mc['temperature_K_sd']:.1f} times the propagated standard uncertainty", "supp scenarios", "U1")
    ys = sorted((r["ratio_to_baseline"]["Y"], r["id"]) for r in seeded["scenarios"])
    inside = [v for v, _ in ys if abs(v - 1) < 0.05]
    has(SUPP, f"between {inside[0]:.3f} and {inside[-1]:.3f} in {len(inside)} of the {len(ys)} scenarios", "supp scenarios", "Y range")
    has(SUPP, f"C6 ({scen['C6']['ratio_to_baseline']['Y']:.3f}) and C8 ({scen['C8']['ratio_to_baseline']['Y']:.3f})", "supp scenarios", "Y exceptions")
    has(SUPP, f"changes the fitted temperature by $-{abs(100 * (scen['U4']['temperature_ratio'] - 1)):.1f}\\%$", "supp scenarios", "U4 temperature")
    check("supp scenarios: U4 changes the composition by less than 1%",
          all(abs(v - 1) < 0.01 for v in scen["U4"]["ratio_to_baseline"].values()))
    has(SUPP, f"The baseline scatter of {seeded['baseline']['residual_sd']:.3f} reflects", "supp indicators", "baseline scatter")
    s_lo, s_hi = seeded["residual_sd_95_range"]
    has(SUPP, f"a scatter of about {mc['residual_sd_p50']:.2f} (95\\% range {s_lo:.3f}--{s_hi:.3f})", "supp indicators", "scatter under the input uncertainties")
    val = seeded["validation_test"]
    has(SUPP, f"({val['draws_per_scenario']:,} draws per scenario; the generator is restarted with seed {val['seed']} for every scenario)", "supp indicators", "validation Monte Carlo")
    has(SUPP, f"under which it rises to {scen['C7']['residual_sd']:.3f}, {scen['C7']['residual_sd_ratio']:.1f} times the baseline value", "supp indicators", "scatter under C7")
    has(SUPP, f"Under U1, the scatter about the imposed slope is {scen['U1']['residual_sd']:.3f}, inside the range", "supp indicators", "scatter under U1")
    slips = [r for r in seeded["scenarios"] if r["family"] == "slip"]
    uncs = [r for r in seeded["scenarios"] if r["family"] == "uncertainty"]
    check("supp scenarios: six slips move X outside the 95% interval; comparison scenarios stay inside",
          [r["id"] for r in slips if r["outside_95_interval"]["X"]] == ["C3", "C4", "C5", "C6", "C8", "C9"]
          and not any(any(r["outside_95_interval"].values()) for r in uncs)
          and "move X outside the 95\\% interval of the propagated input uncertainties; C1, C2, and C7 stay inside it, as do the four comparison scenarios" in SUPP)
    check("supp indicators: repeatability-only zeta flags all nine slips and U1, U2, U3",
          all(r["flag_R_repeatability_only"] for r in slips)
          and [r["id"] for r in uncs if r["flag_R_repeatability_only"]] == ["U1", "U2", "U3"]
          and "exceeds 2 for all nine slips, but also for U1, U2, and U3" in SUPP)
    lo95, hi95 = seeded["saha_stark_ratio_95_range"]
    has(SUPP, f"({scen['C3']['saha_stark_ratio']:.2f} and {scen['C4']['saha_stark_ratio']:.2f} against a range of {lo95:.2f}--{hi95:.2f})", "supp indicators", "twofold slips")
    has(SUPP, f"X is {pct(scen['C4']['ratio_to_baseline']['X'])}\\% too high but $\\zeta_{{\\mathrm{{X}}}}={scen['C4']['zeta_vs_reference']['X']:.1f}$", "supp indicators", "C4 passes")

    # check counts and versions
    logs = [(OUT / f).read_text().splitlines()[0] for f in
            ("check_log_examples.txt", "check_log_record.txt", "check_log_seeded_defects.txt")]
    counts = [int(l.split()[0]) for l in logs]
    check(f"supp: check counts {counts} are quoted and sum to {sum(counts)}",
          f"perform {sum(counts)} automated checks: {counts[0]} on the worked examples" in SUPP
          and f"{counts[1]} on the record, of which 25 confirm the reported values and {counts[1] - 25} test" in SUPP
          and f"and {counts[2]} on the expected" in SUPP)
    req = (HERE / "requirements.txt").read_text()
    versions = dict(re.findall(r"^(numpy|matplotlib)==([\d.]+)", req, re.M))
    check("supp: NumPy and Matplotlib versions agree with requirements.txt",
          f"NumPy~{versions.get('numpy')}" in SUPP and f"Matplotlib~{versions.get('matplotlib')}" in SUPP)

    # citations and files
    supp_entries = entries(SUPP_BIB)
    cited = {k.strip() for c in re.findall(r"\\cite\{([^}]*)\}", SUPP) for k in c.split(",")}
    check(f"supp: all {len(cited)} citation keys resolve in references_supplement.bib", cited <= set(supp_entries))
    check("supp: every entry of references_supplement.bib is cited", set(supp_entries) <= cited)
    if HAVE_MAIN:
        main_entries = entries(BIB)
        check("supp: reference entries are identical to those of the article",
              all(k in main_entries and main_entries[k] == v for k, v in supp_entries.items()))
    for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", SUPP):
        check(f"supp: figure file {fig} exists", (SUPP_DIR / fig).exists())
    for tab in re.findall(r"\\tabinput\{([^}]+)\}", SUPP):
        check(f"supp: table body {tab} exists", (SUPP_DIR / tab).exists())
    check("supp: five tables and one figure", len(re.findall(r"\\begin\{table\}", SUPP)) == 5
          and len(re.findall(r"\\begin\{figure\}", SUPP)) == 1)
    labels = set(re.findall(r"\\label\{([^}]+)\}", SUPP))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", SUPP))
    check("supp: every \\ref has a \\label", refs <= labels)


def main() -> int:
    ex = json.loads((OUT / "worked_examples.json").read_text())
    summ = json.loads((OUT / "summary.json").read_text())
    seeded = json.loads((OUT / "seeded_defects.json").read_text())
    scen = {r["id"]: r for r in seeded["scenarios"]}
    if HAVE_MAIN:
        main_checks(ex, summ, seeded, scen)
    supplement_checks(ex, summ, seeded, scen)

    n_ok = sum(ok for ok, _ in results)
    lines = [f"{n_ok} of {len(results)} text consistency checks passed."
             + ("" if HAVE_MAIN else " (main.tex not found: supplement only)"), ""]
    lines += [f"{'PASS' if ok else 'FAIL'}: {name}" for ok, name in results]
    text = "\n".join(lines) + "\n"
    (OUT / "check_log_manuscript.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
