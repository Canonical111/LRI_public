#!/usr/bin/env python3
"""Diagnosis of the C4/C5 offset of the joint thermal extrapolation (PLAN G3: D1-D4 plus a labelled calibration check).

Exact C4 and C5 are used only in the labelled calibration check and as after-the-fact comparisons; the diagrammatic
C6 and C7 only as after-the-fact comparisons. Nothing here is a fit target in a headline number.

The original model classes (analysis_original/analyze_joint.py) are imported unchanged. `thermal_fit` below is a
re-implementation of ThermalModel.fit that additionally allows per-order tail bases and fixed intercepts; it is
checked against ThermalModel to 1e-9 relative before use.

Usage: python analysis/diagnose_systematic.py [--thermal-extra rows.json ...] [--phi6-extra rows.json ...]
       [--out analysis/diagnosis.json]
Extra rows are exported lists (export_results.py) with cutoffs beyond the saved data. With extra thermal rows the
frozen reference models (fitted at 16 <= L <= 50) are evaluated on them (the held-out test of D2).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / 'analysis_original'
sys.path.insert(0, str(ORIG))
from analyze_joint import MODELS, load, ls, eseries, design, GapModel, ThermalModel, A, C2, C3  # noqa: E402

EXACT = {4: 45.42488010356, 5: -731.13947662454}
COMPARE = {6: (14331.8, 0.5), 7: (-322550.0, 41.0)}   # diagrammatic, after-the-fact only
REF_LO, REF_HI = 16, 50


def thermal_rows(extra):
    rows = {r['cutoff']: r for r in load(['prior_c7/C7_completed_runs.json', 'C7_extension.json'])}
    for f in extra:
        for r in json.loads(Path(f).read_text()):
            if r['cutoff'] in rows:
                old = np.array(rows[r['cutoff']]['C']); new = np.array(r['C'])
                assert np.all(abs(old - new) <= 1e-7 + 2e-11 * abs(old)), f"L={r['cutoff']}: new row disagrees with saved row"
                continue   # PLAN §3.5: the saved rows are kept at L <= 50
            rows[r['cutoff']] = r
    rows = [rows[k] for k in sorted(rows)]
    return np.array([r['cutoff'] for r in rows], float), np.array([r['C'] for r in rows])


def gap_rows(extra, order):
    files = ['phi6_validation.json', 'phi6_production.json', 'phi6_extension.json']
    if order == 3:
        files += ['phi6_thin3.json', 'phi6_thin3_extension.json']
    rows = {r['cutoff']: r for r in load(files)}
    for f in extra:
        for r in json.loads(Path(f).read_text()):
            if r['degree'] >= order and r['cutoff'] not in rows:
                rows[r['cutoff']] = r
    rows = [rows[k] for k in sorted(rows)]
    return rows


def thermal_fit(L, C, w, terms_of_k, fixed=None, shift=0, free_exponents=False, maxorder=7):
    """ThermalModel.fit with per-order terms and optionally fixed intercepts {k: value}."""
    fixed = fixed or {}
    L = np.asarray(L, float) + shift; x = C[:, 2] - C2
    lim = {2: C2, 3: C3}; w = dict(w); diag = {}
    for k in range(4, maxorder + 1):
        free = free_exponents and k >= 5
        if free:
            w[k - 2] = 0
        e = eseries(L, w, k - 2)
        off = np.zeros(len(L))
        for j in range(1, k - 1):
            off -= e[j] * (C[:, k - j] - lim[k - j])
        X = design(L, x, terms_of_k(k))
        if free:
            X = np.column_stack([X, -np.log(L) * x])
        y = C[:, k] - off
        if k in fixed:
            p, d = ls(X[:, 1:], y - fixed[k]); p = np.r_[fixed[k], p]
        else:
            p, d = ls(X, y)
        d['max_residual'] = float(max(abs(X @ p - y)))
        diag[k] = d; lim[k] = float(p[0])
        if free:
            w[k - 2] = float(p[-1])
    return lim, diag


def const_terms(name):
    return lambda k: MODELS[name]


def gap_omega(rows, scheme='raw', terms='A', lo=16, free_log=False, fixed_omega3=None):
    L = np.array([r['cutoff'] for r in rows], float)
    Y = np.array([r[scheme]['D6'] for r in rows])
    m = L >= lo
    gm = GapModel(MODELS[terms], scheme, free_log, fixed_omega3=fixed_omega3).fit(L[m], Y[m])
    return {1: 3.5, **gm.lim}


def rel(a, b):
    return a / b - 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--thermal-extra', nargs='*', default=[])
    ap.add_argument('--phi6-extra', nargs='*', default=[]); ap.add_argument('--out', type=Path, default=ROOT / 'analysis/diagnosis.json')
    a = ap.parse_args()
    L, C = thermal_rows(a.thermal_extra)
    Lmax = int(L.max())
    fs = json.loads((ORIG / 'final_summary.json').read_text())
    w_ref = {int(k): v for k, v in fs['gap_reference'].items()}
    ref_mask = (L >= REF_LO) & (L <= REF_HI)
    out = dict(data=dict(thermal_cutoffs=[int(x) for x in L], thermal_max=Lmax), exact=EXACT, compare=COMPARE)

    # Check the re-implementation against the original ThermalModel.
    worst = 0.
    for name in ('A', 'B', 'C', 'F'):
        for free in (False, True):
            orig = ThermalModel(MODELS[name], w_ref, free_exponents=free).fit(L[ref_mask], C[ref_mask]).lim
            mine, _ = thermal_fit(L[ref_mask], C[ref_mask], w_ref, const_terms(name), free_exponents=free)
            worst = max(worst, max(abs(rel(mine[k], orig[k])) for k in range(4, 8)))
    assert worst < 1e-9, worst
    out['reimplementation_check_max_rel'] = worst

    # Reference A/B/C at 16..50 (as in final_summary), and after-the-fact comparisons.
    ref = {}
    for name in ('A', 'B', 'C'):
        lim, diag = thermal_fit(L[ref_mask], C[ref_mask], w_ref, const_terms(name))
        ref[name] = dict(C={k: lim[k] for k in range(4, 8)}, rel_to_exact={k: rel(lim[k], EXACT[k]) for k in (4, 5)},
                         sigma_to_compare={k: (lim[k] - COMPARE[k][0]) / COMPARE[k][1] for k in (6, 7)},
                         condition={k: diag[k]['condition'] for k in range(4, 8)})
    out['reference'] = ref

    # D1: the 4032-variant ensemble of combined_stress.py, now with C4 and C5.
    gaps = [r for r in json.loads((ORIG / 'gap_extrapolations.json').read_text()) if r['scheme'] == 'raw' and r['model'] != 'minimal']
    saved = json.loads((ORIG / 'combined_stress_results.json').read_text())
    L50, C50 = L[L <= REF_HI], C[L <= REF_HI]
    ens, i = [], 0
    for gr in gaps:
        w = {1: 3.5, **{int(k): v for k, v in gr['omega'].items()}}
        for name, terms in MODELS.items():
            for lo in (12, 16, 20, 24):
                for shift in (-2, 0, 2):
                    m = L50 >= lo
                    try:
                        mod = ThermalModel(terms, w, shift=shift).fit(L50[m], C50[m])
                    except ValueError:
                        continue
                    s = saved[i]; i += 1
                    assert (s['thermal_model'], s['lo'], s['shift']) == (name, lo, shift)
                    assert abs(rel(mod.lim[7], s['C7'])) < 1e-6 and abs(rel(mod.lim[6], s['C6'])) < 1e-6
                    ens.append(dict(gap_model=gr['model'], gap_lo=gr['lo'], gap_free_log=gr['free_leading_log'],
                                    thermal_model=name, lo=lo, shift=shift, **{f'C{k}': mod.lim[k] for k in range(4, 8)}))
    assert i == len(saved) == len(ens)
    d4 = np.array([rel(r['C4'], EXACT[4]) for r in ens]); d5 = np.array([rel(r['C5'], EXACT[5]) for r in ens])
    both = [r for r, x, y in zip(ens, d4, d5) if abs(x) < 1e-3 and abs(y) < 1e-3]
    q = lambda v: dict(min=float(np.min(v)), p05=float(np.percentile(v, 5)), median=float(np.median(v)),
                       p95=float(np.percentile(v, 95)), max=float(np.max(v)))
    # Linear association of C6, C7 with the C4, C5 errors across the ensemble (a labelled heuristic, not a result).
    X = np.column_stack([np.ones(len(ens)), d4, d5])
    assoc = {}
    for k in (6, 7):
        y = np.array([r[f'C{k}'] for r in ens]); p, *_ = np.linalg.lstsq(X, y, rcond=None)
        r2 = 1 - np.sum((y - X @ p) ** 2) / np.sum((y - y.mean()) ** 2)
        assoc[k] = dict(at_zero_C4_C5_error=float(p[0]), dCk_d_relC4=float(p[1]), dCk_d_relC5=float(p[2]), r2=float(r2))
    out['D1'] = dict(variants=len(ens), reproduces_saved_C6_C7=True, rel_C4_error=q(d4), rel_C5_error=q(d5),
                     fraction_C4_below_exact=float(np.mean(d4 < 0)), fraction_C5_more_negative=float(np.mean(d5 > 0)),
                     both_within_1em3=len(both),
                     both_within_1em3_C6=q([r['C6'] for r in both]) if both else None,
                     both_within_1em3_C7=q([r['C7'] for r in both]) if both else None,
                     ensemble_regression_heuristic=assoc)

    # D2: window dependence (reference gap input, shift 0).
    his = [h for h in range(36, Lmax + 1, 2) if h in set(int(x) for x in L)]
    d2 = []
    for name in MODELS:
        for lo in (12, 16, 20, 24):
            for hi in his:
                m = (L >= lo) & (L <= hi)
                try:
                    lim, diag = thermal_fit(L[m], C[m], w_ref, const_terms(name))
                except ValueError:
                    continue
                d2.append(dict(model=name, lo=lo, hi=hi, C4=lim[4], C5=lim[5], C6=lim[6], C7=lim[7],
                               cond4=diag[4]['condition'], cond5=diag[5]['condition']))
    out['D2'] = d2

    # D3: alternative tail structures at the reference window (lo 16, hi = REF_HI and hi = Lmax).
    d3 = []
    for hi in sorted({REF_HI, Lmax}):
        m = (L >= REF_LO) & (L <= hi)
        variants = {}
        for name in ('A', 'B', 'C'):
            variants[f'{name}'] = (const_terms(name), w_ref, False)
            variants[f'{name}+free_exponents'] = (const_terms(name), w_ref, True)
        variants['A+z^j/L (j<=k-2)'] = (lambda k: MODELS['A'] + [(1, j) for j in range(1, k - 1)], w_ref, False)
        variants['A+z^j/L^1.5 (2<=j<=k-2)'] = (lambda k: MODELS['A'] + [(1.5, j) for j in range(2, k - 1)], w_ref, False)
        variants['A+both log towers'] = (lambda k: MODELS['A'] + [(1, j) for j in range(1, k - 1)] + [(1.5, j) for j in range(2, k - 1)], w_ref, False)
        g5 = gap_rows(a.phi6_extra, 5)
        w_vac = gap_omega(g5, 'vacuum_subtracted')
        w_freelog = gap_omega(g5, 'raw', free_log=True)
        w_rawfree3 = gap_omega(g5, 'raw')
        for name in ('A', 'B', 'C'):
            variants[f'{name} gap=vacuum_subtracted'] = (const_terms(name), w_vac, False)
            variants[f'{name} gap=free_leading_log'] = (const_terms(name), w_freelog, False)
            variants[f'{name} gap=raw,omega3 free'] = (const_terms(name), w_rawfree3, False)
        for label, (tk, w, free) in variants.items():
            try:
                lim, diag = thermal_fit(L[m], C[m], w, tk, free_exponents=free)
            except ValueError as e:
                d3.append(dict(variant=label, hi=hi, error=str(e))); continue
            d3.append(dict(variant=label, hi=hi, C4=lim[4], C5=lim[5], C6=lim[6], C7=lim[7],
                           rel4=rel(lim[4], EXACT[4]), rel5=rel(lim[5], EXACT[5]),
                           cond=max(diag[k]['condition'] for k in range(4, 8))))
    out['D3'] = d3
    out['gap_inputs'] = dict(reference=w_ref, vacuum_subtracted=w_vac, free_leading_log=w_freelog, raw_omega3_free=w_rawfree3)

    # D4: cutoff-coordinate shifts.
    d4s = []
    for name in ('A', 'B', 'C'):
        for shift in (-4, -2, 0, 2, 4):
            lim, _ = thermal_fit(L[ref_mask], C[ref_mask], w_ref, const_terms(name), shift=shift)
            d4s.append(dict(model=name, shift=shift, C4=lim[4], C5=lim[5], C6=lim[6], C7=lim[7]))
    out['D4'] = d4s

    # Calibration check (labelled): refit with the exact C4 (and C5) imposed; compare residuals with the free fit.
    cal = []
    for hi in sorted({REF_HI, Lmax}):
        m = (L >= REF_LO) & (L <= hi)
        for name in ('A', 'B', 'C'):
            free_lim, free_d = thermal_fit(L[m], C[m], w_ref, const_terms(name))
            fix_lim, fix_d = thermal_fit(L[m], C[m], w_ref, const_terms(name), fixed={4: EXACT[4], 5: EXACT[5]})
            cal.append(dict(model=name, hi=hi,
                            max_residual_free={k: free_d[k]['max_residual'] for k in (4, 5)},
                            max_residual_exact_imposed={k: fix_d[k]['max_residual'] for k in (4, 5)},
                            C6_C7_with_exact_C4_C5_imposed={k: fix_lim[k] for k in (6, 7)}))
    out['calibration_check'] = cal

    # Residual-ratio curves R_n(L) = [LHS_n(L) - C_n(exact)] / T2(L), n = 4, 5 (reference gap input).
    x = C[:, 2] - C2
    e = eseries(L, w_ref, 3)
    lhs4 = C[:, 4] + e[1] * (C[:, 3] - C3) + e[2] * (C[:, 2] - C2)
    lhs5 = C[:, 5] + e[1] * (C[:, 4] - EXACT[4]) + e[2] * (C[:, 3] - C3) + e[3] * (C[:, 2] - C2)
    out['residual_ratio'] = [dict(L=int(l), T2=float(t), R4=float((p - EXACT[4]) / t), R5=float((s - EXACT[5]) / t))
                             for l, t, p, s in zip(L, x, lhs4, lhs5) if l >= 10]

    # Held-out test (only with extra thermal rows): frozen reference models at 16..50 predict L > 50.
    new = L > REF_HI
    if new.any():
        pred = {}
        for name in ('A', 'B', 'C'):
            mod = ThermalModel(MODELS[name], w_ref).fit(L[ref_mask], C[ref_mask])
            P = mod.predict(L[new], C[new, 2], C[new, 3])
            pred[name] = [dict(L=int(l), **{f'C{k}_pred_minus_actual': float(P[i, k - 4] - C[j, k]) for k in range(4, 8)})
                          for i, (j, l) in enumerate(zip(np.where(new)[0], L[new]))]
        out['heldout'] = pred

    a.out.write_text(json.dumps(out, indent=1, default=float) + '\n')
    s = out['D1']
    print(f"reference C4 rel err: {[round(ref[n]['rel_to_exact'][4], 5) for n in 'ABC']}; C5: {[round(ref[n]['rel_to_exact'][5], 5) for n in 'ABC']}")
    print(f"D1: {s['variants']} variants; C4 rel err {s['rel_C4_error']}; C5 {s['rel_C5_error']}; both<1e-3: {s['both_within_1em3']}")
    print('D1 heuristic', json.dumps(s['ensemble_regression_heuristic']))
    for c in cal:
        print('calibration', c['model'], c['hi'], {k: f"{c['max_residual_free'][k]:.2e}->{c['max_residual_exact_imposed'][k]:.2e}" for k in (4, 5)},
              {k: round(v, 1) for k, v in c['C6_C7_with_exact_C4_C5_imposed'].items()})
    print('wrote', a.out)


if __name__ == '__main__':
    main()
