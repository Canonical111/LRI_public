#!/usr/bin/env python3
"""Generate every table body and figure coordinate list of note/lri_mc_note.tex from the packaged data and results.

The note must compile on its own, so the generated rows are embedded in it verbatim. This script (1) writes them to OUTDIR (one file
per table/figure) and (2) with --check NOTE.tex verifies that every generated line occurs verbatim in the note, i.e. that no number in
the note's tables or plots was typed by hand or has drifted from the records. Pure standard library (json, csv).

Usage: make_note_tables.py OUTDIR [--check note/lri_mc_note.tex] [--root PACKAGE_ROOT]

Public-release copy (2026-10-13), companion of the public note. Changes against the 2026-10-07 package version:
- the 1D figure shows sigma_stat and sigma_sys as separate bars: sigma_sys is a model-family half-range, not a standard deviation,
  so no quadrature sum is drawn; crossing values carry sigma_inf only (Delta_omega' is a sensitivity scale);
- platform labels in the cross-platform table are generic.
Input paths are relative to the MC folder (--root, default: two levels above this file).
"""
import argparse, csv, json, math, re, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
J = lambda p: json.loads((PKG / p).read_text())
E2P1 = 'results/2d/evaluation_P1_20260930_215057/evaluation_2d.json'
E3P1 = 'results/3d/evaluation_P1_54387089_20260930_215057/evaluation_3d.json'
E2B = 'data/2d/prod/evaluation_20260922_083649/evaluation_2d.json'
E3B = 'data/3d/prod/evaluation_54387089_20260923_194523/evaluation_3d.json'
CAL = 'results/2d3d_reanalysis/calibration/run_20260930_213748/CALIBRATION.json'

def f(x, n=5): return '--' if x is None else f'{x:.{n}f}'
def pm(v, e, n=5): return f'{v:.{n}f}({round(e * 10 ** n)})' if e is not None else f'{v:.{n}f}'
LBL = {'EQUILIBRATION FAILED': 'equil.\\ failed', 'COVERAGE-LIMITED': 'coverage-limited', 'MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE': 'model-limited',
       'CONDITIONAL': 'conditional', 'REBLOCKING UNAVAILABLE': 'reblock.\\ unavail.', 'REBLOCKING FAILED': 'reblock.\\ failed',
       'CROSS-CHECK UNAVAILABLE': 'x-check unavail.', 'CROSS-CHECK FAILED': 'x-check failed', 'ACCEPTED (sigma_sys-dominated)': 'accepted ($\\sigma_{\\rm sys}$-dom.)',
       'ACCEPTED': 'accepted'}
def label(dec):
    base, suf = (dec.split(' [', 1) + [''])[:2]
    return '\\lbl{' + LBL.get(base, base) + '}' + (' [$\\sigma$]' if 'above target' in suf else '')

def records(dim):
    tag = '' if dim == 2 else '54387089_'
    out = {}
    for d in sorted((PKG / f'data/{dim}d/prod').glob(f'analysis_{tag}b2000_s*'), key=lambda p: float(p.name.split('_s')[-1])):
        r = json.loads((d / 'results.json').read_text()); out[r['s']] = sorted(r['rows'], key=lambda x: x['L'])
    return out

def t_pairs(dim):
    L = []
    for s, rows in records(dim).items():
        cells = []
        for x in rows:
            v = x['values']; e = x['statistical_stderr']
            cells.append(f"{v[0]:.7f}({round(e[0] * 1e7)}) & {pm(v[2], e[2], 4)} & {pm(v[1], e[1], 4)}")
        L.append(f"{s:g} & {(dim - s) / 2:g} & " + ' & '.join(cells) + ' \\\\')
    return L

def short_reason(x):
    if x.get('eligible'): return 'yes'
    r = x.get('reason', '')
    if r.startswith('chi2/dof'): return 'no: $\\chi^2$'
    if r.startswith("omega'"): return 'no: $\\omega^\\prime$ edge'
    if r.startswith('sigma_inf'): return 'no: (iii)'
    return 'no'

