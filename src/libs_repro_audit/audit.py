"""Core numerical functions for the CF-LIBS/LIPS reproducibility audit.

Each function implements one deterministic check from the five-checkpoint
framework (A1-A5) described in:

    Homa Saeidfirozeh et al.,
    "Can a published CF-LIBS quantification be reconstructed? A
    reproducibility-audit framework and reporting checklist."

All equation numbers below refer to that article. The functions operate
only on printed values; no raw spectra are required.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Optional

KB_EV_K = 8.617333262145e-5


def finite_number(value: float, name: str) -> float:
    """Reject booleans, nonnumeric values, NaN and infinities."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------

def load_printed_values(path: Optional[str] = None) -> dict:
    """Load the machine-actionable record of printed input values.

    Parameters
    ----------
    path:
        Optional explicit path to a JSON record. When omitted, the
        packaged ``data/printed_values.json`` shipped with the repository
        is used.
    """
    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    # repository layout: <root>/data/printed_values.json
    root = Path(__file__).resolve().parents[2]
    candidate = root / "data" / "printed_values.json"
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    # installed-package fallback
    with resources.files("libs_repro_audit").joinpath("printed_values.json").open(
        "r", encoding="utf-8"
    ) as fh:  # pragma: no cover
        return json.load(fh)


# ----------------------------------------------------------------------
# A5 - validation: signed relative deviation, Eq. (1)
# ----------------------------------------------------------------------

def signed_relative_deviation(c_lips: float, c_icp: float) -> float:
    """Signed relative deviation delta in percent, Eq. (1).

    delta = (C_LIPS - C_ICP) / C_ICP * 100

    A single-point delta contributes to an assessment of observed
    agreement/trueness; it is not by itself a complete estimate of
    method bias.
    """
    finite_number(c_lips, "method value")
    finite_number(c_icp, "reference value")
    if c_icp == 0:
        raise ZeroDivisionError("ICP-OES comparison value must be non-zero")
    return (c_lips - c_icp) / c_icp * 100.0


# ----------------------------------------------------------------------
# A1/A2 - Stark broadening, Eq. (2)
# ----------------------------------------------------------------------

def stark_ne(fwhm_nm: float, w_s_nm: float, exponent: int = 16) -> float:
    """Electron density from the printed Stark relation, Eq. (2).

    N_e ~ (delta_lambda_FWHM / (2 * W_s)) * 10**exponent   [cm^-3]

    Both widths in nm. The exponent is the normalization used in the
    quoted relationship (16 in the case-study article).
    """
    finite_number(fwhm_nm, "FWHM")
    finite_number(w_s_nm, "Stark half-width")
    finite_number(exponent, "reference-density exponent")
    if fwhm_nm < 0:
        raise ValueError("FWHM must be non-negative")
    if w_s_nm <= 0:
        raise ValueError("Stark width parameter W_s must be positive")
    return fwhm_nm / (2.0 * w_s_nm) * 10.0**exponent


def effective_stark_width(fwhm_nm: float, ne_comparison: float,
                          exponent: int = 16) -> float:
    """W_s that would be required for Eq. (2) to reproduce ne_comparison.

    W_s_eff = fwhm / (2 * N_e_comp / 10**exponent)
    """
    finite_number(fwhm_nm, "FWHM")
    finite_number(ne_comparison, "comparison electron density")
    if fwhm_nm < 0:
        raise ValueError("FWHM must be non-negative")
    ne_norm = ne_comparison / 10.0**exponent
    if ne_norm <= 0:
        raise ValueError("comparison electron density must be positive")
    return fwhm_nm / (2.0 * ne_norm)


def instrumental_fwhm(wavelength_nm: float, resolving_power: float) -> float:
    """Resolution width lambda/R (nm); R alone does not specify line shape."""
    finite_number(wavelength_nm, "wavelength")
    finite_number(resolving_power, "resolving power")
    if wavelength_nm <= 0:
        raise ValueError("wavelength must be positive")
    if resolving_power <= 0:
        raise ValueError("resolving power must be positive")
    return wavelength_nm / resolving_power


def quadrature_corrected_fwhm(observed_fwhm_nm: float,
                              instrumental_fwhm_nm: float) -> float:
    """Observed FWHM corrected by Gaussian quadrature subtraction (nm).

    Valid only for Gaussian-on-Gaussian convolution. This is NOT an
    upper bound on the correction of a Lorentzian/Voigt profile.
    """
    finite_number(observed_fwhm_nm, "observed FWHM")
    finite_number(instrumental_fwhm_nm, "instrumental FWHM")
    if observed_fwhm_nm <= 0 or instrumental_fwhm_nm < 0:
        raise ValueError("observed width must be positive; instrument width non-negative")
    if instrumental_fwhm_nm >= observed_fwhm_nm:
        raise ValueError("instrumental width exceeds observed width")
    return math.sqrt(observed_fwhm_nm**2 - instrumental_fwhm_nm**2)


