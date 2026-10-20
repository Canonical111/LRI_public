#!/usr/bin/env python3
"""Re-extrapolate C_4 after adding the zero-mode spectator-window shift dC4^zm(L) (zero_mode_window.py) to the
consistent-scheme data, and compare with the uncorrected fits.  Writes zm_corrected_C4.csv and prints tables."""
import csv, math, os
import numpy as np
import exact_low_orders as ex
import zero_mode_window as zw
import fits, reference
HERE = os.path.dirname(os.path.abspath(__file__))
REF = reference.load()

def dC4zm(L):
    W, dW = ex.weights(L); c, dc, c1J = ex.bundles(L, W, dW)
    e_m = zw.second_order_all_cutoffs(c, L); e = e_m.sum(axis=1); etil = e - e[0][None, :]
    lv = np.arange(L + 1); Ep = {}
    for p in range(4):
        tot = 0.0
        for mm in (1, 2, 3, 4):
            Z = ex.zop("V", mm)
            for p1 in range(ex.NZ):
                amp2 = Z[p1, p] ** 2
                if amp2 == 0.0: continue
                den = (p1 - p) / 2.0 + mm / 2.0 + lv
                Dp = zw.G1 ** 2 * (etil[p1, L] - etil[p1, L - lv]); mask = c[mm] != 0
                tot += math.factorial(mm) * amp2 * math.fsum(c[mm][mask] * Dp[mask] / den[mask] ** 2)
        Ep[p] = zw.G1 ** 2 * tot
    return ex.Pi(Ep)

ht = fits.load_ht()
rows = []
for L in sorted(ht["consistent"]):
    d = dC4zm(L)
    rows.append(dict(L=L, C4_consistent=ht["consistent"][L][4], dC4_zm=d, C4_full=ht["consistent"][L][4] + d))
with open(os.path.join(HERE, "zm_corrected_C4.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows: print(f"L={r['L']:3d} C4cons={r['C4_consistent']:.10f} dC4zm={r['dC4_zm']:+.8f} C4full={r['C4_full']:.10f}")
ser_full = {r["L"]: r["C4_full"] for r in rows}
ser_cons = {r["L"]: r["C4_consistent"] for r in rows}
ref = REF[4][0]
print(f"\nreference C4 = {ref:.8f}")
for name, ser in (("consistent", ser_cons), ("consistent+zm", ser_full)):
    print(f"--- {name}")
    for (j1, j2) in [(1, 0), (1, 1), (2, -1), (2, 0), (2, 1)]:
        vals = []
        for Lmin in (10, 12, 14, 16):
            Ls = np.array([x for x in sorted(ser) if Lmin <= x <= 30], float); y = np.array([ser[int(x)] for x in Ls])
            cinf, coef, mr, cond = fits.fit_tower(Ls, y, j1, j2)
            _, _, mrf, _ = fits.fit_tower(Ls, y, j1, j2, cinf=ref)
            vals.append(f"{Lmin}:{cinf:.4f}({(cinf-ref)/ref:+.1%},r{mrf/mr:.0f})")
        print(f"  tower({j1},{j2}) " + "  ".join(vals))
    # joint omega1 = 9/2
    T2 = {L: v[2] - REF[2][0] for L, v in ht["consistent"].items()}; T3 = {L: v[3] - REF[3][0] for L, v in ht["consistent"].items()}
    for R in (("1/L2",), ("1/L2", "l/L2")):
        vals = []
        for Lmin in (10, 12, 14, 16):
            Ls = np.array([x for x in sorted(ser) if Lmin <= x <= 30], float); l = np.log(Ls)
            t2 = np.array([T2[int(x)] for x in Ls]); t3 = np.array([T3[int(x)] for x in Ls])
            y = np.array([ser[int(x)] for x in Ls]) + 4.5 * l * t3 + 0.5 * 20.25 * l ** 2 * t2
            tail = [1 / Ls, l * t2, 1 / Ls ** 2] + ([l / Ls ** 2] if "l/L2" in R else [])
            coef, mr, _ = fits.lsq(np.column_stack([np.ones_like(Ls)] + tail), y)
            _, mrf, _ = fits.lsq(np.column_stack(tail), y - ref)
            vals.append(f"{Lmin}:{coef[0]:.4f}({(coef[0]-ref)/ref:+.1%},w2 {-coef[2]:+.1f},r{mrf/mr:.0f})")
        print(f"  joint R={'+'.join(R):9s} " + "  ".join(vals))
