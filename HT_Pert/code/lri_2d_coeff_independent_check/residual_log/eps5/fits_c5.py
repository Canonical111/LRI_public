#!/usr/bin/env python3
"""Large-L forms and extrapolations of C_5(L) in every scheme.

C_5(scheme)(L) = C_5(raw)(L) + dC_5(scheme)(L): raw from prod5.py (L <= Lraw), shifts from delta5.py (L <= 1000;
the shifts are exact to ~1e-14 against brute force at L <= 8 and against rs_exact/zeromode_exact at L <= 18).
Step 1: divergent content of the shifts (L <= 1000): dC5 = a L + b2 ln^2 L + b1 ln L + c + tower.
Step 2: raw C_5(L), L <= Lraw: the same form; a_raw from a free fit.
Step 3: every scheme: C_5^S(L) = a_S L + ... with a_S free (must vanish for a convergent scheme), then a_S = 0 imposed
        (and a_S = 0 with b2 = b1 = 0, the convergence hypothesis) -> A_S = C_5^S(inf) estimates.
Fit tower: fitx (fitlib + L, L ln L, ln^3 L).  The quoted spreads are over towers and fit windows (systematic).
usage: python3 fits_c5.py ../results/eps5/c5_L160.npz ../results/eps5/dC5_L1000.npz"""
import os
import sys

import numpy as np

import fitx as F

HERE = os.path.dirname(os.path.abspath(__file__))
REF5 = -38.833645896225360553
SCHEMES = ["consistent", "consistent2", "zeromode", "zeromode2", "Z2", "Zb", "W2", "W3m", "W3e", "Wb", "W3x", "Wc"]
TOWERS = {"t1": ["1/L", "l/L"], "t2": ["1/L", "l/L", "l2/L"], "t3": ["1/L", "l/L", "l2/L", "1/L2"],
          "t4": ["1/L", "l/L", "l2/L", "l3/L", "1/L2", "l/L2"]}


def summarize(L, y, lead, Lmins, Lmax=None, towers=("t1", "t2", "t3")):
    vals = {k: [] for k in lead}
    res = []
    for tn in towers:
        for Lmin in Lmins:
            cc, r, nn = F.fit(L, y, lead + TOWERS[tn], Lmin, Lmax)
            for k in lead:
                vals[k].append(cc[k])
            res.append(r)
    return {k: (float(np.median(v)), float((max(v) - min(v)) / 2)) for k, v in vals.items()}, float(np.median(res))


def fmt(s):
    return " ".join(f"{k}={v[0]:+.6f}({v[1]:.0e})" for k, v in s.items())


def main():
    prod = np.load(sys.argv[1])
    sh = np.load(sys.argv[2])
    Lr = prod["L"].astype(float)
    nr = len(Lr)
    Ls = sh["L"].astype(float)
    raw = prod["raw_C5"]
    out = [f"# C5 continuum = {REF5}", f"# raw: {sys.argv[1]} (L <= {int(Lr.max())}); shifts: {sys.argv[2]} (L <= {int(Ls.max())})"]
    # step 1
    out.append("\n== step 1: divergent content of the shifts, dC5 = a L + b2 l2 + b1 l + c + tower (L <= %d)" % Ls.max())
    a_sh = {}
    for s in SCHEMES:
        st, r = summarize(Ls, sh[f"{s}_dC5"], ["L", "1", "l", "l2"], [100, 200, 300], towers=("t1", "t2", "t3", "t4"))
        a_sh[s] = st["L"][0]
        out.append(f"  {s:11s} {fmt(st)}")
    # step 2
    Lmins = [30, 40, 60] if Lr.max() >= 150 else [16, 20, 24]
    out.append(f"\n== step 2: raw C5(L), L <= {int(Lr.max())}, Lmin in {Lmins}")
    for lead in (["L", "1", "l", "l2"], ["L", "1", "l", "l2", "l3"], ["LlL", "L", "1", "l", "l2"]):
        st, r = summarize(Lr, raw, lead, Lmins)
        out.append(f"  {'+'.join(lead):18s} {fmt(st)}  res~{r:.0e}")
    st, r = summarize(Lr, raw, ["L", "1", "l", "l2"], Lmins)
    a_raw = st["L"][0]
    out.append(f"  -> a_raw = {a_raw:+.6f} +- {st['L'][1]:.0e};  scheme linear coefficients a_S = a_raw + a_shift:")
    for s in SCHEMES:
        out.append(f"     {s:11s} a_shift = {a_sh[s]:+.7f}   a_S = {a_raw + a_sh[s]:+.6f}")
    # step 3
    out.append(f"\n== step 3: C5^S(L) = raw + shift, L <= {int(Lr.max())}")
    for s in ["raw"] + SCHEMES:
        y = raw if s == "raw" else raw + sh[f"{s}_dC5"][:nr]
        vals = ", ".join(f"{y[int(x) // 2]:+.5f}" for x in (20, 40, 80, 120, 160, 200) if x <= Lr.max())
        out.append(f"-- {s}: C5 at L = 20, 40, 80, 120, 160[, 200]: {vals}")
        for lead, tag in ((["L", "1", "l", "l2"], "free a,b2,b1"), (["1", "l", "l2"], "a=0      "),
                          (["1", "l"], "a=b2=0   "), (["1"], "a=b2=b1=0")):
            st, r = summarize(Lr, y, lead, Lmins)
            A = st["1"]
            out.append(f"   {tag}  A = {A[0]:+.4f} +- {A[1]:.1e} (A - ref = {A[0] - REF5:+.3f})  " +
                       " ".join(f"{k}={v[0]:+.5f}({v[1]:.0e})" for k, v in st.items() if k != "1") + f"  res~{r:.0e}")
    # step 4: profile over a hypothesized raw linear coefficient (the free linear fits above are not decisive)
    out.append("\n== step 4: profile over the raw linear coefficient a: fits of raw(L) - a L (L <= %d, Lmin 30..80, "
               "towers t1..t4); the stable a is where A is least window/tower dependent and needs no logs" % Lr.max())
    out.append("   a_raw     | lead 1+l+l2: A (spread) b2 b1 | lead 1+l: A (spread) b1 | lead 1: A (spread) res")
    grid = sorted(set([-0.001, 0.0, 0.0002, 0.0005, 0.001, 0.0015, 0.002, 0.003, 0.004] + [-a_sh[s] for s in SCHEMES]))
    for a in grid:
        y = raw - a * Lr
        row = []
        for lead in (["1", "l", "l2"], ["1", "l"], ["1"]):
            st, r = summarize(Lr, y, lead, [30, 40, 60, 80], towers=("t1", "t2", "t3", "t4"))
            row.append((st, r))
        tag = ",".join(s for s in SCHEMES if abs(-a_sh[s] - a) < 1e-12)
        (s0, r0), (s1, r1), (s2, r2) = row
        out.append(f"  {a:+.6f} | {s0['1'][0]:9.3f} ({s0['1'][1]:6.2f}) {s0['l2'][0]:+.4f} {s0['l'][0]:+.3f} | "
                   f"{s1['1'][0]:8.3f} ({s1['1'][1]:5.2f}) {s1['l'][0]:+.3f} | {s2['1'][0]:8.3f} ({s2['1'][1]:5.2f}) "
                   f"{r2:.0e}  {('= -a_shift of ' + tag) if tag else ''}")
    txt = "\n".join(out)
    print(txt)
    os.makedirs(os.path.join(HERE, "..", "fits"), exist_ok=True)
    open(os.path.join(HERE, "..", "fits", "fits_c5.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()
