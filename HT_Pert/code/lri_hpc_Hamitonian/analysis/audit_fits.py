#!/usr/bin/env python3
"""Independent audit of the REPORT (PHI6_JOINT_C7_REPORT.md) fits (PLAN G2).

Written from the report's equations, NOT importing analysis_original/analyze_joint.py:

  gap (REPORT §5):   Y_k(L) + sum_{j=1}^{k-2} e_j(log L) [Y_{k-j}(L) - w_{k-j}] = w_k + b x(L) + sum_i c_i f_i(L),
                     x(L) = d_2(L) - w_2^raw,  w_1 = 7/2,  w_2^raw = -5A + 1/54.
  thermal (REPORT §6): C_n(L) + sum_{j=1}^{n-2} e_j(log L) [C_{n-j}(L) - C_{n-j}(inf)] = C_n(inf) + a_n T2(L) + sum_i c_i f_i(L),
                     T2(L) = C_2(L) - A/9;  C_2, C_3 known controls; e_j(l) = [eps^j] exp(l sum_k w_k eps^k).
  Subleading bases f_i = L^{-p} (log L)^j:  A: (1,0)(1.5,0)(1.5,1)(2,0)  B: A+(2,1)  C: (1,0)(1,1)(1.5,0)(1.5,1).

Each least-squares problem is solved by column-scaled QR (numpy) and cross-checked at 50 digits (mpmath QR).
Checks (exit status 1 on failure):
  - reference gap fit (basis B, 24<=L<=128, cubic order, third+fifth-order data) gives w3 = 556.2143040434153;
  - reference exponents w4, w5 (basis A, L>=16, fifth-order data, w3 fixed) agree with final_summary.json;
  - reference thermal intercepts C4..C7 for bases A,B,C (16<=L<=50) agree with final_summary.json to 1e-6 relative;
  - held-out test: train 16<=L<=40, predict C4..C7 at L=42..50 recursively; the maximum errors must equal the
    saved original values (final_joint_models.json, lo=16, hi=40, shift=0) to 1e-9 + 1e-6 relative, and round to the
    REPORT §6 quotes for C7 (0.012, 0.0036, 0.013);
  - the float64 QR and the 50-digit mpmath QR agree to 1e-6 relative in every fitted parameter;
  - a discrepancy inventory (REPORT text versus code/data) is written with the results.
Writes analysis/audit_fits.json.
"""
import json, math, sys
from pathlib import Path
import numpy as np
import mpmath as mp

ROOT = Path(__file__).resolve().parents[1]
ORIG = ROOT / 'analysis_original'
A = math.pi + 4 * math.log(2)
C2INF, C3INF = A / 9, -3.71985632290183342249
W1, W2RAW = 3.5, -5 * A + 1 / 54
SOLVES = []  # float64-vs-mpmath deviations of every least-squares solve
BASES = {'A': [(1, 0), (1.5, 0), (1.5, 1), (2, 0)],
         'B': [(1, 0), (1.5, 0), (1.5, 1), (2, 0), (2, 1)],
         'C': [(1, 0), (1, 1), (1.5, 0), (1.5, 1)]}


def rows(names):
    by = {}
    for n in names:
        for r in json.loads((ORIG / n).read_text()):
            by[r['cutoff']] = r
    return [by[k] for k in sorted(by)]


def exp_jets(ell, w, kmax):
    """[eps^j] exp(ell * sum_k w_k eps^k), j = 0..kmax, via the power-series exponential recurrence."""
    e = [np.ones_like(ell)]
    for k in range(1, kmax + 1):
        acc = np.zeros_like(ell)
        for j in range(1, k + 1):
            acc = acc + j * w.get(j, 0.0) * ell * e[k - j]
        e.append(acc / k)
    return e


