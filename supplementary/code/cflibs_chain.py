#!/usr/bin/env python3
"""Minimal, dependency-free implementation of the CF-LIBS calculation chain.

This module accompanies the Perspective "Towards Reconstructable CF-LIBS
Quantification". It is NOT a general CF-LIBS solver. It implements, in the
simplest textbook form, the relations discussed at the five checkpoints
(A1-A5) so that every number quoted in the article can be regenerated:

  A1  Voigt-width relations and Stark-width electron density
  A2  Boltzmann-plot temperature (common slope, species-specific intercepts)
  A3  McWhirter criterion; Saha balance
  A4  Closure, mole fractions, mass fractions
  A5  Signed deviation, relative standard deviation, zeta score

Assumptions of the model: homogeneous, optically thin plasma in local
thermodynamic equilibrium; neutral and singly ionized stages only; no
lowering of the ionization energy. Only the Python standard library is used.
"""
from __future__ import annotations

import math
import random
from typing import Dict, Iterable, List, Sequence, Tuple

# --------------------------------------------------------------------------
# Physical constants (2019 SI exact values; electron mass from CODATA 2022)
# --------------------------------------------------------------------------
K_B_J = 1.380649e-23            # J/K, exact
E_CHARGE = 1.602176634e-19      # C, exact
H_PLANCK = 6.62607015e-34       # J s, exact
C_LIGHT = 299792458.0           # m/s, exact
M_ELECTRON = 9.1093837139e-31   # kg, CODATA 2022

K_B_EV = K_B_J / E_CHARGE                      # 8.617333262e-5 eV/K
HC_EV_NM = H_PLANCK * C_LIGHT / E_CHARGE * 1e9  # 1239.841984 eV nm
#: (2 pi m_e k_B / h^2)^(3/2) in cm^-3 K^-3/2
SAHA_PREFACTOR = (2 * math.pi * M_ELECTRON * K_B_J / H_PLANCK**2) ** 1.5 * 1e-6

# Olivero-Longbothum coefficients for the Voigt FWHM approximation
_OL_A = 0.5346
_OL_B = 0.2166


def _finite(*values: float) -> None:
    for v in values:
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"non-finite or non-numeric input: {v!r}")


class SeededNormal:
    """Box-Muller normal deviates built on random.random() only.

    Each deviate uses two successive outputs u1, u2 of random.Random(seed).random():

        z = sqrt(-2 ln(1 - u1)) cos(2 pi u2)

    (1 - u1 lies in (0, 1], which keeps the logarithm finite). random.random()
    is the one generator output that Python guarantees to be reproducible
    across versions for a given seed, so the constructed record and the Monte
    Carlo propagation are bit-for-bit repeatable.
    """

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def draw(self) -> float:
        u1 = 1.0 - self._rng.random()        # (0, 1]
        u2 = self._rng.random()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


# --------------------------------------------------------------------------
# A1  Linewidths and electron density
# --------------------------------------------------------------------------
def voigt_fwhm(lorentz_fwhm: float, gauss_fwhm: float) -> float:
    """Voigt FWHM from Lorentzian and Gaussian FWHM (Olivero & Longbothum)."""
    _finite(lorentz_fwhm, gauss_fwhm)
    if lorentz_fwhm < 0 or gauss_fwhm < 0:
        raise ValueError("widths must be non-negative")
    return _OL_A * lorentz_fwhm + math.sqrt(_OL_B * lorentz_fwhm**2 + gauss_fwhm**2)


def lorentz_from_voigt(voigt: float, gauss_fwhm: float) -> float:
    """Lorentzian FWHM consistent with an observed Voigt FWHM and a Gaussian FWHM.

    Closed-form inversion of the Olivero-Longbothum approximation. Raises
    ValueError when the Gaussian width is not smaller than the observed width
    (the Lorentzian component is then unresolved).
    """
    _finite(voigt, gauss_fwhm)
    if voigt <= 0 or gauss_fwhm < 0:
        raise ValueError("observed width must be positive, Gaussian width non-negative")
    if gauss_fwhm > voigt:
        raise ValueError("Gaussian width exceeds observed width: Lorentzian component unresolved")
    a2 = _OL_A**2 - _OL_B          # 0.0692
    disc = (2 * _OL_A * voigt) ** 2 - 4 * a2 * (voigt**2 - gauss_fwhm**2)
    return (2 * _OL_A * voigt - math.sqrt(disc)) / (2 * a2)


