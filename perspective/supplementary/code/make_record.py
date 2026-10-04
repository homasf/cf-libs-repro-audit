#!/usr/bin/env python3
"""Generate the constructed CF-LIBS reporting record used in the Perspective.

The record describes a HYPOTHETICAL ternary sample made of three hypothetical
elements X, Y and Z. Their molar masses, ionization energies, partition
functions and line data are invented values of realistic magnitude (a light
metal, a transition metal and a heavy refractory metal). Nothing here is a
measurement, and the line data must not be used as atomic data.

Forward model: homogeneous, optically thin LTE plasma at a chosen temperature
and electron density; neutral and singly ionized charge states; partition
functions taken as constants; Gaussian intensity noise from a seeded
generator. The script writes

    ../record/record.json            the reporting record (inputs and conventions)
    ../record/line_intensities.csv   replicate-level integrated line intensities

and is deterministic: running it twice gives byte-identical files.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import cflibs_chain as cf

HERE = Path(__file__).resolve().parent
REC_DIR = HERE.parent / "record"

# ---------------------------------------------------------------- truth ----
T_TRUE_K = 10000.0
NE_TRUE_CM3 = 1.00e17
MASS_FRACTION_TRUE = {"X": 0.060, "Y": 0.910, "Z": 0.030}
N_REPLICATES = 5
INTENSITY_REL_SD = 0.03
SEED = 20261002
SCALE = 2.5e-3          # arbitrary instrument factor F (sets a count-like scale)

ELEMENTS = {
    "X": {"molar_mass_g_mol": 27.0, "ionization_energy_eV": 6.00,
          "note": "hypothetical light metal"},
    "Y": {"molar_mass_g_mol": 56.0, "ionization_energy_eV": 7.90,
          "note": "hypothetical transition metal (matrix)"},
    "Z": {"molar_mass_g_mol": 184.0, "ionization_energy_eV": 7.50,
          "note": "hypothetical heavy refractory metal"},
}
SPECIES = {
    "X I":  {"partition_function": 6.0,  "ground_level_g": 2},
    "X II": {"partition_function": 1.1,  "ground_level_g": 1},
    "Y I":  {"partition_function": 58.0, "ground_level_g": 9},
    "Y II": {"partition_function": 64.0, "ground_level_g": 10},
    "Z I":  {"partition_function": 14.0, "ground_level_g": 1},
    "Z II": {"partition_function": 16.0, "ground_level_g": 2},
}
# species, E_lower (eV), E_upper (eV), g_upper, A_ki (s^-1)
# No line of the matrix element Y ends on its ground level.
LINES = [
    ("X I", 0.00, 3.14, 2, 5.0e7),
    ("X I", 0.00, 4.02, 4, 6.0e7),
    ("X I", 0.00, 4.83, 6, 7.5e7),
    ("X I", 3.14, 5.24, 2, 1.2e7),
    ("Y I", 0.86, 3.33, 11, 1.6e7),
    ("Y I", 0.92, 3.40, 7, 1.0e7),
    ("Y I", 0.99, 4.10, 9, 2.5e7),
    ("Y I", 1.48, 4.73, 7, 6.0e7),
    ("Y I", 2.20, 5.10, 9, 4.0e7),
    ("Y I", 2.40, 5.85, 5, 8.0e7),
    ("Y I", 3.21, 6.20, 7, 5.0e7),
    ("Y II", 0.99, 4.77, 10, 2.2e8),
    ("Y II", 1.07, 5.55, 8, 1.5e8),
    ("Y II", 1.67, 5.90, 6, 3.0e7),
    ("Y II", 2.58, 7.10, 10, 1.8e8),
    ("Y II", 3.20, 7.75, 8, 1.2e8),
    ("Z II", 0.00, 4.40, 6, 1.0e8),
    ("Z II", 1.46, 5.80, 8, 1.6e8),
    ("Z II", 1.67, 6.10, 10, 9.0e7),
    ("Z II", 2.90, 6.95, 8, 7.0e7),
    ("Z II", 3.10, 7.60, 6, 1.1e8),
]
A_REL_SD = 0.10
U_REL_SD = 0.05
STARK = {
    "species": "X I",
    "line_id": "XI_4",
    "line_note": "non-resonant line (lower level at 3.14 eV)",
    "fit_profile": "Voigt",
    "instrument_gaussian_fwhm_nm": 0.060,
    "instrument_gaussian_fwhm_sd_nm": 0.005,
    "instrument_profile_source": ("constructed value; an experimental record states how the "
                                  "instrumental profile was measured at the diagnostic wavelength"),
    "width_treatment": "voigt",
    "width_treatment_definition": ("Lorentzian FWHM from the closed-form inversion of the Olivero-Longbothum "
                                   "approximation W = 0.5346 L + sqrt(0.2166 L^2 + G^2)"),
    "stark_parameter_nm": 0.0062,
    "stark_parameter_definition": "electron-impact half width at half maximum (HWHM)",
    "stark_parameter_source": "constructed value (no database)",
    "reference_density_cm3": 1.0e16,
    "reference_temperature_K": 10000.0,
    "stark_parameter_rel_sd": 0.20,
    "other_broadening": "Doppler and resonance broadening neglected; ion-broadening term neglected",
    "observed_fwhm_sd_nm": 0.003,
}
MC_DRAWS = 200000
MC_SEED = 97531


def _first_deviates(seed: int, count: int) -> list:
    """First normal deviates of the documented generator, stored as a check."""
    normal = cf.SeededNormal(seed)
    return [normal.draw() for _ in range(count)]


def sig_str(value: float, digits: int = 4) -> str:
    """Format with a fixed number of significant digits, keeping trailing zeros."""
    if value == 0:
        return "0"
    exponent = int(math.floor(math.log10(abs(value))))
    decimals = max(digits - 1 - exponent, 0)
    rounded = round(value, digits - 1 - exponent)
    return f"{rounded:.{decimals}f}"


def forward_intensities() -> dict:
    """Noise-free photon-unit line intensities for the true plasma state."""
    names = list(ELEMENTS)
    molar = [ELEMENTS[n]["molar_mass_g_mol"] for n in names]
    x = cf.mass_to_mole([MASS_FRACTION_TRUE[n] for n in names], molar)
    n_el = dict(zip(names, x))                       # relative elemental number densities
    out = {}
    counters: dict = {}
    for sp, e_i, e_k, g_k, a_ki in LINES:
        el, stage = sp.split()
        s_ratio = cf.saha_ratio(T_TRUE_K, NE_TRUE_CM3,
                                SPECIES[f"{el} II"]["partition_function"],
                                SPECIES[f"{el} I"]["partition_function"],
                                ELEMENTS[el]["ionization_energy_eV"])
        n_species = n_el[el] / (1.0 + s_ratio) if stage == "I" else n_el[el] * s_ratio / (1.0 + s_ratio)
        counters[sp] = counters.get(sp, 0) + 1
        line_id = f"{sp.replace(' ', '')}_{counters[sp]}"
        inten = (SCALE * n_species * g_k * a_ki / SPECIES[sp]["partition_function"]
                 * math.exp(-e_k / (cf.K_B_EV * T_TRUE_K)))
        out[line_id] = {"species": sp, "E_i_eV": e_i, "E_k_eV": e_k, "g_k": g_k,
                        "A_ki_s-1": a_ki,
                        "wavelength_nm": round(cf.HC_EV_NM / (e_k - e_i), 2),
                        "intensity": inten}
    return out


def build() -> tuple[dict, list]:
    clean = forward_intensities()
    normal = cf.SeededNormal(SEED)
    rows = []
    for line_id, info in clean.items():
        reps = [sig_str(info["intensity"] * (1.0 + INTENSITY_REL_SD * normal.draw()), 4)
                for _ in range(N_REPLICATES)]
        rows.append([line_id] + reps)

    stark = dict(STARK)
    l_true = 2.0 * STARK["stark_parameter_nm"] * NE_TRUE_CM3 / STARK["reference_density_cm3"]
    stark["observed_fwhm_nm"] = round(cf.voigt_fwhm(l_true, STARK["instrument_gaussian_fwhm_nm"]), 5)
    stark["wavelength_nm"] = clean[STARK["line_id"]]["wavelength_nm"]

    record = {
        "record_version": "1.2",
        "title": "Constructed CF-LIBS reporting record (hypothetical ternary sample X-Y-Z)",
        "disclaimer": ("All values are constructed for illustration. X, Y and Z are hypothetical "
                       "elements; the line data are not atomic data and the sample does not exist."),
        "conventions": {
            "intensity_units": "photon",
            "intensity_definition": ("integrated line area after background subtraction and "
                                     "relative spectral-response correction; common arbitrary scale"),
            "boltzmann_ordinate": "ln[I / (g_k A_ki)]",
            "logarithm": "natural",
            "energy_unit": "eV",
            "temperature_unit": "K",
            "fit": "unweighted least squares; one common slope, one intercept per species",
            "temperature_model": "one temperature common to all species",
            "saha": ("neutral and singly ionized charge states; no ionization-energy lowering; "
                     "electron density from the Stark width; temperature from the Boltzmann plot"),
            "partition_functions": "constants (not re-evaluated when the temperature changes)",
            "residual_definition": ("residual standard deviation of the Boltzmann plot with n - (number of "
                                    "species) - 1 degrees of freedom; where one value is quoted, it is the "
                                    "arithmetic mean over the replicates"),
            "result_definition": ("arithmetic mean of the replicate-level mass fractions; mole fractions are "
                                  "likewise the arithmetic mean of the replicate-level mole fractions"),
            "replicate_definition": ("one replicate = one accumulated spectrum; replicates differ "
                                     "only by independent intensity noise in this constructed case"),
            "dispersion_measure": "sample standard deviation (n - 1) of the replicate-level results",
            "internal_basis": "mole fraction over the closure set",
            "reported_basis": "mass fraction over the closure set",
            "closure_set": list(ELEMENTS),
            "constituents_outside_closure_set": "none (constructed sample)",
            "constants": {"k_B_eV_per_K": cf.K_B_EV, "hc_eV_nm": cf.HC_EV_NM,
                          "saha_constant_cm-3_K-1.5": cf.SAHA_PREFACTOR,
                          "saha_constant_definition": ("(2 pi m_e k_B / h^2)^(3/2); the Saha equation contains "
                                                       "twice this value (statistical weight of the electron)"),
                          "source": "2019 SI exact constants; electron mass CODATA 2022"},
        },
        "acquisition": {
            "status": "not applicable - constructed data",
            "fields_required_in_an_experimental_record": [
                "laser wavelength, pulse duration, pulse energy, spot size",
                "ambient gas and pressure", "gate delay and gate width", "number of accumulated pulses",
                "collection geometry", "spectrometer, detector, spectral range and resolving power",
                "wavelength calibration", "relative spectral-response calibration and its lamp",
                "background and continuum treatment, integration limits, deblending"],
        },
        "elements": ELEMENTS,
        "species": {sp: dict(v, partition_function_source="constructed constant",
                             partition_function_rel_sd=U_REL_SD)
                    for sp, v in SPECIES.items()},
        "stark_line": stark,
        "assumption_checks": [
            {"assumption": "local thermodynamic equilibrium",
             "test": "McWhirter criterion, N_e >= 1.6e12 sqrt(T[K]) (dE[eV])^3",
             "largest_gap_eV": 3.14,
             "gap_definition": "X I ground level to first excited level",
             "temperature_used": "mean of the replicate temperatures",
             "acceptance": "electron density above the threshold",
             "not_covered": "relaxation-time and diffusion-length criteria (not meaningful for constructed data)"},
            {"assumption": "Saha-Boltzmann consistency",
             "test": "electron density implied by the ion-to-neutral ratio of Y versus the Stark value",
             "acceptance": "none imposed; the ratio is reported"},
            {"assumption": "optical thinness",
             "status": "true by construction",
             "note": ("an experimental record lists line-ratio tests with lines, measured and expected "
                      "ratios; lines ending on or near a ground level (XI_1 to XI_3, ZII_1) would "
                      "have to be tested or excluded")},
            {"assumption": "homogeneity and stoichiometric ablation",
             "status": "not applicable - constructed data"},
        ],
        "lines": [{"id": k, "species": v["species"], "wavelength_nm": v["wavelength_nm"],
                   "E_i_eV": v["E_i_eV"], "E_k_eV": v["E_k_eV"], "g_k": v["g_k"],
                   "A_ki_s-1": v["A_ki_s-1"], "A_rel_sd": A_REL_SD,
                   "data_source": "constructed (no database, no accuracy class)"}
                  for k, v in clean.items()],
        "intensity_file": "line_intensities.csv",
        "n_replicates": N_REPLICATES,
        "reference": {
            "basis": "mass fraction",
            "values": MASS_FRACTION_TRUE,
            "standard_uncertainty": {"X": 0.0006, "Y": 0.0020, "Z": 0.0003},
            "provenance": "constructed nominal composition",
        },
        "uncertainty_budget": {
            "components": [
                {"quantity": "Stark parameter", "relative_standard_uncertainty": STARK["stark_parameter_rel_sd"],
                 "distribution": "lognormal, median 1"},
                {"quantity": "observed FWHM of the diagnostic line",
                 "standard_uncertainty_nm": STARK["observed_fwhm_sd_nm"], "distribution": "normal"},
                {"quantity": "instrumental FWHM",
                 "standard_uncertainty_nm": STARK["instrument_gaussian_fwhm_sd_nm"], "distribution": "normal"},
                {"quantity": "transition probability of each line", "relative_standard_uncertainty": A_REL_SD,
                 "distribution": "lognormal, median 1, independent between lines"},
                {"quantity": "partition function of each species", "relative_standard_uncertainty": U_REL_SD,
                 "distribution": "lognormal, median 1, independent between species"},
                {"quantity": "intensity noise",
                 "treatment": "standard deviation of the mean of the replicate-level results"},
            ],
            "monte_carlo": {
                "draws": MC_DRAWS, "seed": MC_SEED,
                "lognormal_parameter": "sigma = sqrt(ln(1 + r^2)) for a relative standard uncertainty r",
                "generator": ("standard normal deviate z = sqrt(-2 ln(1 - u1)) cos(2 pi u2), where u1 and u2 "
                              "are successive outputs of Python's random.Random(seed).random(); one deviate "
                              "per pair of uniform deviates"),
                "check_deviates": [round(v, 6) for v in _first_deviates(MC_SEED, 3)],
                "draw_order": ("per draw: Stark parameter, observed width, instrumental width, transition "
                               "probabilities in line order, partition functions in species order"),
                "percentiles": "order statistic with 0-based index round(q (n - 1)) of the sorted draws",
                "relative_uncertainties": "standard deviation over the draws divided by the plug-in value",
                "combination": "Monte Carlo standard deviation combined in quadrature with the standard deviation of the mean",
            },
        },
        "generation": {"T_true_K": T_TRUE_K, "Ne_true_cm3": NE_TRUE_CM3,
                       "scale_factor_F": SCALE,
                       "intensity_rel_sd": INTENSITY_REL_SD, "seed": SEED,
                       "noise_model": ("I = I0 (1 + 0.03 z) with standard normal deviates z from the generator "
                                       "defined under uncertainty_budget; five replicate deviates per line, "
                                       "lines in the order of the line list; rounded to four significant digits"),
                       "note": ("the true plasma state is listed so that the forward model can be "
                                "checked; an experimental record has no such block")},
    }
    return record, rows


def main() -> None:
    REC_DIR.mkdir(parents=True, exist_ok=True)
    record, rows = build()
    with open(REC_DIR / "line_intensities.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["line_id"] + [f"replicate_{i + 1}" for i in range(N_REPLICATES)])
        writer.writerows(rows)
    with open(REC_DIR / "record.json", "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    print(f"Wrote {REC_DIR / 'record.json'} and line_intensities.csv "
          f"({len(rows)} lines x {N_REPLICATES} replicates).")


if __name__ == "__main__":
    main()
