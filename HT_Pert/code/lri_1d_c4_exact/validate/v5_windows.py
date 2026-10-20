#!/usr/bin/env python3
"""A5: window pieces.
  (i)  shift4 (from a production npz, even grid) vs dC_reconciled.json "shift4" on that file's 67-row grid
       (even L <= 152; the file has no rows at L = 130, 132, 134, 138, 140, 142, 146, 148, 150): <= 1e-12 abs;
  (ii) Delta R4 = H_odd(L-1)/2916 at every even L of the npz: <= 1e-14 relative;
  (iii) own two-vertex g2D window sum vs the closed form fast(L), even L <= 400: <= 1e-12 abs (computed here).
usage: python3 validate/v5_windows.py results/c4_1d_L400.npz [--g2D-Lmax 400]"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "vendor"))
import exact_fast          # noqa: E402
import windows1d as wn     # noqa: E402

REF = os.path.join(HERE, "..", "inputs", "dC_reconciled.json")    # copy, sha256 in inputs/MANIFEST.txt
MISSING = {130, 132, 134, 138, 140, 142, 146, 148, 150}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("npz")
    ap.add_argument("--g2D-Lmax", type=int, default=400)
    a = ap.parse_args()
    d = np.load(a.npz)
    Ls = d["even_L"]
    s4 = dict(zip(Ls.tolist(), d["even_shift4"]))
    ref = json.load(open(REF))
    rows = sorted(int(k) for k in ref)
    ok = True
    assert len(rows) == 67 and set(range(2, 153, 2)) - set(rows) == MISSING, "unexpected reference grid"
    if Ls.max() < 152:
        print(f"npz Lmax {Ls.max()} < 152: (i) incomplete"); ok = False
    for k in ("even_shift4", "even_dR4", "even_dR4_closed"):
        if d[k].shape != Ls.shape or not np.all(np.isfinite(d[k])):
            print(f"non-finite or misshaped {k}"); ok = False
    w1 = float(np.max([abs(s4[L] - ref[str(L)]["shift4"]) for L in rows if L in s4]))
    print(f"(i)   shift4 vs dC_reconciled ({sum(L in s4 for L in rows)} rows): max abs {w1:.2e}")
    ok &= bool(w1 <= 1e-12)
    print("      engine shift4 at the 9 cutoffs without reference: "
          + ", ".join(f"{L}:{s4[L]:.15f}" for L in sorted(MISSING) if L in s4))
    w2 = float(np.max(np.abs(d["even_dR4"] - d["even_dR4_closed"]) / d["even_dR4_closed"]))
    print(f"(ii)  Delta R4 vs H_odd(L-1)/2916 (L <= {Ls.max()}): max rel {w2:.2e}")
    ok &= bool(w2 <= 1e-14)
    gw = wn.g2D_window(a.g2D_Lmax)
    w3 = float(np.max([abs(gw[L] - exact_fast.fast(L)) for L in gw]))
    print(f"(iii) own g2D window sum vs fast(L) (L <= {a.g2D_Lmax}): max abs {w3:.2e}")
    ok &= bool(w3 <= 1e-12) and len(gw) == a.g2D_Lmax // 2
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