def t_series(dim):
    E = J(E2P1 if dim == 2 else E3P1)['points']; L = []
    for s, P in E.items():
        first = True
        for q in ('U4', 'U6', 'U8', 'Y', 'J'):
            x = P['series'][q]
            if 'omega' not in x: continue
            sf = x.get('sigma_inf', x.get('sigma_inf_fixed_information')); sp = x.get('sigma_inf_profiled')
            dof = x['dof']
            L.append(f"{(s if first else ''):s} & {'U4+Y' if q == 'J' else q} & {x['Delta_inf']:.4f} & {x['omega']:.2f} [{x['omega_interval'][0]:.2f}, {x['omega_interval'][1]:.2f}] & "
                     f"{x['chi2']:.2f}/{dof} & {f(sf, 4)} & {f(sp, 4)} & {short_reason(x)} \\\\")
            first = False
    return L

def t_decisions(dim):
    B = J(E2B if dim == 2 else E3B)['points']; P1 = J(E2P1 if dim == 2 else E3P1)['points']; L = []
    for s in P1:
        b, p = B[s], P1[s]; qb, qp = b['quoted'] or {}, p['quoted'] or {}; xb, xp = b['crosscheck'], p['crosscheck']; rule = p['sigma_rule']
        val = f"{qp['Delta_epsilon']:.5f}" if qp else '--'
        sb = f(qb.get('sigma_stat')) if qb else '--'; sp_ = f(qp.get('sigma_stat')) if qp else '--'; ss = f(qp.get('sigma_sys')) if qp and qp.get('sigma_sys') is not None else '--'
        if 'difference' in xb:
            sdp = xp.get('sigma_D') if rule.get('applied') == 'profiled' else xp.get('sigma_D_profiled')
            z = f"{xb['difference']:+.4f}; {xb['difference'] / xb['sigma_D']:+.2f} / {xb['difference'] / sdp:+.2f}"
        else: z = '--'
        L.append(f"{s} & {(dim - float(s)) / 2:g} & {label(b['decision'])} & {label(p['decision'])} & {rule['applied']} & {val} & {sb} & {sp_} & {ss} & {z} \\\\")
    return L

def t_calib(dim):
    C = J(CAL)['strata'][str(dim)]; L = []
    st_ = lambda x: {'P': 'P', 'F': 'F'}.get(x['status'][0], 'nc')
    cell = lambda x: (f"{x['n_eligible']}: {x['cov1_profiled']:.2f}/{x['cov2_profiled']:.2f} ({x['cov1_fixed']:.2f}) {st_(x)}" if x['n_eligible'] else f"0 {st_(x)}")
    for s, st in C.items():
        c = st['crosscheck']; cx = (f"{c['n_both_eligible']}: {c['false_fail_profiled']:.3f} ({c['false_fail_fixed']:.2f}) {st_(c)}" if c['n_both_eligible'] else f"0 {st_(c)}")
        L.append(f"{s} & " + ' & '.join(cell(st[q]) for q in ('U4', 'U6', 'U8', 'Y', 'J')) + f" & {cx} \\\\")
    return L

def t_eps():
    scan = {round(r['ds'], 7): r for r in J('data/1d/scan_data/FIT_V3_SCAN.json')}; L = []
    with open(PKG / 'data/1d/reference/published_and_epsilon_reference.csv') as fh:
        rows = sorted(csv.DictReader(fh), key=lambda r: float(r['Delta_sigma']))
    for r in rows:
        ds = round(float(r['Delta_sigma']), 7); S = scan.get(ds) or scan.get(round(ds, 4)) or {}
        dag = '$\\dagger$'
        sys_ = str(round(S['sigma_sys'] * 1e5)) if S.get('sigma_sys') is not None else dag
        mc = (f"{S['Delta_epsilon']:.5f}({round(S['sigma_stat'] * 1e5)})({sys_})" if S.get('Delta_epsilon') is not None else 'largest pair')
        L.append(f"{float(r['Delta_sigma']):.7g} & {float(r['epsilon_GFF']):.3f} & {float(r['six_loop_GFF_only']):.4f} & {float(r['six_loop_endpoint_assisted']):.4f} & {mc} \\\\")
    return L

