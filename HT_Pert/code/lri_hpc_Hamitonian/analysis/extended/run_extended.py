#!/usr/bin/env python3
"""Extended joint analysis with the new cutoffs (PLAN G6).

The model code is analyze_joint.py in this directory, a byte-identical copy of analysis_original/analyze_joint.py
(check_identity.py enforces that; review LRI-004). This driver changes only configuration:
  - loader file lists (the new exported rows *_new.json first, the saved rows after them, so the saved rows win at
    any overlapping cutoff, PLAN §3.5);
  - separately parameterized windows for the cubic gap fit (omega3), the fifth-order gap fit (omega4, omega5) and the
    thermal fit;
  - reference selection and summary filters.
The frozen original reference models (original gap input, thermal 16 <= L <= 50) are refitted here from the saved
rows only and used for the held-out predictions of the new cutoffs.

Usage: cd analysis/extended && python run_extended.py   (writes extended_summary.json)
Data: thermal_new.json, phi6_d5_new.json, phi6_d3_new.json from export_results.py (fetch_results.sh).
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from analyze_joint import MODELS, load, GapModel, ThermalModel, D  # noqa: E402  (unchanged original code)
assert Path(D) == HERE

EXACT = {4: 45.42488010356, 5: -731.13947662454}
DIAGRAMMATIC = {6: (14331.8, 0.5), 7: (-322550.0, 41.0)}   # after-the-fact comparison only
SAVED_THERMAL = ['prior_c7/C7_completed_runs.json', 'C7_extension.json']
SAVED_GAP5 = ['phi6_validation.json', 'phi6_production.json', 'phi6_extension.json']
SAVED_GAP3 = SAVED_GAP5 + ['phi6_thin3.json', 'phi6_thin3_extension.json']
NEW = {'thermal': 'thermal_new.json', 'gap5': 'phi6_d5_new.json', 'gap3': 'phi6_d3_new.json'}

# Reference choices of the original analysis (final_joint.py / fit_omega3.py), and the extended windows.
OMEGA3 = dict(model='B', lo=24, free_log=False, hi_original=128)
OMEGA45 = dict(model='A', lo=16, hi_original=58)
THERMAL = dict(models=('A', 'B', 'C'), lo=16, shift=0, hi_original=50)


def present(name):
    return [name] if (HERE / name).exists() else []


def check_overlap(new_name, saved_names, kind):
    """Refuse new rows that disagree with saved rows at a shared cutoff (PLAN §3.5, review IR-004); the saved rows are
    then kept by the loader order. Thermal: C. phi6: D6 and C of both prescriptions on the shared orders.
    Tolerance 1e-7 + 2e-11|x| (the package regression tolerance). Returns the overlapping cutoffs."""
    if not (HERE / new_name).exists():
        return []
    saved = {r['cutoff']: r for r in load(saved_names)}
    shared = []
    for r in json.loads((HERE / new_name).read_text()):
        old = saved.get(r['cutoff'])
        if old is None:
            continue
        pairs = [(old['C'], r['C'])] if kind == 'thermal' else \
            [(old[p][k], r[p][k]) for p in ('raw', 'vacuum_subtracted') for k in ('D6', 'C')]
        for a, b in pairs:
            n = min(len(a), len(b)); a, b = np.array(a[:n]), np.array(b[:n])
            if not np.all(abs(a - b) <= 1e-7 + 2e-11 * abs(a)):
                raise ValueError(f'{new_name}: cutoff {r["cutoff"]} disagrees with the saved row: {a} vs {b}')
        shared.append(r['cutoff'])
    return shared


def sources(name):
    return sorted({r.get('source_sha256') for r in json.loads((HERE / name).read_text())}) if (HERE / name).exists() else []


def arrays(rows, key):
    L = np.array([r['cutoff'] for r in rows], float)
    return L, np.array([key(r) for r in rows])


def omega3_fit(L3, Y3, hi):
    m = (L3 >= OMEGA3['lo']) & (L3 <= hi)
    gm = GapModel(MODELS[OMEGA3['model']], 'raw', OMEGA3['free_log']).fit(L3[m], Y3[m], 3)
    return gm.lim[3], int(m.sum())


def omega45_fit(L5, Y5, hi, w3):
    m = (L5 >= OMEGA45['lo']) & (L5 <= hi)
    gm = GapModel(MODELS[OMEGA45['model']], fixed_omega3=w3).fit(L5[m], Y5[m])
    return {1: 3.5, **gm.lim}, int(m.sum())


def main():
    overlaps = dict(thermal=check_overlap(NEW['thermal'], SAVED_THERMAL, 'thermal'),
                    gap5=check_overlap(NEW['gap5'], SAVED_GAP3, 'phi6'),
                    gap3=check_overlap(NEW['gap3'], SAVED_GAP3, 'phi6'))
    provenance = {k: sources(v) for k, v in NEW.items()}
    if any(len(v) > 1 for v in provenance.values()) or len({s for v in provenance.values() for s in v}) > 1:
        raise ValueError(f'new rows come from more than one solver source: {provenance}')
    gap3 = load(present(NEW['gap3']) + present(NEW['gap5']) + SAVED_GAP3)
    gap5 = load(present(NEW['gap5']) + SAVED_GAP5)
    th = load(present(NEW['thermal']) + SAVED_THERMAL)
    th_saved = load(SAVED_THERMAL)
    L3, Y3 = arrays(gap3, lambda r: r['raw']['D6'][:4])
    L5, Y5 = arrays(gap5, lambda r: r['raw']['D6'])
    LL, CC = arrays(th, lambda r: r['C'])
    Ls, Cs = arrays(th_saved, lambda r: r['C'])
    # Completed campaign cutoffs come from the exported identities, not from fit-window boundaries (review IR2-003).
    exported = {k: sorted(r['cutoff'] for r in json.loads((HERE / v).read_text())) if (HERE / v).exists() else []
                for k, v in NEW.items()}
    out = dict(data=dict(cubic_gap_max=int(L3.max()), fifth_gap_max=int(L5.max()), thermal_max=int(LL.max()),
                         thermal_new=exported['thermal'], gap5_new=exported['gap5'], gap3_new=exported['gap3']),
               overlap_checked=overlaps, new_row_sources=provenance)

    # Frozen original reference (saved rows only) and its held-out predictions of the new thermal cutoffs.
    fs = json.loads((HERE.parent.parent / 'analysis_original' / 'final_summary.json').read_text())
    w_orig = {int(k): v for k, v in fs['gap_reference'].items()}
    frozen = {}
    new = LL > THERMAL['hi_original']
    for name in THERMAL['models']:
        m = (Ls >= THERMAL['lo']) & (Ls <= THERMAL['hi_original'])
        mod = ThermalModel(MODELS[name], w_orig, shift=THERMAL['shift']).fit(Ls[m], Cs[m])
        ref = fs['selected_models'][THERMAL['models'].index(name)]
        assert ref['model'] == name and all(abs(mod.lim[k] / ref['C'][str(k)] - 1) < 1e-9 for k in range(4, 8))
        rec = dict(C={k: mod.lim[k] for k in range(4, 8)})
        if new.any():
            P = mod.predict(LL[new], CC[new, 2], CC[new, 3])
            rec['heldout'] = [dict(L=int(l), **{f'C{k}': dict(pred=float(P[i, k - 4]), actual=float(CC[j, k]),
                                                             err=float(P[i, k - 4] - CC[j, k]),
                                                             err_over_distance=float((P[i, k - 4] - CC[j, k]) / (CC[j, k] - mod.lim[k])))
                                                   for k in range(4, 8)})
                              for i, (j, l) in enumerate(zip(np.where(new)[0], LL[new]))]
        frozen[name] = rec
    out['frozen_original_reference'] = frozen

    # omega3 versus the cubic-gap window; omega4, omega5 versus the fifth-order window.
    his3 = sorted({OMEGA3['hi_original'], *[h for h in (176, 256, 320, 400, 480) if h <= L3.max()], int(L3.max())})
    out['omega3_vs_hi'] = {h: dict(zip(('omega3', 'points'), omega3_fit(L3, Y3, h))) for h in his3}
    w3_orig = out['omega3_vs_hi'][OMEGA3['hi_original']]['omega3']
    w3_ext = out['omega3_vs_hi'][int(L3.max())]['omega3']
    his5 = sorted({OMEGA45['hi_original'], *[h for h in (70, 84, 100, 122, 140) if h <= L5.max()], int(L5.max())})
    out['omega45_vs_hi'] = {h: dict(omega=omega45_fit(L5, Y5, h, w3_ext)[0], points=omega45_fit(L5, Y5, h, w3_ext)[1])
                            for h in his5}
    w_ext = omega45_fit(L5, Y5, int(L5.max()), w3_ext)[0]
    out['gap_reference'] = dict(original=w_orig, extended=w_ext, omega3_original_window=w3_orig)

    # Thermal intercepts versus the thermal window, for the original and the extended gap input.
    hisT = sorted({THERMAL['hi_original'], *[h for h in range(60, int(LL.max()) + 1, 10) if h in set(LL.astype(int))], int(LL.max())})
    tab = []
    for gap_label, w in (('original', w_orig), ('extended', w_ext)):
        for name in THERMAL['models']:
            for hi in hisT:
                m = (LL >= THERMAL['lo']) & (LL <= hi)
                mod = ThermalModel(MODELS[name], w, shift=THERMAL['shift']).fit(LL[m], CC[m])
                tab.append(dict(gap=gap_label, model=name, hi=hi, points=int(m.sum()),
                                **{f'C{k}': mod.lim[k] for k in range(4, 8)},
                                cond=max(mod.diag[k]['condition'] for k in range(4, 8))))
    out['thermal_vs_hi'] = tab

    # Spreads at the extended window, as in final_summary ranges: all bases, lo in (12,16,20,24), shift in (-2,0,2).
    rows = []
    for name, terms in MODELS.items():
        for lo in (12, 16, 20, 24):
            for shift in (-2, 0, 2):
                m = LL >= lo
                try:
                    mod = ThermalModel(terms, w_ext, shift=shift).fit(LL[m], CC[m])
                except ValueError:
                    continue
                rows.append(dict(model=name, lo=lo, shift=shift, C={k: mod.lim[k] for k in range(4, 8)}))
    rng = lambda rs: {k: [min(r['C'][k] for r in rs), max(r['C'][k] for r in rs)] for k in range(4, 8)}
    out['variants_extended'] = rows
    # Extended D2: every basis x lower edge x upper edge (extended gap input, shift 0), with conditioning.
    win = []
    for name, terms in MODELS.items():
        for lo in (12, 16, 20, 24):
            for hi in hisT:
                m = (LL >= lo) & (LL <= hi)
                try:
                    mod = ThermalModel(terms, w_ext).fit(LL[m], CC[m])
                except ValueError:
                    continue
                win.append(dict(model=name, lo=lo, hi=hi, **{f'C{k}': mod.lim[k] for k in range(4, 8)},
                                cond={k: mod.diag[k]['condition'] for k in range(4, 8)},
                                residual={k: mod.diag[k]['residual'] for k in range(4, 8)}))
    out['window_table'] = win
    out['ranges_extended'] = dict(all_shifted_models=rng(rows),
                                  ABC_shifted=rng([r for r in rows if r['model'] in 'ABC']),
                                  ABC_unshifted=rng([r for r in rows if r['model'] in 'ABC' and r['shift'] == 0]))
    out['comparison'] = dict(exact=EXACT, diagrammatic=DIAGRAMMATIC)
    (HERE / 'extended_summary.json').write_text(json.dumps(out, indent=1, default=float) + '\n')

    print('data:', out['data'])
    print('omega3 vs hi:', {h: round(v['omega3'], 4) for h, v in out['omega3_vs_hi'].items()})
    print('omega4,5 vs hi:', {h: (round(v['omega'][4], 2), round(v['omega'][5], 0)) for h, v in out['omega45_vs_hi'].items()})
    for r in tab:
        print(f"{r['gap']:9s} {r['model']} hi={r['hi']:3d} C4={r['C4']:.6f} ({r['C4'] / EXACT[4] - 1:+.2e}) "
              f"C5={r['C5']:.4f} ({r['C5'] / EXACT[5] - 1:+.2e}) C6={r['C6']:.2f} C7={r['C7']:.1f}")
    if new.any():
        for name, rec in frozen.items():
            worst = {k: max(abs(h[f'C{k}']['err']) for h in rec['heldout']) for k in range(4, 8)}
            print('frozen', name, 'max |held-out error|', {k: f'{v:.3g}' for k, v in worst.items()})


if __name__ == '__main__':
    main()
