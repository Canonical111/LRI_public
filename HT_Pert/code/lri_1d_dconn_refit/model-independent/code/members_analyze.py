#!/usr/bin/env python3
"""Delta-model error propagation from the exact member propagation (members_prop.npz) for the LSQ families, with the
configuration selection of the medoid-central run held fixed.

For each member of dC_k (k = 6, 7, 8) and each propagation type ('seam': member replaces the modelled dC only at
L > 44; 'smooth': member - medoid added at every L) the family statistics are recomputed with the shifted intercepts
(calibration biases b6, b7 shifted consistently). Each member also gets a data-consistency score: the fraction of the
family's calibrated configurations that stay adequate (max residual <= FAC x floor at every order n >= k) once that
member is used; 'consistent' members keep >= 50 %.
usage: members_analyze.py GRID_RUNDIR MEMBERS_RUNDIR
"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('MI_LIGHT', '1')
RUN, MRUN = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], RUN]
import importlib.util
spec = importlib.util.spec_from_file_location('an', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analyze_core.py'))
an = importlib.util.module_from_spec(spec); spec.loader.exec_module(an)
np = an.np

Z = np.load(os.path.join(MRUN, 'members_prop.npz'))
I = json.load(open(os.path.join(MRUN, 'members_prop_index.json')))
CI = {(e['cfg']['tails'], e['cfg']['lead'], e['cfg']['lo'], e['cfg']['hi']): i for i, e in enumerate(I['index'])}
OUT = {'checks': {}, 'families': {}}

# consistency of the base values with the grid run
mx = 0.0
for (t, l, lo, hi), i in CI.items():
    for level in ('full', 'full3'):
        b = I['index'][i]['base'].get(level, {})
        for mn, (c, mres) in b.items():
            mode, n = mn[0], int(mn[1:])
            fam = ('dconn', mode, level, 'wf', hi)
            r = an.R[fam].get((t, l, lo), {}).get(n)
            if r:
                mx = max(mx, abs(c - r['c']) / max(1.0, abs(r['c'])))
OUT['checks']['base_vs_grid_maxrel'] = mx
print('base vs grid max rel diff %.1e' % mx)

FAC = an.FAC
for level in ('full', 'full3'):
    for mode in ('E', 'S'):
        for hi in (72, 92, 118):
            fam = ('dconn', mode, level, 'wf', hi)
            if fam not in an.R:
                continue
            fl = an.floors(fam)
            base8, sel8 = an.c8_family(fam) if hi <= 92 else (None, None)
            low = {n: an.lower_family(fam, n) for n in range(4, 8)}
            ent = {}
            for typ in ('seam', 'smooth'):
                for k in (6, 7, 8):
                    key = '%s_%s_%s_hi%d_k%d' % (mode, typ, level, hi, k)
                    if 'dc_' + key not in Z:
                        continue
                    DC = Z['dc_' + key]; MR = Z['mr_' + key]
                    nm = DC.shape[1]
                    rows = collections.defaultdict(list)
                    for i in range(nm):
                        cv = {}
                        for key3, nrows in an.R[fam].items():
                            ci = CI[key3 + (hi,)]
                            for n, r in nrows.items():
                                d = DC[ci, i, n] if n >= k and np.isfinite(DC[ci, i, n]) else 0.0
                                cv[(key3, n)] = r['c'] + d
                        # consistency score over the calibrated (or adequate-at-7) configurations
                        ref_sel = sel8['cal'] if sel8 else low[7][1]['adq']
                        ok = []
                        for key3 in ref_sel:
                            ci = CI[key3 + (hi,)]
                            ok.append(all(MR[ci, i, n] <= FAC * fl[n] for n in range(k, 9) if np.isfinite(MR[ci, i, n])))
                        rows['consistent_frac'].append(float(np.mean(ok)) if ok else np.nan)
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
                    cf = np.array(rows['consistent_frac'])
                    good = cf >= 0.5
                    summ = dict(n_members=nm, n_consistent=int(good.sum()), consistent_frac_median=float(np.nanmedian(cf)))
                    for q, v in rows.items():
                        if q == 'consistent_frac':
                            continue
                        v = np.array(v)
                        d = dict(halfrange=float((v.max() - v.min()) / 2), std=float(v.std()), min=float(v.min()), max=float(v.max()),
                                 p16_p84=[float(np.percentile(v, 16)), float(np.percentile(v, 84))])
                        if good.sum() >= 3:
                            vg = v[good]
                            d.update(cons_halfrange=float((vg.max() - vg.min()) / 2), cons_std=float(vg.std()),
                                     cons_p16_p84=[float(np.percentile(vg, 16)), float(np.percentile(vg, 84))])
                        summ[q] = d
                    ent['%s_k%d' % (typ, k)] = summ
            OUT['families']['%s %s hi%d' % (level, mode, hi)] = ent
json.dump(OUT, open(os.path.join(MRUN, 'members_analysis.json'), 'w'), indent=1)
for fam, ent in OUT['families'].items():
    for tk, s in ent.items():
        line = '%-16s %-10s cons %2d/%2d' % (fam, tk, s['n_consistent'], s['n_members'])
        for q in ('C6', 'C7', 'C8_uncal', 'C8_cal'):
            if q in s:
                line += ' | %s hr %.3g std %.3g%s' % (q, s[q]['halfrange'], s[q]['std'],
                                                    (' [cons hr %.3g std %.3g]' % (s[q]['cons_halfrange'], s[q]['cons_std'])) if 'cons_std' in s[q] else '')
        print(line)
