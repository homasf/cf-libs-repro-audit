#!/usr/bin/env python3
"""Run every calculation of the supplementary package in the right order.

    python3 run_all.py               # calculations and checks (standard library only)
    python3 run_all.py --figures     # additionally redraw Figures 2-4 and S1
                                     # (needs NumPy and Matplotlib)
    python3 run_all.py --check-text  # additionally compare the numbers quoted in
                                     # the article and the supplement with the outputs

The run takes a few minutes; most of the time is spent in the Monte Carlo
propagations (200,000 draws for the record, 20,000 draws per scenario).

The constructed record in ../record/ is shipped with the package. It is
regenerated only on request (--regenerate-record), in which case the script
confirms that the regenerated files are identical to the shipped ones.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC = HERE.parent / "record"


def run(script: str, *args: str) -> int:
    print(f"\n=== {script} {' '.join(args)}".rstrip())
    return subprocess.call([sys.executable, str(HERE / script), *args], cwd=HERE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    status = 0
    if "--regenerate-record" in sys.argv:
        files = [REC / "record.json", REC / "line_intensities.csv"]
        before = [digest(f) for f in files]
        status |= run("make_record.py")
        after = [digest(f) for f in files]
        same = before == after
        print("Regenerated record identical to the shipped record:", "yes" if same else "NO")
        status |= 0 if same else 1
    status |= run("worked_examples.py")
    status |= run("reconstruct_record.py")
    status |= run("seeded_defects.py")
    status |= run("make_tables.py")
    if "--figures" in sys.argv:
        status |= run("make_figures.py")
    if "--check-text" in sys.argv:
        status |= run("check_manuscript.py")
    print("\nALL CHECKS PASSED" if status == 0 else "\nSOME CHECKS FAILED")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
