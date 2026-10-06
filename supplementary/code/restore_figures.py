#!/usr/bin/env python3
"""Restore the fixed manuscript figure assets and verify their SHA256 hashes.

These figures are supplied raster artwork in PDF wrappers. This script copies
the exact packaged files; it does not calculate or draw new artwork. Numerical
calculations and optional diagnostic plots are separate operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "figure_assets"
DESTINATION = HERE.parent / "figures"
EXPECTED_NAMES = {
    "fig1_chain.pdf", "fig2_linewidth.pdf", "fig3_basis.pdf",
    "fig4_sensitivity.pdf", "figS1_boltzmann.pdf",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset_checks(assets: Path) -> tuple[list, list]:
    """Verify file integrity; these checks do not assess figure meaning."""
    manifest = json.loads((assets / "figure_manifest.json").read_text(encoding="utf-8"))
    entries = manifest["figures"]
    if {entry["pdf_file"] for entry in entries} != EXPECTED_NAMES or len(entries) != 5:
        raise ValueError("The figure manifest must identify the five manuscript figures.")
    checks = []
    for entry in entries:
        if entry["png_file"] != Path(entry["pdf_file"]).with_suffix(".png").name:
            raise ValueError("The figure manifest must pair each PDF with its PNG.")
        for filename_key, hash_key in (("pdf_file", "pdf_sha256"),
                                        ("png_file", "png_sha256")):
            filename = entry[filename_key]
            if Path(filename).name != filename:
                raise ValueError("The manifest contains an invalid asset filename.")
            if not re.fullmatch(r"[0-9a-f]{64}", entry[hash_key]):
                raise ValueError(f"Invalid SHA256 in the figure manifest: {filename}")
            path = assets / filename
            checks.append((path.is_file() and digest(path) == entry[hash_key],
                           f"packaged asset SHA256: {filename}"))
    return entries, checks


def verify(assets: Path = ASSETS, destination: Path = DESTINATION,
           log_path: Path | None = None) -> int:
    """Check ten supplied assets and five restored PDF copies without writing figures."""
    entries, checks = asset_checks(assets)
    for entry in entries:
        path = destination / entry["pdf_file"]
        checks.append((path.is_file() and digest(path) == entry["pdf_sha256"],
                       f"restored PDF SHA256: {entry['pdf_file']}"))
    n_asset = sum(ok for ok, _ in checks[:10])
    n_copy = sum(ok for ok, _ in checks[10:])
    text = (f"{n_asset} of 10 packaged figure asset checks passed.\n"
            f"{n_copy} of 5 restored figure PDF checks passed.\n\n"
            "Scope: file integrity and identity of fixed supplied artwork.\n"
            "These checks do not assess the analytical content of a drawing.\n\n")
    text += "\n".join(("PASS" if ok else "FAIL") + ": " + name
                      for ok, name in checks) + "\n"
    if log_path is not None:
        log_path.write_text(text, encoding="utf-8")
    print(text)
    return 0 if all(ok for ok, _ in checks) else 1


def restore(assets: Path, destination: Path) -> int:
    # Check all inputs before writing any output.
    entries, checks = asset_checks(assets)
    failures = [name for ok, name in checks if not ok]
    if failures:
        raise ValueError("Figure asset checksum mismatch or missing file: "
                         + "; ".join(failures))
    destination.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        source = assets / entry["pdf_file"]
        target = destination / entry["pdf_file"]
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        if digest(target) != entry["pdf_sha256"]:
            raise ValueError(f"Restored figure checksum mismatch: {target.name}")
        print(f"Restored fixed figure: {target.name}")
    print("All five manuscript figure PDFs match the packaged SHA256 hashes.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ASSETS,
                        help="Directory containing fixed PDF and PNG figure assets.")
    parser.add_argument("--destination", type=Path, default=DESTINATION,
                        help="Directory receiving the fixed manuscript figure PDFs.")
    parser.add_argument("--check-assets", action="store_true",
                        help="Check all fixed assets and restored PDF copies without copying files.")
    args = parser.parse_args()
    if args.check_assets:
        return verify(args.assets, args.destination)
    return restore(args.assets, args.destination)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: cannot verify or restore figure assets: {error}")
        raise SystemExit(1)
