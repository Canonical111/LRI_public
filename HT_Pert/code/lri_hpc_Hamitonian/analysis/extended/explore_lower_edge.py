#!/usr/bin/env python3
"""EXPLORATORY, POST HOC: dependence of the thermal intercepts on the lower window edge, with the extended data.

This analysis was chosen after the extended data had been seen (2026-09-29), because the free-fit residuals of
the reference window (lo = 16) grow far above the data accuracy once hi reaches about 110. It is not part of the
pre-registered protocol (PLAN G3/G6), whose conclusion is reported separately in UPDATED_RESULTS.md. The original
model classes are used unchanged; the extra tail structures use analysis/diagnose_systematic.thermal_fit, which is
checked against ThermalModel.

For lo in {16, 24, 32, 40, 50, 60, 70} and hi = the largest thermal cutoff, it fits:
  - every basis in MODELS with the extended gap input;
  - A, B and D with free thermal exponents;
  - A and D plus the z^j/L log tower, the z^j/L^1.5 tower, and an extra L^-0.75 term (probes of a slow term the
    bases lack);
  - A, B and D with the original gap input.
It writes explore_lower_edge.json and prints a compact table.
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
from analyze_joint import MODELS, load, ThermalModel  # noqa: E402
from diagnose_systematic import thermal_fit, const_terms  # noqa: E402

EXACT = {4: 45.42488010356, 5: -731.13947662454}
DIAGRAMMATIC = {6: (14331.8, 0.5), 7: (-322550.0, 41.0)}


def main():
    th = load(['thermal_new.json', 'prior_c7/C7_completed_runs.json', 'C7_extension.json'])
    L = np.array([r['cutoff'] for r in th], float); C = np.array([r['C'] for r in th])
    ex = json.loads((HERE / 'extended_summary.json').read_text())
    w_ext = {int(k): v for k, v in ex['gap_reference']['extended'].items()}
    w_orig = {int(k): v for k, v in ex['gap_reference']['original'].items()}
    hi = int(L.max())
    variants = {name: (const_terms(name), w_ext, False) for name in MODELS}
    for name in ('A', 'B', 'D'):
        variants[f'{name}+free_exponents'] = (const_terms(name), w_ext, True)
        variants[f'{name} gap=original'] = (const_terms(name), w_orig, False)
    for name in ('A', 'D'):
        variants[f'{name}+z^j/L'] = (lambda k, n=name: MODELS[n] + [(1, j) for j in range(1, k - 1) if (1, j) not in MODELS[n]], w_ext, False)
        variants[f'{name}+z^j/L^1.5'] = (lambda k, n=name: MODELS[n] + [(1.5, j) for j in range(2, k - 1) if (1.5, j) not in MODELS[n]], w_ext, False)
        variants[f'{name}+L^-0.75'] = (lambda k, n=name: MODELS[n] + [(0.75, 0)], w_ext, False)
    rows = []
    for lo in (16, 24, 32, 40, 50, 60, 70):
        m = (L >= lo) & (L <= hi)
        for label, (tk, w, free) in variants.items():
            try:
                lim, diag = thermal_fit(L[m], C[m], w, tk, free_exponents=free)
            except ValueError as e:
                rows.append(dict(lo=lo, hi=hi, variant=label, error=str(e))); continue
            rows.append(dict(lo=lo, hi=hi, variant=label, points=int(m.sum()),
                             **{f'C{k}': lim[k] for k in range(4, 8)},
                             rel4=lim[4] / EXACT[4] - 1, rel5=lim[5] / EXACT[5] - 1,
                             max_residual={k: diag[k]['max_residual'] for k in range(4, 8)},
                             cond=max(diag[k]['condition'] for k in range(4, 8))))
    out = dict(label='EXPLORATORY, POST HOC (not the pre-registered protocol)', hi=hi,
               thermal_cutoffs=[int(x) for x in L], rows=rows)
    summ = {}
    for lo in (16, 24, 32, 40, 50, 60, 70):
        ok = [r for r in rows if r['lo'] == lo and 'C4' in r and r['variant'] != 'minimal']
        well = [r for r in ok if r['max_residual'][4] < 1e-8]
        summ[lo] = dict(n=len(ok), n_residual_below_1e8=len(well),
                        rel4_range=[min(r['rel4'] for r in ok), max(r['rel4'] for r in ok)],
                        rel4_range_well_fitting=[min(r['rel4'] for r in well), max(r['rel4'] for r in well)] if well else None,
                        rel5_range=[min(r['rel5'] for r in ok), max(r['rel5'] for r in ok)],
                        C6_range=[min(r['C6'] for r in ok), max(r['C6'] for r in ok)],
                        C7_range=[min(r['C7'] for r in ok), max(r['C7'] for r in ok)])
    out['summary_excluding_minimal'] = summ
    (HERE / 'explore_lower_edge.json').write_text(json.dumps(out, indent=1, default=float) + '\n')
    print(f'EXPLORATORY (post hoc); hi = {hi}')
    for lo, s in summ.items():
        wf = s['rel4_range_well_fitting']
        print(f"lo={lo:3d} n={s['n']:2d} well={s['n_residual_below_1e8']:2d} C4 {s['rel4_range'][0]:+.3e}..{s['rel4_range'][1]:+.3e}"
              f" (well-fitting {wf[0]:+.3e}..{wf[1]:+.3e})" if wf else f"lo={lo:3d} n={s['n']:2d} well=0 C4 {s['rel4_range'][0]:+.3e}..{s['rel4_range'][1]:+.3e}",
              f"C5 {s['rel5_range'][0]:+.2e}..{s['rel5_range'][1]:+.2e} C6 {s['C6_range'][0]:.1f}..{s['C6_range'][1]:.1f}"
              f" C7 {s['C7_range'][0]:.0f}..{s['C7_range'][1]:.0f}")


if __name__ == '__main__':
    main()