def t_oned():
    R = J('results/1d/oned_xcheck/run_20260930_202320/oned_xcheck.json'); L = []
    for ds, P in R['points'].items():
        a, b = P['profiled (recorded rule)'], P["fixed central omega'"]
        us = '\\_'
        sers = ', '.join(n.replace('_', us) + f": {x['central_omega']:.2f} ({x['omega_draw_16_50_84'][0]:.2f}--{x['omega_draw_16_50_84'][2]:.2f})" for n, x in P['series'].items())
        L.append(f"{ds} & {P['recorded']['difference']:+.5f} & {a['sigma_D']:.5f} & {a['z']:+.2f} & {b['sigma_D']:.5f} & {b['z']:+.2f} & {sers} \\\\")
    return L

REFIT = 'results/1d/refit_workstation_20261007'
L1 = {'ACCEPTED': 'accepted', 'ACCEPTED (sigma_sys-dominated)': 'accepted ($\\sigma_{\\rm sys}$-dom.)', 'CROSS-CHECK FAILED': 'x-check failed',
      'CROSS-CHECK UNAVAILABLE': 'x-check unavail.', 'CONDITIONAL (sigma_sys coverage absent)': 'conditional',
      'MODEL-LIMITED, EXTRAPOLATION UNAVAILABLE': 'model-limited'}
def l1(dec): return '\\lbl{' + L1.get(dec.split(' (fewer')[0], dec) + '}'
# the 1D report rows carry the report's upper-case labels and Unicode dashes; the note uses the label set of its table 2
FINAL = {'ACCEPTED ($\\sigma_{\\rm sys}$-dominated)': '\\lbl{accepted ($\\sigma_{\\rm sys}$-dominated)}', 'ACCEPTED': '\\lbl{accepted}',
         'CONDITIONAL ($\\sigma_{\\rm sys}$ coverage absent)': '\\lbl{conditional}', 'CROSS-CHECK FAILED': '\\lbl{cross-check failed}',
         'CROSS-CHECK UNAVAILABLE': '\\lbl{cross-check unavailable}', 'MODEL-LIMITED, EXTRAP.\\ UNAVAILABLE': '\\lbl{model-limited}'}
def final_rows(lines):
    out = []
    for l in lines:
        c = l.split(' & ')
        if len(c) > 2:
            if c[2] not in FINAL: sys.exit(f'make_note_tables.py: unknown 1D label {c[2]!r}')
            c[2] = FINAL[c[2]]
        out.append(' & '.join(c).replace('\u2014', '--'))
    return out

def t_refit():
    """1D: production decision vs the cross-platform refit of the packaged snapshot (results/1d/refit_workstation_20261007/ds*/fit_v3.json)."""
    L = []
    for d in sorted((PKG / REFIT).glob('ds*/fit_v3.json'), key=lambda q: float(q.parent.name[2:])):
        ds = d.parent.name[2:]; sel = J(f'data/1d/scan_data/ds{ds}/fits_v3_SELECTED.json')['selected_run']
        P = J(f'data/1d/scan_data/ds{ds}/{sel}/fit_v3.json')['points'][ds]; N = json.loads(d.read_text())['points'][ds]
        def row(X):
            q = X.get('quoted') or {}; sy = (X.get('sigma_sys') or {}).get('value')
            return l1(X['decision']), len(X.get('quotable') or []), q.get('Delta_epsilon'), q.get('sigma_stat'), sy
        a, b = row(P), row(N)
        dd = '--' if a[2] is None or b[2] is None else f'{abs(a[2] - b[2]):.0e}'
        sy = lambda v: '--' if v is None else f'{v:.5f}'
        L.append(f"{ds} & {a[0]} & {a[1]} & {sy(a[4])} & {b[0]} & {b[1]} & {sy(b[4])} & {dd}{' & changed' if a[0] != b[0] else ' & '} \\\\")
    return L

