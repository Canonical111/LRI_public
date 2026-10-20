#!/usr/bin/env python3
"""Large-L asymptotics of C_4(L) in the raw, consistent and corrected schemes.

Inputs: results/c4_L<Lmax>.npz (largest available), results/windows_L20000.npz.
Outputs: fits/fit_summary.txt (printed), fits/fit_table.csv (every fit), fits/blind_check.txt.

Models (l = ln L):
  corrected / consistent:  A + beta*l + sum_{j=1..J} sum_{k=0..K_j} a_jk l^k / L^j     ("log" family)
                           A +          sum ...                                          ("no-log" family)
  raw = consistent - Delta_cons, with Delta_cons = kappa L + lambda l + c + ... known exactly (windows.py);
  the raw fits use the same families plus a free kappa*L term.
The l^2/L coefficient has the RG prediction c2 = A2*omega1^2/2 = -5/pi (A2 = -40/(81 pi) from C_2, omega1 = 9/2
from C_3); fits are done with it free and fixed."""
import csv
import glob
import json
import os
import sys

import numpy as np

import fitlib as F

HERE = os.path.dirname(os.path.abspath(__file__))
REF4 = F.REF[4]
C2TH = -5.0 / np.pi

LOGM = {"log T22": ["1", "l"] + F.tower(2, 2),
        "log T232": ["1", "l"] + F.tower(2, 3, 2),
        "log T22+l3/L": ["1", "l", "l3/L"] + F.tower(2, 2),
        "log T332": ["1", "l"] + F.tower(3, 3, 2)}
NOLOGM = {"nolog T232": ["1"] + F.tower(2, 3, 2),
          "nolog T22+l3/L": ["1", "l3/L"] + F.tower(2, 2),
          "nolog T22+l4,l3/L": ["1", "l4/L", "l3/L"] + F.tower(2, 2),
          "nolog T333": ["1"] + F.tower(3, 3, 3)}


def load():
    files = sorted(glob.glob(os.path.join(HERE, "results", "c4_L*.npz")),
                   key=lambda f: int(f.split("_L")[-1].split(".")[0].split("_")[0]))
    files = [f for f in files if "local" not in f]
    big = files[-1]
    return np.load(big), os.path.basename(big), np.load(os.path.join(HERE, "results", "windows_L20000.npz"))


