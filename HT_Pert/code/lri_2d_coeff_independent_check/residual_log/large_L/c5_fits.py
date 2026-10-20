#!/usr/bin/env python3
"""(B) ln L in C_5^Wc / C_5^Wcs: refits with the exact delta^(3)(L), blind tests, and a calibration of the protocol on
C_4^W (whose limit and log-free form are known to L = 2000).

Inputs (read-only):
  ../results/eps5/c5_L200.npz           raw C_5(L), C_4(L), L <= 200 (exact, float)
  ../results/eps5/dC5_L1000_all.npz      scheme shifts (Wc, Zb, consistent, Wb), L <= 1000
  ../results/legw/legw_L1000.npz         S(L), L <= 1000 (C_5 response to (1/2) X at eps^3)
  results/tag3_L*.npz                    exact-to-float delta^(3)(L) from tagchan.py (largest file used)
  ../C4W_by_L.csv                        C_4^W(L), L <= 2000 (slope form of D^chi; calibration only)
Model families (linear least squares, columns scaled): A [+ b ln L] + tower, tower T(k1,k2,k3) = ln^0..k1 L / L,
ln^0..k2 L / L^2, ln^0..k3 L / L^3 (k = -1: none).
usage: python3 c5_fits.py   (writes fits/c5_fits.txt)"""
import csv
import glob
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "..", "results")
REF5, REF4 = -38.833645896225360553, 5.048868431354847
D3INF = -4.0 / (81.0 * np.pi)

TOWERS = {"T(2,0,-1)": (2, 0, -1), "T(2,1,-1)": (2, 1, -1), "T(2,2,-1)": (2, 2, -1), "T(3,0,-1)": (3, 0, -1),
          "T(3,1,-1)": (3, 1, -1), "T(3,2,-1)": (3, 2, -1), "T(2,2,0)": (2, 2, 0)}
SIMPLE = ["T(2,0,-1)", "T(2,1,-1)", "T(2,2,-1)"]
RICH = ["T(3,0,-1)", "T(3,1,-1)", "T(3,2,-1)", "T(2,2,0)"]


def tower(k1, k2, k3):
    return [(i, j) for j, k in ((1, k1), (2, k2), (3, k3)) for i in range(k + 1)]


def design(Ls, cols, withlog):
    l = np.log(Ls)
    X = [np.ones_like(Ls)] + ([l] if withlog else []) + [l ** i / Ls ** j for i, j in cols]
    return np.column_stack(X)


def fit(L, y, cols, Lmin, Lmax, withlog):
    sel = (L >= Lmin) & (L <= Lmax)
    X = design(L[sel], cols, withlog)
    sc = np.abs(X).max(axis=0)
    c, *_ = np.linalg.lstsq(X / sc, y[sel], rcond=None)
    c = c / sc
    return c, float(np.abs(y[sel] - X @ c).max()), int(sel.sum())


def predict(c, cols, Lp, withlog):
    return design(np.atleast_1d(np.asarray(Lp, float)), cols, withlog) @ c


def survey(L, y, ref, Lmax, lmins, towers, out, label):
    """A - ref and b for both families over towers x Lmin; returns arrays."""
    a0, a1, b1 = [], [], []
    for tn in towers:
        cols = tower(*TOWERS[tn])
        for m in lmins:
            npar = 2 + len(cols)
            if int(((L >= m) & (L <= Lmax)).sum()) < npar + 4:
                continue
            c0, _, _ = fit(L, y, cols, m, Lmax, False)
            c1, _, _ = fit(L, y, cols, m, Lmax, True)
            a0.append(c0[0] - ref)
            a1.append(c1[0] - ref)
            b1.append(c1[1])
    a0, a1, b1 = map(np.array, (a0, a1, b1))
    out.append(f"  {label:34s} no-log: A-ref {np.median(a0):+.5f} [{a0.min():+.5f}, {a0.max():+.5f}]   "
               f"free log: b median {np.median(b1):+.5f} [{b1.min():+.4f}, {b1.max():+.4f}], A-ref [{a1.min():+.3f}, {a1.max():+.3f}]")
    return a0, a1, b1


