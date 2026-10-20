"""Meromorphic Chebyshev quadrature weights for c6sum (same formulas and layout as reference/prepare.py).

For every (axis j, bucket b2, Laurent order r = -1..5, node i) the weight integrates t^{a+eps*b2/2} times the
degree-N Chebyshev-Lobatto interpolant of a smooth factor, with a = L-2-j-b2/2 and the eps-expansion of
1/(a+k+1+eps*b2/2). Writes

  w_{L}_{N}.bin     float64, shape (L-1, 2L+1, 7, N+1), C order (read by the double engine);
  w_{L}_{N}.dd.bin  float64 pairs (hi, lo) with hi+lo equal to the weight to about 1e-32 (reference engine).
Entries below 10^(-dps/2) in magnitude are exact zeros of the formulas computed as ~10^-dps residuals; they are
stored as 0. reference/prepare.py stores the 80-digit residuals (~1e-80) instead; every other entry agrees bitwise.

Usage: python weights.py OUTDIR L N[,N...] [--dps 100] [--check]
OUTDIR/weights_manifest.json links each (L, N) to the SHA256 of its float64 and double-double files and the digits
used; assembly and rounding analysis require every level's weights hash to match this manifest.
--check integrates random degree-<=N polynomials p in mpmath and compares with the exact Laurent coefficients of
int_0^1 t^{a+eps b} p(t) dt, for every (axis, b2, r):
  forward error of the double-double weights: |Q_dd - exact| / max(|exact|, 1e-20 S) <= 1e-12   (formula check);
  rounding of the stored float64 weights:     |Q_64 - exact| / S                        <= 1e-15   (storage check),
where S = sum_i |w_i p(t_i)| measures the cancellation. Both worst values are reported.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import sys, json, random, argparse, hashlib
from pathlib import Path
import mpmath as mp
import numpy as np

MAXR = 5


def chebpoly(N):
    """Shifted Chebyshev polynomials T*_0..T*_N on [0,1] as integer monomial coefficient tuples.
    Identical recurrence to reference/lri_numerical_resolution/verification/source/ising_five_loop.chebpoly."""
    p = [(1,), (-1, 2)]
    for k in range(1, N):
        a = p[-1]; b = p[-2]
        c = [0] * (len(a) + 1)
        for i, v in enumerate(a):
            c[i] -= 2 * v; c[i + 1] += 4 * v
        for i, v in enumerate(b):
            c[i] -= v
        p.append(tuple(c))
    return p[:N + 1]


def weights(L, N, dps=100):
    """Return the weights as an mpmath nested list out[axis][b2][r+1][i] (exact to about dps digits)."""
    with mp.workdps(dps):
        pol = chebpoly(N)
        cx = [[mp.cos(mp.pi * k * i / N) for k in range(N + 1)] for i in range(N + 1)]
        out = [[[[mp.mpf(0)] * (N + 1) for _ in range(MAXR + 2)] for _ in range(2 * L + 1)] for _ in range(L - 1)]
        for axis in range(L - 1):
            for b2 in range(2 * L + 1):
                a2 = 2 * (L - 2 - axis) - b2; a = mp.mpf(a2) / 2; b = mp.mpf(b2) / 2
                jr = int(-a - 1) if a2 <= -2 and a2 % 2 == 0 else -1
                mom = []
                for poly in pol:
                    row = []
                    for r in range(-1, MAXR + 1):
                        if r == -1:
                            val = mp.mpf(poly[jr]) / b if 0 <= jr < len(poly) else mp.mpf(0)
                        else:
                            val = mp.fsum(mp.mpf(c) * (-b) ** r / (mp.mpf(k) + a + 1) ** (r + 1) for k, c in enumerate(poly) if k != jr)
                        row.append(val)
                    mom.append(row)
                for i in range(N + 1):
                    factor = mp.mpf(2) / N * (mp.mpf('.5') if i in (0, N) else 1)
                    for r in range(MAXR + 2):
                        out[axis][b2][r][i] = factor * mp.fsum((mp.mpf('.5') if k in (0, N) else 1) * cx[i][k] * mom[k][r] for k in range(N + 1))
                if jr == 0:
                    for i in range(N + 1):
                        out[axis][b2][0][i] = mp.mpf(0)
                    out[axis][b2][0][N] = 1 / b
        return out


def to_arrays(out, L, N, dps):
    hi = np.zeros((L - 1, 2 * L + 1, MAXR + 2, N + 1))
    dd = np.zeros((L - 1, 2 * L + 1, MAXR + 2, N + 1, 2))
    with mp.workdps(dps):
        for axis in range(L - 1):
            for b2 in range(2 * L + 1):
                for r in range(MAXR + 2):
                    for i in range(N + 1):
                        v = out[axis][b2][r][i]
                        if abs(v) < mp.mpf(10) ** (-(dps // 2)):
                            v = mp.mpf(0)  # mathematically zero weights appear as ~10^-dps residuals
                        h = float(v); lo = float(v - mp.mpf(h))
                        hi[axis, b2, r, i] = h; dd[axis, b2, r, i, 0] = h; dd[axis, b2, r, i, 1] = lo
    return hi, dd


def check(L, N, hi, dd, trials=3, seed=12345, dps=60):
    """Returns (worst forward error of the dd weights, worst scaled error of the float64 weights)."""
    rng = random.Random(seed * 1000 + 17 * L + N)
    worst_fwd = 0.0; worst_scaled = 0.0
    with mp.workdps(dps):
        nodes = [(1 + mp.cos(mp.pi * i / N)) / 2 for i in range(N + 1)]
        nodes[0] = mp.mpf(1); nodes[N] = mp.mpf(0)
        for axis in range(L - 1):
            for b2 in range(2 * L + 1):
                a2 = 2 * (L - 2 - axis) - b2; a = mp.mpf(a2) / 2; b = mp.mpf(b2) / 2
                for _ in range(trials):
                    coef = [mp.mpf(rng.randint(-1000, 1000)) / 997 for _ in range(N + 1)]
                    fvals = [mp.fsum(c * x ** k for k, c in enumerate(coef)) for x in nodes]
                    exact = [mp.mpf(0)] * (MAXR + 2)
                    for k, c in enumerate(coef):
                        s = a + k + 1
                        if s == 0:
                            exact[0] += c / b
                        else:
                            for r in range(MAXR + 1):
                                exact[r + 1] += c * (-b) ** r / s ** (r + 1)
                    for r in range(MAXR + 2):
                        t64 = [mp.mpf(hi[axis, b2, r, i]) * fvals[i] for i in range(N + 1)]
                        tdd = [(mp.mpf(dd[axis, b2, r, i, 0]) + mp.mpf(dd[axis, b2, r, i, 1])) * fvals[i] for i in range(N + 1)]
                        S = mp.fsum(abs(x) for x in t64)
                        if S == 0 and exact[r] == 0:
                            continue
                        worst_fwd = max(worst_fwd, float(abs(mp.fsum(tdd) - exact[r]) / max(abs(exact[r]), mp.mpf('1e-20') * S)))
                        worst_scaled = max(worst_scaled, float(abs(mp.fsum(t64) - exact[r]) / S))
    return worst_fwd, worst_scaled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('outdir'); ap.add_argument('L', type=int); ap.add_argument('Ns')
    ap.add_argument('--dps', type=int, default=100); ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    od = Path(args.outdir); od.mkdir(parents=True, exist_ok=True)
    report = {}
    for N in map(int, args.Ns.split(',')):
        out = weights(args.L, N, args.dps)
        hi, dd = to_arrays(out, args.L, N, args.dps)
        hi.tofile(od / f'w_{args.L}_{N}.bin'); dd.tofile(od / f'w_{args.L}_{N}.dd.bin')
        man_p = od / 'weights_manifest.json'
        man = json.loads(man_p.read_text()) if man_p.exists() else {}
        man[f'L{args.L}_N{N}'] = {'bin': f'w_{args.L}_{N}.bin', 'bin_sha256': hashlib.sha256((od / f'w_{args.L}_{N}.bin').read_bytes()).hexdigest(),
                                  'dd': f'w_{args.L}_{N}.dd.bin', 'dd_sha256': hashlib.sha256((od / f'w_{args.L}_{N}.dd.bin').read_bytes()).hexdigest(), 'dps': args.dps}
        man_p.write_text(json.dumps(man, indent=1, sort_keys=True))
        rec = {'L': args.L, 'N': N, 'dps': args.dps, 'max_abs_weight': float(np.max(np.abs(hi)))}
        if args.check:
            fwd, scaled = check(args.L, N, hi, dd)
            rec.update({'check_forward_dd': fwd, 'check_scaled_float64': scaled, 'check_pass': fwd <= 1e-12 and scaled <= 1e-15})
        report[f'L{args.L}_N{N}'] = rec
        print(json.dumps(rec), flush=True)
    (od / f'weights_report_L{args.L}.json').write_text(json.dumps(report, indent=1))
    if args.check and not all(r['check_pass'] for r in report.values()):
        sys.exit(1)


if __name__ == '__main__':
    main()
