#!/usr/bin/env python3
"""Reconstruct the constructed CF-LIBS record and test its reported values.

Reader-side script. It uses ONLY the files in ../record/:

    record.json            inputs, conventions and constructed reference values
    line_intensities.csv   replicate-level integrated line intensities
    reported_values.json   the values "as printed" (rounded for publication)

and regenerates every reported quantity along the checkpoints A1-A5.

A deterministic reported value counts as reconstructed when the recomputed
value agrees with it within half a unit of the last printed digit. Values that
depend on the Monte Carlo propagation of the input uncertainties are
regenerated exactly with the seed and generator documented in the record; an
independent seed reproduces them only within the Monte Carlo standard error,
which the script also tests.

    python3 reconstruct_record.py                   # reconstruct and check
    python3 reconstruct_record.py --write-reported  # author side: (re)create reported_values.json

The script shares the module cflibs_chain.py with the generator of the record.
It therefore tests whether the record is complete, not whether the model is right.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import cflibs_chain as cf

HERE = Path(__file__).resolve().parent
REC_DIR = HERE.parent / "record"
OUT_DIR = HERE.parent / "outputs"

CHECK_SEED = 24680          # independent seed for the statistical-reproducibility test
CHECK_DRAWS = 20000


def load() -> tuple[dict, list]:
    with open(REC_DIR / "record.json", encoding="utf-8") as fh:
        record = json.load(fh)
    with open(REC_DIR / record["intensity_file"], newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    n_rep = record["n_replicates"]
    replicates = [{row["line_id"]: float(row[f"replicate_{r}"]) for row in rows}
                  for r in range(1, n_rep + 1)]
    return record, replicates


def replicate_results(record: dict, replicates: list, overrides: dict | None = None) -> list:
    return [cf.reconstruct(record, inten, overrides) for inten in replicates]


def mean_mass_fractions(record: dict, replicates: list, overrides: dict | None = None) -> list:
    res = replicate_results(record, replicates, overrides)
    n = len(res)
    return [sum(r["mass_fraction"][i] for r in res) / n for i in range(len(res[0]["elements"]))]


def saha_stark_ratio(results: list, element: str = "Y") -> float:
    """Mean over replicates of N_e(Saha balance of an element) / N_e(Stark)."""
    return sum(r["saha_checks"][element]["ne_from_saha_cm3"] / r["n_e_cm3"] for r in results) / len(results)


def percentile(sorted_vals: list, q: float) -> float:
    """Order statistic with (0-based) index round(q (n - 1)) of the sorted values."""
    return sorted_vals[int(round(q * (len(sorted_vals) - 1)))]


def merge_overrides(base: dict | None, extra: dict) -> dict:
    """Combine a scenario override with the perturbation of one Monte Carlo draw.

    Multiplicative factors that occur in both are multiplied; everything else
    is taken from the draw.
    """
    if not base:
        return extra
    out = dict(base)
    for key, val in extra.items():
        if key in out and key.endswith("_factor") and isinstance(val, dict):
            merged = dict(out[key])
            for k, v in val.items():
                merged[k] = merged.get(k, 1.0) * v
            out[key] = merged
        elif key in out and key.endswith("_factor"):
            out[key] = out[key] * val
        else:
            out[key] = val
    return out


def monte_carlo(record: dict, replicates: list, draws: int, seed: int,
                base_overrides: dict | None = None) -> dict:
    """Propagate the input uncertainties that replicates do not sample.

    Sampled inputs (independent): Stark parameter, observed and instrumental
    widths, every transition probability, every partition function; see
    record["uncertainty_budget"]. Replicate intensity noise is not sampled; it
    enters separately as the standard deviation of the mean.

    base_overrides  optional perturbation scenario (see seeded_defects.py) that
                    is applied in every draw, so that the input uncertainties
                    are propagated through the perturbed calculation.
    """
    rng = cf.SeededNormal(seed)
    st = record["stark_line"]

    def sigma(rel: float) -> float:
        return math.sqrt(math.log(1.0 + rel * rel))

    sig_w = sigma(st["stark_parameter_rel_sd"])
    sig_a = {ln["id"]: sigma(ln["A_rel_sd"]) for ln in record["lines"]}
    sig_u = {sp: sigma(v["partition_function_rel_sd"]) for sp, v in record["species"].items()}
    names = list(record["elements"])
    n = len(replicates)
    w_draws = {nm: [] for nm in names}
    t_draws, ne_draws, ratio_draws, scatter_draws = [], [], [], []
    for _ in range(draws):
        ov = {
            "stark_param_factor": math.exp(sig_w * rng.draw()),
            "observed_fwhm_nm": st["observed_fwhm_nm"] + st["observed_fwhm_sd_nm"] * rng.draw(),
            "instrument_gaussian_fwhm_nm": (st["instrument_gaussian_fwhm_nm"]
                                            + st["instrument_gaussian_fwhm_sd_nm"] * rng.draw()),
            "line_a_factor": {lid: math.exp(s * rng.draw()) for lid, s in sig_a.items()},
            "u_factor": {sp: math.exp(s * rng.draw()) for sp, s in sig_u.items()},
        }
        res = replicate_results(record, replicates, merge_overrides(base_overrides, ov))
        for i, nm in enumerate(names):
            w_draws[nm].append(sum(r["mass_fraction"][i] for r in res) / n)
        t_draws.append(sum(r["temperature_K"] for r in res) / n)
        ne_draws.append(res[0]["n_e_cm3"])
        ratio_draws.append(saha_stark_ratio(res))
        scatter_draws.append(sum(r["residual_sd"] for r in res) / n)
    out = {"draws": draws, "seed": seed, "elements": {}}
    for nm in names:
        vals = sorted(w_draws[nm])
        m, s = cf.mean_sd(vals)
        out["elements"][nm] = {"mean": m, "sd": s, "p025": percentile(vals, 0.025),
                               "p50": percentile(vals, 0.5), "p975": percentile(vals, 0.975)}
    out["temperature_K_sd"] = cf.mean_sd(t_draws)[1]
    out["n_e_sd_cm3"] = cf.mean_sd(ne_draws)[1]
    ratios = sorted(ratio_draws)
    out["saha_stark_ratio_p025"] = percentile(ratios, 0.025)
    out["saha_stark_ratio_p975"] = percentile(ratios, 0.975)
    scatter = sorted(scatter_draws)
    out["residual_sd_p025"] = percentile(scatter, 0.025)
    out["residual_sd_p50"] = percentile(scatter, 0.5)
    out["residual_sd_p975"] = percentile(scatter, 0.975)
    return out


def analyze() -> dict:
    record, replicates = load()
    res = replicate_results(record, replicates)
    names = res[0]["elements"]
    n = len(res)
    ref = record["reference"]
    mc_cfg = record["uncertainty_budget"]["monte_carlo"]

    summary: dict = {"n_replicates": n, "elements": names}
    # A1
    st = record["stark_line"]
    summary["A1"] = {"observed_fwhm_nm": st["observed_fwhm_nm"],
                     "instrument_gaussian_fwhm_nm": st["instrument_gaussian_fwhm_nm"],
                     "stark_fwhm_nm": res[0]["lorentz_fwhm_nm"],
                     "n_e_cm3": res[0]["n_e_cm3"],
                     "n_e_if_width_uncorrected_cm3": cf.reconstruct(record, replicates[0], {"width_treatment": "none"})["n_e_cm3"],
                     "n_e_if_quadrature_cm3": cf.reconstruct(record, replicates[0], {"width_treatment": "quadrature"})["n_e_cm3"]}
    # A2
    temps = [r["temperature_K"] for r in res]
    t_mean, t_sd = cf.mean_sd(temps)
    summary["A2"] = {"temperature_K_replicates": temps, "temperature_K_mean": t_mean,
                     "temperature_K_sd": t_sd,
                     "slope_per_eV_replicate_1": res[0]["slope_per_eV"],
                     "slope_se_per_eV_replicate_1": res[0]["slope_se_per_eV"],
                     "residual_sd_replicate_1": res[0]["residual_sd"],
                     "residual_sd_mean": sum(r["residual_sd"] for r in res) / n,
                     "intercepts_replicate_1": res[0]["intercepts"],
                     "n_lines": res[0]["n_lines"]}
    # A3
    ratios = [r["saha_checks"]["Y"]["ne_from_saha_cm3"] / r["n_e_cm3"] for r in res]
    threshold = cf.mcwhirter_threshold(t_mean, cf.lte_gap_ev(record))
    summary["A3"] = {"mcwhirter_threshold_cm3": threshold,
                     "ne_over_threshold": res[0]["n_e_cm3"] / threshold,
                     "ne_saha_over_ne_stark_replicates": ratios,
                     "ne_saha_over_ne_stark_mean": sum(ratios) / n,
                     "saha_ion_to_neutral_replicate_1": res[0]["saha_ratio"]}
    # A4
    x_mean = [sum(r["mole_fraction"][i] for r in res) / n for i in range(len(names))]
    w_rep = [[r["mass_fraction"][i] for r in res] for i in range(len(names))]
    w_stats = [cf.mean_sd(v) for v in w_rep]
    summary["A4"] = {"mole_fraction_mean": dict(zip(names, x_mean)),
                     "mass_fraction_mean": {nm: s[0] for nm, s in zip(names, w_stats)},
                     "mass_fraction_replicates": dict(zip(names, w_rep))}
    # A5
    mc = monte_carlo(record, replicates, mc_cfg["draws"], mc_cfg["seed"])
    a5 = {}
    for nm, (m, s) in zip(names, w_stats):
        u_rep = s / math.sqrt(n)
        u_in = mc["elements"][nm]["sd"]
        u_c = math.sqrt(u_rep**2 + u_in**2)
        a5[nm] = {"mean": m, "sd": s, "rsd_percent": 100.0 * s / m,
                  "u_repeatability_of_mean": u_rep, "u_inputs_monte_carlo": u_in,
                  "u_combined": u_c, "u_combined_rel_percent": 100.0 * u_c / m,
                  "reference": ref["values"][nm], "u_reference": ref["standard_uncertainty"][nm],
                  "signed_deviation_percent": cf.signed_relative_deviation(m, ref["values"][nm]),
                  "zeta": cf.zeta_score(m, u_c, ref["values"][nm], ref["standard_uncertainty"][nm]),
                  "mc_p025": mc["elements"][nm]["p025"], "mc_p50": mc["elements"][nm]["p50"],
                  "mc_p975": mc["elements"][nm]["p975"], "mc_mean": mc["elements"][nm]["mean"]}
    summary["A5"] = a5
    summary["monte_carlo"] = {"draws": mc["draws"], "seed": mc["seed"],
                              "note": ("relative uncertainties refer to the plug-in values; percentiles are order "
                                       "statistics with index round(q (n - 1)) of the sorted draws"),
                              "temperature_K_sd": mc["temperature_K_sd"],
                              "temperature_rel_sd_percent": 100.0 * mc["temperature_K_sd"] / t_mean,
                              "n_e_sd_cm3": mc["n_e_sd_cm3"],
                              "n_e_rel_sd_percent": 100.0 * mc["n_e_sd_cm3"] / res[0]["n_e_cm3"],
                              "saha_stark_ratio_p025": mc["saha_stark_ratio_p025"],
                              "saha_stark_ratio_p975": mc["saha_stark_ratio_p975"],
                              "residual_sd_p025": mc["residual_sd_p025"],
                              "residual_sd_p50": mc["residual_sd_p50"],
                              "residual_sd_p975": mc["residual_sd_p975"]}
    return {"record": record, "replicates": replicates, "results": res, "summary": summary}


def two_sig(value: float) -> dict:
    """Round to two significant digits and return the value with its printed increment."""
    exponent = int(math.floor(math.log10(abs(value))))
    inc = 10.0 ** (exponent - 1)
    return {"value": round(value / inc) * inc if inc >= 1 else round(value, 1 - exponent), "increment": inc}


def clean(value: float, decimals: int) -> float:
    """Round and avoid a negative zero."""
    r = round(value, decimals)
    return 0.0 if r == 0 else r


def reported_from(summary: dict) -> dict:
    """Publication-style rounding of the reconstructed quantities."""
    names = summary["elements"]
    a5 = summary["A5"]
    det = {
        "A1_stark_fwhm_nm": {"value": round(summary["A1"]["stark_fwhm_nm"], 4), "increment": 1e-4},
        "A1_n_e_1e17_cm3": {"value": round(summary["A1"]["n_e_cm3"] / 1e17, 2), "increment": 0.01},
        "A2_temperature_K": {"value": round(summary["A2"]["temperature_K_mean"], -1), "increment": 10.0},
        "A2_temperature_replicate_sd_K": two_sig(summary["A2"]["temperature_K_sd"]),
        "A3_mcwhirter_threshold_1e15_cm3": {"value": round(summary["A3"]["mcwhirter_threshold_cm3"] / 1e15, 2), "increment": 0.01},
        "A3_ne_saha_over_ne_stark": {"value": round(summary["A3"]["ne_saha_over_ne_stark_mean"], 2), "increment": 0.01},
        "A4_mole_percent": {n: {"value": round(100 * summary["A4"]["mole_fraction_mean"][n], 3), "increment": 0.001} for n in names},
        "A4_mass_percent": {n: {"value": round(100 * summary["A4"]["mass_fraction_mean"][n], 3), "increment": 0.001} for n in names},
        "A5_rsd_percent": {n: {"value": round(a5[n]["rsd_percent"], 1), "increment": 0.1} for n in names},
        "A5_signed_deviation_percent": {n: {"value": clean(a5[n]["signed_deviation_percent"], 1), "increment": 0.1} for n in names},
    }
    mc = {
        "A2_temperature_propagated_u_K": two_sig(summary["monte_carlo"]["temperature_K_sd"]),
        "A5_u_combined_percentage_points": {n: two_sig(100 * a5[n]["u_combined"]) for n in names},
        "A5_zeta": {n: {"value": clean(a5[n]["zeta"], 2), "increment": 0.01} for n in names},
    }
    return {
        "note": ("Values as printed in Supplementary Text S1. Each entry gives the printed value and "
                 "its printed increment. Deterministic values are reconstructed within half an increment. "
                 "Monte Carlo-based values are printed with two significant digits, a precision at which "
                 "any seed reproduces them; their unrounded values (outputs/summary.json) are regenerated "
                 "exactly with the seed and generator stated in record.json."),
        "deterministic": det,
        "monte_carlo_based": mc,
    }


def flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict) and "value" in v and "increment" in v:
            out[prefix + k] = (v["value"], v["increment"])
        elif isinstance(v, dict):
            out.update(flatten(v, prefix + k + "."))
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = analyze()
    summary = data["summary"]
    recomputed = reported_from(summary)

    reported_path = REC_DIR / "reported_values.json"
    if "--write-reported" in sys.argv:
        with open(reported_path, "w", encoding="utf-8") as fh:
            json.dump(recomputed, fh, indent=2)
            fh.write("\n")
        print(f"Wrote {reported_path}")

    # ---------------- outputs ----------------
    names = summary["elements"]
    with open(OUT_DIR / "replicate_results.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["replicate", "temperature_K", "n_e_cm3"] + [f"mole_percent_{n}" for n in names]
                    + [f"mass_percent_{n}" for n in names] + ["ne_saha_over_ne_stark_Y", "residual_sd"])
        for i, r in enumerate(data["results"], start=1):
            wr.writerow([i, f"{r['temperature_K']:.1f}", f"{r['n_e_cm3']:.4e}"]
                        + [f"{100 * v:.4f}" for v in r["mole_fraction"]]
                        + [f"{100 * v:.4f}" for v in r["mass_fraction"]]
                        + [f"{r['saha_checks']['Y']['ne_from_saha_cm3'] / r['n_e_cm3']:.4f}", f"{r['residual_sd']:.4f}"])
    rec = data["record"]
    with open(OUT_DIR / "boltzmann_points_replicate1.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["line_id", "species", "E_k_eV", "ordinate_ln_I_over_gA", "fitted_ordinate"])
        r1 = data["results"][0]
        for ln in rec["lines"]:
            y = cf.boltzmann_ordinate(data["replicates"][0][ln["id"]], ln["g_k"], ln["A_ki_s-1"])
            fit = r1["intercepts"][ln["species"]] + r1["slope_per_eV"] * ln["E_k_eV"]
            wr.writerow([ln["id"], ln["species"], ln["E_k_eV"], f"{y:.5f}", f"{fit:.5f}"])

    # independent-seed Monte Carlo for the statistical-reproducibility test
    mc2 = monte_carlo(rec, data["replicates"], CHECK_DRAWS, CHECK_SEED)
    summary["monte_carlo"]["independent_seed_check"] = {
        "seed": CHECK_SEED, "draws": CHECK_DRAWS,
        "sd_ratio_to_documented_seed": {n: mc2["elements"][n]["sd"] / summary["A5"][n]["u_inputs_monte_carlo"] for n in names}}
    with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")

    # ---------------- checks ----------------
    lines = []
    ok = True

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and cond
        lines.append(f"{'PASS' if cond else 'FAIL'}: {name}{(' - ' + detail) if detail else ''}")

    with open(reported_path, encoding="utf-8") as fh:
        reported = json.load(fh)
    for group, label in (("deterministic", "deterministic"), ("monte_carlo_based", "Monte Carlo-based")):
        rep_flat, new_flat = flatten(reported[group]), flatten(recomputed[group])
        for key, (val, inc) in rep_flat.items():
            new_val = new_flat[key][0]
            check(f"reported {label} value {key} = {val:g} reconstructed", abs(new_val - val) <= inc / 2 + 1e-12,
                  f"recomputed {new_val:g}")

    gen = rec["generation"]
    a1, a2, a5 = summary["A1"], summary["A2"], summary["A5"]
    check("A1 recovered N_e within 1% of the generating value",
          abs(a1["n_e_cm3"] / gen["Ne_true_cm3"] - 1) < 0.01, f"{a1['n_e_cm3']:.4e}")
    check("A2 recovered T within 2% of the generating value",
          abs(a2["temperature_K_mean"] / gen["T_true_K"] - 1) < 0.02, f"{a2['temperature_K_mean']:.1f} K")
    check("A3 N_e exceeds the McWhirter threshold", summary["A3"]["ne_over_threshold"] > 1,
          f"ratio {summary['A3']['ne_over_threshold']:.1f}")
    check("A4 mole fractions sum to unity",
          abs(sum(summary["A4"]["mole_fraction_mean"].values()) - 1) < 1e-12)
    check("A4 mass fractions sum to unity",
          abs(sum(summary["A4"]["mass_fraction_mean"].values()) - 1) < 1e-12)
    for nm in names:
        check(f"A5 {nm}: |zeta| < 2 (compatible with the constructed reference)", abs(a5[nm]["zeta"]) < 2,
              f"zeta {a5[nm]['zeta']:.2f}")
    check("A5 minor constituents: combined uncertainty exceeds twice the repeatability of the mean",
          all(a5[nm]["u_combined"] > 2 * a5[nm]["u_repeatability_of_mean"] for nm in ("X", "Z")))
    ratios = summary["monte_carlo"]["independent_seed_check"]["sd_ratio_to_documented_seed"]
    check("A5 Monte Carlo uncertainties reproduced within 3% by an independent seed",
          all(abs(r - 1) < 0.03 for r in ratios.values()),
          ", ".join(f"{n} {r:.3f}" for n, r in ratios.items()))

    header = [f"{sum(l.startswith('PASS') for l in lines)} of {len(lines)} checks passed.",
              "Checks concern the constructed record and this script only. They do not validate",
              "any experiment, plasma model or published study.", ""]
    text = "\n".join(header + lines) + "\n"
    (OUT_DIR / "check_log_record.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
