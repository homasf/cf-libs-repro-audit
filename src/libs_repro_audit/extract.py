"""AI-assisted extraction agent (``cf-libs-audit-extract``).

Drafts an audit record from a paper's text using a configured chat-completion
endpoint, under the strict extraction contract of AGENT_GUIDE.md. It never judges
reproducibility — it only transcribes printed values into the record
schema. Every draft it writes is stamped ``"verification": "DRAFT —
UNVERIFIED"``. ``cf-libs-audit`` warns about this stamp and still runs the
audit. A human must check each value against the PDF and replace the stamp
with their name and date before treating the record as verified.

Usage:
    # Set LIBS_AUDIT_API_URL, LIBS_AUDIT_MODEL and LIBS_AUDIT_API_KEY.
    # The URL must be the full chat-completion endpoint URL.
    pdftotext paper.pdf paper.txt          # or any text export
    cf-libs-audit-extract paper.txt -o draft_record.json
    #  -> verify every value against the PDF, fill 'verification'
    cf-libs-audit draft_record.json -o report.html

Uses the Python standard library only. No endpoint or model is selected by default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_VARS = ("LIBS_AUDIT_API_URL", "LIBS_AUDIT_MODEL", "LIBS_AUDIT_API_KEY")

EXTRACTION_SYSTEM = """\
You are assisting with a reproducibility audit of a CF-LIBS/LIPS
publication. Fill the JSON template using ONLY values printed in the paper
text supplied by the user (tables, equations, figure axis labels,
accompanying text). Rules:
1. Never estimate, interpolate, round differently, or fill gaps from
   background knowledge. If a value is not printed, omit the field and list
   it under a top-level "missing" array instead.
2. For every block, fill the "source" field with the exact table, equation
   or section where the value appears.
3. Transcribe coefficients at full printed precision, including zero slopes
   (write 0.0, do not "fix" them).
4. If the paper states the same quantity with different exponents or units
   in different places, record each variant in a top-level "conflicts" array
   with locations; do not resolve the conflict.
5. For the "qualitative" block, set a flag true only if the diagnostic is
   explicitly reported with numerical inputs, not merely mentioned.
6. Respond with ONLY the completed JSON object — no preamble, no markdown
   fences."""


def _template() -> str:
    source_tree = (Path(__file__).resolve().parents[2] / "examples"
                   / "template.json")
    path = source_tree if source_tree.exists() else \
        Path(__file__).resolve().with_name("template.json")
    return path.read_text(encoding="utf-8")


class _ResponseError(ValueError):
    """A response that cannot supply text, with its body for inspection."""

    def __init__(self, raw: str) -> None:
        super().__init__("the endpoint returned an invalid chat-completion response")
        self.raw = raw


def _call_api(api_url: str, model: str, api_key: str, paper_text: str) -> str:
    payload = {
        "model": model,
        "max_tokens": 4000,
        "messages": [{"role": "system", "content": EXTRACTION_SYSTEM}, {
            "role": "user",
            "content": (
                "TEMPLATE:\n" + _template() +
                "\n\nPAPER TEXT:\n" + paper_text
            ),
        }],
    }
    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "authorization": "Bearer " + api_key,
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise _ResponseError(raw) from None
    if not isinstance(content, str):
        raise _ResponseError(raw)
    return content


def _save_raw(output: str, raw: str) -> None:
    try:
        Path(output + ".raw.txt").write_text(raw, encoding="utf-8")
    except OSError:
        print("error: the raw output could not be saved for inspection.",
              file=sys.stderr)
    else:
        print(f"raw output saved to {output}.raw.txt for inspection.",
              file=sys.stderr)


def _reject_constant(value: str) -> None:
    raise ValueError("nonstandard JSON constant")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="cf-libs-audit-extract",
        description="Draft an audit record from paper text with an LLM. "
                    "The draft is UNVERIFIED until a human checks every "
                    "value against the PDF (see AGENT_GUIDE.md).",
        epilog="Required environment variables: LIBS_AUDIT_API_URL "
               "(full chat-completion endpoint), LIBS_AUDIT_MODEL and "
               "LIBS_AUDIT_API_KEY. No endpoint or model defaults are provided.")
    ap.add_argument("paper_text", help="plain-text export of the paper "
                                       "(e.g. from pdftotext)")
    ap.add_argument("-o", "--output", default="draft_record.json")
    args = ap.parse_args(argv)

    config = {name: os.environ.get(name, "").strip() for name in CONFIG_VARS}
    missing = [name for name in CONFIG_VARS if not config[name]]
    if missing:
        print("error: set the required environment variables: "
              + ", ".join(missing) + ". The API key is read from the "
              "environment and is not stored in the draft.",
              file=sys.stderr)
        return 2

    try:
        text = Path(args.paper_text).read_text(encoding="utf-8", errors="replace")
    except OSError:
        print("error: could not read the paper text file.", file=sys.stderr)
        return 1
    print(f"extracting printed values from {args.paper_text} "
          f"({len(text)} chars) using the configured model ...")
    try:
        raw = _call_api(config["LIBS_AUDIT_API_URL"], config["LIBS_AUDIT_MODEL"],
                        config["LIBS_AUDIT_API_KEY"], text)
    except _ResponseError as exc:
        print("error: the endpoint returned an invalid chat-completion "
              "response; expected choices[0].message.content as text.",
              file=sys.stderr)
        _save_raw(args.output, exc.raw)
        return 1
    except (urllib.error.URLError, OSError, ValueError):
        print("error: the extraction request failed. Check the configured "
              "endpoint, model, credentials and connection.", file=sys.stderr)
        return 1
    stripped = raw.strip()
    fence = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped,
                         flags=re.IGNORECASE)
    content = fence.group(1).strip() if fence else stripped

    try:
        record = json.loads(content, parse_constant=_reject_constant)
    except ValueError:
        print("error: model output was not valid JSON.", file=sys.stderr)
        _save_raw(args.output, raw)
        return 1
    if not isinstance(record, dict):
        print("error: model output must be a JSON object.", file=sys.stderr)
        _save_raw(args.output, raw)
        return 1

    record["verification"] = (
        "DRAFT — UNVERIFIED: a human must check every value against the "
        "PDF, then replace this field with 'verified by <name>, <date>'."
    )
    try:
        Path(args.output).write_text(json.dumps(record, indent=2, allow_nan=False),
                                     encoding="utf-8")
    except ValueError:
        print("error: model output contains a nonfinite JSON number.",
              file=sys.stderr)
        _save_raw(args.output, raw)
        return 1
    except OSError:
        print("error: could not write the draft record.", file=sys.stderr)
        return 1
    print(f"draft written to {args.output}")
    print("NEXT STEP (required): verify every value against the paper — "
          "see the checklist in AGENT_GUIDE.md — before running "
          f"'cf-libs-audit {args.output}'.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