def quadrature_subtraction_width(observed: float, gauss_fwhm: float) -> float:
    """Quadrature subtraction sqrt(W^2 - G^2): exact only when BOTH profiles are Gaussian."""
    _finite(observed, gauss_fwhm)
    if gauss_fwhm > observed:
        raise ValueError("Gaussian width exceeds observed width")
    return math.sqrt(observed**2 - gauss_fwhm**2)


def stark_density(stark_fwhm: float, half_width_param: float, n_ref: float) -> float:
    """N_e = (Delta_lambda_S / (2 w)) * N_ref.

    stark_fwhm        Stark (Lorentzian) FWHM of the line
    half_width_param  Stark parameter: electron-impact HALF width (HWHM) at n_ref,
                      in the same wavelength unit as stark_fwhm
    n_ref             reference electron density of the tabulation (cm^-3)
    """
    _finite(stark_fwhm, half_width_param, n_ref)
    if stark_fwhm < 0 or half_width_param <= 0 or n_ref <= 0:
        raise ValueError("invalid Stark inputs")
    return stark_fwhm / (2.0 * half_width_param) * n_ref


# --------------------------------------------------------------------------
# A2  Boltzmann plot
# --------------------------------------------------------------------------
def boltzmann_ordinate(intensity: float, g_upper: float, a_ki: float,
                       wavelength_nm: float | None = None,
                       intensity_units: str = "photon",
                       log: str = "ln") -> float:
    """Ordinate of the Boltzmann plot.

    intensity_units = "photon": y = ln[I / (g A)]
    intensity_units = "energy": y = ln[I lambda / (g A)]
    (lambda in nm; a constant offset common to all lines is irrelevant.)
    """
    _finite(intensity, g_upper, a_ki)
    if intensity <= 0 or g_upper <= 0 or a_ki <= 0:
        raise ValueError("intensity, g and A must be positive")
    arg = intensity / (g_upper * a_ki)
    if intensity_units == "energy":
        if wavelength_nm is None or wavelength_nm <= 0:
            raise ValueError("wavelength required for energy-unit intensities")
        arg *= wavelength_nm
    elif intensity_units != "photon":
        raise ValueError("intensity_units must be 'photon' or 'energy'")
    if log == "ln":
        return math.log(arg)
    if log == "log10":
        return math.log10(arg)
    raise ValueError("log must be 'ln' or 'log10'")


def common_slope_fit(groups: Dict[str, Sequence[Tuple[float, float]]]) -> dict:
    """Least-squares fit y = q_s + m E with one slope m and one intercept per group.

    groups maps a species label to a sequence of (E_upper_eV, y) points.
    Returns the slope, its standard error, the intercepts and the residual SD.
    """
    sxx = sxy = 0.0
    means = {}
    n_tot = 0
    for label, pts in groups.items():
        if len(pts) < 2:
            raise ValueError(f"species {label}: at least two lines are required")
        e_mean = sum(p[0] for p in pts) / len(pts)
        y_mean = sum(p[1] for p in pts) / len(pts)
        means[label] = (e_mean, y_mean)
        for e, y in pts:
            sxx += (e - e_mean) ** 2
            sxy += (e - e_mean) * (y - y_mean)
        n_tot += len(pts)
    if sxx <= 0:
        raise ValueError("no spread in upper-level energies")
    slope = sxy / sxx
    intercepts = {lab: ym - slope * em for lab, (em, ym) in means.items()}
    ss_res = 0.0
    for label, pts in groups.items():
        for e, y in pts:
            ss_res += (y - intercepts[label] - slope * e) ** 2
    dof = n_tot - len(groups) - 1
    resid_sd = math.sqrt(ss_res / dof) if dof > 0 else float("nan")
    slope_se = resid_sd / math.sqrt(sxx) if dof > 0 else float("nan")
    return {"slope": slope, "slope_se": slope_se, "intercepts": intercepts,
            "residual_sd": resid_sd, "n_lines": n_tot, "sxx": sxx,
            "mean_energy": {lab: em for lab, (em, _) in means.items()}}