def blind(L, y, Lfit, Lpred, lmins, towers):
    """fit L in [Lmin, Lfit], predict every L in (Lfit, Lpred]; returns per (tower, Lmin): (err no-log, err free-log,
    b) with err = max |prediction - data| over the prediction range."""
    res = []
    selp = (L > Lfit) & (L <= Lpred)
    for tn in towers:
        cols = tower(*TOWERS[tn])
        for m in lmins:
            c0, _, _ = fit(L, y, cols, m, Lfit, False)
            c1, _, _ = fit(L, y, cols, m, Lfit, True)
            e0 = float(np.abs(predict(c0, cols, L[selp], False) - y[selp]).max())
            e1 = float(np.abs(predict(c1, cols, L[selp], True) - y[selp]).max())
            res.append((tn, m, e0, e1, c1[1], c0[0], c1[0]))
    return res


REFS = {2: 0.308065413582197915296547609537, 3: -0.874850012652633689512263602361, 4: REF4, 5: REF5}


def tail_section(out, L, p, c5wcs, c5wc, c4w, L4, c4):
    """4a: maximal ln power k1 of the 1/L tail of C_n (blind fit <= 160 -> 200, no-log, towers T(k1, k2, -1));
    4b: with the selected tail, free ln L vs no ln L (blind tests, b ranges, A); 4c: profile in b (fit y - b ln L
    without log; blind error vs b), calibrated by injection on 7.7 C_4^W."""
    out.append("\n== 4a. tail structure: max ln power k1 in the 1/L tail; no-log fits A + T(k1,k2,-1), blind fit [Lmin,160] -> 162..200")
    out.append("   entry: blind max error e (median over Lmin 40, 60, 80) and A - exact at L <= 200 (median)")
    series = {2: p["raw_C2"], 3: p["raw_C3"], 4: c4w, 5: c5wcs}
    best = {}
    for nn, y in series.items():
        row = []
        for k1 in range(0, 5):
            es, As = [], []
            for k2 in (1, 2):
                for m in (40, 60, 80):
                    cols = tower(k1, k2, -1)
                    c, _, _ = fit(L, y, cols, m, 160, False)
                    sel = L > 160
                    es.append(float(np.abs(predict(c, cols, L[sel], False) - y[sel]).max()))
                    c2, _, _ = fit(L, y, cols, m, 200, False)
                    As.append(c2[0] - REFS[nn])
            row.append((k1, float(np.median(es)), float(np.median(As))))
        best[nn] = min(row, key=lambda r: r[1])[0]
        out.append(f"   C_{nn}: " + "  ".join(f"k1={k}: e={e:.1e} A-ex={a:+.1e}" for k, e, a in row) + f"   -> best k1 = {best[nn]}")
    # ---- 4b
    out.append("\n== 4b. C_5 with the ln^3 L / L tail (towers T(3,0,-1), T(3,1,-1), T(3,2,-1); Lmin 30..80):"
               " no-log vs free-log")
    T3 = [(3, 0, -1), (3, 1, -1), (3, 2, -1)]
    for lab, y in (("C_5^Wcs", c5wcs), ("C_5^Wc", c5wc)):
        for Lfit in (140, 160, 180):
            e0s, e1s, bs = [], [], []
            for tt in T3:
                cols = tower(*tt)
                for m in (30, 40, 60, 80):
                    c0, _, _ = fit(L, y, cols, m, Lfit, False)
                    c1, _, _ = fit(L, y, cols, m, Lfit, True)
                    sel = L > Lfit
                    e0s.append(float(np.abs(predict(c0, cols, L[sel], False) - y[sel]).max()))
                    e1s.append(float(np.abs(predict(c1, cols, L[sel], True) - y[sel]).max()))
                    bs.append(c1[1])
            e0s, e1s, bs = map(np.array, (e0s, e1s, bs))
            out.append(f"   {lab:8s} blind fit <= {Lfit} -> 200: median e(no log) {np.median(e0s):.2e}, e(free log) {np.median(e1s):.2e};"
                       f" no-log better in {int((e0s < e1s).sum())}/{len(e0s)}; b(free) median {np.median(bs):+.4f} [{bs.min():+.4f}, {bs.max():+.4f}]")
        A0, A1, B1 = [], [], []
        for tt in T3:
            cols = tower(*tt)
            for m in (30, 40, 60, 80):
                c0, _, _ = fit(L, y, cols, m, 200, False)
                c1, _, _ = fit(L, y, cols, m, 200, True)
                A0.append(c0[0]); A1.append(c1[0]); B1.append(c1[1])
        A0, A1, B1 = map(np.array, (A0, A1, B1))
        out.append(f"   {lab:8s} L <= 200: no-log A = {np.median(A0):.5f} [{A0.min():.5f}, {A0.max():.5f}] (median - exact {np.median(A0) - REF5:+.5f});"
                   f"  free log: b median {np.median(B1):+.4f} [{B1.min():+.4f}, {B1.max():+.4f}], A [{A1.min():.3f}, {A1.max():.3f}]")
    # ---- 4c profile in b
    out.append("\n== 4c. profile in b: fit y - b ln L with A + tower (no further log) on [Lmin, 160], blind error on 162..200;"
               " b* = argmin of the median blind error")
    bgrid = np.round(np.arange(-0.08, 0.0801, 0.0025), 6)

    def profile(LL, y, towers, lmins):
        med = []
        for b in bgrid:
            es = []
            for tt in towers:
                cols = tower(*tt)
                for m in lmins:
                    yy = y - b * np.log(np.maximum(LL, 1.0))
                    c, _, _ = fit(LL, yy, cols, m, 160, False)
                    sel = (LL > 160) & (LL <= 200)
                    es.append(float(np.abs(predict(c, cols, LL[sel], False) - yy[sel]).max()))
            med.append(np.median(es))
        med = np.array(med)
        i = int(np.argmin(med))
        # resolution: b range where the median error is within a factor 2 of the minimum
        ok = bgrid[med <= 2 * med[i]]
        return bgrid[i], med[i], ok.min(), ok.max(), med
    T2 = [(2, 0, -1), (2, 1, -1), (2, 2, -1)]
    for lab, LL, y, tws in (("C_5^Wcs, k1=3 towers", L, c5wcs, T3), ("C_5^Wc,  k1=3 towers", L, c5wc, T3),
                            ("C_5^Wcs, k1=2 towers (misspecified)", L, c5wcs, T2)):
        b0, e0, lo, hi, _ = profile(LL, y, tws, (30, 40, 60, 80))
        out.append(f"   {lab:38s} b* = {b0:+.4f} (median blind error {e0:.1e}); factor-2 band [{lo:+.4f}, {hi:+.4f}]")
    out.append("   calibration on y = 7.7 C_4^W + beta ln L (tail k1 = 2, towers T(2,0..2,-1)), L <= 200 only:")
    sel4 = L4 <= 200
    for beta in (0.0, -0.02, -0.04, +0.03):
        b0, e0, lo, hi, _ = profile(L4[sel4], 7.7 * c4[sel4] + beta * np.log(L4[sel4]), T2, (30, 40, 60, 80))
        out.append(f"     beta = {beta:+.3f}: b* = {b0:+.4f} (median blind error {e0:.1e}); factor-2 band [{lo:+.4f}, {hi:+.4f}]")
    out.append("   calibration with an extra ln^3 L / L term (tail k1 = 3) on y = 7.7 C_4^W + 2 ln^3 L / L + beta ln L, towers T(3,..):")
    for beta in (0.0, -0.03):
        yy = 7.7 * c4[sel4] + 2.0 * np.log(L4[sel4]) ** 3 / L4[sel4] + beta * np.log(L4[sel4])
        b0, e0, lo, hi, _ = profile(L4[sel4], yy, T3, (30, 40, 60, 80))
        out.append(f"     beta = {beta:+.3f}: b* = {b0:+.4f} (median blind error {e0:.1e}); factor-2 band [{lo:+.4f}, {hi:+.4f}]")


