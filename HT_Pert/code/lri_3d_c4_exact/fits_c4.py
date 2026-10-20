#!/usr/bin/env python3
"""Large-L asymptotics of C_2, C_3, C_4(L) of the 3D model in every window scheme; blind tests.

Inputs (results/): c4_L<max>.npz (full engine), windows_L8000.npz, offdiag_L8000.npz, dchi_L<max>.npz (optional).
Schemes:  raw; consistent (package); zm = raw + diagonal zero-mode window (Delta_cons + Delta_zm);
          zmfull = raw + full zero-mode window incl. Delta z != 0 (offdiag3d 'full');
          zmfull+chi = zmfull + leading-order chi-attached window (dchi3d), when available.
Output: fits/fit_summary.txt and fits/C4_by_L.csv."""
import csv
import glob
import os

import numpy as np

import fitlib3d as F

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")


def latest(pat):
    fs = glob.glob(os.path.join(R, pat))
    key = lambda f: int(os.path.basename(f).split("_L")[1].split(".")[0])
    return max(fs, key=key) if fs else None


def main():
    os.makedirs(os.path.join(HERE, "fits"), exist_ok=True)
    out = []
    P = lambda s="": (out.append(s), print(s))
    fc = latest("c4_L*.npz")
    d = np.load(fc)
    w = np.load(os.path.join(R, "windows_L8000.npz"))
    o = np.load(os.path.join(R, "offdiag_L8000.npz"))
    fd = latest("dchi_L*.npz")
    dc = np.load(fd) if fd else None
    L = d["L"].astype(float)
    n = len(L)
    P(f"# inputs: {os.path.basename(fc)} (L <= {int(L[-1])}), windows_L8000, offdiag_L8000"
      + (f", {os.path.basename(fd)}" if fd else ""))
    P(f"# continuum: C2 = {F.C2_EXACT:.15f}, C3 = {F.C3_EXACT:.12f}, C4 = {F.C4_EXACT:.15f}")
    P(f"# Delta_cons full engine vs cancellation-free windows3d: max |diff| = "
      f"{np.max(np.abs(d['Dcons'] - w['Dcons'][:n])):.1e}")
    schemes = {"raw": d["C4raw"], "consistent": d["C4cons"], "zm": d["C4raw"] + o["diag"][:n],
               "zmfull": d["C4raw"] + o["full"][:n]}
    if dc is not None:
        m = min(n, len(dc["L"]))
        schemes["zmfull+chi"] = schemes["zmfull"][:m] + dc["dC4chi"][:m]
        P(f"# chi shift overlap check (dchi_L600 vs {os.path.basename(fd)}): "
          + (f"{np.max(np.abs(np.load(os.path.join(R, 'dchi_L600.npz'))['dC4chi'][:290] - dc['dC4chi'][:290])):.1e}"
             if os.path.exists(os.path.join(R, 'dchi_L600.npz')) else "n/a"))
    # ---------------------------------------------------------------- exact windows
    Lw = w["L"].astype(float)
    P("\n== 1. Exact window shifts to L = 8000 (cancellation-free; residual = max fit residual)")
    for name, y, names in (
            ("Delta_cons", w["Dcons"], ["L^2", "L^1", "L^0.5", "l1*L^0", "1"] + F.tower([-0.5, -1, -1.5, -2])),
            ("Delta_zm", w["Dzm"], ["L^1", "l1*L^0.5", "L^0.5", "l1*L^0", "1"]
             + F.tower([-0.5, -1, -1.5], {-0.5: 1, -1: 1})),
            ("Delta_off", o["off"], ["L^1", "l1*L^0.5", "L^0.5", "l1*L^0", "1"]
             + F.tower([-0.5, -1, -1.5], {-0.5: 1, -1: 1}))):
        for Lmin in (800, 1600):
            c, res, k = F.fit(Lw, y, names, Lmin)
            P(f"  {name:10s} Lmin={Lmin:5d} res={res:.0e}  " + " ".join(f"{a}={b:.9g}" for a, b in list(c.items())[:5]))
    # ---------------------------------------------------------------- C2, C3
    P("\n== 2. C2, C3 (full engine) -> continuum")
    c, res, _ = F.fit(Lw, w["C2"], ["1"] + F.tower([-1.5, -2, -2.5, -3, -3.5]), 1000)
    P(f"  C2: limit - exact = {c['1'] - F.C2_EXACT:+.1e} (L <= 8000, tower L^-3/2..L^-7/2; res {res:.0e}); "
      f"C2(8000) - exact = {w['C2'][-1] - F.C2_EXACT:+.3e}")
    for Lmin in (100, 200, 300):
        if Lmin + 100 > L[-1]:
            continue
        c, res, _ = F.fit(L, d["C3"], ["1"] + F.tower([-1, -1.5, -2, -2.5, -3], {-1: 1, -1.5: 1}), Lmin)
        P(f"  C3: Lmin={Lmin} limit - exact = {c['1'] - F.C3_EXACT:+.2e} res {res:.0e}")
    # ---------------------------------------------------------------- C4: complete window W = zmfull + chi
    T4 = F.tower([-1, -1.5, -2, -2.5], {-1: 1, -1.5: 1})
    fams = {"T4": T4, "T4a (+L^-3)": F.tower([-1, -1.5, -2, -2.5, -3], {-1: 1, -1.5: 1}),
            "T4c (+lnL/L^2)": F.tower([-1, -1.5, -2, -2.5], {-1: 1, -1.5: 1, -2: 1}),
            "T4d (short)": F.tower([-1, -1.5, -2], {-1: 1, -1.5: 1}),
            "T1 (with L^-1/2)": F.tower([-0.5, -1, -1.5, -2], {-0.5: 1, -1: 1})}
    rows = []
    if "zmfull+chi" in schemes:
        y = schemes["zmfull+chi"]
        LL = L[:len(y)]
        P(f"\n== 3. Complete window W = zmfull + chi (leading order): C4(L={int(LL[-1])}) = {y[-1]:.10f}")
        P("   limit A - C4(3) in units of 1e-6, by tower and fit window Lmin..Lmax")
        for fname, tw in fams.items():
            line = []
            for Lmin in (80, 100, 150, 200, 250, 300):
                for Lmx in (500, int(LL[-1])):
                    if Lmin + 150 > Lmx:
                        continue
                    c, res, k = F.fit(LL, y, ["1"] + tw, Lmin, Lmax=Lmx)
                    line.append(f"{Lmin}-{Lmx}:{(c['1'] - F.C4_EXACT) * 1e6:+.1f}")
                    rows.append(dict(scheme="W", family=fname, Lmin=Lmin, Lmax=Lmx, A=c["1"], res=res))
            P(f"   {fname:18s} " + " ".join(line))
        for fname in fams:
            c, res, k = F.fit(LL, y, ["1"] + fams[fname], 150, Lmax=400)
            sel = LL > 400
            P(f"   blind {fname:18s} fit 150..400: A - C4(3) = {(c['1'] - F.C4_EXACT):+.1e}; "
              f"max |pred - data| for 400 < L <= {int(LL[-1])}: {np.max(np.abs(F.predict(c, LL[sel]) - y[sel])):.1e}")
        P("   A fixed at C4(3), one free divergent term b (tower T4):")
        for extra in ("l1*L^0", "L^0.5", "l1*L^0.5", "L^1"):
            out_ = []
            for Lmin in (100, 200, 300):
                c, res, k = F.fit(LL, y - F.C4_EXACT, [extra] + T4, Lmin)
                out_.append(f"Lmin={Lmin}: b={c[extra]:+.2e} (res {res:.0e})")
            P(f"     {extra:10s} " + " | ".join(out_))
        # the chi window removes exactly the residual sqrt(L) of the zero-mode scheme
        zf = schemes["zmfull"]
        P("   zmfull alone, A + b sqrt(L) + T4 (compare -[sqrt(L) coefficient of the chi shift]):")
        for Lmin in (100, 150, 200):
            c, res, k = F.fit(L, zf, ["1", "L^0.5"] + T4, Lmin)
            P(f"     Lmin={Lmin}: A={c['1']:.6f} b={c['L^0.5']:+.5e} res {res:.0e}")
        cc, res, k = F.fit(dc["L"].astype(float), dc["dC4chi"], ["L^0.5", "l1*L^0", "1"] + F.tower([-0.5, -1]), 300,
                           Lmax=980)
        P(f"     chi shift (L <= 1000): sqrt(L) coefficient {cc['L^0.5']:+.5e}")
    # ---------------------------------------------------------------- divergences of the package schemes
    P("\n== 4. Large-L form of each scheme (W converges to C4(3); the others differ from W by exact window shifts):")
    P("   C4_zmfull = C4_W - chi;  C4_zm = C4_zmfull - Delta_off;  C4_cons = C4_zm - Delta_zm;  C4_raw = C4_cons - Delta_cons")
    for sname, y in schemes.items():
        LL = L[:len(y)]
        P(f"   {sname:11s} C4(L={int(LL[-1])}) = {y[-1]:+.8f}")
    with open(os.path.join(HERE, "fits", "fit_summary.txt"), "w") as f:
        f.write("\n".join(out) + "\n")
    if rows:
        with open(os.path.join(HERE, "fits", "fit_table.csv"), "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
    with open(os.path.join(HERE, "C4_by_L.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        cols = ["L", "C2", "C3", "C4_raw", "C4_consistent", "Delta_cons", "C4_zm", "C4_zmfull"] + \
               (["C4_W"] if "zmfull+chi" in schemes else [])
        wr.writerow(cols)
        for j in range(n):
            row = [int(L[j]), f"{d['C2'][j]:.16g}", f"{d['C3'][j]:.16g}", f"{d['C4raw'][j]:.16g}",
                   f"{d['C4cons'][j]:.16g}", f"{w['Dcons'][j]:.16g}", f"{schemes['zm'][j]:.16g}",
                   f"{schemes['zmfull'][j]:.16g}"]
            if "zmfull+chi" in schemes:
                row.append(f"{schemes['zmfull+chi'][j]:.16g}" if j < len(schemes["zmfull+chi"]) else "")
            wr.writerow(row)


if __name__ == "__main__":
    main()