def temperature_from_slope(slope_per_ev: float, log: str = "ln") -> float:
    """T (K) from the Boltzmann-plot slope; slope = -1/(k_B T) for natural logs."""
    _finite(slope_per_ev)
    if slope_per_ev >= 0:
        raise ValueError("Boltzmann slope must be negative")
    factor = 1.0 if log == "ln" else math.log(10.0)
    return -1.0 / (K_B_EV * slope_per_ev * factor)


# --------------------------------------------------------------------------
# A3  Plasma-model checks
# --------------------------------------------------------------------------
def mcwhirter_threshold(temperature_k: float, delta_e_ev: float) -> float:
    """Minimum N_e (cm^-3) of the McWhirter criterion; T in kelvin, dE in eV."""
    _finite(temperature_k, delta_e_ev)
    if temperature_k <= 0 or delta_e_ev <= 0:
        raise ValueError("temperature and energy gap must be positive")
    return 1.6e12 * math.sqrt(temperature_k) * delta_e_ev**3


def saha_ratio(temperature_k: float, n_e: float, u_ion: float, u_neutral: float,
               e_ion_ev: float) -> float:
    """n_II / n_I from the Saha equation (no ionization-energy lowering)."""
    _finite(temperature_k, n_e, u_ion, u_neutral, e_ion_ev)
    if min(temperature_k, n_e, u_ion, u_neutral, e_ion_ev) <= 0:
        raise ValueError("Saha inputs must be positive")
    return (2.0 * SAHA_PREFACTOR * temperature_k**1.5 / n_e * (u_ion / u_neutral)
            * math.exp(-e_ion_ev / (K_B_EV * temperature_k)))


# --------------------------------------------------------------------------
# A4  Concentration basis
# --------------------------------------------------------------------------
def _check_vectors(a: Sequence[float], b: Sequence[float]) -> None:
    if len(a) == 0 or len(a) != len(b):
        raise ValueError("vectors must be non-empty and of equal length")
    for v in list(a) + list(b):
        _finite(v)
    if any(v < 0 for v in a) or any(m <= 0 for m in b):
        raise ValueError("fractions must be non-negative and molar masses positive")
    if sum(a) <= 0:
        raise ValueError("fractions sum to zero")


def mole_to_mass(x: Sequence[float], molar_mass: Sequence[float]) -> List[float]:
    """w_s = x_s M_s / sum_j x_j M_j (normalized to unity)."""
    _check_vectors(x, molar_mass)
    tot = sum(xi * mi for xi, mi in zip(x, molar_mass))
    return [xi * mi / tot for xi, mi in zip(x, molar_mass)]


def mass_to_mole(w: Sequence[float], molar_mass: Sequence[float]) -> List[float]:
    """x_s = (w_s / M_s) / sum_j (w_j / M_j) (normalized to unity)."""
    _check_vectors(w, molar_mass)
    tot = sum(wi / mi for wi, mi in zip(w, molar_mass))
    return [wi / mi / tot for wi, mi in zip(w, molar_mass)]


def mean_molar_mass_from_mole(x: Sequence[float], molar_mass: Sequence[float]) -> float:
    _check_vectors(x, molar_mass)
    s = sum(x)
    return sum(xi * mi for xi, mi in zip(x, molar_mass)) / s


# --------------------------------------------------------------------------
# A5  Validation statistics
# --------------------------------------------------------------------------
def signed_relative_deviation(c_method: float, c_reference: float) -> float:
    """100 (C_m - C_r) / C_r, in percent."""
    _finite(c_method, c_reference)
    if c_reference <= 0:
        raise ValueError("reference value must be positive")
    return 100.0 * (c_method - c_reference) / c_reference


def mean_sd(values: Iterable[float]) -> Tuple[float, float]:
    vals = list(values)
    if len(vals) < 2:
        raise ValueError("at least two values are required")
    m = sum(vals) / len(vals)
    s = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    return m, s


def rsd_percent(values: Iterable[float]) -> float:
    m, s = mean_sd(values)
    if m <= 0:
        raise ValueError("mean must be positive")
    return 100.0 * s / m


