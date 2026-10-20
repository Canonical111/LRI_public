#!/usr/bin/env python3
"""eps^5 asymptotics of the 3D model: shifts by window class, C5 per scheme, extrapolation of the convergent candidates
(Wc, Wcs) with a calibration of the same protocol on C4^W (known limit), descendant identity (T3).

Inputs (../results/):
  c5raw_all_L<max>.npz   raw C5(L) to the largest L (prod5 --raw_only); c5_L20.npz (every scheme, L <= 20, check)
  dC5_L<max>.npz         scheme shifts dC5^S = C5^S - C5^raw (delta5, exact window sums)
  eps5/legw_L<max>.npz   S(L): the C5 response to (1/2) X at eps^3 (Wcs = Wc + delta3 S)
  tag/tag_L*.json        delta^(3)(L), tagged-phi brute force (L <= 16)
  eps5/desc_L*.json, tagchi/tagchi_L*.json   R_n of chi_11 (Wc, Wcs, raw, W2; tagged legs)
  ../C4_by_L.csv         C4^W(L) of the C4 study (calibration)
Output: ../fits/fits5_summary.txt"""
import csv
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import fitlib3d as F  # noqa: E402

R = os.path.join(HERE, "..", "results")
C5_EXACT = -5.8503514207513272292179442304977443001
SCHEMES = ["consistent", "consistent2", "zeromode2", "Z2", "Zb", "W2", "W3m", "Wb", "Wc"]
OUT = []


def P(s=""):
    OUT.append(s)
    print(s, flush=True)


def latest(pat):
    fs = glob.glob(os.path.join(R, pat))
    key = lambda f: int(os.path.basename(f).split("_L")[1].split(".")[0])
    return max(fs, key=key) if fs else None


def delta3_table():
    d = {}
    for f in glob.glob(os.path.join(R, "tag", "tag_L*.json")):
        r = json.load(open(f))
        if "delta3" in r:
            d[int(r["L"])] = float(r["delta3"])
    return dict(sorted(d.items()))


# ------------------------------------------------------------------------------------------------ towers
TOWERS = {
    "A [1/L, L^-3/2, L^-2 (+lnL/L)]": F.tower([-1, -1.5, -2], {-1: 1}),
    "B [1/L .. L^-5/2 (+lnL/L, lnL L^-3/2)]": F.tower([-1, -1.5, -2, -2.5], {-1: 1, -1.5: 1}),
    "C [L^-1/2, 1/L, L^-3/2]": F.tower([-0.5, -1, -1.5]),
    "D [L^-1/2 .. L^-2]": F.tower([-0.5, -1, -1.5, -2]),
    "E [1/L, L^-3/2]": F.tower([-1, -1.5]),
}


def extrapolate(L, y, Lmins, Lmaxs, label, exact, towers=TOWERS, extra=()):
    """Spread of the limit A over towers and fit windows; returns list of (tower, Lmin, Lmax, A, res)."""
    rows = []
    for tn, tw in towers.items():
        line = []
        for Lmin in Lmins:
            for Lmx in Lmaxs:
                npts = int(np.sum((L >= Lmin) & (L <= Lmx)))
                if npts < len(tw) + len(extra) + 3:
                    continue
                c, res, k = F.fit(L, y, ["1"] + list(extra) + tw, Lmin, Lmax=Lmx)
                rows.append((tn, Lmin, Lmx, c["1"], res))
                line.append(f"{Lmin}-{Lmx}:{c['1'] - exact:+.4f}")
        P(f"   {label} {tn:40s} " + " ".join(line))
    return rows


def blind(L, y, Lfit, label, exact):
    for tn, tw in TOWERS.items():
        Lmin = 8
        sel = L > Lfit
        if np.sum((L >= Lmin) & (L <= Lfit)) < len(tw) + 3 or not np.any(sel):
            continue
        c, res, k = F.fit(L, y, ["1"] + tw, Lmin, Lmax=Lfit)
        P(f"   blind {label} {tn:40s} fit {Lmin}..{Lfit}: A - exact = {c['1'] - exact:+.4f}; "
          f"max |pred - data| for {Lfit} < L <= {int(L[-1])}: {np.max(np.abs(F.predict(c, L[sel]) - y[sel])):.1e}")


def summary(rows, exact, label):
    A = np.array([r[3] for r in rows])
    if len(A) == 0:
        return
    med = np.median(A)
    P(f"   {label}: median A = {med:+.5f} (A - exact = {med - exact:+.5f}); full spread [{A.min():+.5f}, {A.max():+.5f}]"
      f" -> A - exact in [{A.min() - exact:+.5f}, {A.max() - exact:+.5f}] ({len(A)} fits)")


