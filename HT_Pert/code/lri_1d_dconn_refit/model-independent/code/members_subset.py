#!/usr/bin/env python3
"""refit72: delta-model propagation restricted to data-consistent member subsets (exact member propagation from
members_prop.npz; selection of the primary run held fixed, as in members_analyze.py).

With dC exact to L = 72 the kept delta-v1 ensemble contains many members whose value at the last exact point misses the
exact data by >> the S10 noise (seam residual at L = 72: dC7 median 3.6e-7 vs noise rms 1.3e-8). Used as a continuation
('seam' type: exact to 72, member beyond) they put a step into the data that the LSQ fits cannot absorb; the published
envelope (half-range at L = 74: 1.9e-5 for dC7) is dominated by such members. 'smooth' type (member - central added at
every L, including the exact points) avoids the step but perturbs the exact data by the member's misfit.
Subsets: all | mi_cons (member keeps >= 50 % of the calibrated configurations adequate, members_analyze rule) |
floor (maxres <= QF x best maxres of the same training window, the delta stage's floor-level rule, QF = 3) |
floor_cons (both).
usage: members_subset.py GRID_RUNDIR MEMBERS_RUNDIR OUT.json
"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('MI_LIGHT', '1')
RUN, MRUN, OUTP = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = [sys.argv[0], RUN]
import importlib.util
spec = importlib.util.spec_from_file_location('an', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analyze_core.py'))
an = importlib.util.module_from_spec(spec); spec.loader.exec_module(an)
np = an.np
QF = float(os.environ.get('MI_QF', 3))
Z = np.load(os.path.join(MRUN, 'members_prop.npz'))
I = json.load(open(os.path.join(MRUN, 'members_prop_index.json')))
MF = json.load(open(os.path.join(MRUN, 'members_full.json')))
CI = {(e['cfg']['tails'], e['cfg']['lead'], e['cfg']['lo'], e['cfg']['hi']): i for i, e in enumerate(I['index'])}
V = an.V
FLOOR = {}
for k in (6, 7, 8):
    mr = V[k]['maxres']; lo = np.array([int(s.split('lo=')[1].split('|')[0]) for s in V[k]['labels']])
    best = {l: mr[lo == l].min() for l in set(lo)}
    FLOOR[k] = np.array([mr[i] <= QF * best[lo[i]] for i in range(len(mr))])
OUT = dict(QF=QF, n_floor={k: int(FLOOR[k].sum()) for k in FLOOR},
           seam_resid_at_72={k: dict(all_median=float(np.median(np.abs(MF[str(k)]['seam_residual_at_hi']))),
                                     floor_median=float(np.median(np.abs(np.array(MF[str(k)]['seam_residual_at_hi'])[FLOOR[k]]))),
                                     floor_max=float(np.max(np.abs(np.array(MF[str(k)]['seam_residual_at_hi'])[FLOOR[k]]))))
                             for k in FLOOR},
           families={})
FAC = an.FAC
for level, mode, hi in (('full', 'E', 92), ('full3', 'E', 92), ('full', 'E', 118), ('full', 'S', 92), ('full', 'E', 72)):
    fam = ('dconn', mode, level, 'wf', hi)
    fl = an.floors(fam)
    base8, sel8 = an.c8_family(fam) if hi <= 92 else (None, None)
    low = {n: an.lower_family(fam, n) for n in range(4, 8)}
    ent = {}
    for typ in ('seam', 'smooth'):
        for k in (6, 7, 8):
            key = '%s_%s_%s_hi%d_k%d' % (mode, typ, level, hi, k)
            if 'dc_' + key not in Z:
                continue
            DC = Z['dc_' + key]; MR = Z['mr_' + key]; nm = DC.shape[1]
            rows = collections.defaultdict(list)
            for i in range(nm):
                cv = {}
                for key3, nrows in an.R[fam].items():
                    ci = CI[key3 + (hi,)]
                    for n, r in nrows.items():
                        d = DC[ci, i, n] if n >= k and np.isfinite(DC[ci, i, n]) else 0.0
                        cv[(key3, n)] = r['c'] + d
                ref_sel = sel8['cal'] if sel8 else low[7][1]['adq']
                ok = [all(MR[CI[key3 + (hi,)], i, n] <= FAC * fl[n] for n in range(k, 9) if np.isfinite(MR[CI[key3 + (hi,)], i, n]))
                      for key3 in ref_sel]
                rows['cons'].append(float(np.mean(ok)) if ok else np.nan)
                if sel8 and sel8['cal']:
                    s8, _ = an.c8_family(fam, cv, sel8)
                    rows['C8_uncal'].append(s8['uncal_median'] - base8['uncal_median'])
                    rows['C8_cal'].append(s8['cal_median'] - base8['cal_median'])
                for n in range(max(6, k), 8):
                    b, sl = low[n]
                    if b.get('N_adequate'):
                        s, _ = an.lower_family(fam, n, cv, sl)
                        rows['C%d' % n].append(s['median'] - b['median'])
                        if b.get('N_cal'):
                            rows['C%d_cal' % n].append(s['cal_median'] - b['cal_median'])
            cons = np.array(rows.pop('cons')) >= 0.5
            subsets = dict(all=np.ones(nm, bool), mi_cons=cons, floor=FLOOR[k], floor_cons=FLOOR[k] & cons)
            summ = {nm_: dict(n=int(m.sum())) for nm_, m in subsets.items()}
            for q, v in rows.items():
                v = np.array(v)
                for nm_, m in subsets.items():
                    if m.sum() >= 2:
                        summ[nm_][q] = dict(std=float(v[m].std()), halfrange=float((v[m].max() - v[m].min()) / 2),
                                            min=float(v[m].min()), max=float(v[m].max()))
            ent['%s_k%d' % (typ, k)] = summ
    OUT['families']['%s %s hi%d' % (level, mode, hi)] = ent
# quadrature totals over k
TOT = {}
for fk, ent in OUT['families'].items():
    for typ in ('seam', 'smooth'):
        for sub in ('all', 'mi_cons', 'floor', 'floor_cons'):
            for q in ('C6', 'C7', 'C8_uncal', 'C8_cal', 'C6_cal', 'C7_cal'):
                per = {k: ent.get('%s_k%d' % (typ, k), {}).get(sub, {}).get(q) for k in (6, 7, 8)}
                per = {k: v for k, v in per.items() if v}
                if per:
                    TOT['%s|%s|%s|%s' % (fk, typ, sub, q)] = dict(
                        std=float(np.sqrt(sum(v['std'] ** 2 for v in per.values()))),
                        halfrange=float(np.sqrt(sum(v['halfrange'] ** 2 for v in per.values()))),
                        per_k_std={k: round(v['std'], 3) for k, v in per.items()},
                        n={k: ent['%s_k%d' % (typ, k)][sub]['n'] for k in per})
OUT['totals'] = TOT
json.dump(OUT, open(OUTP, 'w'), indent=1)
print('QF', QF, 'n_floor', OUT['n_floor'], 'seam |resid| at 72', json.dumps(OUT['seam_resid_at_72']))
for key, v in TOT.items():
    if key.split('|')[0] in ('full E hi92', 'full3 E hi92', 'full E hi118', 'full E hi72') and key.split('|')[3] in ('C6', 'C7', 'C8_uncal', 'C8_cal'):
        print('%-50s std %9.3g hr %9.3g per-k std %s n %s' % (key, v['std'], v['halfrange'], v['per_k_std'], v['n']))
