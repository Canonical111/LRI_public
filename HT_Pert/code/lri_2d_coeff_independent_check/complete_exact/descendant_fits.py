#!/usr/bin/env python3
"""L dependence of the descendant-identity residuals R_n(L) (results/descendant_<scheme>_L<L>.json).
For each (scheme, descendant, order) the exact values at the largest available L are fitted (least squares, all
points L >= Lmin) with four models and the effective exponent p_eff = d ln|R|/d ln L of the last pair is given:
    decay : R = b/L + c/L^2            (identity restored as L -> inf)
    decayln: R = (b + c ln L)/L        (restored, with a log)
    const : R = a + b/L                (finite violation)
    log   : R = a + c ln L + b/L       (logarithmic growth)
    lin   : R = s L + a + c ln L       (linear growth)
The model with the smallest rms residual relative to max|R| is reported, together with the fitted large-L
coefficient. This is a descriptive diagnostic of 6-8 exact points, not an extrapolation with error bars.
usage: python3 descendant_fits.py [--Lmin 6] > results/descendant_fits.txt"""
import argparse, glob, json, math, os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")
MODELS = {
    "decay": lambda L: np.stack([1 / L, 1 / L ** 2], 1),
    "decayln": lambda L: np.stack([1 / L, np.log(L) / L], 1),
    "const": lambda L: np.stack([np.ones_like(L), 1 / L], 1),
    "log": lambda L: np.stack([np.ones_like(L), np.log(L), 1 / L], 1),
    "lin": lambda L: np.stack([L, np.ones_like(L), np.log(L)], 1),
}


def classify(Ls, vals):
    L = np.array(Ls, float)
    y = np.array(vals, float)
    scale = max(abs(y).max(), 1e-300)
    out = {}
    for name, f in MODELS.items():
        A = f(L)
        if A.shape[1] >= len(L):
            continue
        c, *_ = np.linalg.lstsq(A, y, rcond=None)
        rms = float(np.sqrt(np.mean((A @ c - y) ** 2)) / scale)
        out[name] = (rms, c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Lmin", type=int, default=6)
    a = ap.parse_args()
    files = glob.glob(os.path.join(R, "descendant_*_L*.json"))
    schemes = sorted({re.match(r"descendant_(.+)_L\d+\.json", os.path.basename(f)).group(1) for f in files})
    order = ["raw", "consistent", "zeromode", "complete2", "W", "W+V", "W2", "WnoM", "WM2", "WM3", "WB", "W+VB",
             "W2B", "WnoMB", "WM2B", "WM3B", "Wn", "W+Vn", "W2n"]
    schemes = [s for s in order if s in schemes]
    print(f"# fits over L >= {a.Lmin}; columns: scheme desc n | R(L_max) | p_eff(last pair) | best model "
          f"(rms/max|R|) and its coefficients; 'restored' = decay model best and |R| decreasing")
    summary = {}
    for s in schemes:
        Ls = sorted(int(re.search(r"_L(\d+)\.json", f).group(1)) for f in glob.glob(os.path.join(R, f"descendant_{s}_L*.json")))
        D = {L: json.load(open(os.path.join(R, f"descendant_{s}_L{L}.json")))["descendants"] for L in Ls}
        for dn in ("odd1", "odd2", "odd3", "even1", "even2"):
            Lh = [L for L in Ls if L >= a.Lmin and dn in D[L]]
            if len(Lh) < 4:
                continue
            first_bad = None
            for n in range(1, 9):
                vals = [D[L][dn]["residual_float"][n] for L in Lh]
                if any(v is None for v in vals):
                    print(f"{s:10s} {dn:5s} n={n}: incomplete")
                    continue
                if max(abs(v) for v in vals) == 0:
                    print(f"{s:10s} {dn:5s} n={n}: identically 0 for every L")
                    continue
                fits = classify(Lh, vals)
                best = min(fits, key=lambda k: fits[k][0])
                pe = (math.log(abs(vals[-1] / vals[-2])) / math.log(Lh[-1] / Lh[-2])
                      if vals[-1] * vals[-2] > 0 else float("nan"))
                # classification by the effective exponent of the last pair (fits are descriptive only)
                if math.isnan(pe):
                    cls = "sign change"
                elif pe <= -0.7:
                    cls = "restored (~1/L)"
                elif abs(pe) < 0.15:
                    cls = "constant"
                elif pe > 0.15:
                    cls = "grows"
                else:
                    cls = "slow decrease"
                restored = cls.startswith("restored")
                if not restored and first_bad is None:
                    first_bad = (n, cls)
                co = ", ".join(f"{x:+.4g}" for x in fits[best][1])
                print(f"{s:10s} {dn:5s} n={n}: R({Lh[-1]})={vals[-1]:+.5g}  p_eff={pe:+.2f}  best={best} "
                      f"({fits[best][0]:.1e}) [{co}]  -> {cls}")
            summary[(s, dn)] = first_bad
            print(f"{s:10s} {dn:5s} first order not restored: {first_bad}")
    print("\n# summary: first order whose residual is not restored (L >= %d; rule: p_eff of the last pair <= -0.7)" % a.Lmin)
    for (s, dn), n in summary.items():
        print(f"{s:10s} {dn:5s} {n}")


if __name__ == "__main__":
    main()