def main():
    out = []
    P = lambda s="": (out.append(s), print(s))
    d, name, w = load()
    L = d["L"].astype(float)
    Lmax = int(L[-1])
    P(f"# C_4 asymptotics from {name} (L = 0..{Lmax}) and windows_L20000.npz; reference C_4(2) = {REF4:.15f}")
    P(f"# RG prediction for the l^2/L coefficient: -5/pi = {C2TH:.6f}")
    rows = []

    # ------------------------------------------------------------------ windows
    P("\n== 1. Exact window shifts (L <= 20000, cancellation-free, windows.py)")
    Lw = w["L"].astype(float)
    for Lmin in (500, 2000):
        c, mr, n = F.fit(Lw, w["Delta_cons"], ["L", "l", "1"] + F.tower(2, 2), Lmin)
        P(f"  Delta_cons = C4cons - C4raw: Lmin={Lmin}: kappa={c['L']:.12e} lambda={c['l']:.9f} const={c['1']:.9f}"
          f" maxres={mr:.0e}")
    P(f"      (analytic, continuum/: kappa = 2.20729299645267e-4, lambda = -40/(81*864*pi) = {-40/(81*864*np.pi):.9f})")
    for key in ["Delta_zm"] + [f"Delta_zm_m{m}" for m in range(1, 5)]:
        c, mr, n = F.fit(Lw, w[key], ["l", "1"] + F.tower(2, 2), 2000)
        P(f"  {key:13s} = mu*l + nu + ...: mu={c['l']:.11f} nu={c['1']:.11f} maxres={mr:.0e}")
    P(f"      (m=2: 4/(81 pi) = {4/(81*np.pi):.11f})")
    cmu, _, _ = F.fit(Lw, w["Delta_zm"], ["l", "1"] + F.tower(2, 2), 2000)
    MU, NU = cmu["l"], cmu["1"]

    # ------------------------------------------------------------------ main fits
    for key in ("C4corr", "C4cons", "C4raw"):
        P(f"\n== 2. {key}: fits A + [beta*l] + tower (+ kappa*L for raw), windows L in [Lmin, {Lmax}]")
        y = d[key]
        fams = [("log", LOGM, False), ("log, c2=-5/pi", {k: v for k, v in LOGM.items()}, True),
                ("nolog", NOLOGM, False)]
        for fam, models, fixc2 in fams:
            for mname, names in models.items():
                nn = list(names) + (["L"] if key == "C4raw" else [])
                fixed = None
                if fixc2:
                    nn = [x for x in nn if x != "l2/L"]
                    fixed = {"l2/L": C2TH}
                vals = []
                for Lmin in (100, 200, 300, 400):
                    if Lmin > Lmax / 2:
                        continue
                    c, mr, n = F.fit(L, y, nn, Lmin, None, fixed)
                    rows.append(dict(scheme=key, family=fam, model=mname, Lmin=Lmin, Lmax=Lmax,
                                     A=c["1"], beta=c.get("l", 0.0), c2=c.get("l2/L", C2TH if fixc2 else np.nan),
                                     kappa=c.get("L", np.nan), maxres=mr, npts=n))
                    vals.append(f"{Lmin}:{c['1']:.5f}" + (f"[b{c['l']:+.5f}]" if "l" in c else "")
                                + (f"[k{c['L']:.4e}]" if "L" in c else "") + f" r{mr:.0e}")
                P(f"  {fam:14s} {mname:18s} " + "  ".join(vals))
    with open(os.path.join(HERE, "fits", "fit_table.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    # ------------------------------------------------------------------ out-of-sample test
    P(f"\n== 3. Out-of-sample test: fit on [200, Lcut], predict (Lcut, {Lmax}]")
    for Lcut in sorted(set([600, 1000, Lmax // 2])):
        if Lcut >= Lmax:
            continue
        for key in ("C4corr",):
            for mname, names in list(LOGM.items())[:2] + list(NOLOGM.items()):
                c, mr, n = F.fit(L, d[key], names, 200, Lcut)
                sel = L > Lcut
                X = np.column_stack([F.basis(k, L[sel]) for k in names])
                err = X @ np.array([c[k] for k in names]) - d[key][sel]
                P(f"  {key} Lcut={Lcut:5d} {mname:18s} max|pred-data| = {np.abs(err).max():.1e}  A={c['1']:.5f}")

    # ------------------------------------------------------------------ blind predictions (made before the L=2000 run)
    bp = os.path.join(HERE, "fits", "blind_predictions_L1200_2000.json")
    if os.path.exists(bp) and Lmax >= 2000:
        b = json.load(open(bp))
        P(f"\n== 4. Blind predictions recorded {b['made']} from L <= 1000 vs the L = {Lmax} run")
        for key, preds in b["pred"].items():
            for mname, pv in preds.items():
                diffs = [pv[i] - d[key][int(x) // 2] for i, x in enumerate(b["L"])]
                P(f"  {key:7s} {mname:20s} pred-data at L=" + " ".join(f"{int(x)}:{v:+.1e}" for x, v in zip(b["L"], diffs)))

    # ------------------------------------------------------------------ summary numbers
    P("\n== 5. Summary. Stable set: models {log T22, log T22+l3/L} x {c2 free, c2 = -5/pi} x Lmin in"
      " {200, 300, 400}; quoted value = median, uncertainty = half the full spread (all fits shown above)")
    cdc, _, _ = F.fit(Lw, w["Delta_cons"], ["L", "l", "1"] + F.tower(2, 2), 2000)
    summ = {}
    for key in ("C4corr", "C4cons"):
        sel = [r for r in rows if r["scheme"] == key and r["family"].startswith("log")
               and r["model"] in ("log T22", "log T22+l3/L") and r["Lmin"] >= 200]
        A = np.array([r["A"] for r in sel])
        B = np.array([r["beta"] for r in sel])
        summ[key] = (np.median(A), (A.max() - A.min()) / 2, np.median(B), (B.max() - B.min()) / 2)
        P(f"  {key:7s}: C4(L) = A + beta ln L + O(ln^2 L / L):  beta = {np.median(B):+.6f} +- {(B.max()-B.min())/2:.6f},"
          f"  A = {np.median(A):.5f} +- {(A.max()-A.min())/2:.5f}   ({len(sel)} fits)")
    A, dA, B, dB = summ["C4cons"]
    P(f"  C4raw  : = C4cons - Delta_cons exactly, Delta_cons = kappa L + lambda ln L + c + ... (exact windows):"
      f"  C4raw(L) = {A - cdc['1']:.5f} - {cdc['L']:.10e} L + ({B - cdc['l']:+.6f}) ln L + O(ln^2 L/L)")
    nsel = {key: np.array([r["A"] for r in rows if r["scheme"] == key and r["family"] == "nolog" and r["Lmin"] >= 200])
            for key in ("C4corr", "C4cons")}
    for key, An in nsel.items():
        P(f"  {key:7s} no-log fits (disfavoured, sec. 3/4): A from {An.min():.4f} to {An.max():.4f}")
    P(f"  beta_corr - beta_cons = {summ['C4corr'][2] - summ['C4cons'][2]:.6f};  mu (exact windows) = {MU:.10f}")
    P(f"  candidates: -8/(243 pi) = {-8/(243*np.pi):.7f} (= -(2/3) * 4/(81 pi)),  -1/(12 pi) = {-1/(12*np.pi):.7f}")
    with open(os.path.join(HERE, "fits", "fit_summary.txt"), "w") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
