#!/usr/bin/env python3
"""A5 (PLAN.md): window pieces of a production result (Lmax >= 152) vs the references.
  * inputs/dC_reconciled.json on its actual 67 rows (asserted): dC5_Dconn <= 1e-11 abs for L <= 100 and <= 3e-10 for
    102 <= L <= 152; dC5_bubble <= 1e-13; dC5_rows5 and B5 <= 1e-12; A4, B4 <= 1e-12; dC5_rows4 vs the exact identity
    2 C2(L) (3 A4 - B4) on the reference A4/B4 <= 1e-12 (the reference rows4 column carries ~6e-12 fit noise from B's
    rho coefficients and is only reported); dC5_g2D <= 1e-12 for
    L <= 118 and <= 3e-10 above (B's capped-space reference noise); shift4 <= 1e-12;
  * inputs/top5.jsonl (B's closed-form top sums, L <= 160): B5 and A4/B4 <= 1e-12;
  * inputs/d5_all.json (package g2D, L = 4..118): dC5_g2D <= 1e-12;
  * closed forms vs engine at every even L of the result: Delta R4 (engine) = H_odd(L-1)/2916 <= 1e-14 relative;
    Delta R5 engine (cancellation-free) vs closed <= 1e-14 relative; own g2D C4 window sum vs fast(L) <= 1e-12;
  * odd-shell invariant: the p = 0 eps^5 vacuum shells at m = c-1 and c-3 vanish: |vacodd5| <= 1e-13 |B5|.
usage: python3 validate/v5_windows.py RESULT.npz"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.join(HERE, "..", "inputs")
MISSING = {130, 132, 134, 138, 140, 142, 146, 148, 150}


def main():
    d = np.load(sys.argv[1])
    Ls = d["even_L"].astype(int)
    ev = {k[5:]: d[k] for k in d.files if k.startswith("even_")}
    for k, v in ev.items():
        if v.shape != Ls.shape or not np.all(np.isfinite(v)):
            print(f"FAIL non-finite or misshaped even_{k}")
            sys.exit(1)
    idx = {int(L): i for i, L in enumerate(Ls)}
    ok = True

    def gate(name, val, tol):
        nonlocal ok
        good = bool(np.isfinite(val) and val <= tol)
        ok &= good
        print(f"{'PASS' if good else 'FAIL'} {name}: {val:.2e} (tol {tol:.0e})")

    ref = json.load(open(os.path.join(INP, "dC_reconciled.json")))
    rows = sorted(int(k) for k in ref)
    assert len(rows) == 67 and set(range(2, 153, 2)) - set(rows) == MISSING, "unexpected reference grid"
    if Ls.max() < 152:
        print("FAIL result does not reach L = 152")
        sys.exit(1)

    def maxdev(col, mine, Lsel):
        v = [abs(ev[mine][idx[L]] - ref[str(L)][col]) for L in Lsel if ref[str(L)].get(col) is not None]
        return float(np.max(v)) if v else np.inf

    lo = [L for L in rows if L <= 100]
    mid = [L for L in rows if 100 < L <= 152]
    gate("dC5_Dconn vs dC_reconciled L<=100", maxdev("dC5_Dconn", "dC5_Dconn", lo), 1e-11)
    gate("dC5_Dconn vs dC_reconciled 102..152", maxdev("dC5_Dconn", "dC5_Dconn", mid), 3e-10)
    gate("dC5_bubble", maxdev("dC5_bubble", "dC5_bubble", rows), 1e-13)
    gate("dC5_rows5", maxdev("dC5_rows5", "dC5_rows5", rows), 1e-12)
    gate("B5", maxdev("B5", "B5", rows), 1e-12)
    # rows4 = 2 C2(L) (3 A4 - B4) is an exact identity (A2 rationals); the reference COLUMN dC5_rows4 was built from B's
    # fitted response coefficients and is inconsistent with the reference's own A4/B4 by up to ~6e-12 (sign-alternating
    # fit noise growing with L).  Gate: rows4 vs the identity on the reference A4/B4 (which are themselves gated below and
    # vs B's closed-form top5); the raw column deviation is reported (PLAN deviation, logged in PLAN-REVIEW-LOG.md).
    r4ref = [2 * d["C2"][4 * L] * (3 * ref[str(L)]["A4"] - ref[str(L)]["B4"]) for L in rows
             if ref[str(L)].get("A4") is not None]
    r4min = [ev["dC5_rows4"][idx[L]] for L in rows if ref[str(L)].get("A4") is not None]
    gate("dC5_rows4 vs 2 C2 (3 A4_ref - B4_ref)", float(np.max(np.abs(np.array(r4min) - np.array(r4ref)))), 1e-12)
    print(f"INFO dC5_rows4 vs the reference column (B's fitted rho; not a gate): {maxdev('dC5_rows4', 'dC5_rows4', rows):.2e}")
    col = [abs(ref[str(L)]["dC5_rows4"] - 2 * d["C2"][4 * L] * (3 * ref[str(L)]["A4"] - ref[str(L)]["B4"])) for L in rows
           if ref[str(L)].get("dC5_rows4") is not None]
    print(f"INFO reference column vs its own identity (reference noise): {max(col):.2e}")
    gate("A4", maxdev("A4", "A4", rows), 1e-12)
    gate("B4", maxdev("B4", "B4", rows), 1e-12)
    gate("dC5_g2D L<=118", maxdev("dC5_g2D", "dC5_g2D", [L for L in rows if L <= 118]), 1e-12)
    gate("dC5_g2D 120..152", maxdev("dC5_g2D", "dC5_g2D", [L for L in rows if L > 118]), 3e-10)
    gate("shift4", maxdev("shift4", "shift4", rows), 1e-12)
    top5 = [json.loads(l) for l in open(os.path.join(INP, "top5.jsonl")) if l.strip()]
    db = []
    for r in top5:
        L = int(r["L"])
        if L in idx:
            db.append(max(abs(ev["B5"][idx[L]] - r["B5"]), abs(ev["A4"][idx[L]] - r["A4"]),
                          abs(ev["B4"][idx[L]] - r["B4"])))
    gate(f"B5, A4, B4 vs top5.jsonl ({len(db)} cutoffs)", float(np.max(db)) if db else np.inf, 1e-12)
    d5 = json.load(open(os.path.join(INP, "d5_all.json")))
    dg = [abs(ev["dC5_g2D"][idx[int(L)]] - v["delta_C"][5]) for L, v in d5.items() if int(L) in idx]
    gate(f"dC5_g2D vs d5_all ({len(dg)} cutoffs)", float(np.max(dg)) if dg else np.inf, 1e-12)
    gate("Delta R4 engine vs H_odd/2916 (rel)", float(np.max(np.abs(ev["dR4"] - ev["dR4_closed"]) / ev["dR4_closed"])),
         1e-14)
    gate("Delta R5 engine vs closed (rel)", float(np.max(np.abs(ev["dR5_engine"] - ev["dR5"]) / np.abs(ev["dR5"]))), 1e-14)
    gate("own g2D C4 window vs fast", float(np.max(np.abs(ev["g2D_C4_engine"] - ev["fast_g2D"]))), 1e-12)
    gate("odd-shell invariant |vacodd5|/|B5|", float(np.max(np.abs(ev["vacodd5"]) / np.abs(ev["B5"]))), 1e-13)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
