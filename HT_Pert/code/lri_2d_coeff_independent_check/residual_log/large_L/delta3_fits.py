#!/usr/bin/env python3
"""(A) large-L asymptotics of delta^(3)(L) from the tagchan.py outputs (results/tag3_L*.npz, results/tag3nu_L*.npz).
Writes fits/delta3_fits.txt.  Local, fits of existing data only."""
import glob
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D3 = -4.0 / (81.0 * np.pi)
EXACT = {2: -73 / 7776, 4: -15071 / 1105920, 6: -19800685 / 1337720832, 8: -3988698385 / 260919263232,
         10: -4402468441 / 283467841536, 12: -12093335756425 / 771857162698752,
         14: -698270312137541 / 44332308831928320, 16: -17345700448126303825 / 1097581272385718321152}


def basis(n, L):
    l = np.log(L)
    return {"1": np.ones_like(L), "l/L": l / L, "1/L": 1 / L, "l2/L": l * l / L, "l2/L2": l * l / L ** 2,
            "l/L2": l / L ** 2, "1/L2": 1 / L ** 2, "1/L3": 1 / L ** 3, "l/L3": l / L ** 3}[n]


def fit(L, y, names, Lmin, Lmax, fixed=None):
    m = (L >= Lmin) & (L <= Lmax)
    Ls, ys = L[m], y[m].copy()
    if fixed is not None:
        ys = ys - fixed
    X = np.column_stack([basis(n, Ls) for n in names])
    sc = np.abs(X).max(axis=0)
    c, *_ = np.linalg.lstsq(X / sc, ys, rcond=None)
    c = c / sc
    return dict(zip(names, c)), float(np.abs(ys - X @ c).max())


def pred(c, Lp):
    return sum(v * basis(k, np.atleast_1d(float(Lp)))[0] for k, v in c.items())