# ----------------------------------------------------------------------
# A4 - empirical equations: inversion, invertibility, scale check
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class LinearEquation:
    """A printed empirical relation  y = a + b*C  (C in ppm).

    For N_e relations, y is the normalized density N_e / 10^16 cm^-3.
    For T_e relations, y is the temperature in K.
    """
    a: float
    b: float

    def __post_init__(self) -> None:
        finite_number(self.a, "intercept")
        finite_number(self.b, "slope")

    @property
    def invertible(self) -> bool:
        """A zero printed slope makes the equation non-invertible."""
        return self.b != 0.0

    def invert(self, y: float) -> float:
        """Concentration C = (y - a) / b. Raises if the slope is zero."""
        finite_number(y, "dependent value")
        if not self.invertible:
            raise ZeroDivisionError(
                "printed slope is 0.0: equation returns a constant plasma "
                "parameter and cannot be inverted for concentration"
            )
        return (y - self.a) / self.b


def ne_scale_check(eq: LinearEquation, ne_value: float,
                   exponents: tuple[int, ...] = (16, 17)) -> dict[int, float]:
    """Concentration implied by each candidate electron-density exponent.

    ``ne_value`` is the mantissa (e.g. 1.54382). For each exponent p the
    normalized input to the printed relation (which carries its own
    1e16 normalization) is ne_value * 10**(p - 16).
    Returns {exponent: concentration_ppm}.
    """
    out: dict[int, float] = {}
    for p in exponents:
        y = ne_value * 10.0 ** (p - 16)
        out[p] = eq.invert(y)
    return out


def voigt_lorentzian_fwhm(observed: float, gaussian: float) -> float:
    """Invert Olivero--Longbothum (1977), in consistent width units.

    Assumes an actual Voigt FWHM, Gaussian response and Lorentzian
    remainder. A width from a different fitted profile is only a scenario.
    Uses a rationalized root to avoid cancellation near the resolution limit.
    """
    finite_number(observed, "observed width")
    finite_number(gaussian, "Gaussian width")
    if observed <= 0 or gaussian < 0 or gaussian > observed:
        raise ValueError("require 0 <= Gaussian width <= positive observed width")
    a, b = 0.5346, 0.2166
    d = observed * observed - gaussian * gaussian
    return 2 * d / (2 * a * observed + math.sqrt(
        (2 * a * observed)**2 - 4 * (a*a - b) * d))


def mcwhirter_threshold(temperature: float, delta_e_ev: float,
                       temperature_unit: str = "K") -> float:
    """Necessary collisional-equilibrium estimate, not an LTE verdict.

    temperature_unit='eV' means k_B*T in eV, converted to kelvin first.
    The relevant energy gap and applicability require expert assessment.
    """
    finite_number(temperature, "temperature")
    finite_number(delta_e_ev, "energy gap")
    if temperature <= 0 or delta_e_ev <= 0:
        raise ValueError("temperature and energy gap must be positive")
    if temperature_unit not in ("K", "eV"):
        raise ValueError("temperature_unit must be K or eV")
    t_k = temperature if temperature_unit == "K" else temperature / KB_EV_K
    return 1.6e12 * math.sqrt(t_k) * delta_e_ev**3


def convert_composition(fractions: list[float], molar_masses: list[float],
                        from_basis: str) -> list[float]:
    """Convert a complete mass/mole composition; returns fractions summing to 1.

    Input may use percent or fractional units. Missing matrix species are
    never inferred: a partial composition yields only subset normalization.
    """
    if not fractions or len(fractions) != len(molar_masses):
        raise ValueError("nonempty compositions and masses must have equal lengths")
    if from_basis not in ("mass", "mole"):
        raise ValueError("from_basis must be mass or mole")
    for f, m in zip(fractions, molar_masses):
        finite_number(f, "fraction")
        finite_number(m, "molar mass")
        if f < 0 or m <= 0:
            raise ValueError("fractions must be non-negative and molar masses positive")
    terms = [f/m if from_basis == "mass" else f*m
             for f, m in zip(fractions, molar_masses)]
    total = math.fsum(terms)
    if total <= 0:
        raise ValueError("composition must have a positive total")
    return [t/total for t in terms]


def inverse_rounding_interval(a: float, b: float, y: float,
                              a_halfwidth: float = 0, b_halfwidth: float = 0,
                              y_halfwidth: float = 0) -> tuple[float, float]:
    """Endpoint envelope for C=(y-a)/b under declared rounding intervals.

    These are numerical rounding bounds, not experimental uncertainties.
    A slope interval containing zero has no finite inverse envelope.
    """
    LinearEquation(a, b)
    finite_number(y, "dependent value")
    for value in (a_halfwidth, b_halfwidth, y_halfwidth):
        finite_number(value, "rounding half-width")
        if value < 0:
            raise ValueError("rounding half-widths must be non-negative")
    if b-b_halfwidth <= 0 <= b+b_halfwidth:
        raise ValueError("rounding interval for slope contains zero")
    candidates = [(yy-aa)/bb
                  for yy in (y-y_halfwidth, y+y_halfwidth)
                  for aa in (a-a_halfwidth, a+a_halfwidth)
                  for bb in (b-b_halfwidth, b+b_halfwidth)]
    return min(candidates), max(candidates)
