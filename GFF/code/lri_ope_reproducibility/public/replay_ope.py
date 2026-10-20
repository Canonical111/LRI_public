#!/usr/bin/env python3
"""Public test and replay for GFF/code/lri_ope_reproducibility (Part V of the GFF note).

Usage, from GFF/code/lri_ope_reproducibility/ (public.mk calls these):
  python3 -I public/replay_ope.py test   --work .work
  python3 -I public/replay_ope.py replay --work .work --checks ../ope_checks

test    verifies MANIFEST.sha256 (every shipped listed file byte-identical; absent only the DROPPED files below), runs
        the package's own "quick" task into WORK/quick, and verifies the manifest again, so that no shipped file was
        written.
replay  runs "quick" if WORK/quick is missing, then the checks of Section 34 ("Checks made for this note"): every
        folder ope_checks/<name>/ with a commands.json is run. commands.json is a list of
        {"script": <file in that folder>, "args": [...], "expect": <optional output file>}; in "args" the placeholders
        {pkg} (this package), {code} (GFF/code), {data} (GFF/data), {results} (GFF/results), {work} (the work folder
        of that check) and {quick} (WORK/quick) are substituted. A check passes when its script exits 0 and, if
        "expect" is given, writes that file. The table goes to WORK/replay_table.txt; any FAIL gives exit status 1.

The package's run.py writes into results/ by default; this script always passes --output-dir.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
CODE = PKG.parent
GFF = CODE.parent
# Files of the delivered package that the public export leaves out (author rule 2026-10-16: one TeX note per direction).
# The package's note is merged into the condensed note GFF/note (Part V, Section 34); the thermal source is a
# byte-identical copy of that note at commit 22a2850 and is read by no program (data/source/PROVENANCE.json keeps its
# sha256). Only the package's run.py "note" task and scripts/check_standalone_note.py read the note; public.mk calls
# neither.
DROPPED = ("note/lri_ope_note.tex", "note/lri_ope_note.pdf", "data/source/thermal_note_2026-10-15.tex")


def run(cmd, cwd):
    print("RUN", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=cwd).returncode


def manifest():
    bad, absent, ok = [], [], 0
    lines = [l.split("  ", 1) for l in (PKG / "MANIFEST.sha256").read_text().splitlines() if l.strip()]
    for h, rel in lines:
        f = PKG / rel
        if not f.is_file():
            absent.append(rel)
        elif hashlib.sha256(f.read_bytes()).hexdigest() == h:
            ok += 1
        else:
            bad.append(rel)
    unexpected = [r for r in absent if r not in DROPPED]
    print(f"MANIFEST.sha256: {ok} of {len(lines)} listed files byte-identical; absent {len(absent)} "
          f"(dropped by the public export: {len(absent) - len(unexpected)}); mismatches {bad[:5]}; "
          f"unexpected absent {unexpected[:5]}", flush=True)
    return 1 if bad or unexpected else 0


def quick(work):
    out = (work / "quick").resolve()
    out.mkdir(parents=True, exist_ok=True)
    return run([sys.executable, "-I", PKG / "run.py", "quick", "--output-dir", out], PKG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["test", "replay"])
    ap.add_argument("--work", default=".work")
    ap.add_argument("--checks", default="../ope_checks")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    if a.task == "test":
        rc = manifest() or quick(work) or manifest()
        print("TEST:", "PASS" if rc == 0 else "FAIL")
        return 1 if rc else 0
    rows, nfail = [], 0
    if not (work / "quick" / "coefficients.json").is_file():
        rc = quick(work)
        rows.append(("package", "run.py quick", "PASS" if rc == 0 else "FAIL"))
        nfail += rc != 0
    checks = Path(a.checks).resolve()
    folders = sorted(p.parent for p in checks.glob("*/commands.json"))
    if not folders:
        rows.append(("ope_checks", f"no commands.json under {checks}", "FAIL"))
        nfail += 1
    for folder in folders:
        for i, c in enumerate(json.loads((folder / "commands.json").read_text())):
            w = work / "checks" / folder.name / f"{i:02d}"
            w.mkdir(parents=True, exist_ok=True)
            sub = {"{pkg}": PKG, "{code}": CODE, "{data}": GFF / "data", "{results}": GFF / "results",
                   "{work}": w, "{quick}": work / "quick"}
            args = []
            for x in c.get("args", []):
                x = str(x)
                for k, v in sub.items():
                    x = x.replace(k, str(v))
                args.append(x)
            rc = run([sys.executable, "-I", folder / c["script"]] + args, w)
            ok = rc == 0 and (not c.get("expect") or (w / c["expect"]).is_file())
            nfail += not ok
            rows.append((folder.name, f"{c['script']} {' '.join(c.get('args', []))}"[:90],
                         "PASS" if ok else f"FAIL (exit {rc})"))
    lines = [f"{f:10s} {what:92s} {st}" for f, what, st in rows]
    lines.append(f"OPE replay: {len(rows) - nfail} PASS, {nfail} FAIL")
    text = "\n".join(lines)
    print(text)
    (work / "replay_table.txt").write_text(text + "\n")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