def main():
    files = sorted(glob.glob(os.path.join(HERE, "results", "tag3_L*.npz")), key=lambda f: int(os.path.basename(f)[6:-4]))
    big = np.load(files[-1])
    L = big["L"].astype(float)
    y = big["delta3"]
    Lmax = int(L.max())
    out = [f"# delta3_fits.py: delta^(3)(L) from {os.path.basename(files[-1])} (every even L <= {Lmax}); -4/(81 pi) = {D3:.15f}"]
    # ---- consistency between runs of different Lmax (same L)
    for f in files[:-1]:
        d = np.load(f)
        n = len(d["L"])
        out.append(f"# {os.path.basename(f)} vs {os.path.basename(files[-1])}: max |diff| over L <= {int(d['L'][-1])} = "
                   f"{np.max(np.abs(d['delta3'][1:] - y[1:n])):.1e}")
    out.append("\n== exact values (L <= 16) vs tagchan")
    for Lv, ex in EXACT.items():
        out.append(f"  L={Lv:3d}  exact {ex:+.15f}  tagchan {y[Lv // 2]:+.15f}  diff {y[Lv // 2] - ex:+.1e}")
    out.append("\n== delta^(3)(L) at large L")
    for Lv in (16, 20, 30, 40, 50, 60, 80, 100, 200, 400, 1000, 2000, 4000, 8000, 16000, 32000):
        if Lv <= Lmax:
            out.append(f"  L={Lv:6d}  delta = {y[Lv // 2]:+.13f}   delta - (-4/(81 pi)) = {y[Lv // 2] - D3:+.3e}")
    i0 = int(np.argmin(y[1:])) + 1
    out.append(f"  minimum at L = {int(L[i0])}: delta = {y[i0]:+.10f} (non-monotonic: the L <= 16 data are on the descending branch)")
    # ---- free-limit fits
    out.append("\n== free-limit fits d + tail, Lmin..Lmax; d - (-4/(81 pi)) shown")
    towers = [["1", "1/L", "1/L2"], ["1", "l/L", "1/L"], ["1", "l/L", "1/L", "1/L2"], ["1", "l/L", "1/L", "l/L2", "1/L2"],
              ["1", "l2/L", "l/L", "1/L", "1/L2"], ["1", "l/L", "1/L", "l2/L2", "l/L2", "1/L2"],
              ["1", "l/L", "1/L", "l/L2", "1/L2", "l/L3", "1/L3"]]
    for t in towers:
        row = []
        for Lmin in (200, 400, 1000, 2000):
            if Lmin * 4 > Lmax:
                continue
            c, r = fit(L, y, t, Lmin, Lmax)
            row.append(f"Lmin={Lmin}: {c['1'] - D3:+.2e} (res {r:.0e})")
        out.append(f"  {'+'.join(t):28s} " + "  ".join(row))
    out.append("\n== blind tests: fit [Lmin, Lmax/4], predict L = Lmax")
    for t in towers:
        for Lmin in (100, 200):
            c, r = fit(L, y, t, Lmin, Lmax / 4)
            out.append(f"  {'+'.join(t):28s} Lmin={Lmin}: d - (-4/(81 pi)) = {c['1'] - D3:+.2e}; "
                       f"pred(L={Lmax}) - exact = {pred(c, Lmax) - y[-1]:+.2e}")
    # ---- with d fixed to -4/(81 pi)
    out.append("\n== limit fixed to -4/(81 pi): delta - d = e ln L / L + c / L + tail")
    for t in (["l/L", "1/L"], ["l/L", "1/L", "1/L2"], ["l/L", "1/L", "l/L2", "1/L2"], ["l2/L", "l/L", "1/L", "l/L2", "1/L2"]):
        for Lmin in (200, 1000):
            c, r = fit(L, y, t, Lmin, Lmax, fixed=D3)
            out.append(f"  {'+'.join(t):24s} Lmin={Lmin}: " + " ".join(f"{k}={v:+.7f}" for k, v in c.items()) + f"  res={r:.1e}")
    out.append(f"  compare: -1/(54 pi) = {-1 / (54 * np.pi):+.7f}")
    # ---- charges nu and single legs
    nf = sorted(glob.glob(os.path.join(HERE, "results", "tag3nu_L*.npz")), key=lambda f: int(os.path.basename(f)[8:-4]))
    if nf:
        d = np.load(nf[-1])
        Ln = d["L"].astype(float)
        Lm = int(Ln.max())
        out.append(f"\n== per-unit leg response for symmetric charges nu ({os.path.basename(nf[-1])}):"
                   f" delta_nu = (1/(2 nu)) [c_1^(3)(L - nu; L) - c1tag^(3)(L; nu, nu)]")
        nus = sorted(int(k[9:]) for k in d.files if k.startswith("delta3_nu"))
        for nu in [2] + nus:
            yy = d["delta3"] if nu == 2 else d[f"delta3_nu{nu}"]
            vals = "  ".join(f"L={Lv}: {yy[Lv // 2]:+.9f}" for Lv in (16, 100, 400, 1000, 2000, Lm) if Lv <= Lm)
            c, r = fit(Ln, yy, ["1", "l/L", "1/L", "l/L2", "1/L2"], 200, Lm)
            c2, r2 = fit(Ln, yy, ["1", "l/L", "1/L", "1/L2"], 400, Lm)
            out.append(f"  nu={nu:2d}: {vals}\n         limit (l/L,1/L,l/L2,1/L2; Lmin 200): {c['1']:+.10f} (- (-4/(81 pi)) = {c['1'] - D3:+.1e});"
                       f" (l/L,1/L,1/L2; Lmin 400): {c2['1']:+.10f}; ln L/L coeff {c['l/L']:+.5f}")
        if "c1tag3_in" in d.files:
            # single legs: d = r - c_1'/2, r = [c_1(L) - c1tag(L; 2,0 or 0,2)] / 2, c_1' = [c_1(L) - c_1(L - 2; L)] / 2
            c1L = d["c1_3_L"]
            c1p = (c1L - d["c1_3_Lm2"]) / 2.0
            din = (c1L - d["c1tag3_in"]) / 2.0 - c1p / 2.0
            dout = (c1L - d["c1tag3_out"]) / 2.0 - c1p / 2.0
            cross = (c1L - d["c1tag3"]) - (c1L - d["c1tag3_in"]) - (c1L - d["c1tag3_out"])
            out.append("\n== single legs: d_in, d_out (README Sec. 11.2 definition) and the (2,2) cross term")
            for Lv in (6, 8, 10, 12, 100, 400, 1000, 2000, Lm):
                if Lv <= Lm:
                    i = Lv // 2
                    out.append(f"  L={Lv:5d}: d_in {din[i]:+.9f}  d_out {dout[i]:+.9f}  d_in - d_out {din[i] - dout[i]:+.2e}"
                               f"  cross {cross[i]:+.9f}  (d_in + d_out)/2 + cross/4 = {(din[i] + dout[i]) / 2 + cross[i] / 4:+.9f}")
            for nm, yy in (("d_in", din), ("d_out", dout), ("cross", cross)):
                c, r = fit(Ln, yy, ["1", "l/L", "1/L", "l/L2", "1/L2"], 200, Lm)
                out.append(f"  {nm:6s} limit {c['1']:+.10f}  (ln L/L coeff {c['l/L']:+.5f}, res {r:.0e})")
            c0 = d["c1tag3_00"] - c1L
            out.append(f"  check c1tag^(3)(L; 0, 0) - c_1^(3)(L): max |.| over L <= {Lm} = {np.max(np.abs(c0)):.1e}")
    txt = "\n".join(out)
    print(txt)
    os.makedirs(os.path.join(HERE, "fits"), exist_ok=True)
    open(os.path.join(HERE, "fits", "delta3_fits.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()