XP = 'results/1d/refit_crossplatform_ds0.1727335'
def t_d3():
    """The degree-3 start of the ladder of x0.45_background_Nmin8192_K2 that decides the two changed 1D labels, per platform."""
    cfg = 'x0.45_background_Nmin8192_K2'; L = []
    def row(name, f, ds):
        r = J(f); sel = 'stops at $p=3$' if r['flags'] else 'continues'
        L.append(f"{ds} & {name} & {r['chi2']:.1f} & {r['parameters'][3]:.2f} & {'bound' if r['flags'] else 'interior'} & {sel} \\\\")
    for ds, prod in (('0.1625', 'fits_v3_20260920_102522'), ('0.1727335', 'fits_v3_20260920_102523')):
        row('production (AMD EPYC 7742)', f'data/1d/scan_data/ds{ds}/{prod}/fits/ds{ds}_{cfg}_deg3.json', ds)
        row('Intel i9-13900K, Py 3.12/NumPy 1.26/SciPy 1.11, OpenBLAS', f'{REFIT}/ds{ds}/fits_{cfg}/ds{ds}_{cfg}_deg3.json', ds)
        if ds == '0.1727335':
            for sub, name in (('i9-13900K_py3.8.5_np1.19.2_sp1.5.2_openblas', 'Intel i9-13900K, Py 3.8.5/NumPy 1.19.2/SciPy 1.5.2, OpenBLAS'),
                              ('i9-13900K_py3.8.5_np1.19.2_sp1.5.2_mkl', 'Intel i9-13900K, same versions, MKL'),
                              ('epyc7543_py3.8.5_np1.19.2_sp1.5.2_mkl', 'AMD EPYC 7543, same versions, MKL')):
                row(name, f'{XP}/{sub}/fits_{cfg}/ds{ds}_{cfg}_deg3.json', ds)
    return L


# ---------------------------------------------------------------- added 2026-10-13 (review): robustness, theory and literature tables
def need(rel):
    """Fail loudly when an input of a generated table is missing (a silently skipped table would still report 'N of N')."""
    q = PKG / rel
    if not q.exists(): sys.exit(f'make_note_tables.py: required input {rel} is missing')
    return q

def _gammaincc(a, x):
    """Regularized upper incomplete gamma Q(a, x) (series / continued fraction); chi2 survival = Q(dof/2, chi2/2)."""
    if x <= 0: return 1.0
    if x < a + 1:
        s = t_ = 1.0 / a; n = a
        for _ in range(100000):
            n += 1; t_ *= x / n; s += t_
            if abs(t_) < abs(s) * 1e-16: break
        return 1.0 - s * math.exp(-x + a * math.log(x) - math.lgamma(a))
    b = x + 1 - a; c = 1e300; d = 1 / b; h = d
    for i in range(1, 100000):
        an = -i * (i - a); b += 2; d = an * d + b; d = 1 / d if d else 1e300; c = b + an / c if c else 1e300; e = d * c; h *= e
        if abs(e - 1) < 1e-16: break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
def pval(chi2, dof): return _gammaincc(dof / 2, chi2 / 2)
def fexp(x): return f'{x:.1e}'.replace('e-0', 'e-').replace('e-', '\\times10^{-') + '}' if x < 1e-2 else f'{x:.2f}'

