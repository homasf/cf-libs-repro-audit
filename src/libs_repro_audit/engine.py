"""General-purpose audit engine for CF-LIBS/LIPS reproducibility records.

This module is paper-independent. It consumes an *audit record* — a JSON
document containing the values printed in a publication (see
``examples/template.json``) — and reruns the deterministic checks of the
five-checkpoint framework (A1–A5):

  A5  validation      signed relative deviation vs. the stated tolerance
  A1  linewidth       printed FWHM vs. printed Stark relation (Eq. 2)
  A1  instrument      conditional instrument-response scenarios
  A2  scale           which power-of-ten exponent reproduces the printed
                      concentration estimate (Eqs. 3–4)
  A4  invertibility   zero-slope / constant-mismatch audit of empirical
                      equations
  A3  qualitative     reported / not-reported flags for LTE, optical
                      thinness, self-absorption, atomic-data provenance

Every check returns a :class:`CheckResult` with an explicit status:

  PASS            the declared numerical comparison rule is met
  FAIL            the printed claim is NOT reproduced from the printed values
  NOT_INVERTIBLE  an equation required for inversion has zero slope
  NOT_REPORTED    the record marks a required diagnostic as absent
  REPORTED        the record marks a diagnostic as present (not verified)
  INFO            derived quantity, no claim attached

The engine never judges scientific validity, only whether the published
numerical chain can be reconstructed — a FAIL is a reproducibility finding,
not an accusation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .audit import (
    LinearEquation,
    effective_stark_width,
    instrumental_fwhm,
    quadrature_corrected_fwhm,
    signed_relative_deviation,
    stark_ne,
    finite_number,
    inverse_rounding_interval,
    voigt_lorentzian_fwhm,
)

PASS = "PASS"
FAIL = "FAIL"
NOT_INVERTIBLE = "NOT_INVERTIBLE"
NOT_REPORTED = "NOT_REPORTED"
REPORTED = "REPORTED"
INFO = "INFO"
NOT_ASSESSED = "NOT_ASSESSED"


@dataclass
class CheckResult:
    checkpoint: str          # "A1".."A5"
    name: str                # short identifier, e.g. "validation:Cd:Ne"
    status: str
    detail: str              # one-sentence human-readable finding
    values: dict = field(default_factory=dict)


@dataclass
class AuditReport:
    paper: dict
    results: list[CheckResult]
    verification: str = "Not recorded; source verification required"
    missing: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.results:
            out[r.status] = out.get(r.status, 0) + 1
        return out

    def failed(self) -> list[CheckResult]:
        return [r for r in self.results
                if r.status in (FAIL, NOT_INVERTIBLE, NOT_REPORTED, NOT_ASSESSED)]


# ----------------------------------------------------------------------
# record loading / minimal validation
# ----------------------------------------------------------------------

REQUIRED_TOP_KEYS = ("paper",)


def load_record(path: str | Path) -> dict:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in REQUIRED_TOP_KEYS:
        if key not in record:
            raise ValueError(f"audit record is missing required key '{key}'")
    return record


def _match_inverse(chk: dict, y: float, expected: float,
                   fallback_percent=None, y_scale=1.0):
    """Compare an inversion using explicit rounding or declared tolerances."""
    c = LinearEquation(chk['a'], chk['b']).invert(y)
    finite_number(expected, 'printed estimate')
    rounding = chk.get('rounding')
    if rounding is not None:
        lo, hi = inverse_rounding_interval(
            chk['a'], chk['b'], y, rounding.get('a_halfwidth', 0),
            rounding.get('b_halfwidth', 0),
            rounding.get('y_halfwidth', 0) * y_scale)
        h = rounding.get('estimate_halfwidth', 0)
        finite_number(h, 'estimate rounding half-width')
        if h < 0:
            raise ValueError('estimate rounding half-width must be non-negative')
        return c, lo <= expected+h and hi >= expected-h, {
            'rounding_interval': [lo, hi], 'comparison_basis': 'declared rounding intervals'}
    tol = chk.get('tolerance_percent', fallback_percent)
    atol = chk.get('tolerance_absolute')
    if tol is None and atol is None:
        return c, None, {'comparison_basis': 'no numerical tolerance supplied'}
    for v in (tol, atol):
        if v is not None:
            finite_number(v, 'comparison tolerance')
            if v < 0:
                raise ValueError('comparison tolerances must be non-negative')
    allowed = (atol or 0) + abs(expected) * (tol or 0) / 100
    return c, abs(c-expected) <= allowed, {
        'allowed_absolute_difference': allowed,
        'comparison_basis': chk.get('tolerance_basis', 'explicit numerical tolerance')}


# ----------------------------------------------------------------------
# A5 — validation agreement
# ----------------------------------------------------------------------

def check_validation(record: dict) -> list[CheckResult]:
    block = record.get("validation")
    if not block:
        return []
    tol = block.get("tolerance_percent")
    results = []
    for pt in block.get("points", []):
        tol = pt.get("tolerance_percent", block.get("tolerance_percent"))
        if tol is not None:
            finite_number(tol, 'validation tolerance')
            if tol < 0:
                raise ValueError('validation tolerance must be non-negative')
        delta = signed_relative_deviation(pt["method_value"],
                                          pt["reference_value"])
        name = f"validation:{pt.get('analyte', '?')}:{pt.get('label', '')}"
        values = {
            "method_value": pt["method_value"],
            "reference_value": pt["reference_value"],
            "delta_percent": delta,
            "tolerance_percent": tol,
            "units": pt.get("units", ""),
            "source": pt.get("source", block.get("source", "not supplied")),
            "tolerance_source": pt.get("tolerance_source", block.get("tolerance_source", "not supplied")),
        }
        if tol is None:
            results.append(CheckResult("A5", name, INFO,
                                       f"delta = {delta:+.2f}% "
                                       "(no stated tolerance to test)",
                                       values))
        elif abs(delta) <= tol:
            results.append(CheckResult(
                "A5", name, PASS,
                f"delta = {delta:+.2f}% lies within the stated "
                f"±{tol}% interval", values))
        else:
            results.append(CheckResult(
                "A5", name, FAIL,
                f"delta = {delta:+.2f}% lies OUTSIDE the stated "
                f"±{tol}% interval", values))
    return results


# ----------------------------------------------------------------------
# A1/A2 — Stark linewidth consistency
# ----------------------------------------------------------------------

def check_stark(record: dict,
                ratio_tolerance: float | None = None) -> list[CheckResult]:
    """Does Eq.-(2)-style substitution of the printed FWHM reproduce the
    printed/plotted electron density within an explicitly supplied tolerance?
    A missing tolerance yields INFO, never an automatic pass/fail.
    """
    results = []
    for chk in record.get("stark_checks", []):
        exponent = chk.get("exponent", 16)
        ne_calc = stark_ne(chk["fwhm_nm"], chk["w_s_nm"], exponent)
        ne_comp = chk["ne_comparison_mantissa"] * 10.0 ** exponent
        ratio = ne_calc / ne_comp
        tolerance = chk.get('ratio_tolerance', ratio_tolerance)
        if tolerance is not None:
            finite_number(tolerance, 'Stark ratio tolerance')
            if tolerance < 0:
                raise ValueError('Stark ratio tolerance must be non-negative')
        w_eff = effective_stark_width(chk["fwhm_nm"], ne_comp, exponent)
        name = f"stark:{chk.get('sample', chk.get('line', '?'))}"
        values = {
            "fwhm_nm": chk["fwhm_nm"],
            "w_s_nm": chk["w_s_nm"],
            "ne_calc": ne_calc,
            "ne_comparison": ne_comp,
            "ratio": ratio,
            "w_s_effective_nm": w_eff,
            "ratio_tolerance": tolerance,
            "tolerance_basis": chk.get('tolerance_basis', 'explicit tolerance' if tolerance is not None else 'not supplied'),
            "source": chk.get('source', 'not supplied'),
        }
        if tolerance is None:
            results.append(CheckResult('A1', name, INFO,
                f'calculated/comparison density ratio = {ratio:.4f}; no numerical tolerance supplied', values))
        elif abs(ratio - 1.0) <= tolerance:
            results.append(CheckResult(
                "A1", name, PASS,
                f"printed FWHM reproduces the comparison N_e "
                f"(ratio {ratio:.2f})", values))
        else:
            results.append(CheckResult(
                "A1", name, FAIL,
                f"printed FWHM gives {ratio:.2f}x the comparison N_e; "
                f"an effective W_s of {w_eff:.4f} nm would be required "
                f"instead of the printed {chk['w_s_nm']} nm", values))
    return results


def check_instrument_bound(record: dict) -> list[CheckResult]:
    instr = record.get("instrument")
    if not instr or not record.get("stark_checks"):
        return []
    w_inst = instrumental_fwhm(instr["diagnostic_wavelength_nm"],
                               instr["resolving_power"])
    results = [CheckResult(
        "A1", "instrument:width", INFO,
        f"Resolution width ~ {w_inst:.4f} nm at "
        f"R = {instr['resolving_power']}",
        {"instrumental_fwhm_nm": w_inst,
         "source": instr.get('source', 'not supplied'),
         "assumption": "lambda/R treated as a Gaussian FWHM for scenarios only"})]
    for chk in record.get("stark_checks", []):
        corrected = quadrature_corrected_fwhm(chk["fwhm_nm"], w_inst)
        change = (chk["fwhm_nm"] - corrected) / chk["fwhm_nm"] * 100
        lorentzian = voigt_lorentzian_fwhm(chk['fwhm_nm'], w_inst)
        voigt_change = (chk['fwhm_nm']-lorentzian)/chk['fwhm_nm']*100
        results.append(CheckResult(
            "A1", f"instrument:correction:{chk.get('sample', '?')}", INFO,
            f"quadrature instrumental correction changes the FWHM by "
            f"{change:.2f}%; the Voigt scenario changes it by {voigt_change:.2f}%. "
            "These assume different profile models; neither is a measured correction.",
            {"change_percent": change, "voigt_change_percent": voigt_change,
             "voigt_lorentzian_fwhm_nm": lorentzian}))
    return results


# ----------------------------------------------------------------------
# A2/A4 — power-of-ten scale check
# ----------------------------------------------------------------------

def check_scale(record: dict,
                match_tolerance_percent: float | None = None) -> list[CheckResult]:
    """For each candidate exponent, invert the printed linear equation and
    compare with the printed concentration estimate. Reports which exponent
    (if any) reproduces the printed value within ``match_tolerance_percent``.
    """
    results = []
    for chk in record.get("scale_checks", []):
        eq = LinearEquation(chk["a"], chk["b"])
        if not eq.invertible:
            results.append(CheckResult(
                "A2", f"scale:{chk.get('analyte', '?')}", NOT_INVERTIBLE,
                "scale check impossible: printed slope is zero", dict(chk)))
            continue
        base = chk.get("equation_exponent", 16)
        printed = chk["printed_estimate"]
        matches, per_exponent, comparison_details = [], {}, {}
        assessed = False
        for p in chk.get("candidate_exponents", [16, 17]):
            y = chk["ne_mantissa"] * 10.0 ** (p - base)
            c, match, comparison = _match_inverse(chk, y, printed,
                match_tolerance_percent, 10.0 ** (p-base))
            assessed = assessed or match is not None
            per_exponent[p] = c
            comparison_details[p] = comparison
            if match:
                matches.append(p)
        name = f"scale:{chk.get('analyte', '?')}"
        values = {"per_exponent_ppm": per_exponent,
                  "printed_estimate": printed, "matching_exponents": matches,
                  "comparison_details": comparison_details,
                  "source": chk.get('source', 'not supplied')}
        stated = chk.get("stated_exponent")
        if not assessed:
            results.append(CheckResult('A2', name, INFO,
                'candidate inversions computed; no rounding bounds or numerical tolerance supplied', values))
        elif not matches:
            results.append(CheckResult(
                "A2", name, FAIL,
                "no candidate exponent reproduces the printed estimate",
                values))
        elif stated is not None and stated not in matches:
            results.append(CheckResult(
                "A2", name, FAIL,
                f"exponent inferred from this comparison is 10^{matches[0]} "
                f"(gives {per_exponent[matches[0]]}), but the article "
                f"states 10^{stated}; this does not establish the physical density", values))
        elif len(matches) > 1:
            results.append(CheckResult('A2', name, INFO,
                f'multiple exponents {matches} are compatible with the supplied comparison rule', values))
        else:
            results.append(CheckResult(
                "A2", name, PASS,
                f"exponent 10^{matches[0]} reproduces the printed estimate "
                f"({per_exponent[matches[0]]} vs {printed})", values))
    return results


# ----------------------------------------------------------------------
# A4 — empirical-equation invertibility
# ----------------------------------------------------------------------

def check_equations(record: dict) -> list[CheckResult]:
    results = []
    for chk in record.get("equations", []):
        eq = LinearEquation(chk["a"], chk["b"])
        name = (f"equation:{chk.get('analyte', '?')}:"
                f"{chk.get('parameter', '?')}")
        values = dict(chk)
        if not eq.invertible:
            detail = ("printed slope is 0.0 — equation returns a constant "
                      "and cannot be inverted for concentration")
            op = chk.get("operative_value")
            if op is not None and op != chk["a"]:
                detail += (f"; moreover the constant {chk['a']} does not "
                           f"equal the operative test value {op}")
            results.append(CheckResult("A4", name, NOT_INVERTIBLE,
                                       detail, values))
            continue
        op = chk.get("operative_value")
        expected = chk.get("printed_estimate")
        if op is not None and expected is not None:
            c, match, comparison = _match_inverse(chk, op, expected)
            values['inverted_concentration'] = c
            values.update(comparison)
            if match is None:
                results.append(CheckResult('A4', name, INFO,
                    f'inversion gives {c:.4g}; no numerical comparison rule supplied', values))
            elif match:
                results.append(CheckResult(
                    "A4", name, PASS,
                    f"inversion gives {c:.5g}, compatible with the printed "
                    f"estimate {expected} by the declared comparison rule", values))
            else:
                results.append(CheckResult(
                    "A4", name, FAIL,
                    f"inversion gives {c:.2f}, which does not reproduce "
                    f"the printed estimate {expected}", values))
        else:
            results.append(CheckResult(
                "A4", name, INFO,
                "equation has non-zero slope and is invertible", values))
    return results


# ----------------------------------------------------------------------
# A3 — qualitative reporting flags
# ----------------------------------------------------------------------

QUALITATIVE_ITEMS = {
    "lte_check_reported": "explicit LTE check (e.g. McWhirter with inputs)",
    "optical_thinness_or_self_absorption_reported":
        "optical-thinness / self-absorption diagnostic for analytical lines",
    "atomic_data_provenance_reported":
        "atomic/broadening-data source, version and access date",
    "instrumental_width_reported":
        "numerical instrumental width / line-shape treatment",
    "full_precision_coefficients_available":
        "full-precision coefficients or machine-actionable record",
}


def check_qualitative(record: dict) -> list[CheckResult]:
    block = record.get("qualitative")
    if block is None:
        return []
    results = []
    for key, description in QUALITATIVE_ITEMS.items():
        if key not in block:
            continue
        if block[key] is not None and not isinstance(block[key], bool):
            raise ValueError(f'qualitative flag {key} must be true, false or null')
        if block[key] is None:
            results.append(CheckResult('A3', f'qualitative:{key}', NOT_ASSESSED,
                f'{description}: not assessed', {}))
            continue
        status = REPORTED if block[key] else NOT_REPORTED
        verb = "reported in the article" if block[key] else \
               "not fully specified in the supplied record"
        cp = {'instrumental_width_reported': 'A1',
              'atomic_data_provenance_reported': 'A2',
              'full_precision_coefficients_available': 'A4'}.get(key, 'A3')
        results.append(CheckResult(cp, f"qualitative:{key}", status,
            f"{description}: {verb}",
            {'source': record.get('qualitative_sources', {}).get(key, 'not supplied')}))
    return results


# ----------------------------------------------------------------------
# orchestration + rendering
# ----------------------------------------------------------------------

def run_audit(record: dict) -> AuditReport:
    if not isinstance(record, dict) or not isinstance(record.get('paper'), dict):
        raise ValueError('audit record must contain a paper object')
    results: list[CheckResult] = []
    results += check_validation(record)
    results += check_stark(record)
    results += check_instrument_bound(record)
    results += check_scale(record)
    results += check_equations(record)
    results += check_qualitative(record)
    covered = {r.checkpoint for r in results}
    for cp in ('A1', 'A2', 'A3', 'A4', 'A5'):
        if cp not in covered:
            results.append(CheckResult(cp, 'coverage:' + cp, NOT_ASSESSED,
                'No applicable input/check supplied; this is not a reproduced result.', {}))
    return AuditReport(paper=record.get("paper", {}), results=results,
        verification=record.get('verification', 'Not recorded; source verification required'),
        missing=record.get('missing', []), conflicts=record.get('conflicts', []))


def render_markdown(report: AuditReport) -> str:
    p = report.paper
    lines = [
        "# CF-LIBS/LIPS reproducibility-audit report",
        "",
        f"**Source verification:** {report.verification}",
        f"**Unresolved missing inputs:** {json.dumps(report.missing, ensure_ascii=False)}",
        f"**Recorded conflicts:** {json.dumps(report.conflicts, ensure_ascii=False)}",
        "",
        f"**Audited publication:** {p.get('title', '(untitled)')}",
        f"**DOI:** {p.get('doi', 'n/a')}  |  "
        f"**Record transcribed by:** {p.get('transcribed_by', 'n/a')} "
        f"on {p.get('transcription_date', 'n/a')}",
        "",
        "This report tests only whether the published numerical chain can "
        "be reconstructed from the printed values supplied in the audit "
        "record. It does not assess raw data, true concentrations or "
        "author intent, and a FAIL is a reproducibility finding, not an "
        "allegation.",
        "",
        "## Summary",
        "",
    ]
    counts = report.counts()
    for status in (PASS, FAIL, NOT_INVERTIBLE, NOT_REPORTED, NOT_ASSESSED, REPORTED, INFO):
        if status in counts:
            lines.append(f"- {status}: {counts[status]}")
    lines += ["", "## Findings", ""]
    lines.append("| Checkpoint | Check | Status | Detail |")
    lines.append("|---|---|---|---|")
    for r in report.results:
        lines.append(f"| {r.checkpoint} | `{r.name}` | **{r.status}** | "
                     f"{r.detail} |")
    lines += ['', '## Numerical values, sources and comparison rules', '']
    for r in report.results:
        lines += [f'### {r.name}', '```json',
                  json.dumps(r.values, ensure_ascii=False, indent=2), '```', '']
    lines += [
        "",
        "## Interpretation guide",
        "",
        "PASS: the declared numerical comparison rule is met; physical validity is not established. "
        "FAIL: it does not; possible explanations include typographical "
        "errors, rounding, unreported full-precision coefficients or an "
        "undocumented calculation pathway — any of which the authors could "
        "resolve by clarification. NOT_INVERTIBLE: a printed equation "
        "cannot be used as described. NOT_REPORTED: a minimum reporting "
        "item (Table 3 of the framework paper) is absent from the printed "
        "record.",
        "",
    ]
    return "\n".join(lines)
