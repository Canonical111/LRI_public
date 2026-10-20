#!/usr/bin/env python3
"""Aggregate the model-independent lens: see analyze_core.py for selection/calibration rules.
usage: analyze.py RUNDIR   (env MI_LIGHT=1: families table only; MI_LOS=12,16,..: restrict lower edges; MI_OUT name)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_core import *
if LIGHT:
    OUT['settings'] = dict(FAC=FAC, NOISE=NOISE, BMAX=BMAX, run=RUN, light=True, los=LOS_KEEP)
    json.dump(OUT, open(os.path.join(RUN, OUTNAME + '.json'), 'w'), indent=1, default=float)
    for lab, ent in TAB.items():
        c8 = ent.get('C8') or {}
        print(lab, 'C8 uncal %s cal %s N %s' % (c8.get('uncal_median'), c8.get('cal_median'), c8.get('N_cal')),
              ' '.join('C%d %s' % (n, ent['C%d' % n].get('rel_median_x1e3')) for n in range(4, 8)))
    sys.exit(0)

# ----------------------------------------------------------------------------------------------- delta propagation
ECACHE = {}


def evals(L, om, level, n):
    key = (L, om, level, n)
    if key not in ECACHE:
        w = omegas_for(level, n, om)
        ECACHE[key] = [float(x) for x in eseries(mp.log(L), w, n - 2)]
    return ECACHE[key]


def modelled_L(k):
    return [L for L in V[k]['L'] if L in D['dC'][k] and not D['exact'][k][L]]


def dC_shift_sets(k):
    """list of (label, {L: delta dC_k}) for every kept variant and the envelope edges."""
    Lm = modelled_L(k); cen = {L: D['dC'][k][L] for L in Lm}
    out = []
    for i, lab in enumerate(V[k]['labels']):
        out.append(('v%d' % i, {L: V[k]['pred'][i][V[k]['L'].index(L)] - cen[L] for L in Lm}))
    for s in (+1, -1):
        out.append(('env%+d' % s, {L: s * D['unc'][k][L] for L in Lm}))
        out.append(('typ%+d' % s, {L: s * D['unc_typ'][k][L] for L in Lm}))
    return out


def shifted_cvals(fam, k, dsh):
    """intercepts of every configuration of a dconn family with dC_k shifted by dsh (L -> delta), linear response."""
    kind, mode, level, om, hi = fam
    F = R[fam]; out = {}
    for key, rows in F.items():
        wts = W[key + (hi,)]
        dlim = {}
        for n in sorted(rows):
            r = rows[n]
            if n < k:
                out[(key, n)] = r['c']; continue
            wd = wts[r['wkey']]; Ls = wd['L']; w = np.array(wd['w'])
            omn = om if om in OMSETS else None
            if omn is None:      # wf_eff: omegas differ per config; use wf (second-order effect on the response)
                omn = 'wf'
            dS = np.zeros(len(Ls))
            for a, L in enumerate(Ls):
                e = evals(L, omn, level, n)
                s = e[n - k] * dsh.get(L, 0.0)
                if mode == 'S':
                    for j in range(1, n - 3):
                        m = n - j
                        if m >= 4:
                            s -= e[j] * dlim.get(m, 0.0)
                dS[a] = s
            dc = float(w @ dS)
            out[(key, n)] = r['c'] + dc
            if mode == 'S' and n >= 4:
                dlim[n] = dc
    return out


PROP = {}
for name in ('LSQ-full E wf (primary)', 'LSQ-full3 E wf (+l^2 T2)', 'LSQ-full E raw-omega', 'LSQ-full S wf (self-consistent)'):
    for hi in (60, 72, 92, 118):
        fam = FAMS[name] + (hi,)
        if fam not in R:
            continue
        base8, sel8 = c8_family(fam) if hi <= 92 else (None, None)
        basen = {n: lower_family(fam, n) for n in range(6, 8)}
        ent = {}
        for k in (6, 7, 8):
            if k == 8 and hi > 92:
                continue
            sh = collections.defaultdict(list)
            for lab, dsh in dC_shift_sets(k):
                if not any(L <= hi for L in dsh):
                    continue
                cv = shifted_cvals(fam, k, dsh)
                if base8 and base8.get('N_cal'):
                    s8, _ = c8_family(fam, cv, sel8)
                    for q in ('uncal_median', 'cal_median', 'all_adequate_median'):
                        sh['C8_' + q].append((lab, s8[q] - base8[q]))
                for n in range(max(6, k), 8):
                    b, sl = basen[n]
                    if b.get('N_adequate'):
                        s, _ = lower_family(fam, n, cv, sl)
                        sh['C%d_median' % n].append((lab, s['median'] - b['median']))
                        if b.get('N_cal'):
                            sh['C%d_cal_median' % n].append((lab, s['cal_median'] - b['cal_median']))
            summ = {}
            for q, lst in sh.items():
                vv = np.array([x for lab, x in lst if lab.startswith('v')])
                d = dict(n_var=len(vv))
                if len(vv):
                    d.update(min=float(vv.min()), max=float(vv.max()), halfrange=float((vv.max() - vv.min()) / 2),
                             std=float(vv.std()))
                for lab, x in lst:
                    if not lab.startswith('v'):
                        d[lab] = float(x)
                summ[q] = d
            ent['dC%d' % k] = summ
        PROP['%s|hi%d' % (name, hi)] = ent
OUT['delta_propagation'] = PROP

# residual response to the delta-model extremes (selection robustness)
VR = {}
for hi in (60, 72, 92):
    fam = FAMS['LSQ-full E wf (primary)'] + (hi,)
    _, sel = c8_family(fam)
    fl = floors(fam)
    for k in (6, 7, 8):
        ratios = collections.defaultdict(list)
        for key in sel['cal']:
            for var in ('vmin', 'vmax', 'env+', 'env-'):
                for n in range(k, 9):
                    v = VARRES.get(key + (hi, k, var, 'full', n))
                    if v:
                        ratios[n].append(v['maxres'] / fl[n])
        VR['hi%d_dC%d' % (hi, k)] = {n: dict(max_res_over_floor=float(max(x)), median=float(np.median(x)),
                                              frac_over_FAC=float(np.mean(np.array(x) > FAC))) for n, x in ratios.items()}
OUT['variant_residuals_cal_configs'] = VR

# ----------------------------------------------------------------------------------------------- Jacobian to lower limits
JAC = {}
for hi in (92,):
    fam = FAMS['LSQ-full E wf (primary)'] + (hi,)
    _, sel = c8_family(fam)
    jj = collections.defaultdict(list)
    for key in sel['cal']:
        r = R[fam][key][8]; wd = W[key + (hi,)][r['wkey']]
        for m in range(4, 8):
            g = sum(wd['w'][a] * evals(L, 'wf', 'full', 8)[8 - m] for a, L in enumerate(wd['L']))
            jj[m].append(-g)
    JAC = {m: dict(median=float(np.median(v)), min=float(min(v)), max=float(max(v))) for m, v in jj.items()}
OUT['jacobian_dC8_dlim'] = JAC

# C7 reference alternatives (post hoc truncation-aware -322524, and +-41), through limit and calibration
fam = FAMS['LSQ-full E wf (primary)'] + (92,)
b8, sel = c8_family(fam)
C7ALT = {}
for lab, d7 in (('C7=-322524 (post hoc)', REF7_POSTHOC[0] - REF[7]), ('C7+41', 41.0), ('C7-41', -41.0)):
    cv = {}
    for key, rows in R[fam].items():
        for n, r in rows.items():
            cv[(key, n)] = r['c']
        if 8 in rows:
            wd = W[key + (92,)][rows[8]['wkey']]
            g = sum(wd['w'][a] * evals(L, 'wf', 'full', 8)[1] for a, L in enumerate(wd['L']))
            cv[(key, 8)] = rows[8]['c'] - g * d7
    old = REF[7]; REF[7] = old + d7
    s, _ = c8_family(fam, cv, sel)
    REF[7] = old
    C7ALT[lab] = dict(uncal_median_shift=s['uncal_median'] - b8['uncal_median'], cal_median_shift=s['cal_median'] - b8['cal_median'])
OUT['C7_reference_sensitivity'] = C7ALT

# ----------------------------------------------------------------------------------------------- accelerators
ACC = {}
apath = os.path.join(RUN, 'accel.json')
if os.path.exists(apath):
    AJ = json.load(open(apath))['results']

    def nev_est(nev, fam_sel, dA=None):
        a = np.array(nev['A']) + (dA if dA is not None else 0); b = np.array(nev['B'])
        keys = [tuple(k) for k in nev['keys']]
        if fam_sel == 'N>=6,step>=2':
            sel = [i for i, k in enumerate(keys) if k[0] >= 2 and k[1] >= 6]
        elif fam_sel == 'step>=2':
            sel = [i for i, k in enumerate(keys) if k[0] >= 2]
        else:
            sel = list(range(len(keys)))
        am = a[sel] - a[sel].mean(); bm = b[sel] - b[sel].mean()
        w = -np.dot(am, bm) / np.dot(bm, bm)
        e = a[sel] + w * b[sel]
        return float(np.median(e)), float(w), float(e.std())

    cen = {}
    for r in AJ:
        if r['tag'] != 'central':
            continue
        lab = '%s %s %s top%d' % (r['kind'], r['mode'], r['om'], r['top'])
        ent = {}
        for n, e in r['n'].items():
            n = int(n)
            t = target(r['kind'], 'H' if r['mode'] == 'H' else 'E', n)
            nv, w, sp = nev_est(e['neville'], 'N>=6,step>=2')
            nva, _, _ = nev_est(e['neville'], 'all')
            ent[n] = dict(neville=nv, neville_rel_x1e3=(nv - t) / abs(t) * 1e3, neville_w=w, neville_spread=sp,
                          neville_all=nva, neville_all_rel_x1e3=(nva - t) / abs(t) * 1e3,
                          bst=e['bst']['est_med'], bst_rel_x1e3=(e['bst']['est_med'] - t) / abs(t) * 1e3, bst_w=e['bst']['w'],
                          bst_spread=e['bst']['spread'])
        for meth in ('neville', 'bst'):
            if 8 in ent and all(n in ent for n in range(4, 8)):
                bb = np.mean([ent[n][meth + '_rel_x1e3'] / 1e3 for n in range(4, 8)])
                ent['C8_%s_cal' % meth] = ent[8][meth] * (1 - bb)
                ent['C8_%s_cal_b7' % meth] = ent[8][meth] * (1 - ent[7][meth + '_rel_x1e3'] / 1e3)
        ACC[lab] = ent
        cen[(r['kind'], r['mode'], r['om'], r['top'])] = r
    # Neville delta propagation (dconn E wf), linear
    NP = {}
    for top in (84, 88, 92, 118):
        r = cen.get(('dconn', 'E', 'wf', top))
        if r is None:
            continue
        base = {}
        for n in range(6, 9):
            if str(n) in r['n']:
                base[n] = nev_est(r['n'][str(n)]['neville'], 'N>=6,step>=2')[0]
        tops = {}
        for k in (6, 7, 8):
            if k == 8 and top > 92:
                continue
            res = collections.defaultdict(list)
            for lab, dsh in dC_shift_sets(k):
                for n in range(k, 9):
                    if str(n) not in r['n']:
                        continue
                    nev = r['n'][str(n)]['neville']
                    dA = []
                    for setd in nev['nu']:
                        dA.append(sum(nu * evals(L, 'wf', 'full', n)[n - k] * dsh.get(L, 0.0) for nu, L in zip(setd['nu'], setd['L'])))
                    res[n].append((lab, nev_est(nev, 'N>=6,step>=2', np.array(dA))[0] - base[n]))
            tops['dC%d' % k] = {n: dict(halfrange=float((max(x for l, x in v if l.startswith('v')) - min(x for l, x in v if l.startswith('v'))) / 2),
                                        **{l: float(x) for l, x in v if not l.startswith('v')}) for n, v in res.items()}
        NP['top%d' % top] = tops
    ACC['_neville_delta_propagation'] = NP
    # BST extremes
    BX = collections.defaultdict(dict)
    for r in AJ:
        if r['tag'] == 'central' or r['kind'] != 'dconn':
            continue
        c = cen[('dconn', 'E', 'wf', r['top'])]
        for n, e in r['n'].items():
            BX['top%d|%s' % (r['top'], r['tag'])][n] = e['bst']['est_med'] - c['n'][n]['bst']['est_med']
    ACC['_bst_delta_extremes'] = BX
OUT['accelerators'] = ACC
OUT['settings'] = dict(FAC=FAC, NOISE=NOISE, BMAX=BMAX, run=RUN, corrected=D['path'], variants=VAR_PATH)
json.dump(OUT, open(os.path.join(RUN, OUTNAME + '.json'), 'w'), indent=1, default=float)

# ----------------------------------------------------------------------------------------------- printout
def fmt(x, nd=0):
    return ('%.' + str(nd) + 'f') % x if x is not None else '-'


print('settings FAC %g NOISE %g BMAX %g' % (FAC, NOISE, BMAX))
print('\n=== C8 per family (uncal = median over calibrated set; cal = c8*(1-mean b4..7)); biases x1e3 at n=3..7')
for lab, ent in TAB.items():
    c8 = ent.get('C8')
    if not c8 or not c8.get('N_cal'):
        if c8:
            print('%-58s Nadq %3d Ncal 0  all-adq med %s' % (lab, c8['N_adequate'], fmt(c8.get('all_adequate_median'))))
        continue
    print('%-58s Nadq %3d Ncal %3d | uncal %9.0f [%9.0f,%9.0f] | cal %9.0f [%9.0f,%9.0f] | alt b7 %9.0f m67 %9.0f lin %9.0f m37 %9.0f | b %s' % (
        lab, c8['N_adequate'], c8['N_cal'], c8['uncal_median'], *c8['uncal_range'], c8['cal_median'], *c8['cal_range'],
        c8['cal_alt']['b7'], c8['cal_alt']['mean67'], c8['cal_alt']['lintrend47'], c8['cal_alt']['mean37'],
        ' '.join('%+.2f' % c8['bias_median_x1e3'][n] for n in range(3, 8))))
print('\n=== C3..C7 per family: median over adequate (rel x1e3 vs target) | held-out calibrated (rel x1e3)')
for lab, ent in TAB.items():
    s = '%-58s' % lab
    for n in range(3, 8):
        e = ent.get('C%d' % n, {})
        if e.get('N_adequate'):
            s += ' | C%d %3d %+7.3f' % (n, e['N_adequate'], e['rel_median_x1e3'])
            if e.get('N_cal'):
                s += ' cal %+7.3f' % e['cal_rel_x1e3']
    print(s)
print('\n=== delta-model propagation (half-range over kept variants; env+-1 = full envelope edges)')
for lab, ent in PROP.items():
    for k, summ in ent.items():
        for q, d in summ.items():
            if d.get('n_var'):
                print('%-40s %s %-24s halfrange %.3g  env+ %.3g env- %.3g typ+ %.3g' % (lab, k, q, d['halfrange'], d.get('env+1', np.nan), d.get('env-1', np.nan), d.get('typ+1', np.nan)))
print('\n=== residual response (cal configs) to delta extremes: max res/floor')
for lab, ent in VR.items():
    print(lab, {n: '%.2g (%.0f%%>FAC)' % (d['max_res_over_floor'], 100 * d['frac_over_FAC']) for n, d in ent.items()})
print('\nJacobian dC8/dlim_m (primary cal set, hi92):', {m: '%.0f [%.0f,%.0f]' % (d['median'], d['min'], d['max']) for m, d in JAC.items()})
print('C7 reference sensitivity:', C7ALT)
if ACC:
    print('\n=== accelerators: rel x1e3 at n=3..7 (Neville N>=6,step>=2 | BST), C8 raw & calibrated')
    for lab, ent in ACC.items():
        if lab.startswith('_'):
            continue
        s = '%-28s' % lab
        for n in range(3, 8):
            if n in ent:
                s += ' n%d %+6.2f|%+6.2f' % (n, ent[n]['neville_rel_x1e3'], ent[n]['bst_rel_x1e3'])
        if 8 in ent:
            s += ' | C8 nev %.0f cal %.0f | bst %.0f cal %.0f' % (ent[8]['neville'], ent.get('C8_neville_cal', np.nan), ent[8]['bst'], ent.get('C8_bst_cal', np.nan))
        print(s)
    print('Neville delta propagation:', json.dumps(ACC['_neville_delta_propagation'])[:3000])
    print('BST extremes:', json.dumps(ACC['_bst_delta_extremes'])[:3000])