def points1d():
    for d in sorted((PKG / 'data/1d/scan_data').glob('ds*'), key=lambda q: float(q.name[2:])):
        if not d.is_dir(): continue
        ds = d.name[2:]; sel = J(f'data/1d/scan_data/ds{ds}/fits_v3_SELECTED.json')['selected_run']
        yield ds, d / sel, json.loads(need(f'data/1d/scan_data/ds{ds}/{sel}/fit_v3.json').read_text())['points'][ds]

PLATFORM = {'0.1625', '0.1727335'}
def t_robust1d():
    L = []
    for ds, R, P in points1d():
        q = P.get('quoted') or {}; nq = len(P.get('quotable') or [])
        pv = om = '--'
        if q:
            pv = '$' + fexp(pval(q['chi2'], q['dof'])) + '$' if pval(q['chi2'], q['dof']) < 1e-2 else f"{pval(q['chi2'], q['dof']):.2f}"
            r = json.loads(need(str((R / 'fits' / (q['key'] + '.json')).relative_to(PKG))).read_text()); om = f"{r['omega_correction']:.3f}"
        X = json.loads((R / f'xcheck_ds{ds}.json').read_text()).get('paired', {}) if (R / f'xcheck_ds{ds}.json').exists() else {}
        if 'sigma_D' in X:
            D = sorted(X['paired_differences']); n = len(D)
            def pct(p_):
                k = (n - 1) * p_ / 100; i = int(math.floor(k)); return D[i] + (D[min(i + 1, n - 1)] - D[i]) * (k - i)
            sb = (pct(84) - pct(16)) / 2; dif = X['paired_difference_central']
            xc = f"{dif:+.5f} & {dif / X['sigma_D']:+.2f} & {dif / sb:+.2f}"
        else: xc = '-- & -- & --'
        L.append(f"{ds} & {l1(P['decision'])} & {nq} & {pv} & {om} & {xc} & {'P' if ds in PLATFORM else ''} \\\\")
    return L

def theory(path, key):
    with open(need(path)) as fh: return {key(r): r for r in csv.DictReader(fh)}

def t_theory1d():
    T = theory('data/reference/theory_1d_CB8.csv', lambda r: f"{float(r['Delta_sigma']):.7g}")
    scan = {f"{r['ds']:.7g}": r for r in J('data/1d/scan_data/FIT_V3_SCAN.json')}; L = []
    for ds in sorted(T, key=float):
        t_ = T[ds]; r = scan[ds]; v = float(t_['value'])
        band = f"[{float(t_['band_lo']):.4f}, {float(t_['band_hi']):.4f}]"
        if r.get('Delta_epsilon') is not None:
            mc = pm(r['Delta_epsilon'], r['sigma_stat']); kind = 'fit'; dv = r['Delta_epsilon'] - v
        else:
            q = r['pairs'][-1]; mc = f"{q['Delta_eff_U']:.4f}({round(q['sigma_U'] * 1e4)})"; kind = 'largest pair'; dv = q['Delta_eff_U'] - v
        L.append(f"{ds} & {1 - 4 * float(ds):.3f} & {v:.4f} & {band} & {l1(r['status'])} & {kind} & {mc} & {dv:+.4f} \\\\")
    return L

def t_theory23(dim):
    T = theory('data/reference/theory_2d3d_CB8.csv', lambda r: (r['dim'], f"{float(r['s']):g}"))
    P1 = J(E2P1 if dim == 2 else E3P1)['points']; R = records(dim); L = []
    for s, p in P1.items():
        t_ = T[(str(dim), f'{float(s):g}')]; v = float(t_['value']); q = p['quoted'] or {}
        big = R[float(s)][-1]; u4 = big['values'][2]; su4 = big['statistical_stderr'][2]
        val = f"{q['Delta_epsilon']:.5f}" if q else '--'; ss = f(q.get('sigma_stat')) if q else '--'
        sy = f(q.get('sigma_sys')) if q and q.get('sigma_sys') is not None else '--'
        dq = f"{q['Delta_epsilon'] - v:+.4f}" if q else '--'
        L.append(f"{s} & {label(p['decision'])} & {val} & {ss} & {sy} & {pm(u4, su4, 4)} & {v:.4f} & [{float(t_['band_lo']):.4f}, {float(t_['band_hi']):.4f}] & {dq} & {u4 - v:+.4f} \\\\")
    return L

