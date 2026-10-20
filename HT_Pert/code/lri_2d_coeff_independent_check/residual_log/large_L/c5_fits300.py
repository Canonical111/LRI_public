#!/usr/bin/env python3
"""(B) with raw C_5 to L = 300 (results/c5_L300.npz from lib/prod5.py --raw_only, unmodified code):
  C_5^Wc(L) = raw + Wc shift (../results/eps5/dC5_L1000_all.npz), C_5^Wcs = C_5^Wc + delta^(3)(L) S(L) (exact delta).
Checks: raw L300 vs the L = 200 production run (overlap); tail-power selection with blind fits; free ln L coefficient
and no-log limit as functions of Lmax (120..300); blind tests fit <= 240 -> 242..300; profile in b; calibration on
C_4^W (true b = 0) and on C_4^W with injected logs at the same Lmax.  Writes fits/c5_fits300.txt.
usage: python3 c5_fits300.py"""
import csv
import glob
import os

import numpy as np

import c5_fits as cf

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "..", "results")
REF5, REF4 = cf.REF5, cf.REF4
T3 = [(3, 0, -1), (3, 1, -1), (3, 2, -1)]
T2 = [(2, 0, -1), (2, 1, -1), (2, 2, -1)]


def fit(L, y, cols, Lmin, Lmax, withlog):
    return cf.fit(L, y, cols, Lmin, Lmax, withlog)


def stats_by_lmax(L, y, towers, lmins_at, Lmaxes, ref):
    rows = []
    for Lmax in Lmaxes:
        b, A0 = [], []
        for tt in towers:
            cols = cf.tower(*tt)
            for m in lmins_at(Lmax):
                c1, _, _ = fit(L, y, cols, m, Lmax, True)
                c0, _, _ = fit(L, y, cols, m, Lmax, False)
                b.append(c1[1]); A0.append(c0[0])
        b, A0 = np.array(b), np.array(A0)
        rows.append((Lmax, np.median(b), b.min(), b.max(), np.median(A0) - ref, A0.min() - ref, A0.max() - ref))
    return rows


def blind(L, y, towers, lmins, Lfit, Lpred):
    sel = (L > Lfit) & (L <= Lpred)
    e0, e1, bb = [], [], []
    for tt in towers:
        cols = cf.tower(*tt)
        for m in lmins:
            c0, _, _ = fit(L, y, cols, m, Lfit, False)
            c1, _, _ = fit(L, y, cols, m, Lfit, True)
            e0.append(float(np.abs(cf.predict(c0, cols, L[sel], False) - y[sel]).max()))
            e1.append(float(np.abs(cf.predict(c1, cols, L[sel], True) - y[sel]).max()))
            bb.append(c1[1])
    return np.array(e0), np.array(e1), np.array(bb)


def profile(L, y, towers, lmins, Lfit, Lpred, bgrid):
    sel = (L > Lfit) & (L <= Lpred)
    med = []
    lg = np.log(np.maximum(L, 1.0))
    for b in bgrid:
        es = []
        yy = y - b * lg
        for tt in towers:
            cols = cf.tower(*tt)
            for m in lmins:
                c, _, _ = fit(L, yy, cols, m, Lfit, False)
                es.append(float(np.abs(cf.predict(c, cols, L[sel], False) - yy[sel]).max()))
        med.append(np.median(es))
    med = np.array(med)
    i = int(np.argmin(med))
    ok = bgrid[med <= 2 * med[i]]
    return bgrid[i], med[i], ok.min(), ok.max()


