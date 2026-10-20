"""Parent refit of C_5^Wcs(L), L <= 300 (independent of large_L/c5_fits300.py except for the data assembly).
Null test: the same estimator on C_4^W(L) (exact limit known, no ln L) over the same L range."""
import os, sys
import numpy as np
R = sys.argv[1]  # residual_log
p = np.load(os.path.join(R, "large_L/results/c5_L300.npz")); p2 = np.load(os.path.join(R, "results/eps5/c5_L200.npz"))
d = np.load(os.path.join(R, "results/eps5/dC5_L1000_all.npz")); s = np.load(os.path.join(R, "results/legw/legw_L1000.npz"))
t = np.load(os.path.join(R, "large_L/results/tag3_L16000.npz"))
L = p["L"].astype(float); n = len(L)
assert np.array_equal(d["L"][:n], p["L"]) and np.array_equal(s["L"][:n], p["L"]) and np.array_equal(t["L"][:n], p["L"])
n2 = len(p2["L"]); assert np.array_equal(p2["L"], p["L"][:n2])
for k in ("raw_C4", "raw_C5"):
    print(f"{k}: max rel diff vs c5_L200.npz on L<=200: {np.max(np.abs(p[k][:n2] / p2[k] - 1)):.1e}")
c5wc = p["raw_C5"] + d["Wc_dC5"][:n]; c5wcs = c5wc + t["delta3"][:n] * s["S"][:n]
c4w = p["raw_C4"] + d["Wb_dC4"][:n]
EX5, EX4 = -38.8336458962, 5.048868431354847
print(f"C5^Wcs(L) at L=100,200,300: {c5wcs[49]:.6f} {c5wcs[99]:.6f} {c5wcs[-1]:.6f} (L={L[49]:.0f},{L[99]:.0f},{L[-1]:.0f});"
      f"  C4^W(300) - exact = {c4w[-1]-EX4:+.3e}")
def cols(L, k1, k2, log):
    c = [np.ones_like(L)] + [np.log(L)**k / L for k in range(k1 + 1)] + [np.log(L)**k / L**2 for k in range(k2 + 1)]
    if log: c.append(np.log(L))
    return np.column_stack(c)
def fit(y, lo, hi, k1, k2, log):
    m = (L >= lo) & (L <= hi); A = cols(L[m], k1, k2, log)
    sc = np.abs(A).max(0); return np.linalg.lstsq(A / sc, y[m], rcond=None)[0] / sc
LMIN, K2 = (30, 40, 60, 80, 100), (0, 1, 2)
def blind(y, hi, k1, log):
    m = L > hi; e = []
    for lo in LMIN:
        for k2 in K2:
            c = fit(y, lo, hi, k1, k2, log); e.append(np.abs(cols(L[m], k1, k2, log) @ c - y[m]).max())
    return np.median(e)
for lab, y, ex, ks in (("C5^Wcs", c5wcs, EX5, (2, 3, 4)), ("C4^W (null)", c4w, EX4, (1, 2, 3))):
    print(f"\n### {lab}\n# blind: fit [Lmin,200] -> predict 202..300 (median max|err| over {len(LMIN)*len(K2)} fits)")
    for k1 in ks:
        print(f"k1={k1}: no log {blind(y, 200, k1, False):.1e}   free log {blind(y, 200, k1, True):.1e}"
              f"   | fit [Lmin,240] -> 242..300: no log {blind(y, 240, k1, False):.1e}  free log {blind(y, 240, k1, True):.1e}")
    k1 = ks[1]
    print(f"# k1={k1} towers by Lmax: no-log limit - exact (median [range]); free-log b (median [range])")
    for hi in (160, 200, 240, 280, 300):
        A0 = np.array([fit(y, lo, hi, k1, k2, False)[0] for lo in LMIN for k2 in K2]) - ex
        B = np.array([fit(y, lo, hi, k1, k2, True)[-1] for lo in LMIN for k2 in K2])
        print(f"Lmax={hi}: limit-exact {np.median(A0):+.5f} [{A0.min():+.5f},{A0.max():+.5f}]   b {np.median(B):+.5f} [{B.min():+.5f},{B.max():+.5f}]")
    A0 = np.array([fit(y, lo, 300, k1, k2, False)[0] for lo in LMIN for k2 in K2])
    print(f"# no-log limit L<=300: {np.median(A0):.5f} +- {(A0.max()-A0.min())/2:.5f} (half range); exact {ex}")
print("\n# C5^Wcs: limit shift when b is fixed at +-0.01 (k1=3 towers, L<=300, median over the same fits)")
lnL = np.log(np.where(L > 0, L, 1.0))  # L = 0 never enters a fit (Lmin >= 30)
A5 = np.median([fit(c5wcs, lo, 300, 3, k2, False)[0] for lo in LMIN for k2 in K2])
for b in (-0.01, 0.01):
    A = np.median([fit(c5wcs - b * lnL, lo, 300, 3, k2, False)[0] for lo in LMIN for k2 in K2])
    print(f"b={b:+.2f}: limit {A:.5f}  shift vs no-log {A - A5:+.4f}")