def t_lit1d():
    scan = {f"{r['ds']:.7g}": r for r in J('data/1d/scan_data/FIT_V3_SCAN.json')}; L = []
    with open(need('data/reference/literature_1d.csv')) as fh: rows = sorted(csv.DictReader(fh), key=lambda r: (float(r['Delta_sigma']), r['source']))
    for r in rows:
        ds = f"{float(r['Delta_sigma']):.7g}"; m = scan.get(ds)
        if m and m.get('Delta_epsilon') is not None: ours = pm(m['Delta_epsilon'], m['sigma_stat']) + (f"({round(m['sigma_sys'] * 1e5)})" if m.get('sigma_sys') else ''); lab = l1(m['status']); dv = float(r['DeltaE']) - m['Delta_epsilon']
        elif m: q = m['pairs'][-1]; ours = f"{q['Delta_eff_U']:.4f}({round(q['sigma_U'] * 1e4)}) [finite size]"; lab = l1(m['status']); dv = float(r['DeltaE']) - q['Delta_eff_U']
        else: ours, lab, dv = '--', '--', None
        L.append(f"{ds} & {r['source']}~\\cite{{{r['bibkey']}}} & {r['method']} & {float(r['DeltaE']):.4f}({round(float(r['DeltaE_err']) * 1e4)}) & {ours} & {lab} & {'--' if dv is None else f'{dv:+.4f}'} \\\\")
    return L

LIT_SRC = [('Picco', 'Picco 2012', 'Picco:2012ak'), ('Angelini', 'APR 2014', 'Angelini:2014koy'), ('Xiao', 'Xiao et al.\\ 2025', 'Xiao:2025sk'),
           ('Luijten & Bloete', 'Luijten--Bl\\"ote 1997', 'Luijten:1997cl'), ('Luijten PhD', 'Luijten thesis 1997', 'Luijten:1997th'),
           ('Behan, Lauria', 'Behan et al.\\ 2024', 'Behan:2023ile'), ('Behan, J. Phys', 'Behan 2019', 'Behan:2018hfx'), ('Defenu', 'Defenu et al.\\ 2015', 'Defenu:2014bea')]
def lit_src(paper):
    for k, name, key in LIT_SRC:
        if paper.startswith(k): return f'{name}~\\cite{{{key}}}'
    sys.exit(f'make_note_tables.py: unknown literature source {paper[:40]!r}')
def lit_method(m):
    m = m.lower()
    if 'bootstrap' in m: return 'bootstrap (figure-read)'
    if 'functional rg' in m: return 'functional RG (figure-read)'
    return 'Monte Carlo'
WINDOW = {2: 1.75, 3: 1.963702388}
def t_lit23(dim):
    with open(need(f'data/reference/literature_{dim}d.csv')) as fh: rows = list(csv.DictReader(fh))
    R = records(dim); T = theory('data/reference/theory_2d3d_CB8.csv', lambda r: (r['dim'], float(r['s']))); L = []
    for r in sorted(rows, key=lambda r: (float(r['sigma']), r['paper'])):
        s = float(r['sigma'])
        if not r.get('DeltaE') or not (dim / 2 < s < WINDOW[dim]): continue
        mine = '--'; th = '--'
        for sg, rs in R.items():
            if abs(sg - s) < 1e-6: mine = pm(rs[-1]['values'][2], rs[-1]['statistical_stderr'][2], 4)
        for (dd, sg), v in T.items():
            if dd == str(dim) and abs(sg - s) < 1e-6: th = f"{float(v['value']):.4f}"
        err = f"({round(float(r['DeltaE_err']) * 1e3)})" if r.get('DeltaE_err') not in (None, '', 'nan') else ''
        lm = r['Lmax'].split(' ')[0] if r['Lmax'][:1].isdigit() else '--'
        src = lit_src(r['paper'])
        if r['paper'].startswith('Luijten PhD'):   # two analyses at the same s: name the table or section of the thesis
            m = re.match(r'(Table|Sec\.) ([0-9.]+[0-9])', r['location'])
            if m: src += f", {'Tab.' if m.group(1) == 'Table' else 'Sec.'}~{m.group(2)}"
        L.append(f"{s:g} & {src} & {lit_method(r['method'])} & {lm} & {float(r['DeltaE']):.3f}{err} & {mine} & {th} \\\\")
    return L

