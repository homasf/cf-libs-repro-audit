#!/usr/bin/env python3
"""Seed single perturbations into the reconstruction of the constructed record.

Two families of scenarios are applied, one at a time, to the record of
../record/:

  U1-U4  errors of a plasma parameter or an input, of a size comparable with
         its uncertainty (temperature, Stark parameter, transition
         probabilities, slope of the spectral response), shown for comparison,
  C1-C9  convention or reporting slips (instrumental width not removed or
         removed in quadrature, half versus full width in either direction,
         reference density wrong by a factor of 10 in either direction,
         intensity-unit convention, ground-level statistical weights in place
         of partition functions, mole fractions reported as mass fractions).

For every scenario the mean mass fractions are recomputed and compared with
the baseline reconstruction and with the 95% interval that the assigned input
uncertainties alone produce. Three ways of noticing a perturbation are then
evaluated:

  D  the electron density implied by the Saha balance of element Y relative
     to the Stark value, flagged when it lies outside the 95% range that the
     input uncertainties alone produce,
  S  the residual standard deviation (scatter) of the Boltzmann plot, flagged
     when it exceeds the 97.5th percentile of the scatter that the input
     uncertainties alone produce, and
  R  the normalized deviation (zeta) from the constructed reference, flagged
     when |zeta| > 2 for at least one element. For this test the assigned
     input uncertainties are propagated through the perturbed calculation, as
     an analyst who made the slip would do. The generator is restarted with
     the documented seed for every scenario. zeta is also evaluated with the
     standard deviation of the mean as the only uncertainty of the method.

Outputs: ../outputs/seeded_defects.csv and .json, check_log_seeded_defects.txt

The magnitudes are properties of this constructed case. They illustrate
mechanisms; they are not estimates for any real plasma, sample or study.
"""
from __future__ import annotations

import csv
import json
import math

import cflibs_chain as cf
from reconstruct_record import OUT_DIR, load, monte_carlo, replicate_results, saha_stark_ratio

SCENARIO_DRAWS = 20000      # Monte Carlo draws per scenario for the comparison with the reference
ZETA_LIMIT = 2.0            # conventional compatibility limit for |zeta|

SCENARIOS = [
    # id, family, checkpoint, label, definition, overrides
    ("U1", "uncertainty", "A2", "Temperature +5%",
     "temperature multiplied by 1.05; slope set to -1/(k_B T); species intercepts and scatter re-derived from the data with that slope",
     {"temperature_factor": 1.05}),
    ("U2", "uncertainty", "A2", "Stark parameter +20%",
     "Stark parameter multiplied by 1.20", {"stark_param_factor": 1.20}),
    ("U3", "uncertainty", "A2", "Transition probabilities of X I lines +10%",
     "A_ki of all X I lines multiplied by 1.10", {"ga_factor": {"X I": 1.10}}),
    ("U4", "uncertainty", "A2", "Spectral response tilted by +5% per 100 nm",
     "every intensity multiplied by 1 + 0.05 (lambda - 400 nm)/(100 nm)", {"response_tilt_per_100nm": 0.05}),
    ("C1", "slip", "A1", "Instrumental width not removed",
     "observed width used as the Stark width", {"width_treatment": "none"}),
    ("C2", "slip", "A1", "Quadrature subtraction applied to a Voigt profile",
     "Stark width = sqrt(W^2 - G^2)", {"width_treatment": "quadrature"}),
    ("C3", "slip", "A2", "Half width (HWHM) used as a full width",
     "electron density multiplied by 2", {"ne_factor": 2.0}),
    ("C4", "slip", "A2", "Full width (FWHM) used as a half width",
     "electron density multiplied by 0.5", {"ne_factor": 0.5}),
    ("C5", "slip", "A2", "Reference density too high by a factor of 10",
     "reference density multiplied by 10", {"n_ref_factor": 10.0}),
    ("C6", "slip", "A2", "Reference density too low by a factor of 10",
     "reference density multiplied by 0.1", {"n_ref_factor": 0.1}),
    ("C7", "slip", "A2", "Energy-unit ordinate applied to photon-unit intensities",
     "ordinate ln[I lambda/(g A)] instead of ln[I/(g A)]", {"intensity_units": "energy"}),
    ("C8", "slip", "A4", "Ground-level weights used in place of partition functions",
     ("every partition function replaced by the statistical weight of the ground level; in the propagation "
      "for the reference test, the uncertainty assigned to the partition functions is applied to these weights"),
     {"partition_function": "g0"}),
    ("C9", "slip", "A4", "Mole fractions reported as mass fractions",
     "mole-to-mass conversion omitted", {"skip_mass_conversion": True}),
]