def lstsq(X, y):
    s = np.linalg.norm(X, axis=0)
    Q, R = np.linalg.qr(X / s)
    p = np.linalg.solve(R, Q.T @ y) / s
    with mp.workdps(50):
        pm, _ = mp.qr_solve(mp.matrix((X / s).tolist()), mp.matrix(y.tolist()))
        pm = np.array([float(v) for v in pm]) / s
    dev = float(np.max(np.abs(p - pm) / np.maximum(np.abs(pm), 1e-300)))
    # Every solve (gap, thermal reference and held-out training fits) must agree with 50-digit QR (review LRI-003).
    if not (np.all(np.isfinite(p)) and dev <= 1e-6):
        raise ArithmeticError(f'float64 and mpmath QR disagree (max rel {dev:.3g})')
    SOLVES.append(dev)
    return p, dev


def basis_columns(L, lead, terms):
    z = np.log(L)
    return np.column_stack([np.ones_like(L), lead] + [L ** (-p) * z ** j for p, j in terms])


def gap_fit(L, Y, terms, order, fixed=None):
    """Returns {k: w_k} for k = 2..order. Y[:, k] are the raw gap coefficients d_k(L)."""
    w = {1: W1, 2: W2RAW}
    x = Y[:, 2] - W2RAW
    for k in range(3, order + 1):
        e = exp_jets(np.log(L), w, k - 2)
        y = Y[:, k].copy()
        for j in range(1, k - 1):
            y = y + e[j] * (Y[:, k - j] - w[k - j])
        X = basis_columns(L, x, terms)
        if k == 3 and fixed is not None:
            p, _ = lstsq(X[:, 1:], y - fixed)
            w[3] = fixed
        else:
            p, _ = lstsq(X, y)
            w[k] = float(p[0])
    return w


def thermal_fit(L, C, terms, w):
    lim = {2: C2INF, 3: C3INF}
    par = {}
    T2 = C[:, 2] - C2INF
    worst_mp = 0.0
    for n in range(4, 8):
        e = exp_jets(np.log(L), w, n - 2)
        y = C[:, n].copy()
        for j in range(1, n - 1):
            y = y + e[j] * (C[:, n - j] - lim[n - j])
        p, dev = lstsq(basis_columns(L, T2, terms), y)
        par[n] = p; lim[n] = float(p[0]); worst_mp = max(worst_mp, dev)
    return lim, par, worst_mp


def thermal_predict(L, C2, C3, lim, par, terms, w):
    """Recursive prediction of C4..C7 at new cutoffs from C2, C3 and the fitted model (no C4..C7 inputs)."""
    T2 = C2 - C2INF
    out = {2: C2, 3: C3}
    X = basis_columns(L, T2, terms)
    e = exp_jets(np.log(L), w, 5)
    for n in range(4, 8):
        v = X @ par[n]
        for j in range(1, n - 1):
            v = v - e[j] * (out[n - j] - lim[n - j])
        out[n] = v
    return out


