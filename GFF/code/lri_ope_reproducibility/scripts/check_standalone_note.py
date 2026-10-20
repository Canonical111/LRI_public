#!/usr/bin/env python3
"""Compile only the OPE .tex in an otherwise empty temporary directory."""
from __future__ import annotations
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    if not shutil.which("latexmk"):
        raise SystemExit("Install latexmk and a TeX distribution; see README.md.")
    report = {"only_input": "note/lri_ope_note.tex", "external_bibliography": False,
              "figure_inputs": [], "compiled": False}
    try:
        with tempfile.TemporaryDirectory(prefix="lri_ope_standalone_") as td:
            w = Path(td)
            shutil.copy2(ROOT / "note/lri_ope_note.tex", w / "lri_ope_note.tex")
            cp = subprocess.run(
                ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
                 "-file-line-error", "lri_ope_note.tex"],
                cwd=w, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            if cp.returncode:
                raise RuntimeError(cp.stdout[-15000:])
            text = (w / "lri_ope_note.log").read_text(errors="replace")
            report.update(compiled=True,
                          unresolved_references="There were undefined references" in text,
                          overfull_boxes=[s for s in text.splitlines() if "Overfull" in s],
                          pdf_summary=next((s for s in text.splitlines()
                                            if s.startswith("Output written on")), ""))
            if report["unresolved_references"]:
                raise AssertionError("Undefined standalone references.")
            if report["overfull_boxes"]:
                raise AssertionError("Overfull boxes in standalone source.")
    finally:
        target = ROOT / "results/verification/standalone_latex.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: the source compiled with no external files and no overfull boxes.")

if __name__ == "__main__":
    main()
