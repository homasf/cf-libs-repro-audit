"""Self-contained HTML report renderer.

Produces a single-file, offline, print-friendly audit report. No external
fonts, scripts or images: everything is embedded so the file can accompany
a manuscript submission or referee report unchanged.

Design notes: the header carries an emission-spectrum strip whose accent
is the ~646 nm red of the Ca I diagnostic line used in the worked example;
statuses are encoded in that spectral palette (red = FAIL, green = PASS,
amber = NOT REPORTED). Headings use a journal-style serif stack, data uses
a monospaced stack — both system fonts, so rendering is identical offline.
"""

from __future__ import annotations

import html
import json
from datetime import date

from .engine import (FAIL, INFO, NOT_INVERTIBLE, NOT_REPORTED, PASS,
                     REPORTED, NOT_ASSESSED, AuditReport)

CHECKPOINT_TITLES = {
    "A1": "A1 · Linewidth provenance",
    "A2": "A2 · Plasma-parameter consistency",
    "A3": "A3 · Plasma-model assessment",
    "A4": "A4 · Concentration inversion",
    "A5": "A5 · Validation",
}

STATUS_LABELS = {
    PASS: "PASS",
    FAIL: "FAIL",
    NOT_INVERTIBLE: "NOT INVERTIBLE",
    NOT_REPORTED: "NOT REPORTED",
    REPORTED: "REPORTED",
    INFO: "INFO",
    NOT_ASSESSED: "NOT ASSESSED",
}

_CSS = """
:root {
  --ink: #1c2732; --muted: #5d6b77; --rule: #d8dee3;
  --paper: #f6f8f9; --card: #ffffff;
  --fail: #c0392b; --fail-bg: #faece9;
  --pass: #1e7a4e; --pass-bg: #e9f5ee;
  --warn: #a06a00; --warn-bg: #faf3e2;
  --info: #4a5a68; --info-bg: #eef1f4;
  --serif: Charter, "Bitstream Charter", "Sitka Text", Cambria, Georgia, serif;
  --sans: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", "Cascadia Code", Consolas, "DejaVu Sans Mono", monospace;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink);
       font: 15px/1.55 var(--sans); }
.page { max-width: 900px; margin: 0 auto; padding: 0 28px 64px; }

/* signature: emission-spectrum strip */
.spectrum { height: 10px; background: #10151a; position: relative;
            overflow: hidden; }
.spectrum span { position: absolute; top: 0; bottom: 0; width: 2px; }

header.doc { padding: 34px 0 22px; border-bottom: 2px solid var(--ink); }
.eyebrow { font: 600 11px/1 var(--sans); letter-spacing: .18em;
           text-transform: uppercase; color: var(--muted); }
h1 { font: 700 30px/1.2 var(--serif); margin: 10px 0 4px; }
.subtitle { font: 400 15px/1.5 var(--serif); font-style: italic;
            color: var(--muted); margin: 0; }

.meta { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 40px;
        margin: 20px 0 0; padding: 16px 0 0; border-top: 1px solid var(--rule);
        font-size: 13.5px; }
.meta div { display: flex; gap: 10px; }
.meta dt { color: var(--muted); min-width: 118px; margin: 0; }
.meta dd { margin: 0; font-weight: 500; }

.scope { margin: 22px 0 0; padding: 14px 18px; background: var(--card);
         border: 1px solid var(--rule); border-left: 4px solid var(--ink);
         font-size: 13.5px; color: var(--muted); }

.summary { display: flex; flex-wrap: wrap; gap: 12px; margin: 26px 0 8px; }
.stat { flex: 1 1 120px; background: var(--card); border: 1px solid var(--rule);
        border-radius: 6px; padding: 12px 14px; }
.stat b { display: block; font: 600 26px/1.1 var(--serif); }
.stat span { font: 600 10.5px/1.3 var(--sans); letter-spacing: .12em;
             text-transform: uppercase; color: var(--muted); }
.stat.fail b { color: var(--fail); } .stat.pass b { color: var(--pass); }
.stat.warn b { color: var(--warn); } .stat.info b { color: var(--info); }

h2.cp { font: 700 19px/1.3 var(--serif); margin: 34px 0 2px; }
p.cp-q { margin: 0 0 12px; font-size: 13px; color: var(--muted); }

table { width: 100%; border-collapse: collapse; background: var(--card);
        border: 1px solid var(--rule); border-radius: 6px; overflow: hidden;
        font-size: 13.5px; }
th { text-align: left; font: 600 10.5px/1.3 var(--sans);
     letter-spacing: .12em; text-transform: uppercase; color: var(--muted);
     padding: 9px 14px; border-bottom: 1px solid var(--rule);
     background: #fbfcfd; }
td { padding: 10px 14px; border-bottom: 1px solid #edf0f2;
     vertical-align: top; }
tr:last-child td { border-bottom: 0; }
td.check { font-family: var(--mono); font-size: 12.5px; white-space: nowrap; }
td.status { white-space: nowrap; width: 1%; }

.pill { display: inline-block; font: 700 10.5px/1 var(--sans);
        letter-spacing: .08em; padding: 5px 9px; border-radius: 999px; }
.pill.PASS { color: var(--pass); background: var(--pass-bg); }
.pill.FAIL { color: var(--fail); background: var(--fail-bg); }
.pill.NOT_INVERTIBLE { color: var(--fail); background: var(--fail-bg); }
.pill.NOT_REPORTED { color: var(--warn); background: var(--warn-bg); }
.pill.REPORTED { color: var(--pass); background: var(--pass-bg); }
.pill.INFO { color: var(--info); background: var(--info-bg); }

.interp { margin-top: 36px; padding-top: 18px; border-top: 2px solid var(--ink); }
.interp h2 { font: 700 17px/1.3 var(--serif); margin: 0 0 8px; }
.interp p, footer p { font-size: 13px; color: var(--muted); }
footer { margin-top: 26px; font-size: 12.5px; color: var(--muted); }
footer code { font-family: var(--mono); background: var(--info-bg);
              padding: 1px 6px; border-radius: 4px; }

@media (max-width: 620px) { .meta { grid-template-columns: 1fr; } }
@media print {
  body { background: #fff; } .page { padding: 0 6px; max-width: none; }
  .stat, table, .scope { border-color: #bbb; }
  a { color: inherit; text-decoration: none; }
}
"""