def evaluate(record: dict, replicates: list, overrides: dict | None) -> dict:
    res = replicate_results(record, replicates, overrides)
    n = len(res)
    names = res[0]["elements"]
    per_element = [[r["mass_fraction"][i] for r in res] for i in range(len(names))]
    return {"mass_fraction": [sum(v) / n for v in per_element],
            "sd_of_mean": [cf.mean_sd(v)[1] / math.sqrt(n) for v in per_element],
            "n_e_cm3": res[0]["n_e_cm3"],
            "temperature_K": sum(r["temperature_K"] for r in res) / n,
            "saha_stark_ratio": saha_stark_ratio(res),
            "residual_sd": sum(r["residual_sd"] for r in res) / n}


def validation(record: dict, replicates: list, overrides: dict, ev: dict, seed: int) -> dict:
    """zeta against the constructed reference for a scenario.

    'full': input uncertainties propagated through the perturbed calculation
    and combined with the standard deviation of the mean;
    'repeatability_only': standard deviation of the mean alone.
    """
    names = list(record["elements"])
    ref = record["reference"]
    mc = monte_carlo(record, replicates, SCENARIO_DRAWS, seed, overrides)
    out = {}
    for i, nm in enumerate(names):
        u_rep = ev["sd_of_mean"][i]
        u_c = math.sqrt(u_rep**2 + mc["elements"][nm]["sd"] ** 2)
        args = (ref["values"][nm], ref["standard_uncertainty"][nm])
        out[nm] = {"u_combined": u_c,
                   "u_combined_rel_percent": 100.0 * u_c / ev["mass_fraction"][i],
                   "zeta": cf.zeta_score(ev["mass_fraction"][i], u_c, *args),
                   "zeta_repeatability_only": cf.zeta_score(ev["mass_fraction"][i], u_rep, *args)}
    return out