def fig_theory():
    out = {}
    T1 = theory('data/reference/theory_1d_CB8.csv', lambda r: float(r['Delta_sigma']))
    out['fig1d_cb8'] = [f"({k:.7g},{float(v['value']):.5f})" for k, v in sorted(T1.items())]
    T = theory('data/reference/theory_2d3d_CB8.csv', lambda r: (r['dim'], float(r['s'])))
    for d in ('2', '3'): out[f'fig{d}d_cb8'] = [f"({k[1]:g},{float(v['value']):.5f})" for k, v in sorted(T.items()) if k[0] == d]
    p = J(E3P1)['points']['1.6']['quoted']
    out['fig3d_star_stat'] = [f"(1.6,{p['Delta_epsilon']:.5f}) +- (0,{p['sigma_stat']:.5f})"]
    out['fig3d_star_sys'] = [f"(1.6,{p['Delta_epsilon']:.5f}) +- (0,{p['sigma_sys']:.5f})"]
    return out


RL = 'results/1d/robust_ladder_20261013'
def t_robustladder():
    """1D: production vs the frozen ('trimmed') ladder and the robust ladder, both refitted in one job on one node (diagnostic)."""
    L = []
    for ds, R, P in points1d():
        rows = [P]
        for v in ('trimmed', 'robust'):
            rows.append(json.loads(need(f'{RL}/{v}/ds{ds}/fit_v3.json').read_text())['points'][ds])
        cells = []
        for X in rows:
            sy = (X.get('sigma_sys') or {}).get('value')
            cells.append(f"{l1(X['decision'])} & {len(X.get('quotable') or [])} & {'--' if sy is None else f'{sy:.5f}'}")
        q = [(X.get('quoted') or {}).get('Delta_epsilon') for X in rows]
        dq = '--' if q[0] is None or q[2] is None else f'{abs(q[2] - q[0]):.0e}'
        ch = 'label' if l1(rows[2]['decision']) != l1(rows[1]['decision']) else ('$n_q$' if len(rows[2].get('quotable') or []) != len(rows[1].get('quotable') or []) else '')
        L.append(f"{ds} & " + ' & '.join(cells) + f" & {dq} & {ch} \\\\")
    return L

def fig_1d():
    scan = sorted(J('data/1d/scan_data/FIT_V3_SCAN.json'), key=lambda r: r['ds']); acc, accsys, oth, cr, lp = [], [], [], [], []
    for r in scan:
        if r.get('Delta_epsilon') is not None:
            a = r['status'].startswith('ACCEPTED')
            (acc if a else oth).append(f"({r['ds']:.7g},{r['Delta_epsilon']:.5f}) +- (0,{r['sigma_stat']:.5f})")
            if a and r['sigma_sys']: accsys.append(f"({r['ds']:.7g},{r['Delta_epsilon']:.5f}) +- (0,{r['sigma_sys']:.5f})")
        if r.get('Delta_inf') is not None: cr.append(f"({r['ds']:.7g},{r['Delta_inf']:.5f}) +- (0,{r['sigma_inf']:.5f})")
        if r.get('Delta_epsilon') is None and r.get('pairs'): q = r['pairs'][-1]; lp.append(f"({r['ds']:.7g},{q['Delta_eff_U']:.4f}) +- (0,{q['sigma_U']:.4f})")
    with open(PKG / 'data/1d/reference/published_and_epsilon_reference.csv') as fh: ref = list(csv.DictReader(fh))
    pub = [f"({float(r['Delta_sigma']):.7g},{float(r['published_MC_Delta_epsilon']):.4f}) +- (0,{float(r['published_MC_quoted_error']):.4f})" for r in ref if r['published_MC_Delta_epsilon']]
    eps = [f"({float(r['Delta_sigma']):.7g},{float(r['six_loop_endpoint_assisted']):.4f})" for r in sorted(ref, key=lambda r: float(r['Delta_sigma']))]
    return {'fig1d_accepted': acc, 'fig1d_accepted_sys': accsys, 'fig1d_other': oth, 'fig1d_crossing': cr, 'fig1d_largestpair': lp, 'fig1d_published': pub}