def main():
    fs = json.loads((ORIG / 'final_summary.json').read_text())
    report = {}
    ok = True
    # Gap: cubic coefficient from all data with d3 (fifth- and third-order runs), basis B, 24..128.
    g = rows(['phi6_validation.json', 'phi6_production.json', 'phi6_extension.json', 'phi6_thin3.json', 'phi6_thin3_extension.json'])
    Lg = np.array([r['cutoff'] for r in g], float); Yg = np.array([r['raw']['D6'][:4] for r in g])
    m = (Lg >= 24) & (Lg <= 128)
    w3 = gap_fit(Lg[m], Yg[m], BASES['B'], 3)[3]
    report['omega3'] = w3
    ok &= abs(w3 - fs['omega3_reference']['omega3']) <= 1e-9 * abs(w3)
    # Gap: w4, w5 from fifth-order data, basis A, L >= 16, w3 fixed.
    g5 = rows(['phi6_validation.json', 'phi6_production.json', 'phi6_extension.json'])
    L5 = np.array([r['cutoff'] for r in g5], float); Y5 = np.array([r['raw']['D6'] for r in g5])
    w = gap_fit(L5[L5 >= 16], Y5[L5 >= 16], BASES['A'], 5, fixed=w3)
    report['omega'] = w
    for k in (4, 5):
        ref = fs['gap_reference'][str(k)]
        ok &= abs(w[k] - ref) <= 1e-8 * abs(ref)
    # Thermal reference fits, 16 <= L <= 50.
    th = rows(['prior_c7/C7_completed_runs.json', 'C7_extension.json'])
    L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'] for r in th])
    sel = {r['model']: r['C'] for r in fs['selected_models']}
    report['thermal'] = {}
    for name, terms in BASES.items():
        m = (L >= 16) & (L <= 50)
        lim, par, dev = thermal_fit(L[m], C[m], terms, w)
        rel = max(abs(lim[n] - sel[name][str(n)]) / abs(sel[name][str(n)]) for n in range(4, 8))
        # Held-out: train 16..40, predict 42..50 (C2, C3 used as controls; C4..C7 withheld).
        mt = (L >= 16) & (L <= 40); mh = L > 40
        lt, pt, _ = thermal_fit(L[mt], C[mt], terms, w)
        pred = thermal_predict(L[mh], C[mh, 2], C[mh, 3], lt, pt, terms, w)
        held = {n: float(np.max(np.abs(pred[n] - C[mh, n]))) for n in range(4, 8)}
        report['thermal'][name] = dict(C={n: lim[n] for n in range(4, 8)}, max_rel_vs_final_summary=rel,
                                       float_vs_mpmath_max_rel=dev, heldout_16_40_to_42_50=held)
        ok &= rel <= 1e-6
    quoted = {'A': 0.012, 'B': 0.0036, 'C': 0.013}
    fj = json.loads((ORIG / 'final_joint_models.json').read_text())
    report['heldout_checks'] = {}
    for name in BASES:
        saved = next(r for r in fj if r['model'] == name and r['lo'] == 16 and r['hi'] == 40 and r['shift'] == 0)['heldout']
        mine = [report['thermal'][name]['heldout_16_40_to_42_50'][n] for n in range(4, 8)]
        rel = max(abs(a - b) / abs(b) for a, b in zip(mine, saved))
        close = all(abs(a - b) <= 1e-9 + 1e-6 * abs(b) for a, b in zip(mine, saved))
        rounds = (f'{mine[3]:.2g}' == f'{quoted[name]:.2g}')
        report['heldout_checks'][name] = {'saved': saved, 'mine': mine, 'max_rel': rel, 'within_1e-9_abs_plus_1e-6_rel': close, 'C7_rounds_to_report_quote': rounds}
        ok &= close and rounds
        ok &= report['thermal'][name]['float_vs_mpmath_max_rel'] <= 1e-6
    report['discrepancy_inventory'] = [
        'REPORT §6 does not state the reference thermal window; the code (final_joint.py) uses 16 <= Lambda <= 50, shift 0.',
        'REPORT §5 says the omega3 reference uses basis B and 24 <= Lambda <= 128 on third- and fifth-order data: matches fit_omega3/final_joint.',
        'REPORT §5: omega4, omega5 from the fifth-order data "through 58" with omega3 fixed: code uses basis A, Lambda >= 16 (all fifth-order rows, 4..58).',
        'REPORT §2 says 26 fifth-order phi6 cutoffs (4..50, 54, 58): data have no 52 or 56.',
        'REPORT §6 C4..C7 are fitted successively with C2, C3 exact controls: matches ThermalModel.',
        'REPORT §6 "leading basis function is the actual T2(Lambda)": code uses x = C2(Lambda) - A/9, i.e. T2 as defined in §3.',
        'The report quotes held-out C7 errors to 2 significant figures; the saved values are reproduced to <= 1e-6 relative.',
    ]
    report['qr_crosscheck'] = dict(solves=len(SOLVES), max_rel=max(SOLVES))
    report['pass'] = bool(ok)
    (ROOT / 'analysis' / 'audit_fits.json').write_text(json.dumps(report, indent=1, default=float) + '\n')
    print(json.dumps(report, indent=1, default=float))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