def main():
    fr = latest("c5raw_all_L*.npz")
    fs = latest("dC5_L*.npz")
    fl = latest(os.path.join("eps5", "legw_L*.npz"))
    P(f"# inputs: raw {os.path.basename(fr) if fr else '-'}, shifts {os.path.basename(fs) if fs else '-'}, "
      f"S {os.path.basename(fl) if fl else '-'}")
    P(f"# C5(3) = {C5_EXACT:.15f}")
    zr = np.load(fr)
    zs = np.load(fs)
    Lr = zr["L"].astype(float)
    Ls = zs["L"].astype(float)
    n = len(Lr)
    assert np.all(Ls[:n] == Lr)
    raw = zr["raw_C5"]
    # check against the all-scheme run (L <= 20)
    f20 = os.path.join(R, "c5_L20.npz")
    if os.path.exists(f20):
        z20 = np.load(f20)
        m = len(z20["L"])
        dr = np.max(np.abs(z20["raw_C5"] - raw[:m]))
        ds = max(np.max(np.abs(z20[f"{s}_C5"] - z20["raw_C5"] - zs[f"{s}_dC5"][:m])) for s in SCHEMES)
        P(f"# raw C5 vs c5_L20.npz: max diff {dr:.1e}; delta5 shifts vs prod5 (L <= 20): max diff {ds:.1e}")
    C5 = {"raw": raw}
    for s in SCHEMES:
        C5[s] = raw + zs[f"{s}_dC5"][:n]
    # ---- Wcs: delta3 exact where computed, models beyond
    d3 = delta3_table()
    zl = np.load(fl)
    Sl = dict(zip(zl["L"].astype(int), zl["S"]))
    S = np.array([Sl[int(l)] for l in Lr])
    P("\n== 0. delta^(3)(L) (tagged brute force) and S(L)")
    P("   delta3: " + " ".join(f"{L}:{v:+.6f}" for L, v in d3.items()))
    P("   S(L):   " + " ".join(f"{int(l)}:{Sl[int(l)]:+.6f}" for l in (10, 20, 40, 64, 100, 200, 400) if int(l) in Sl))
    Ld = np.array([L for L in d3 if L >= 6], dtype=float)
    yd = np.array([d3[int(L)] for L in Ld])
    models = {"sqrt(L)+1+L^-1/2": ["L^0.5", "1", "L^-0.5"], "lnL+1+1/L": ["l1*L^0", "1", "L^-1"],
              "sqrt(L)+lnL+1": ["L^0.5", "l1*L^0", "1"], "1+L^-1/2+1/L": ["1", "L^-0.5", "L^-1"]}
    d3m = {}
    for mn, names in models.items():
        c, res, k = F.fit(Ld, yd, names, 6)
        d3m[mn] = c
        P(f"   delta3 model {mn:18s} (L = 6..{int(Ld[-1])}, res {res:.1e}): "
          + " ".join(f"{a}={b:+.5f}" for a, b in c.items())
          + f"   -> delta3(40) = {F.predict(c, np.array([40.0]))[0]:+.5f}, delta3(64) = {F.predict(c, np.array([64.0]))[0]:+.5f}")
    d3arr = {}
    for mn, c in d3m.items():
        v = np.zeros_like(Lr)
        v[Lr >= 2] = F.predict(c, Lr[Lr >= 2])
        for i, l in enumerate(Lr):
            if int(l) in d3:
                v[i] = d3[int(l)]
        d3arr[mn] = v
    Wcs = {mn: C5["Wc"] + v * S for mn, v in d3arr.items()}
    dWcs = np.array([w for w in Wcs.values()])
    P(f"   Wcs - Wc at L = {int(Lr[-1])}: " + " ".join(f"{mn}:{w[-1] - C5['Wc'][-1]:+.5f}" for mn, w in Wcs.items()))
    C5["Wcs"] = np.median(dWcs, axis=0)
    # ---- table
    P(f"\n== 1. C5^S(L) (raw exact to L = {int(Lr[-1])}; shifts exact)")
    show = [l for l in (4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64) if l in Lr]
    for s in ["raw", "consistent", "Zb", "W2", "Wb", "Wc", "Wcs"]:
        P(f"   {s:10s} " + " ".join(f"{l}:{C5[s][list(Lr).index(l)]:+.5f}" for l in show))
    # ---- calibration on C4^W
    rows = list(csv.DictReader(open(os.path.join(HERE, "..", "C4_by_L.csv"))))
    L4 = np.array([float(r["L"]) for r in rows if r["C4_W"]])
    y4 = np.array([float(r["C4_W"]) for r in rows if r["C4_W"]])
    Lmx = int(Lr[-1])
    Lmins = [8, 10, 12, 16]
    Lmaxs = sorted({Lmx - 8, Lmx})
    P(f"\n== 2. Calibration: the same protocol on C4^W (continuum known), L <= {Lmx}  [entries: A - C4(3)]")
    sel = L4 <= Lmx
    r4 = extrapolate(L4[sel], y4[sel], Lmins, Lmaxs, "C4^W", F.C4_EXACT)
    summary(r4, F.C4_EXACT, "C4^W")
    P(f"   (C4^W(L = {Lmx}) - C4(3) = {y4[L4 == Lmx][0] - F.C4_EXACT:+.5f}; the protocol with L <= 600 gives 1.22807(2))")
    # ---- C5 extrapolations
    P(f"\n== 3. Extrapolation of C5^S(L), L <= {Lmx}  [entries: A - C5(3)]")
    allrows = {}
    for s in ["Wc", "Wcs", "Zb", "Wb", "consistent"]:
        allrows[s] = extrapolate(Lr, C5[s], Lmins, Lmaxs, f"{s:5s}", C5_EXACT)
        summary(allrows[s], C5_EXACT, s)
    P("\n   Wcs model dependence (delta3 extrapolation), tower A, Lmin 10:")
    for mn, w in Wcs.items():
        c, res, k = F.fit(Lr, w, ["1"] + TOWERS["A [1/L, L^-3/2, L^-2 (+lnL/L)]"], 10)
        P(f"     {mn:18s}: A - C5(3) = {c['1'] - C5_EXACT:+.5f}")
    if Lmx >= 32:
        P("\n   Blind tests: fit Lmin..Lfit, predict Lfit < L <= Lmax (prediction error) and the limit")
        for Lfit in (Lmx - 12, Lmx - 8):
            for s in ("Wc", "Wcs"):
                blind(Lr, C5[s], Lfit, s, C5_EXACT)
            blind(L4[sel], y4[sel], Lfit, "C4^W", F.C4_EXACT)
    # ---- free divergent term
    P("\n== 4. Divergence tests: A fixed at C5(3), one free divergent term b + tower A (Lmin 10)")
    for s in ("Wc", "Wcs", "Wb", "Zb"):
        out = []
        for dv in ("L^0.5", "l1*L^0", "L^1"):
            c, res, k = F.fit(Lr, C5[s] - C5_EXACT, [dv] + TOWERS["A [1/L, L^-3/2, L^-2 (+lnL/L)]"], 10)
            out.append(f"{dv}: b={c[dv]:+.3e} (res {res:.0e})")
        P(f"   {s:5s} " + " | ".join(out))
    c4o = []
    for dv in ("L^0.5", "l1*L^0", "L^1"):
        c, res, k = F.fit(L4[sel], y4[sel] - F.C4_EXACT, [dv] + TOWERS["A [1/L, L^-3/2, L^-2 (+lnL/L)]"], 10)
        c4o.append(f"{dv}: b={c[dv]:+.3e} (res {res:.0e})")
    P("   C4^W  " + " | ".join(c4o) + "   (calibration: C4^W converges)")
    # ---- local exponents
    P("\n== 5. Local convergence: d(L) = C(L) - C(L-4); ratio d(L)/d(L-4) (1/L tail: ((L-4)/L)^2 ~ 0.8 at L = 40)")
    for s in ("Wc", "Wcs", "raw"):
        idx = [list(Lr).index(l) for l in show if l >= 12]
        P(f"   {s:5s} " + " ".join(f"{int(Lr[i])}:{(C5[s][i] - C5[s][i - 2]) / (C5[s][i - 2] - C5[s][i - 4]):.3f}"
                               for i in idx))
    i4 = [np.where(L4 == l)[0][0] for l in show if l >= 12]
    P(f"   C4^W  " + " ".join(f"{int(L4[i])}:{(y4[i] - y4[i - 2]) / (y4[i - 2] - y4[i - 4]):.3f}" for i in i4))
    with open(os.path.join(HERE, "..", "fits", "fits5_summary.txt"), "w") as f:
        f.write("\n".join(OUT) + "\n")
    np.savez(os.path.join(R, "eps5", "C5_schemes.npz"), L=Lr, **{k: v for k, v in C5.items()},
             **{f"Wcs[{k}]": v for k, v in Wcs.items()})


if __name__ == "__main__":
    main()