def main():
    out = []
    p3 = np.load(os.path.join(HERE, "results", "c5_L300.npz"))
    p2 = np.load(os.path.join(R, "eps5", "c5_L200.npz"))
    d = np.load(os.path.join(R, "eps5", "dC5_L1000_all.npz"))
    s = np.load(os.path.join(R, "legw", "legw_L1000.npz"))
    tagf = sorted(glob.glob(os.path.join(HERE, "results", "tag3_L*.npz")), key=lambda f: int(os.path.basename(f)[6:-4]))[-1]
    t = np.load(tagf)
    L = p3["L"].astype(float)
    n = len(L)
    n2 = len(p2["L"])
    out.append(f"# c5_fits300.py: raw C_5 from results/c5_L300.npz (every even L <= {int(L.max())}); delta from {os.path.basename(tagf)}")
    for k in ("raw_C2", "raw_C3", "raw_C4", "raw_C5"):
        dd = np.abs(p3[k][:n2] - p2[k])
        rel = dd / np.maximum(np.abs(p2[k]), 1e-30)
        out.append(f"# overlap with the L = 200 production run, {k}: max |diff| {dd[1:].max():.1e}, max rel {rel[1:].max():.1e}")
    c5wc = p3["raw_C5"] + d["Wc_dC5"][:n]
    c5wcs = c5wc + t["delta3"][:n] * s["S"][:n]
    c4w = p3["raw_C4"] + d["Wb_dC4"][:n]
    out.append(f"# C_5^Wcs(300) = {c5wcs[-1]:.8f}, C_5^Wc(300) = {c5wc[-1]:.8f}, C_4^W(300) = {c4w[-1]:.10f}")
    rows = list(csv.DictReader(open(os.path.join(HERE, "..", "C4W_by_L.csv"))))
    L4 = np.array([float(r["L"]) for r in rows])
    c4cal = np.array([float(r["C4_W"]) for r in rows])
    m4 = (L4 >= 2) & (L4 <= L.max())
    L4, c4cal = L4[m4], c4cal[m4]
    lmins = (30, 40, 60, 80)
    # ---- 1. tail power, blind fit <= 240 -> 300
    out.append("\n== 1. tail structure: max ln power k1 of the 1/L tail (no-log, towers T(k1,1..2,-1), Lmin 40, 60, 80);"
               " blind fit <= 240 -> 242..300 (median max error) and A - exact at L <= 300")
    for nn, y, ref in ((4, c4w, REF4), (5, c5wcs, REF5)):
        row = []
        for k1 in range(0, 5):
            es, As = [], []
            for k2 in (1, 2):
                for m in (40, 60, 80):
                    cols = cf.tower(k1, k2, -1)
                    c, _, _ = fit(L, y, cols, m, 240, False)
                    sel = L > 240
                    es.append(float(np.abs(cf.predict(c, cols, L[sel], False) - y[sel]).max()))
                    c2, _, _ = fit(L, y, cols, m, L.max(), False)
                    As.append(c2[0] - ref)
            row.append((k1, np.median(es), np.median(As)))
        best = min(row, key=lambda r: r[1])[0]
        out.append(f"   C_{nn}: " + "  ".join(f"k1={k}: e={e:.1e} A-ex={a:+.1e}" for k, e, a in row) + f"  -> best k1 = {best}")
    # ---- 2. free ln L coefficient and no-log limit vs Lmax
    out.append("\n== 2. free ln L coefficient b (median [min, max]) and no-log limit A - exact (median [min, max]) vs Lmax;"
               " towers with the ln^3 L / L tail T(3,0..2,-1), Lmin 30, 40, 60, 80")
    Lmaxes = [x for x in (120, 140, 160, 180, 200, 220, 240, 260, 280, 300) if x <= L.max()]
    for lab, y, ref in (("C_5^Wcs", c5wcs, REF5), ("C_5^Wc", c5wc, REF5)):
        for (Lmax, bm, bl, bh, am, al, ah) in stats_by_lmax(L, y, T3, lambda x: lmins, Lmaxes, ref):
            out.append(f"   {lab:8s} Lmax={Lmax}: b {bm:+.4f} [{bl:+.4f}, {bh:+.4f}]   A-exact {am:+.5f} [{al:+.5f}, {ah:+.5f}]")
    out.append("   calibration: 7.7 C_4^W + 2 ln^3 L / L + beta ln L (same towers and Lmin)")
    for beta in (0.0, -0.01, -0.03):
        yy = 7.7 * c4cal + 2.0 * np.log(L4) ** 3 / L4 + beta * np.log(L4)
        for (Lmax, bm, bl, bh, am, al, ah) in stats_by_lmax(L4, yy, T3, lambda x: lmins, [x for x in Lmaxes if x >= 160], 7.7 * REF4):
            out.append(f"     beta={beta:+.2f} Lmax={Lmax}: b {bm:+.4f} [{bl:+.4f}, {bh:+.4f}]   A-exact {am:+.5f}")
    # ---- 3a. blind test fit <= 200 -> 202..300 by tower family k1 = 2, 3, 4
    out.append("\n== 3a. blind test: fit [Lmin, 200], predict 202..300; towers T(k1, 0..2, -1), Lmin 30, 40, 60, 80;"
               " median max error without (e0) and with (e1) a free ln L, free b (median [min, max]), no-log A - exact")
    for lab, y in (("C_5^Wcs", c5wcs), ("C_5^Wc", c5wc), ("C_4^W", c4w)):
        ref = REF4 if lab == "C_4^W" else REF5
        for k1 in (2, 3, 4):
            tws = [(k1, 0, -1), (k1, 1, -1), (k1, 2, -1)]
            e0, e1, bb = blind(L, y, tws, lmins, 200, 300)
            A = [fit(L, y, cf.tower(*tt), m, 200, False)[0][0] for tt in tws for m in lmins]
            out.append(f"   {lab:8s} k1={k1}: e0 {np.median(e0):.2e}  e1 {np.median(e1):.2e}  (no-log better in {int((e0 < e1).sum())}/{len(e0)});"
                       f" b {np.median(bb):+.4f} [{bb.min():+.4f}, {bb.max():+.4f}];  A(L<=200)-exact {np.median(A) - ref:+.5f}")
    # ---- 3. blind tests
    out.append("\n== 3. blind tests: fit [Lmin, Lfit], predict (Lfit, Lpred]: median max error no-log (e0) and free-log (e1)")
    for lab, y in (("C_5^Wcs", c5wcs), ("C_5^Wc", c5wc), ("C_4^W (c1 form)", c4w)):
        towers = T3 if lab.startswith("C_5") else T2
        for Lfit, Lpred in ((200, 300), (240, 300), (260, 300)):
            e0, e1, bb = blind(L, y, towers, lmins, Lfit, Lpred)
            out.append(f"   {lab:16s} fit <= {Lfit} -> {Lpred}: e0 {np.median(e0):.2e}  e1 {np.median(e1):.2e};"
                       f" no-log better in {int((e0 < e1).sum())}/{len(e0)}; b(free) median {np.median(bb):+.4f}")
    for beta in (-0.01, -0.03):
        yy = 7.7 * c4cal + 2.0 * np.log(L4) ** 3 / L4 + beta * np.log(L4)
        e0, e1, bb = blind(L4, yy, T3, lmins, 240, 300)
        out.append(f"   calib beta={beta:+.2f}       fit <= 240 -> 300: e0 {np.median(e0):.2e}  e1 {np.median(e1):.2e};"
                   f" no-log better in {int((e0 < e1).sum())}/{len(e0)}; b(free) median {np.median(bb):+.4f}")
    # ---- 4. profile in b
    out.append("\n== 4. profile in b (fit y - b ln L without log on [Lmin, 240], blind 242..300; factor-2 band)")
    bgrid = np.round(np.arange(-0.08, 0.0801, 0.0025), 6)
    for lab, LL, y, tw in (("C_5^Wcs", L, c5wcs, T3), ("C_5^Wc", L, c5wc, T3)):
        b0, e0, lo, hi = profile(LL, y, tw, lmins, 240, 300, bgrid)
        out.append(f"   {lab:8s} b* = {b0:+.4f} (median blind error {e0:.1e}); band [{lo:+.4f}, {hi:+.4f}]")
    for beta in (0.0, -0.01, -0.03):
        yy = 7.7 * c4cal + 2.0 * np.log(L4) ** 3 / L4 + beta * np.log(L4)
        b0, e0, lo, hi = profile(L4, yy, T3, lmins, 240, 300, bgrid)
        out.append(f"   calib beta={beta:+.2f}: b* = {b0:+.4f} (median blind error {e0:.1e}); band [{lo:+.4f}, {hi:+.4f}]")
    # ---- 5. final refit
    out.append("\n== 5. refit, L <= 300, no ln L, tail ln^0..3 L / L + ln^0..k2 L / L^2 (k2 = 0..2), Lmin 30, 40, 60, 80, 100")
    for lab, y in (("C_5^Wcs", c5wcs), ("C_5^Wc", c5wc)):
        A = []
        for tt in T3:
            for m in (30, 40, 60, 80, 100):
                c, _, _ = fit(L, y, cf.tower(*tt), m, L.max(), False)
                A.append(c[0])
        A = np.array(A)
        out.append(f"   {lab:8s} A = {np.median(A):.5f} +- {(A.max() - A.min()) / 2:.5f}  [{A.min():.5f}, {A.max():.5f}]"
                   f"  (median - exact {np.median(A) - REF5:+.5f})")
    txt = "\n".join(out)
    print(txt)
    open(os.path.join(HERE, "fits", "c5_fits300.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()
