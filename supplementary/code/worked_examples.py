#!/usr/bin/env python3
"""Constructed worked examples quoted in the Perspective (checkpoints A1-A5).

Every number printed in the main text and tables that is not taken from the
constructed record is generated here and written to

    ../outputs/worked_examples.json
    ../outputs/table_linewidth.csv        (Figure 2, Table S1)
    ../outputs/table_basis.csv            (Table 2, Figure 3)
    ../outputs/check_log_examples.txt

The alloy compositions are nominal grade designations used only as familiar
arithmetic examples; no measurement of any material is implied.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import cflibs_chain as cf

OUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

# Abridged standard atomic weights (IUPAC 2021 report), g/mol
ATOMIC_WEIGHT = {"Li": 6.94, "Al": 26.982, "Ti": 47.867, "V": 50.942, "Fe": 55.845,
                 "Ni": 58.693, "Sn": 118.71, "W": 183.84, "Pb": 207.2}

# Nominal mass percentages of familiar alloy families (arithmetic examples only)
MATERIALS = {
    "Ti-6Al-4V (titanium alloy)": {"Ti": 90.0, "Al": 6.0, "V": 4.0},
    "90W-7Ni-3Fe (tungsten heavy alloy)": {"W": 90.0, "Ni": 7.0, "Fe": 3.0},
    "63Sn-37Pb (solder)": {"Sn": 63.0, "Pb": 37.0},
    "Al-2.5Li (aluminum-lithium alloy)": {"Al": 97.5, "Li": 2.5},
}

# Hypothetical elements of the constructed record (see make_record.py)
ATOMIC_WEIGHT.update({"X": 27.0, "Y": 56.0, "Z": 184.0})
RECORD_MATERIAL = {"Constructed record X-Y-Z (hypothetical)": {"X": 6.0, "Y": 91.0, "Z": 3.0}}


def voigt_fwhm_numeric(lorentz_fwhm: float, gauss_fwhm: float, n: int = 4000) -> float:
    """FWHM of an exact Voigt profile by direct numerical convolution (Simpson rule).

    Independent of the Olivero-Longbothum approximation; used only to check it.
    """
    sigma = gauss_fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    gamma = lorentz_fwhm / 2.0
    lim = 8.0 * sigma
    h = 2.0 * lim / n

    def profile(x: float) -> float:
        total = 0.0
        for i in range(n + 1):
            t = -lim + i * h
            weight = 1.0 if i in (0, n) else (4.0 if i % 2 else 2.0)
            total += weight * math.exp(-0.5 * (t / sigma) ** 2) * gamma / ((x - t) ** 2 + gamma**2)
        return total

    half = 0.5 * profile(0.0)
    lo, hi = 0.0, lorentz_fwhm + gauss_fwhm
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if profile(mid) > half:
            lo = mid
        else:
            hi = mid
    return lo + hi


def approximation_check() -> dict:
    """Accuracy of the Olivero-Longbothum width against an exact Voigt profile."""
    worst = 0.0
    for i in range(1, 10):
        lor, gau = i / 10.0, 1.0 - i / 10.0
        worst = max(worst, abs(cf.voigt_fwhm(lor, gau) / voigt_fwhm_numeric(lor, gau) - 1.0))
    # operating point of the constructed record: W = 0.14954 nm, G = 0.060 nm
    w_obs, g_inst = 0.14954, 0.060
    l_ol = cf.lorentz_from_voigt(w_obs, g_inst)
    lo, hi = 0.5 * l_ol, 1.5 * l_ol
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if voigt_fwhm_numeric(mid, g_inst) < w_obs:
            lo = mid
        else:
            hi = mid
    l_exact = 0.5 * (lo + hi)
    return {"max_relative_deviation_percent": 100.0 * worst,
            "record_point": {"observed_fwhm_nm": w_obs, "instrument_fwhm_nm": g_inst,
                             "lorentz_fwhm_approximation_nm": l_ol, "lorentz_fwhm_exact_nm": l_exact,
                             "relative_difference_percent": 100.0 * (l_exact / l_ol - 1.0)}}


def example_a1() -> dict:
    """Instrumental contribution to an observed Voigt width."""
    rows = []
    for ratio in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        lor = cf.lorentz_from_voigt(1.0, ratio)
        quad = cf.quadrature_subtraction_width(1.0, ratio)
        rows.append({"G_over_W": ratio, "L_over_W_voigt": lor, "L_over_W_quadrature": quad,
                     "ne_bias_uncorrected_percent": 100 * (1.0 / lor - 1.0),
                     "ne_bias_quadrature_percent": 100 * (quad / lor - 1.0)})
    # width close to the instrumental resolution
    w_obs, g_inst = 0.120, 0.100
    lor = cf.lorentz_from_voigt(w_obs, g_inst)
    near = {"observed_fwhm_nm": w_obs, "instrument_fwhm_nm": g_inst, "lorentz_fwhm_nm": lor,
            "density_overestimate_factor_if_uncorrected": w_obs / lor,
            "density_overestimate_factor_if_quadrature": cf.quadrature_subtraction_width(w_obs, g_inst) / lor}
    # an instrumental profile that is Lorentzian instead of Gaussian: widths add linearly
    lorentz_instrument = {}
    for ratio in (0.4, 0.8):
        true_share = 1.0 - ratio
        lorentz_instrument[f"G_over_W_{ratio:.1f}"] = {
            "stark_share": true_share,
            "ne_bias_uncorrected_percent": 100 * (1.0 / true_share - 1.0),
            "ne_bias_quadrature_percent": 100 * (math.sqrt(1.0 - ratio**2) / true_share - 1.0)}
    return {"table": rows, "near_resolution": near, "lorentzian_instrument": lorentz_instrument,
            "approximation_check": approximation_check(),
            "convention_factors": {"half_vs_full_width": 2.0, "reference_density_1e16_vs_1e17": 10.0}}


def example_a2() -> dict:
    """Boltzmann-plot conventions."""
    t_k = 10000.0
    slope_ln = -1.0 / (cf.K_B_EV * t_k)
    slope_log10 = slope_ln / math.log(10.0)
    return {"temperature_K": t_k, "kT_eV": cf.K_B_EV * t_k,
            "slope_ln_per_eV": slope_ln, "slope_log10_per_eV": slope_log10,
            "temperature_if_log10_slope_read_as_ln_K": -1.0 / (cf.K_B_EV * slope_log10),
            "kelvin_per_eV": 1.0 / cf.K_B_EV,
            "saha_prefactor_cm-3_K-1.5": 2.0 * cf.SAHA_PREFACTOR,
            "saha_prefactor_cm-3_eV-1.5": 2.0 * cf.SAHA_PREFACTOR / cf.K_B_EV**1.5,
            "saha_prefactor_ratio": cf.K_B_EV**-1.5}


def example_a3() -> dict:
    """McWhirter criterion and a temperature-unit slip."""
    t_k, d_e = 10000.0, 3.14
    correct = cf.mcwhirter_threshold(t_k, d_e)
    t_ev = cf.K_B_EV * t_k
    slip = cf.mcwhirter_threshold(t_ev, d_e)     # eV number inserted where kelvin is required
    return {"temperature_K": t_k, "temperature_eV": t_ev, "gap_eV": d_e,
            "threshold_cm3": correct, "threshold_with_eV_inserted_cm3": slip,
            "ratio": correct / slip}


def example_a4_sensitivity() -> dict:
    """Logarithmic sensitivities of Boltzmann and Saha factors."""
    t_k = 10000.0
    kt = cf.K_B_EV * t_k
    out = {"kT_eV": kt}
    for e_k in (3.0, 4.0, 5.0, 6.0):
        out[f"dln_n_dlnT_Ek_{e_k:.0f}eV"] = -e_k / kt
    for e_ion in (6.0, 7.0, 8.0, 9.0):
        out[f"dln_Saha_dlnT_Eion_{e_ion:.0f}eV"] = 1.5 + e_ion / kt
        # exact change of the ion-to-neutral ratio for a 5% higher temperature
        out[f"Saha_factor_for_T_plus_5pct_Eion_{e_ion:.0f}eV"] = (
            cf.saha_ratio(1.05 * t_k, 1e17, 1.0, 1.0, e_ion) / cf.saha_ratio(t_k, 1e17, 1.0, 1.0, e_ion))
    return out


def example_a4_lowering() -> dict:
    """Debye-Hueckel estimate of the ionization-energy lowering and its effect on the Saha ratio."""
    t_k, n_e_cm3 = 10000.0, 1.0e17
    eps0 = 8.8541878188e-12            # F/m, CODATA 2022
    n_e = n_e_cm3 * 1e6                # m^-3
    out = {"temperature_K": t_k, "n_e_cm3": n_e_cm3}
    for label, charge_factor in (("electrons_only", 1.0), ("electrons_and_singly_charged_ions", 2.0)):
        debye_m = math.sqrt(eps0 * cf.K_B_J * t_k / (charge_factor * n_e * cf.E_CHARGE**2))
        lowering_ev = cf.E_CHARGE / (4.0 * math.pi * eps0 * debye_m)      # e^2/(4 pi eps0 lambda_D), in eV
        out[label] = {"debye_length_nm": debye_m * 1e9, "lowering_eV": lowering_ev,
                      "saha_ratio_factor": math.exp(lowering_ev / (cf.K_B_EV * t_k))}
    return out


def example_a4_basis() -> dict:
    """Mole and mass fractions for nominal alloy grades."""
    rows = []
    for name, comp in {**MATERIALS, **RECORD_MATERIAL}.items():
        els = list(comp)
        w = [comp[e] / 100.0 for e in els]
        m = [ATOMIC_WEIGHT[e] for e in els]
        x = cf.mass_to_mole(w, m)
        back = cf.mole_to_mass(x, m)
        mbar = cf.mean_molar_mass_from_mole(x, m)
        for e, wi, xi, mi, bi in zip(els, w, x, m, back):
            rows.append({"material": name, "element": e, "molar_mass": mi,
                         "mass_percent": 100 * wi, "mole_percent": 100 * xi,
                         "mean_molar_mass": mbar, "M_over_mean": mi / mbar,
                         "reported_over_true_if_unconverted": xi / wi,
                         "relative_error_percent_if_unconverted": 100 * (xi / wi - 1.0),
                         "roundtrip_mass_percent": 100 * bi})
    return {"rows": rows}


def example_a4_closure() -> dict:
    """Detected-set normalization versus whole-sample mass fractions."""
    # constructed mineral-element content of a dried biological material, mg/kg of dry mass
    whole = {"K": 20000.0, "Ca": 12000.0, "Mg": 4000.0, "P": 3000.0, "S": 2500.0, "Fe": 300.0}
    total = sum(whole.values())
    subset_percent = {k: 100 * v / total for k, v in whole.items()}
    return {"whole_sample_mg_per_kg": whole, "detected_total_mg_per_kg": total,
            "detected_total_mass_percent": total / 1e4,
            "subset_normalized_percent": subset_percent,
            "scale_factor_subset_to_whole": total / 1e6}


def example_a4_inverse() -> dict:
    """Inverse use of a weak empirical relation y = a + b C."""
    a, b, c = 1.80, 0.050, 4.0          # C in mass percent
    y = a + b * c
    amp = y / (b * c)
    rel_y = 0.05
    c_lo = (y - a) / 0.055      # a slope printed as 0.05 is compatible with 0.045 ... 0.055
    c_hi = (y - a) / 0.045
    return {"a": a, "b": b, "C": c, "y": y, "amplification": amp,
            "rel_uncertainty_y": rel_y, "rel_uncertainty_C": amp * rel_y,
            "C_if_slope_rounded_up": c_lo, "C_if_slope_rounded_down": c_hi,
            "rel_spread_from_one_digit_slope_percent": [100 * (c_lo / c - 1), 100 * (c_hi / c - 1)]}


def example_a5() -> dict:
    """Deviation, dispersion and uncertainty are different quantities."""
    reps = [47.1, 47.6, 47.9, 48.2, 48.7]
    mean, sd = cf.mean_sd(reps)
    ref, u_ref = 45.0, 0.30
    u_rep = sd / math.sqrt(len(reps))
    u_full = 0.06 * mean
    return {"replicates": reps, "mean": mean, "sd": sd, "rsd_percent": 100 * sd / mean,
            "reference": ref, "u_reference": u_ref,
            "signed_deviation_percent": cf.signed_relative_deviation(mean, ref),
            "u_repeatability_of_mean": u_rep,
            "zeta_repeatability_only": cf.zeta_score(mean, u_rep, ref, u_ref),
            "u_full_assumed": u_full,
            "zeta_full_uncertainty": cf.zeta_score(mean, u_full, ref, u_ref)}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res = {"A1": example_a1(), "A2": example_a2(), "A3": example_a3(),
           "A4_sensitivity": example_a4_sensitivity(), "A4_basis": example_a4_basis(),
           "A4_closure": example_a4_closure(), "A4_inverse": example_a4_inverse(),
           "A4_lowering": example_a4_lowering(),
           "A5": example_a5()}
    with open(OUT_DIR / "worked_examples.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
        fh.write("\n")
    with open(OUT_DIR / "table_linewidth.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["G_over_W", "L_over_W_voigt", "L_over_W_quadrature",
                     "Ne_overestimate_percent_uncorrected", "Ne_overestimate_percent_quadrature"])
        for r in res["A1"]["table"]:
            wr.writerow([f"{r['G_over_W']:.1f}", f"{r['L_over_W_voigt']:.4f}", f"{r['L_over_W_quadrature']:.4f}",
                         f"{r['ne_bias_uncorrected_percent']:.1f}", f"{r['ne_bias_quadrature_percent']:.1f}"])
    with open(OUT_DIR / "table_basis.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["material", "element", "molar_mass_g_mol", "mass_percent", "mole_percent",
                     "mean_molar_mass_g_mol", "M_over_mean", "reported_over_true_if_unconverted",
                     "relative_error_percent_if_unconverted"])
        for r in res["A4_basis"]["rows"]:
            wr.writerow([r["material"], r["element"], r["molar_mass"], f"{r['mass_percent']:.2f}",
                         f"{r['mole_percent']:.2f}", f"{r['mean_molar_mass']:.2f}", f"{r['M_over_mean']:.4f}",
                         f"{r['reported_over_true_if_unconverted']:.4f}",
                         f"{r['relative_error_percent_if_unconverted']:.1f}"])

    # ------------------------------ checks ------------------------------
    lines, ok = [], True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok = ok and cond
        lines.append(f"{'PASS' if cond else 'FAIL'}: {name}")

    a1 = res["A1"]["table"]
    check("A1 Voigt inversion round trip", all(abs(cf.voigt_fwhm(r["L_over_W_voigt"], r["G_over_W"]) - 1.0) < 1e-12 for r in a1))
    check("A1 quadrature subtraction always leaves a wider Lorentzian than the Voigt inversion",
          all(r["L_over_W_quadrature"] > r["L_over_W_voigt"] for r in a1))
    # the Olivero-Longbothum coefficients give W = 1.000003 L for a pure Lorentzian
    check("A1 zero Gaussian width returns the observed width (to 1 part in 1e5)",
          abs(cf.lorentz_from_voigt(0.2, 0.0) / 0.2 - 1.0) < 1e-5)
    check("A1 G/W = 0.5: uncorrected density overestimated by 36%", round(a1[4]["ne_bias_uncorrected_percent"]) == 36)
    appr = res["A1"]["approximation_check"]
    check("A1 the width approximation agrees with an exact Voigt profile to better than 0.03%",
          appr["max_relative_deviation_percent"] < 0.03)
    check("A1 exact inversion at the operating point of the record gives 0.12397 nm (approximation: 0.12400 nm)",
          f"{appr['record_point']['lorentz_fwhm_exact_nm']:.5f}" == "0.12397"
          and f"{appr['record_point']['lorentz_fwhm_approximation_nm']:.5f}" == "0.12400")
    check("A3 unit slip lowers the threshold by sqrt(11604.5) = 107.7", abs(res["A3"]["ratio"] - math.sqrt(1 / cf.K_B_EV)) < 1e-6)
    basis = res["A4_basis"]["rows"]
    check("A4 mole/mass round trip", all(abs(r["roundtrip_mass_percent"] - r["mass_percent"]) < 1e-10 for r in basis))
    check("A4 unconverted error equals mean molar mass over molar mass",
          all(abs(r["reported_over_true_if_unconverted"] - 1.0 / r["M_over_mean"]) < 1e-12 for r in basis))
    al = next(r for r in basis if r["element"] == "Al" and r["material"].startswith("Ti"))
    check("A4 Ti-6Al-4V: 6.00 mass% Al equals 10.20 mole%", abs(al["mole_percent"] - 10.20) < 0.005)
    sens = res["A4_sensitivity"]
    check("A2 a 5% higher T raises the Saha ratio by a factor of 1.50 (E_ion 6 eV) to 1.77 (9 eV)",
          round(sens["Saha_factor_for_T_plus_5pct_Eion_6eV"], 2) == 1.50
          and round(sens["Saha_factor_for_T_plus_5pct_Eion_9eV"], 2) == 1.77)
    rec_rows = {r["element"]: r for r in basis if r["material"].startswith("Constructed")}
    check("A4 constructed record: 6/91/3 mass% equals 11.92/87.20/0.87 mole%",
          [round(rec_rows[e]["mole_percent"], 2) for e in "XYZ"] == [11.92, 87.20, 0.87])
    check("A4 inverse relation amplifies a 5% input uncertainty to 50%", abs(res["A4_inverse"]["rel_uncertainty_C"] - 0.50) < 1e-9)
    low = res["A4_lowering"]
    check("A4 ionization-energy lowering is 0.07 to 0.09 eV at 1e17 cm^-3 and 10,000 K",
          round(low["electrons_only"]["lowering_eV"], 2) == 0.07
          and round(low["electrons_and_singly_charged_ions"]["lowering_eV"], 2) == 0.09)
    li = res["A1"]["lorentzian_instrument"]["G_over_W_0.4"]
    check("A1 Lorentzian instrumental profile at G/W = 0.4: overestimates of 67% and 53%",
          round(li["ne_bias_uncorrected_percent"]) == 67 and round(li["ne_bias_quadrature_percent"]) == 53)
    check("A2 Saha prefactor: 4.83e15 with T in K and 6.04e21 with T in eV",
          f"{res['A2']['saha_prefactor_cm-3_K-1.5']:.2e}" == "4.83e+15"
          and f"{res['A2']['saha_prefactor_cm-3_eV-1.5']:.2e}" == "6.04e+21")
    check("A5 signed deviation +6.4%, RSD 1.3%", round(res["A5"]["signed_deviation_percent"], 1) == 6.4 and round(res["A5"]["rsd_percent"], 1) == 1.3)
    for bad, label in (((float("nan"), 0.1), "NaN width"), ((0.1, 0.2), "unresolved Lorentzian"), ((-0.1, 0.05), "negative width")):
        try:
            cf.lorentz_from_voigt(*bad)
            check(f"reject {label}", False)
        except ValueError:
            check(f"reject {label}", True)
    for fn, args, label in ((cf.signed_relative_deviation, (1.0, 0.0), "zero comparator"),
                            (cf.mole_to_mass, ([], []), "empty vectors"),
                            (cf.mole_to_mass, ([0.5, 0.5], [1.0, 0.0]), "zero molar mass"),
                            (cf.mcwhirter_threshold, (-1.0, 3.0), "negative temperature")):
        try:
            fn(*args)
            check(f"reject {label}", False)
        except ValueError:
            check(f"reject {label}", True)
    text = "\n".join([f"{sum(l.startswith('PASS') for l in lines)} of {len(lines)} checks passed.", ""] + lines) + "\n"
    (OUT_DIR / "check_log_examples.txt").write_text(text, encoding="utf-8")
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