def run() -> dict:
    record, replicates = load()
    names = list(record["elements"])
    seed = record["uncertainty_budget"]["monte_carlo"]["seed"]
    base = evaluate(record, replicates, None)
    ref = record["reference"]
    rows = []
    for sid, family, checkpoint, label, definition, ov in SCENARIOS:
        ev = evaluate(record, replicates, ov)
        val = validation(record, replicates, ov, ev, seed)
        rows.append({"id": sid, "family": family, "checkpoint": checkpoint, "label": label,
                     "definition": definition, "overrides": ov,
                     "mass_percent": {n: 100 * v for n, v in zip(names, ev["mass_fraction"])},
                     "ratio_to_baseline": {n: v / b for n, v, b in zip(names, ev["mass_fraction"], base["mass_fraction"])},
                     "n_e_ratio": ev["n_e_cm3"] / base["n_e_cm3"],
                     "temperature_ratio": ev["temperature_K"] / base["temperature_K"],
                     "saha_stark_ratio": ev["saha_stark_ratio"],
                     "residual_sd": ev["residual_sd"],
                     "u_combined_rel_percent": {n: val[n]["u_combined_rel_percent"] for n in names},
                     "zeta_vs_reference": {n: val[n]["zeta"] for n in names},
                     "zeta_repeatability_only": {n: val[n]["zeta_repeatability_only"] for n in names}})
    base_zeta_rep = {n: cf.zeta_score(base["mass_fraction"][i], base["sd_of_mean"][i], ref["values"][n],
                                      ref["standard_uncertainty"][n]) for i, n in enumerate(names)}
    return {"elements": names,
            "flag_criteria": {"D": "N_e(Saha balance of Y)/N_e(Stark) outside the 95% range of the baseline Monte Carlo propagation",
                              "S": "residual SD of the Boltzmann plot above the 97.5th percentile of the baseline Monte Carlo propagation",
                              "R": f"|zeta| above {ZETA_LIMIT:g} for at least one element, input uncertainties propagated through the scenario"},
            "validation_test": {"draws_per_scenario": SCENARIO_DRAWS, "seed": seed, "zeta_limit": ZETA_LIMIT,
                                "definition": ("zeta of the scenario result against the constructed reference; the "
                                               "assigned input uncertainties are propagated through the perturbed "
                                               "calculation and combined with the standard deviation of the mean; "
                                               "the generator is restarted with the same seed for every scenario")},
            "baseline": {"mass_percent": {n: 100 * v for n, v in zip(names, base["mass_fraction"])},
                         "saha_stark_ratio": base["saha_stark_ratio"], "residual_sd": base["residual_sd"],
                         "zeta_repeatability_only": base_zeta_rep},
            "scenarios": rows}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res = run()
    names = res["elements"]
    summ = json.loads((OUT_DIR / "summary.json").read_text())
    a5 = summ["A5"]
    mc = summ["monte_carlo"]
    base_w = summ["A4"]["mass_fraction_mean"]
    res["baseline"]["zeta_vs_reference"] = {n: a5[n]["zeta"] for n in names}
    res["monte_carlo_95_interval_ratio"] = {n: [a5[n]["mc_p025"] / base_w[n], a5[n]["mc_p975"] / base_w[n]] for n in names}
    res["saha_stark_ratio_95_range"] = [mc["saha_stark_ratio_p025"], mc["saha_stark_ratio_p975"]]
    res["residual_sd_95_range"] = [mc["residual_sd_p025"], mc["residual_sd_p975"]]
    lo, hi = res["saha_stark_ratio_95_range"]
    for r in res["scenarios"]:
        r["outside_95_interval"] = {n: not (res["monte_carlo_95_interval_ratio"][n][0] <= r["ratio_to_baseline"][n]
                                            <= res["monte_carlo_95_interval_ratio"][n][1]) for n in names}
        r["residual_sd_ratio"] = r["residual_sd"] / res["baseline"]["residual_sd"]
        r["flag_D"] = not (lo <= r["saha_stark_ratio"] <= hi)
        r["flag_S"] = r["residual_sd"] > res["residual_sd_95_range"][1]
        r["max_abs_zeta"] = max(abs(v) for v in r["zeta_vs_reference"].values())
        r["flag_R"] = r["max_abs_zeta"] > ZETA_LIMIT
        r["flagged_by_any"] = r["flag_D"] or r["flag_S"] or r["flag_R"]
        r["flag_R_repeatability_only"] = max(abs(v) for v in r["zeta_repeatability_only"].values()) > ZETA_LIMIT

    with open(OUT_DIR / "seeded_defects.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["id", "family", "checkpoint", "label", "definition", "Ne_ratio", "T_ratio"]
                    + [f"mass_percent_{n}" for n in names] + [f"ratio_{n}" for n in names]
                    + ["Ne_Saha_over_Ne_Stark_Y", "residual_sd"] + [f"zeta_{n}" for n in names]
                    + [f"zeta_repeatability_only_{n}" for n in names] + ["flags"])
        wr.writerow(["BASE", "baseline", "", "Baseline reconstruction", "", "1.0000", "1.0000"]
                    + [f"{res['baseline']['mass_percent'][n]:.4f}" for n in names] + ["1.0000"] * len(names)
                    + [f"{res['baseline']['saha_stark_ratio']:.4f}", f"{res['baseline']['residual_sd']:.4f}"]
                    + [f"{res['baseline']['zeta_vs_reference'][n]:.2f}" for n in names]
                    + [f"{res['baseline']['zeta_repeatability_only'][n]:.2f}" for n in names] + [""])
        for r in res["scenarios"]:
            wr.writerow([r["id"], r["family"], r["checkpoint"], r["label"], r["definition"],
                         f"{r['n_e_ratio']:.4f}", f"{r['temperature_ratio']:.4f}"]
                        + [f"{r['mass_percent'][n]:.4f}" for n in names]
                        + [f"{r['ratio_to_baseline'][n]:.4f}" for n in names]
                        + [f"{r['saha_stark_ratio']:.4f}", f"{r['residual_sd']:.4f}"]
                        + [f"{r['zeta_vs_reference'][n]:.2f}" for n in names]
                        + [f"{r['zeta_repeatability_only'][n]:.2f}" for n in names]
                        + ["".join(k for k in "DSR" if r[f"flag_{k}"])])
    with open(OUT_DIR / "seeded_defects.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
        fh.write("\n")

    print(f"{'id':<4}{'label':<58}{'Ne':>7}{'T':>7}" + "".join(f"{n:>8}" for n in names)
          + f"{'Saha/St':>9}{'resid':>8}" + "".join(f"{'z_' + n:>8}" for n in names) + "  flags")
    for r in res["scenarios"]:
        print(f"{r['id']:<4}{r['label']:<58}{r['n_e_ratio']:>7.3f}{r['temperature_ratio']:>7.3f}"
              + "".join(f"{r['ratio_to_baseline'][n]:>8.3f}" for n in names)
              + f"{r['saha_stark_ratio']:>9.3f}{r['residual_sd']:>8.3f}"
              + "".join(f"{r['zeta_vs_reference'][n]:>8.2f}" for n in names)
              + "  " + "".join(k for k in "DSR" if r[f"flag_{k}"]))
    print("95% Monte Carlo interval (ratio):", {n: [round(v, 3) for v in res["monte_carlo_95_interval_ratio"][n]] for n in names})
    print("95% range of the Saha/Stark ratio:", [round(v, 3) for v in res["saha_stark_ratio_95_range"]])
    print("95% range of the residual SD:", [round(v, 3) for v in res["residual_sd_95_range"]])

    # ---- checks on the expected behavior of the seeded scenarios ----
    by_id = {r["id"]: r for r in res["scenarios"]}
    slips = [r for r in res["scenarios"] if r["family"] == "slip"]
    uncs = [r for r in res["scenarios"] if r["family"] == "uncertainty"]
    lines, ok = [], True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok = ok and cond
        lines.append(f"{'PASS' if cond else 'FAIL'}: {name}")

    record, _ = load()
    molar = [record["elements"][n]["molar_mass_g_mol"] for n in names]
    check("C5 and C6: a tenfold reference-density slip changes the electron density tenfold",
          abs(by_id["C5"]["n_e_ratio"] - 10.0) < 1e-9 and abs(by_id["C6"]["n_e_ratio"] - 0.1) < 1e-9)
    check("C3 and C4: a half-/full-width slip changes the electron density twofold",
          abs(by_id["C3"]["n_e_ratio"] - 2.0) < 1e-9 and abs(by_id["C4"]["n_e_ratio"] - 0.5) < 1e-9)
    check("C1: an uncorrected width overestimates the electron density", by_id["C1"]["n_e_ratio"] > 1.15)
    check("C2: quadrature subtraction undercorrects a Voigt profile",
          1.0 < by_id["C2"]["n_e_ratio"] < by_id["C1"]["n_e_ratio"])
    x_base = cf.mass_to_mole([res["baseline"]["mass_percent"][n] for n in names], molar)
    check("C9: unconverted values equal the baseline mole fractions (to 0.05 percentage points)",
          all(abs(100 * xb - by_id["C9"]["mass_percent"][n]) < 0.05 for xb, n in zip(x_base, names)))
    check("Every scenario still sums to 100%",
          all(abs(sum(r["mass_percent"].values()) - 100.0) < 1e-9 for r in res["scenarios"]))
    check("C8 and C9 leave both internal consistency indicators unchanged",
          all(abs(by_id[k]["saha_stark_ratio"] - res["baseline"]["saha_stark_ratio"]) < 1e-9
              and abs(by_id[k]["residual_sd"] - res["baseline"]["residual_sd"]) < 1e-9 for k in ("C8", "C9")))
    out_x = [r["id"] for r in slips if r["outside_95_interval"]["X"]]
    check(f"{len(out_x)} of {len(slips)} slips move X outside the 95% Monte Carlo interval: {', '.join(out_x)}",
          out_x == ["C3", "C4", "C5", "C6", "C8", "C9"])
    check("None of the uncertainty scenarios U1-U4 moves an element outside its 95% Monte Carlo interval",
          not any(any(r["outside_95_interval"].values()) for r in uncs))
    flag_d = [r["id"] for r in slips if r["flag_D"]]
    check(f"The density ratio flags {len(flag_d)} of {len(slips)} slips: {', '.join(flag_d)}", flag_d == ["C3", "C4", "C5", "C6"])
    flag_s = [r["id"] for r in slips if r["flag_S"]]
    check(f"The scatter of the Boltzmann plot flags {len(flag_s)} of {len(slips)} slips: {', '.join(flag_s)}", flag_s == ["C7"])
    flag_r = [r["id"] for r in slips if r["flag_R"]]
    check(f"The comparison with the reference flags {len(flag_r)} of {len(slips)} slips: {', '.join(flag_r)}",
          0 < len(flag_r) < len(slips))
    n_y = sum(abs(r["ratio_to_baseline"]["Y"] - 1) < 0.05 for r in res["scenarios"])
    check(f"Major element Y stays within 5% of the baseline in {n_y} of the {len(res['scenarios'])} scenarios", n_y >= 9)
    check("The baseline is compatible with the reference (|zeta| < 2 for every element)",
          all(abs(v) < ZETA_LIMIT for v in res["baseline"]["zeta_vs_reference"].values()))
    flag_any = [r["id"] for r in slips if r["flagged_by_any"]]
    check(f"{len(flag_any)} of {len(slips)} slips are flagged by at least one indicator; no indicator flags all of them",
          len(flag_any) < len(slips) and max(len(flag_d), len(flag_s), len(flag_r)) < len(flag_any))
    check("None of the uncertainty scenarios U1-U4 is flagged by any indicator",
          not any(r["flagged_by_any"] for r in uncs))
    rep_slips = [r["id"] for r in slips if r["flag_R_repeatability_only"]]
    rep_uncs = [r["id"] for r in uncs if r["flag_R_repeatability_only"]]
    check(f"With repeatability as the only uncertainty, |zeta| > 2 for {len(rep_slips)} of {len(slips)} slips "
          f"and for {', '.join(rep_uncs)} among the uncertainty scenarios",
          len(rep_slips) == len(slips) and len(rep_uncs) >= 1)
    text = "\n".join([f"{sum(l.startswith('PASS') for l in lines)} of {len(lines)} checks passed.", ""] + lines) + "\n"
    (OUT_DIR / "check_log_seeded_defects.txt").write_text(text, encoding="utf-8")
    print("\n" + text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