def zeta_score(c_method: float, u_method: float, c_reference: float, u_reference: float) -> float:
    """(C_m - C_r) / sqrt(u_m^2 + u_r^2) with standard uncertainties."""
    _finite(c_method, u_method, c_reference, u_reference)
    denom = math.sqrt(u_method**2 + u_reference**2)
    if denom <= 0:
        raise ValueError("combined uncertainty must be positive")
    return (c_method - c_reference) / denom


# --------------------------------------------------------------------------
# Complete reconstruction of a record (used for the constructed example)
# --------------------------------------------------------------------------
def lte_gap_ev(record: dict) -> float:
    """Largest energy gap used in the McWhirter criterion, as stated in the record."""
    for item in record["assumption_checks"]:
        if "largest_gap_eV" in item:
            return item["largest_gap_eV"]
    raise ValueError("record states no energy gap for the McWhirter criterion")


def reconstruct(record: dict, intensities: Dict[str, float], overrides: dict | None = None) -> dict:
    """Run A1-A4 on a record and one set of line intensities.

    record       parsed JSON record (see supplementary/record/record.json)
    intensities  mapping line id -> integrated line intensity
    overrides    optional modifications used for the Monte Carlo propagation and
                 for the perturbation scenarios; the recognized keys are listed below

    Recognized override keys (all optional):
      width_treatment              "voigt", "quadrature" or "none"
      observed_fwhm_nm             replaces the stored observed width
      instrument_gaussian_fwhm_nm  replaces the stored instrumental width
      stark_param_factor           multiplies the Stark parameter
      n_ref_factor                 multiplies the reference density
      ne_factor                    multiplies the resulting electron density
      intensity_units              "photon" or "energy" (ordinate of the Boltzmann plot)
      ga_factor                    {species: factor} on the transition probabilities of a species
      line_a_factor                {line id: factor} on single transition probabilities
      response_tilt_per_100nm      intensities multiplied by 1 + tilt (lambda - 400 nm)/(100 nm)
      temperature_factor           multiplies the fitted temperature; intercepts re-derived
      partition_function           "g0": ground-level statistical weights replace U
      u_factor                     {species: factor} on the partition functions
      skip_mass_conversion         True: mole fractions returned in place of mass fractions
    """
    ov = overrides or {}
    conv = record["conventions"]
    elements = record["elements"]
    species = record["species"]

    # ---- A1: electron density from the Stark-broadened line ----
    st = record["stark_line"]
    w_obs = ov.get("observed_fwhm_nm", st["observed_fwhm_nm"])
    g_inst = ov.get("instrument_gaussian_fwhm_nm", st["instrument_gaussian_fwhm_nm"])
    method = ov.get("width_treatment", st["width_treatment"])
    if method == "voigt":
        l_stark = lorentz_from_voigt(w_obs, g_inst)
    elif method == "quadrature":
        l_stark = quadrature_subtraction_width(w_obs, g_inst)
    elif method == "none":
        l_stark = w_obs
    else:
        raise ValueError(f"unknown width treatment {method!r}")
    w_param = st["stark_parameter_nm"] * ov.get("stark_param_factor", 1.0)
    n_ref = st["reference_density_cm3"] * ov.get("n_ref_factor", 1.0)
    n_e = stark_density(l_stark, w_param, n_ref) * ov.get("ne_factor", 1.0)

    # ---- A2: common-slope Boltzmann plot ----
    units = ov.get("intensity_units", conv["intensity_units"])
    ga_factor = ov.get("ga_factor", {})          # species -> multiplicative factor on gA
    line_factor = ov.get("line_a_factor", {})    # line id -> multiplicative factor on A_ki
    resp_tilt = ov.get("response_tilt_per_100nm", 0.0)
    groups: Dict[str, List[Tuple[float, float]]] = {}
    for line in record["lines"]:
        sp = line["species"]
        inten = intensities[line["id"]]
        if resp_tilt:
            inten *= 1.0 + resp_tilt * (line["wavelength_nm"] - 400.0) / 100.0
        a_ki = line["A_ki_s-1"] * ga_factor.get(sp, 1.0) * line_factor.get(line["id"], 1.0)
        y = boltzmann_ordinate(inten, line["g_k"], a_ki, line["wavelength_nm"], units)
        groups.setdefault(sp, []).append((line["E_k_eV"], y))
    fit = common_slope_fit(groups)
    slope = fit["slope"]
    if "temperature_factor" in ov:               # impose a relative error on T
        t_k = temperature_from_slope(slope) * ov["temperature_factor"]
        slope = -1.0 / (K_B_EV * t_k)
        intercepts = {}
        for sp, pts in groups.items():
            em = sum(p[0] for p in pts) / len(pts)
            ym = sum(p[1] for p in pts) / len(pts)
            intercepts[sp] = ym - slope * em
        # scatter about the imposed lines, with the degrees of freedom of the fit
        ss_res = sum((y - intercepts[sp] - slope * e) ** 2 for sp, pts in groups.items() for e, y in pts)
        residual_sd = math.sqrt(ss_res / (fit["n_lines"] - len(groups) - 1))
    else:
        t_k = temperature_from_slope(slope)
        intercepts = fit["intercepts"]
        residual_sd = fit["residual_sd"]

    # ---- A4: species densities, Saha completion, closure ----
    use_g0 = ov.get("partition_function", "U(T)") == "g0"
    rel_density: Dict[str, float] = {}
    for sp, q in intercepts.items():
        u = species[sp]["ground_level_g"] if use_g0 else species[sp]["partition_function"]
        u *= ov.get("u_factor", {}).get(sp, 1.0)
        rel_density[sp] = u * math.exp(q)

    totals: Dict[str, float] = {}
    saha: Dict[str, float] = {}
    for el, info in elements.items():
        sp_i, sp_ii = f"{el} I", f"{el} II"
        u_i = species[sp_i]["ground_level_g"] if use_g0 else species[sp_i]["partition_function"]
        u_ii = species[sp_ii]["ground_level_g"] if use_g0 else species[sp_ii]["partition_function"]
        u_i *= ov.get("u_factor", {}).get(sp_i, 1.0)
        u_ii *= ov.get("u_factor", {}).get(sp_ii, 1.0)
        s_ratio = saha_ratio(t_k, n_e, u_ii, u_i, info["ionization_energy_eV"])
        saha[el] = s_ratio
        has_i, has_ii = sp_i in rel_density, sp_ii in rel_density
        if has_i and has_ii:
            totals[el] = rel_density[sp_i] + rel_density[sp_ii]
        elif has_i:
            totals[el] = rel_density[sp_i] * (1.0 + s_ratio)
        elif has_ii:
            totals[el] = rel_density[sp_ii] * (1.0 + 1.0 / s_ratio)
        else:
            raise ValueError(f"element {el} has no observed lines")

    names = list(elements.keys())
    tot = sum(totals[n] for n in names)
    x = [totals[n] / tot for n in names]
    molar = [elements[n]["molar_mass_g_mol"] for n in names]
    if ov.get("skip_mass_conversion", False):
        w = list(x)                               # seeded defect: mole fractions reported as mass fractions
    else:
        w = mole_to_mass(x, molar)

    # ---- A3: consistency checks that the record allows ----
    saha_checks = {}
    for el in names:
        sp_i, sp_ii = f"{el} I", f"{el} II"
        if sp_i in rel_density and sp_ii in rel_density:
            observed_ratio = rel_density[sp_ii] / rel_density[sp_i]
            # N_e that would make the Saha ratio equal to the observed ratio
            saha_checks[el] = {"observed_ion_to_neutral": observed_ratio,
                               "saha_ion_to_neutral_at_stark_ne": saha[el],
                               "ne_from_saha_cm3": n_e * saha[el] / observed_ratio}
    mcw = mcwhirter_threshold(t_k, lte_gap_ev(record))

    return {"lorentz_fwhm_nm": l_stark, "n_e_cm3": n_e, "temperature_K": t_k,
            "slope_per_eV": slope, "slope_se_per_eV": fit["slope_se"],
            "residual_sd": residual_sd, "intercepts": intercepts,
            "relative_species_density": rel_density, "saha_ratio": saha,
            "elements": names, "mole_fraction": x, "mass_fraction": w,
            "saha_checks": saha_checks, "mcwhirter_threshold_cm3": mcw,
            "n_lines": fit["n_lines"]}
