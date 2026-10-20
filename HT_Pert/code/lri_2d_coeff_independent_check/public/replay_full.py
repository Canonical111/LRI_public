#!/usr/bin/env python3
"""replay-full: rerun the shipped (verbatim) analysis scripts on a scratch copy and compare what they write with the
shipped outputs, number by number.

Run from HT_Pert/code/lri_2d_coeff_independent_check (make -f public.mk replay-full; about a minute). The scripts write
next to themselves, so they run in .work/full (a copy of the snapshot); the shipped tree is not touched. Each regenerated
output is compared with the shipped one token by token: equal text, or numbers equal within one unit of the last printed digit, rel 1e-3 or
abs 1e-10 (one of the three suffices). The stable fits reproduce to the printed digit; the looser criteria are for
the ill-conditioned fits the outputs also print (log T332 of the raw C4; T22+l3/L with a free log at Lmin 400 in
fits_final.txt; the [min, max] ranges at small Lmax in c5_fits300.txt and refit_c5_300.txt, whose extremes come from
towers with nearly as many parameters as points), whose 4th digit moves with the BLAS build (seen: up to 4e-4 between
symmetry AMD and Intel nodes and a laptop), and for printed fit residuals. numpy 2
prints np.int64(6) where numpy 1 printed 6; both are normalized away. Status: PASS / FAIL per
output, exit 1 on any FAIL. public/replay_p2.py is the authoritative replay; this target shows that the shipped fit
outputs are what the shipped scripts produce from the shipped data.

c4_exact/fits_c4.py (verbatim) drops every results/c4_L*.npz whose ABSOLUTE path contains the substring "local" (it
was meant to skip c4_L160_local.npz). Under a checkout such as /local1/..., /usr/local/... or ~/local/... it would
drop every file and stop with an IndexError. So that one script runs from a scratch copy of c4_exact/ in a fresh
directory whose resolved path has no "local": $HTP_NOLOCAL_TMP if set, else the first of the system temporary
directory, /tmp, /var/tmp, /dev/shm and the home directory that qualifies and is writable. If none does, the job
FAILs with a message asking for HTP_NOLOCAL_TMP. The copy is removed afterwards.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
NUM = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")

# (working dir relative to the package, command, regenerated file (None: stdout), shipped file)
JOBS = [
    ("continuum", ["asymptotics_C2_C3.py"], "continuum/asymptotics_C2_C3.txt", "continuum/asymptotics_C2_C3.txt"),
    ("c4_exact", ["fits_c4.py"], "c4_exact/fits/fit_summary.txt", "c4_exact/fits/fit_summary.txt"),
    ("residual_log", ["fits_final.py"], "residual_log/fits/fits_final.txt", "residual_log/fits/fits_final.txt"),
    ("residual_log/large_L", ["delta3_fits.py"], "residual_log/large_L/fits/delta3_fits.txt", "residual_log/large_L/fits/delta3_fits.txt"),
    ("residual_log/large_L", ["legw_logs.py"], "residual_log/large_L/fits/legw_logs.txt", "residual_log/large_L/fits/legw_logs.txt"),
    ("residual_log/large_L", ["c5_fits300.py"], "residual_log/large_L/fits/c5_fits300.txt", "residual_log/large_L/fits/c5_fits300.txt"),
    ("residual_log", ["fits/parent_check_largeL/refit_c5_300.py", "."], None, "residual_log/fits/parent_check_largeL/refit_c5_300.txt"),
    ("residual_log", ["fits/parent_check_wcs/verify.py", "."], None, "residual_log/fits/parent_check_wcs/verify.txt"),
    ("residual_log", ["fits/parent_check_wcs/fits.py", "."], None, "residual_log/fits/parent_check_wcs/fits.txt"),
    ("residual_log", ["fits/parent_check_wcs/r3zero.py", "."], None, "residual_log/fits/parent_check_wcs/r3zero.txt"),
    ("residual_log", ["fits/parent_check_wcs/blind16.py", "."], None, "residual_log/fits/parent_check_wcs/blind16.txt"),
    ("residual_log", ["fits/parent_check_p5/verify_p5.py", "."], None, "residual_log/fits/parent_check_p5/verify_p5.txt"),
]


# scripts that must run from a path without the substring "local" (see the docstring)
NOLOCAL = {"c4_exact"}


def nolocal_dir():
    """A fresh directory whose resolved absolute path does not contain "local", or None."""
    cands = [os.environ.get("HTP_NOLOCAL_TMP"), tempfile.gettempdir(), "/tmp", "/var/tmp", "/dev/shm", str(Path.home())]
    for c in cands:
        if not c or not os.path.isdir(c) or not os.access(c, os.W_OK) or "local" in str(Path(c).resolve()):
            continue
        for _ in range(5):
            d = Path(tempfile.mkdtemp(prefix="htp2_c4_", dir=c)).resolve()
            if "local" not in str(d):
                return d
            shutil.rmtree(d, ignore_errors=True)
    return None


NPW = re.compile(r"np\.(?:int|float)(?:32|64)\(([^()]*)\)")


def same_numbers(a, b):
    ta, tb = NPW.sub(r"\1", a).split(), NPW.sub(r"\1", b).split()
    if len(ta) != len(tb):
        return False, f"{len(ta)} vs {len(tb)} tokens"
    worst = 0.0
    for x, y in zip(ta, tb):
        if x == y:
            continue
        nx, ny = NUM.findall(x), NUM.findall(y)
        if NUM.sub("#", x) != NUM.sub("#", y) or len(nx) != len(ny):
            return False, f"text differs: {x!r} vs {y!r}"
        for su, sv in zip(nx, ny):
            u, v = float(su), float(sv)
            d = abs(u - v)
            mant = sv.lower().split("e")[0]
            ulp = 10.0 ** (-(len(mant.split(".")[1]) if "." in mant else 0)) * (10.0 ** int(sv.lower().split("e")[1]) if "e" in sv.lower() else 1.0)
            if d > 1e-10 and d > 1e-3 * max(abs(u), abs(v)) and d > 1.5 * ulp:
                return False, f"number differs: {x!r} vs {y!r}"
            if d > 1e-10:
                worst = max(worst, d / max(abs(v), 1e-300))
    return True, f"max rel diff {worst:.1e} (numbers above 1e-10)"


def main():
    T = PKG / ".work" / "full"
    shutil.rmtree(T, ignore_errors=True)
    shutil.copytree(PKG, T, ignore=shutil.ignore_patterns(".work", "public", "docs"))
    nf = 0
    for wd, cmd, regen, shipped in JOBS:
        base, tmp = T, None
        if wd in NOLOCAL:
            tmp = nolocal_dir()
            if tmp is None:
                print(f"FAIL  {shipped}: no writable directory whose path lacks the substring 'local' (needed by the "
                      f"verbatim {wd}/{cmd[0]}); set HTP_NOLOCAL_TMP to one")
                nf += 1
                continue
            shutil.copytree(T / wd, tmp / wd)
            base = tmp
        try:
            r = subprocess.run([sys.executable] + cmd, cwd=base / wd, capture_output=True, text=True)
            if r.returncode:
                print(f"FAIL  {shipped}: script exited {r.returncode}\n{r.stderr[-1500:]}")
                nf += 1
                continue
            new = (base / regen).read_text() if regen else r.stdout
        finally:
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)
        ok, why = same_numbers(new, (PKG / shipped).read_text())
        nf += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {shipped}  ({' '.join(cmd)}): {why}", flush=True)
    print(f"\n{len(JOBS) - nf}/{len(JOBS)} PASS" + (f", {nf} FAIL" if nf else ""))
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