def main():
    out = []
    # ------------------------------------------------------------------ data
    p = np.load(os.path.join(R, "eps5", "c5_L200.npz"))
    d = np.load(os.path.join(R, "eps5", "dC5_L1000_all.npz"))
    s = np.load(os.path.join(R, "legw", "legw_L1000.npz"))
    tagf = sorted(glob.glob(os.path.join(HERE, "results", "tag3_L*.npz")),
                  key=lambda f: int(os.path.basename(f)[6:-4]))[-1]
    t = np.load(tagf)
    L = p["L"].astype(float)
    n = len(L)
    assert np.array_equal(d["L"][:n], p["L"]) and np.array_equal(s["L"][:n], p["L"]) and np.array_equal(t["L"][:n], p["L"])
    delta = t["delta3"][:n]
    S = s["S"][:n]
    c5wc = p["raw_C5"] + d["Wc_dC5"][:n]
    c5wcs = c5wc + delta * S
    c4w = p["raw_C4"] + d["Wb_dC4"][:n]
    out.append(f"# c5_fits.py: delta^(3) from {os.path.basename(tagf)}; C_5^Wcs = raw + Wc shift + delta(L) S(L), exact "
               f"(float) for every even L <= {int(L.max())}")
    out.append(f"# C_5^Wcs - C_5^Wc at L = 50, 100, 200: " + ", ".join(f"{(delta * S)[i]:+.6f}" for i in (25, 50, 100))
               + f";  delta_inf S_inf = {D3INF * 0.367187:+.6f}")
    out.append(f"# C_5^Wcs(200) = {c5wcs[100]:.8f}, C_5^Wc(200) = {c5wc[100]:.8f}")
    # ------------------------------------------------------------------ calibration data: C_4^W to L = 2000
    rows = list(csv.DictReader(open(os.path.join(HERE, "..", "C4W_by_L.csv"))))
    L4 = np.array([float(r["L"]) for r in rows])
    c4 = np.array([float(r["C4_W"]) for r in rows])
    m4 = L4 >= 2
    L4, c4 = L4[m4], c4[m4]
    lmins = (30, 40, 60, 80, 100, 120)
    # ------------------------------------------------------------------ 1. surveys
    out.append("\n== 1. extrapolation surveys, L <= Lmax (A - reference; b = free ln L coefficient)")
    out.append("   simple towers T(2,0..2,-1), Lmin 30..120; rich towers T(3,0..2,-1), T(2,2,0), Lmin 30..60")
    for lab, (LL, yy, ref) in (("C_5^Wcs", (L, c5wcs, REF5)), ("C_5^Wc", (L, c5wc, REF5))):
        for Lmax in (160, 180, 200):
            survey(LL, yy, ref, Lmax, lmins, SIMPLE, out, f"{lab} Lmax={Lmax} simple")
            survey(LL, yy, ref, Lmax, (30, 40, 60), RICH, out, f"{lab} Lmax={Lmax} rich")
    out.append("   calibration: C_4^W (no log, limit known)")
    for Lmax in (200, 300, 400, 600, 1000, 2000):
        sc = Lmax / 200.0
        lm = tuple(int(round(x * sc / 2) * 2) for x in lmins)
        survey(L4, c4, REF4, Lmax, lm, SIMPLE, out, f"C_4^W Lmax={Lmax} simple (Lmin x{sc:g})")
        survey(L4, c4, REF4, Lmax, lm, SIMPLE, out, f"C_4^W Lmax={Lmax} simple (Lmin 30..120)") if Lmax > 200 and False else None
    # scaled to C_5 magnitude
    out.append("   (C_5/C_4 ~ 7.7: the C_4^W ranges above scaled by 7.7 are the expected C_5 ranges for a log-free series with"
               " a C_4-like tail)")
    # ------------------------------------------------------------------ 2. blind tests
    out.append("\n== 2. blind tests: fit [Lmin, Lfit], predict (Lfit, Lpred]; max |prediction - exact|; e0 = no-log, e1 = free log")
    def blind_report(lab, LL, yy, Lfit, Lpred, lm, towers):
        r = blind(LL, yy, Lfit, Lpred, lm, towers)
        e0 = np.array([x[2] for x in r]); e1 = np.array([x[3] for x in r]); bb = np.array([x[4] for x in r])
        w0 = int((e0 < e1).sum())
        out.append(f"  {lab:44s} median e0 {np.median(e0):.2e}  e1 {np.median(e1):.2e};  no-log better in {w0}/{len(r)};"
                   f"  b(free) [{bb.min():+.4f}, {bb.max():+.4f}]")
        return r
    blind_report("C_5^Wcs fit <=160, predict 162..200", L, c5wcs, 160, 200, (30, 40, 60, 80), SIMPLE + RICH[:2])
    blind_report("C_5^Wcs fit <=140, predict 142..200", L, c5wcs, 140, 200, (30, 40, 60, 80), SIMPLE + RICH[:2])
    blind_report("C_5^Wc  fit <=160, predict 162..200", L, c5wc, 160, 200, (30, 40, 60, 80), SIMPLE + RICH[:2])
    blind_report("C_4^W   fit <=160, predict 162..200", L4, c4, 160, 200, (30, 40, 60, 80), SIMPLE + RICH[:2])
    for beta in (-0.03, -0.01, +0.01, +0.03):
        blind_report(f"C_4^W + {beta:+.2f}*7.7 ln L, fit <=160 -> 200", L4, c4 + beta * 7.7 * np.log(L4), 160, 200,
                     (30, 40, 60, 80), SIMPLE + RICH[:2])
    # ------------------------------------------------------------------ 3. injection test: recover a known log at L <= 200
    out.append("\n== 3. injection test on C_4^W (scaled x7.7 so that the tail has the size of C_5's): y = 7.7 C_4^W + beta ln L")
    for beta in (0.0, -0.02, -0.04):
        survey(L4, 7.7 * c4 + beta * np.log(L4), 7.7 * REF4, 200, lmins, SIMPLE, out, f"beta={beta:+.2f} Lmax=200 simple")
        survey(L4, 7.7 * c4 + beta * np.log(L4), 7.7 * REF4, 200, (30, 40, 60), RICH, out, f"beta={beta:+.2f} Lmax=200 rich")
    # ------------------------------------------------------------------ 4. tail structure and the ln L verdict
    tail_section(out, L, p, c5wcs, c5wc, c4w, L4, c4)
    # ------------------------------------------------------------------ 5. continuity with extrap_wcs.py, and Lmax stability
    out.append("\n== 5a. protocol of ../eps5/extrap_wc(s).py (towers t2..t6, Lmin 30, 40, 60, 80; median +- half range), exact delta(L)")
    TOW = {"t2": [(0, 1), (1, 1), (2, 1)], "t3": [(0, 1), (1, 1), (2, 1), (0, 2)], "t4": [(0, 1), (1, 1), (2, 1), (3, 1), (0, 2)],
           "t5": [(0, 1), (1, 1), (2, 1), (0, 2), (1, 2)], "t6": [(0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2)]}
    for lab, y in (("C_5^Wcs", c5wcs), ("C_5^Wc", c5wc)):
        for Lmax in (120, 140, 160, 180, 200):
            A = []
            for cols in TOW.values():
                for m in (30, 40, 60, 80):
                    c, _, _ = fit(L, y, cols, m, Lmax, False)
                    A.append(c[0])
            A = np.array(A)
            out.append(f"   {lab:8s} Lmax={Lmax}: A = {np.median(A):.5f} +- {(A.max() - A.min()) / 2:.5f}  (A - exact {np.median(A) - REF5:+.5f})")
    out.append("\n== 5b. Lmax stability of the no-log limit with the ln^3 L / L tail (T(3,0..2,-1), Lmin 30..80): median [min, max]")
    for lab, y in (("C_5^Wcs", c5wcs), ("C_5^Wc", c5wc)):
        for Lmax in (120, 140, 160, 180, 200):
            A = []
            for tt in ((3, 0, -1), (3, 1, -1), (3, 2, -1)):
                for m in (30, 40, 60, 80):
                    c, _, _ = fit(L, y, tower(*tt), m, Lmax, False)
                    A.append(c[0])
            A = np.array(A)
            out.append(f"   {lab:8s} Lmax={Lmax}: A = {np.median(A):.5f} [{A.min():.5f}, {A.max():.5f}]  (median - exact {np.median(A) - REF5:+.5f})")
    txt = "\n".join(out)
    print(txt)
    os.makedirs(os.path.join(HERE, "fits"), exist_ok=True)
    open(os.path.join(HERE, "fits", "c5_fits.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()
