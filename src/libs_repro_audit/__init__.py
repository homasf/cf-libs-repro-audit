"""Selected printed-value CF-LIBS operations; not a full spectral pipeline."""

from .htmlreport import render_html
from .engine import AuditReport, CheckResult, load_record, render_markdown, run_audit
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

__all__ = [
    "LinearEquation",
    "effective_stark_width",
    "instrumental_fwhm",
    "load_printed_values",
    "ne_scale_check",
    "quadrature_corrected_fwhm",
    "signed_relative_deviation",
    "stark_ne",
    "AuditReport",
    "CheckResult",
    "load_record",
    "render_markdown",
    "run_audit",
    "render_html",
]

__version__ = "2.0.1.dev0"