def fig_23(dim):
    R = records(dim); out = {}
    for k in (0, 3):
        out[f'fig{dim}d_U4_pair{k}'] = [f"({s:g},{rows[k]['values'][2]:.4f}) +- (0,{rows[k]['statistical_stderr'][2]:.4f})" for s, rows in R.items()]
        out[f'fig{dim}d_Y_pair{k}'] = [f"({s:g},{rows[k]['values'][1]:.4f}) +- (0,{rows[k]['statistical_stderr'][1]:.4f})" for s, rows in R.items()]
    return out

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('outdir', type=Path); p.add_argument('--check', type=Path); p.add_argument('--root', type=Path); a = p.parse_args()
    global PKG
    if a.root: PKG = a.root.resolve()
    a.outdir.mkdir(parents=True, exist_ok=True)
    T = {'1d_final': final_rows((PKG / 'results/1d/tables/final_table_rows.tex').read_text().splitlines()),
         '1d_pairs': (PKG / 'results/1d/tables/largest_pairs_rows.tex').read_text().splitlines(),
         '1d_pre': (PKG / 'results/1d/tables/pre_rows.tex').read_text().splitlines(),
         '1d_eps': t_eps(), '1d_oned': t_oned(), '2d_pairs': t_pairs(2), '3d_pairs': t_pairs(3), '2d_series': t_series(2), '3d_series': t_series(3),
         '2d_decisions': t_decisions(2), '3d_decisions': t_decisions(3), 'calib_2d': t_calib(2), 'calib_3d': t_calib(3)}
    if not (PKG / REFIT).is_dir(): sys.exit(f'make_note_tables.py: required input {REFIT} is missing')
    T['1d_refit'] = t_refit(); T['1d_d3'] = t_d3()
    T['1d_robust'] = t_robust1d(); T['1d_theory'] = t_theory1d(); T['2d_theory'] = t_theory23(2); T['3d_theory'] = t_theory23(3)
    T['1d_lit'] = t_lit1d(); T['2d_lit'] = t_lit23(2); T['3d_lit'] = t_lit23(3); T['1d_robustladder'] = t_robustladder()
    figs = {**fig_1d(), **fig_23(2), **fig_23(3), **fig_theory()}
    for k, v in figs.items(): T[k] = [' '.join(v)]
    for k, v in T.items(): (a.outdir / f'{k}.tex').write_text('\n'.join(v) + '\n')
    print(f'wrote {len(T)} files to {a.outdir}')
    if a.check:
        note = a.check.read_text(); missing = [(k, l) for k, v in T.items() for l in v if l.strip() and l.strip() not in note]
        for k, l in missing[:20]: print(f'NOT IN NOTE [{k}]: {l[:150]}')
        print(f'check: {sum(len(v) for v in T.values()) - len(missing)} of {sum(len(v) for v in T.values())} generated lines found verbatim in {a.check.name}')
        sys.exit(1 if missing else 0)

if __name__ == '__main__': main()
