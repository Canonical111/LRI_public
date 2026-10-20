import glob, json, os, sys
from fractions import Fraction as Fr
import numpy as np
R = sys.argv[1]
def fit(L, y, cols):
    A = np.column_stack([c(L) for c in cols]); return np.linalg.lstsq(A, y, rcond=None)[0]
one = lambda L: np.ones_like(L); inv = lambda L: 1 / L; inv2 = lambda L: 1 / L**2; inv3 = lambda L: 1/L**3
lnL = lambda L: np.log(L); lnL_L = lambda L: np.log(L) / L; lnL_L2 = lambda L: np.log(L)/L**2
# delta3(L)
dl = {}
for f in glob.glob(os.path.join(R, "results/tag/tag_L*_a1_phi2_2_real.json")):
    d = json.load(open(f)); L = int(d["L"]); c13 = [Fr(x) for x in d["c1_3"]]
    dl[L] = float((c13[(L - 2) // 2] - (Fr(d["phi2_2_real"]["c1tag"][3]) - 2 * Fr(d["r"][3]))) / 4)
Ls = np.array(sorted(dl), float); y = np.array([dl[int(l)] for l in Ls])
print("delta3:", dict(zip(Ls.astype(int), np.round(y, 7))))
for lo in (6, 8):
    m = Ls >= lo
    for name, cols in [("a+b/L", [one, inv]), ("a+b/L+c/L2", [one, inv, inv2]), ("a+b/L2+c/L3", [one, inv2, inv3]),
                       ("a+b/L+c lnL/L2", [one, inv, lnL_L2]), ("a+b/L2+c lnL/L2", [one, inv2, lnL_L2])]:
        if m.sum() > len(cols):
            print(f"  Lmin={lo} {name:18s} delta_inf={fit(Ls[m], y[m], cols)[0]:+.6f}")
        elif m.sum() == len(cols):
            print(f"  Lmin={lo} {name:18s} (exact) delta_inf={fit(Ls[m], y[m], cols)[0]:+.6f}")
print("  -4/(81 pi) =", -4 / (81 * np.pi))
# S(L)
S = np.load(os.path.join(R, "results/legw/legw_L1000.npz")); L = S["L"].astype(float); s = S["S"]
for lo in (100, 200, 400):
    m = L >= lo
    for name, cols in [("no log: 1,1/L,1/L2,lnL/L,lnL/L2", [one, inv, inv2, lnL_L, lnL_L2]),
                       ("free lnL + same", [lnL, one, inv, inv2, lnL_L, lnL_L2])]:
        p = fit(L[m], s[m], cols)
        print(f"S Lmin={lo:3d} {name:34s} -> {p[:2]}")
# chi_11 Wcs R3 trend
def load(pattern, scheme):
    out = {}
    for f in glob.glob(os.path.join(R, pattern)):
        j = json.load(open(f))
        if scheme not in j["schemes"]: continue
        Lx = j["meta"]["args"]["L"]; out.setdefault(Lx, {}).update({k: Fr(x) for k, x in j["schemes"][scheme]["values"].items() if x is not None})
    return out
wcs = load("ce_wc/out_wcs/*.json", "Wcs"); wc = load("ce_wc/out_local/*.json", "Wc")
for dn, prim in (("odd1", 1), ("odd2", 1)):
    Lr = np.array([l for l in sorted(wcs) if l >= 6], float)
    r3 = np.array([float(wcs[int(l)][f"Ed|{dn}|3"] - wcs[int(l)][f"E|{prim}|3"]) for l in Lr])
    for lo in (6, 8):
        m = Lr >= lo
        for name, cols in [("a+b/L", [one, inv]), ("a+b/L+c/L2", [one, inv, inv2]), ("a+b/L2", [one, inv2]), ("a+b/L2+c/L3", [one, inv2, inv3])]:
            if m.sum() >= len(cols):
                print(f"Wcs R3 {dn} Lmin={lo} {name:12s} -> {fit(Lr[m], r3[m], cols)[0]:+.6f}")
# even1 Wc R3 incl L=16
Lw = np.array([l for l in sorted(wc) if l >= 6 and "Ed|even1|3" in wc[l]], float)
r3w = np.array([float(wc[int(l)]["Ed|even1|3"] - wc[int(l)]["E|2|3"]) for l in Lw])
print("Wc even1 R3:", dict(zip(Lw.astype(int), np.round(r3w, 6))))
for lo in (8, 10):
    m = Lw >= lo
    for name, cols in [("a+b/L+c/L2", [one, inv, inv2]), ("a+b/L+c lnL/L", [one, inv, lnL_L]), ("a+b lnL/L+c/L2", [one, lnL_L, inv2])]:
        if m.sum() >= len(cols):
            print(f"Wc even1 R3 Lmin={lo} {name:14s} -> {fit(Lw[m], r3w[m], cols)[0]:+.5f}   (Wcs needs +{-1.5*-0.0159:.4f})")