# spectral strip: (position %, width px, color) — red group near the Ca I
# 646 nm diagnostic line, echoed across the visible range.
_LINES = [
    (4, "#7b6bd6"), (9, "#6d7fe0"), (13, "#5a9be0"), (21, "#4fb8c9"),
    (27, "#4cc79a"), (33, "#66c96a"), (41, "#9ecb4f"), (48, "#d3c545"),
    (55, "#dfae3e"), (61, "#e0913a"), (68, "#dd7434"), (74, "#d65c30"),
    (80, "#cd4a2c"), (84, "#c0392b"), (86, "#c0392b"), (91, "#a92f24"),
    (96, "#8f261d"),
]

_CP_QUESTIONS = {
    "A1": "Can the linewidth actually entered into the Stark calculation be reconstructed from the printed record?",
    "A2": "Do the printed units, exponents and inputs reproduce the plasma parameters carried into later calculations?",
    "A3": "Are the necessary LTE, optical-thinness and self-absorption diagnostics reported?",
    "A4": "Are the concentration equations supplied with sufficient precision, non-zero slopes and a valid domain?",
    "A5": "Does the stated validation agreement follow from the printed central values?",
}


def _esc(x) -> str:
    return html.escape(str(x))


def render_html(report: AuditReport) -> str:
    p = report.paper
    counts = report.counts()
    n_fail = counts.get(FAIL, 0) + counts.get(NOT_INVERTIBLE, 0)
    n_missing = counts.get(NOT_REPORTED, 0)

    spectrum = "".join(
        f'<span style="left:{pos}%;background:{c};'
        f'box-shadow:0 0 6px {c}"></span>'
        for pos, c in _LINES
    )

    meta_rows = ""
    for label, key in (("Audited publication", "title"),
                       ("Authors", "authors"), ("Journal", "journal"),
                       ("DOI", "doi"), ("Record transcribed by", "transcribed_by"),
                       ("Transcription date", "transcription_date")):
        if p.get(key):
            meta_rows += (f"<div><dt>{_esc(label)}</dt>"
                          f"<dd>{_esc(p[key])}</dd></div>")

    stats = f"""
      <div class="stat pass"><b>{counts.get(PASS, 0)}</b><span>reproduced</span></div>
      <div class="stat fail"><b>{n_fail}</b><span>not reproduced</span></div>
      <div class="stat warn"><b>{n_missing}</b><span>not reported</span></div>
      <div class="stat info"><b>{len(report.results)}</b><span>checks run</span></div>
    """

    sections = ""
    for cp in ("A5", "A1", "A2", "A3", "A4"):
        rows = [r for r in report.results if r.checkpoint == cp]
        if not rows:
            continue
        body = "".join(
            f'<tr><td class="check">{_esc(r.name)}</td>'
            f'<td class="status"><span class="pill {r.status}">'
            f'{STATUS_LABELS[r.status]}</span></td>'
            f'<td>{_esc(r.detail)}</td></tr>'
            for r in rows
        )
        sections += (
            f'<h2 class="cp">{_esc(CHECKPOINT_TITLES[cp])}</h2>'
            f'<p class="cp-q">{_esc(_CP_QUESTIONS[cp])}</p>'
            f'<table><thead><tr><th>Check</th><th>Status</th>'
            f'<th>Finding</th></tr></thead><tbody>{body}</tbody></table>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reproducibility-audit report — {_esc(p.get('title', 'CF-LIBS/LIPS'))}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="spectrum">{spectrum}</div>
<div class="page">
<header class="doc">
  <div class="eyebrow">CF-LIBS/LIPS reproducibility audit · checkpoints A1–A5</div>
  <h1>Reproducibility-audit report</h1>
  <p class="subtitle">Deterministic recalculation of the published numerical
  chain from printed values</p>
  <dl class="meta">{meta_rows}
    <div><dt>Report generated</dt><dd>{date.today().isoformat()} ·
    CF-LIBS Reproducibility Audit</dd></div>
  </dl>
</header>

<div class="scope"><strong>Scope.</strong> This report tests only whether the
published numerical chain can be reconstructed from the printed values in the
audit record. It does not assess raw spectra, true sample concentrations or
author intent. A FAIL is a reproducibility finding — typographical errors,
rounding or unreported full-precision coefficients can cause one, and any can
be resolved by author clarification.</div>

<div class="summary">{stats}</div>
<div class="scope"><strong>Source verification:</strong> {_esc(report.verification)}<br>
<strong>Missing inputs:</strong> {_esc(report.missing)}<br>
<strong>Recorded conflicts:</strong> {_esc(report.conflicts)}</div>

{sections}
<details><summary>Numerical values, sources and comparison rules</summary>
<pre>{_esc(json.dumps([{'checkpoint': r.checkpoint, 'name': r.name,
    'status': r.status, 'values': r.values} for r in report.results], ensure_ascii=False, indent=2))}</pre></details>

<div class="interp">
<h2>Interpretation</h2>
<p><strong>PASS</strong> — the printed claim follows from the printed values.
<strong>FAIL</strong> — it does not, from the values as printed.
<strong>NOT INVERTIBLE</strong> — a printed equation cannot be used as
described (e.g. zero slope). <strong>NOT REPORTED</strong> — a
minimum-reporting item (Table 3 of the framework article) is absent from the
printed record; absence is a completeness finding, not evidence the
underlying physics is wrong.</p>
</div>

<footer>
<p>Generated by <strong>CF-LIBS Reproducibility Audit</strong>, the
machine-actionable record accompanying Saeidfirozeh et al.,
<em>Can a published CF-LIBS quantification be reconstructed? A
reproducibility-audit framework and reporting checklist</em>. Anyone can
regenerate this report from the same audit record:
<code>cf-libs-audit record.json -o report.html</code></p>
</footer>
</div>
</body>
</html>
"""
