#!/usr/bin/env python3
"""Smooth central continuations of dC6..dC8 for the hi = 72 delta-v1 rebuild, built exactly as the two downstream
lenses built theirs from the hi = 44 model, plus comparisons with the earlier (hi = 44) model.

  median     the published central (pointwise median of the kept fits); not smooth.
  medoid     model-independent lens (model-independent/code/common.py smooth_central, copied to lens_compat/mi_common.py):
             the ONE kept fit closest to the median, rms of (pred - median)/dC_unc over the modelled L.
  floormean  joint lens (joint/code/data.py prescription 'dconn', copied to lens_compat/joint_data.py): mean of the kept
             fits with maxres <= 3 x the best maxres in the same training window.
  floormedoid ONE floor-level kept fit (maxres <= 3 x window best) closest to the floor-mean (rms of (pred - floormean)/dC_unc
             over the modelled L). A single smooth member like the medoid, but joining the exact values at the noise level;
             usable in the MI lens as DCONN_CENTRAL='k6:i,k7:j,k8:l'.
Also: member std / half-range per L (for correlated propagation), seam misfit at the last exact point, noise of the new
exact points (residual of the smooth curves at L = 46..72), roughness, and three ready-to-use corrected files
  <tag>_medoid_corrected.json      exact dC to 72, medoid beyond          (what the MI lens would build)
  <tag>_floormean_corrected.json   exact dC to 72, floor-mean beyond      (what the joint lens would build)
  <tag>_floormedoid_corrected.json exact dC to 72, floor-level medoid beyond   (recommended single-member central)
  <tag>_floormean_s46_corrected.json exact dC to 44 (quiet S10 archive), floor-mean curve at every L >= 46 (the noisy
                                   S10 cluster points 46..72 replaced by the smooth fit through them; sensitivity option)
Usage: smooth_central.py [--tag delta_v1_hi72]"""
import sys, os, json, copy, argparse, hashlib
from math import comb
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'lens_compat'))
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--tag', default='delta_v1_hi72')
a = ap.parse_args()
OUT = os.path.normpath(os.path.join(HERE, '..', 'out'))
ARCH = '<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit'
NEW = dict(corr=f'{OUT}/{a.tag}_corrected.json', var=f'{OUT}/{a.tag}_variants.json', vfull=f'{OUT}/variants_full_hi72.json')
OLD = dict(corr=f'{ARCH}/delta/out/delta_v1_corrected.json', var=f'{ARCH}/delta/out/delta_v1_variants.json',
           vfull=f'{ARCH}/joint/out/variants_full.json')
os.environ['DCONN_CENTRAL'] = 'medoid'
import mi_common
import joint_data


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def sig(y):
    s = {kk: float(np.sqrt(np.mean(np.diff(y, kk) ** 2)) / np.sqrt(comb(2 * kk, kk))) for kk in range(3, min(len(y) - 3, 22))}
    return min(s.values())


def build(P):
    mi_common.VAR_PATH = P['var']
    D = mi_common.load_corrected(P['corr'])            # medoid applied at the modelled L
    J = joint_data.load(corr=P['corr'], vfull=P['vfull'], with_perts=False)
    pub = json.load(open(P['corr']))
    V = mi_common.load_variants(P['var'])
    VF = json.load(open(P['vfull']))
    res = {}
    for k in (6, 7, 8):
        ms = pub['model_summary']['dC%d' % k]
        Lm = ms['L']; hi = ms['hi_exact']
        Lseq = [r['L'] for r in pub['sequences']['C%d' % k]]
        Lmod = [L for L in Lm if L in Lseq]                    # modelled L inside the corrected sequence
        jL = list(J['L'].astype(int))
        floor = [float(J['dconn'][jL.index(L), k] - J['raw'][jL.index(L), k]) for L in Lmod]
        Pv = V[k]['pred']; iv = [V[k]['L'].index(L) for L in Lmod]
        mem = D['central_members'][k]['member']
        b = VF['dC%d' % k]; Pf = np.array(b['pred']); Lf = b['L']
        exact = {int(L): v for L, v in b['exact'].items()}
        Lx = sorted(exact)
        # floor-level member set (joint definition) for full-L floor-mean curve
        mr = np.array(b['maxres']); lo = np.array([int(s.split('lo=')[1].split('|')[0]) for s in b['labels']])
        best = {l: mr[lo == l].min() for l in set(lo)}
        fl = np.array([mr[i] <= joint_data.QF * best[lo[i]] for i in range(len(mr))])
        imf = [Lf.index(L) for L in Lmod]
        uncm = np.array([ms['unc'][Lm.index(L)] for L in Lmod])
        fmc = Pf[fl].mean(0)
        fidx = np.where(fl)[0]
        dfl = np.sqrt(np.mean(((Pf[fidx][:, imf] - fmc[imf]) / uncm) ** 2, 1))
        fmem = int(fidx[np.argmin(dfl)])
        cur = dict(medoid=Pf[mem], floormean=fmc, floormedoid=Pf[fmem], mean=Pf.mean(0), median=np.median(Pf, 0))
        seam = {}; noise = {}
        for nm, c in cur.items():
            mis = np.array([c[Lf.index(L)] - exact[L] for L in Lx])
            seam[nm] = float(mis[-1])
            new = [i for i, L in enumerate(Lx) if L >= 46]
            old = [i for i, L in enumerate(Lx) if 24 <= L <= 44]
            noise[nm] = dict(rms_46_72=float(np.sqrt(np.mean(mis[new] ** 2))) if new and hi > 44 else None,
                             max_46_72=float(np.abs(mis[new]).max()) if new and hi > 44 else None,
                             rms_24_44=float(np.sqrt(np.mean(mis[old] ** 2))), max_24_44=float(np.abs(mis[old]).max()),
                             misfit_at_44=float(mis[Lx.index(44)]))
        # roughness of the assembled dC sequence (exact to hi, central beyond) over hi-12 .. hi+18
        rough = {}
        win = [L for L in Lseq if hi - 12 <= L <= min(hi + 18, max(Lseq))]
        for nm, vals in (('median', ms['central']), ('medoid', [float(Pv[mem, Lm.index(L)]) if L in Lm else None for L in Lm]),
                         ('floormean', None)):
            seqv = []
            for L in win:
                if L in exact:
                    seqv.append(exact[L])
                elif nm == 'floormean':
                    seqv.append(floor[Lmod.index(L)])
                else:
                    seqv.append(vals[Lm.index(L)])
            rough[nm] = sig(np.array(seqv))
        res[k] = dict(hi_exact=hi, L=Lmod, median=[ms['central'][Lm.index(L)] for L in Lmod],
                      medoid=[float(Pv[mem, i]) for i in iv], floormean=floor,
                      floormedoid=[float(Pv[fmem, i]) for i in iv],
                      floormedoid_member=dict(member=fmem, label=b['labels'][fmem], maxres=float(mr[fmem]),
                                              rms_dist_over_unc_to_floormean=float(dfl.min())),
                      unc=[ms['unc'][Lm.index(L)] for L in Lmod], unc_typ=[ms['unc_typ'][Lm.index(L)] for L in Lmod],
                      u_env=[ms['u_env'][Lm.index(L)] for L in Lmod],
                      member_std=[float(Pv[:, i].std()) for i in iv], n_kept=int(Pv.shape[0]), n_floor=int(fl.sum()),
                      medoid_member=D['central_members'][k], seam_misfit_at_hi=seam, noise=noise, roughness=rough,
                      L_ref=[L for L in Lm if L not in Lseq],
                      medoid_ref=[float(Pv[mem, Lm.index(L)]) for L in Lm if L not in Lseq],
                      median_ref=[ms['central'][Lm.index(L)] for L in Lm if L not in Lseq],
                      unc_ref=[ms['unc'][Lm.index(L)] for L in Lm if L not in Lseq],
                      unc_typ_ref=[ms['unc_typ'][Lm.index(L)] for L in Lm if L not in Lseq],
                      member_std_ref=[float(Pv[:, Lm.index(L)].std()) for L in Lm if L not in Lseq],
                      floormean_ref=[float(Pf[fl][:, Lf.index(L)].mean()) for L in Lm if L not in Lseq],
                      floormedoid_ref=[float(Pf[fmem, Lf.index(L)]) for L in Lm if L not in Lseq],
                      curves_allL=dict(L=Lf, medoid=cur['medoid'].tolist(), floormean=cur['floormean'].tolist(),
                                       floormedoid=cur['floormedoid'].tolist()))
    return res, pub


new, pubN = build(NEW)
old, pubO = build(OLD)

# ------------------------------------------------------------------ corrected files with a smooth central
def write_variant(name, pick, from_L=None, note=''):
    d = copy.deepcopy(pubN)
    for k in (6, 7, 8):
        r = new[k]; cur = r['curves_allL']; Lf = cur['L']
        for row in d['sequences']['C%d' % k]:
            L = row['L']
            if from_L is None:
                if row['exact']:
                    continue
                v = r[pick][r['L'].index(L)]
                row['dC_source'] = 'modelled (delta-v1, %s central)' % pick
            else:
                if L < from_L:
                    continue
                v = cur[pick][Lf.index(L)]
                if row['exact']:
                    row['dC_source'] = 'smoothed: %s curve through the exact S10 cluster value (exact dC = %.17g)' % (pick, row['dC'])
                    row['dC_exact_value'] = row['dC']
                    row['exact'] = False
                    row['dC_unc'] = r['noise'][pick]['rms_46_72']; row['dC_unc_typ'] = r['noise'][pick]['rms_46_72']
                else:
                    row['dC_source'] = 'modelled (delta-v1, %s central)' % pick
            row['dC'] = float(v); row['corrected'] = row['raw'] + row['dC']
    d['tag'] = '%s_%s' % (a.tag, name)
    d['central_rule'] = note
    d['derived_from'] = dict(path=NEW['corr'], sha256=sha(NEW['corr']))
    p = f'{OUT}/{a.tag}_{name}_corrected.json'
    json.dump(d, open(p, 'w'), indent=1)
    return p


files = {
    'medoid': write_variant('medoid', 'medoid', note='medoid kept fit beyond the last exact L (model-independent lens rule); exact dC to 72'),
    'floormean': write_variant('floormean', 'floormean', note='mean of floor-level kept fits (QF=3) beyond the last exact L (joint lens rule); exact dC to 72'),
    'floormedoid': write_variant('floormedoid', 'floormedoid', note='floor-level medoid kept fit beyond the last exact L (single smooth member, seam at noise level); exact dC to 72'),
    'floormean_s46': write_variant('floormean_s46', 'floormean', from_L=46,
                                   note='exact dC to 44 (quiet S10 archive); floor-mean curve at every L >= 46, i.e. the S10 cluster points 46..72 replaced by the smooth fit through them (difference = their noise)'),
}

# ------------------------------------------------------------------ comparison tables
cmp = {}
for k in (6, 7, 8):
    cmp[k] = {}
    for L in (74, 80, 92, 100, 118):
        def get(r, key, L):
            if L in r['L']:
                return r[key][r['L'].index(L)]
            if L in r['L_ref'] and key + '_ref' in r:
                return r[key + '_ref'][r['L_ref'].index(L)]
            return None
        cmp[k][L] = {nm: dict(median=get(r, 'median', L), medoid=get(r, 'medoid', L), floormean=get(r, 'floormean', L),
                              floormedoid=get(r, 'floormedoid', L),
                              unc=get(r, 'unc', L), unc_typ=get(r, 'unc_typ', L), member_std=get(r, 'member_std', L))
                     for nm, r in (('new_hi72', new[k]), ('old_hi44', old[k]))}
summary = dict(created=pubN['created'], tag=a.tag, inputs=dict(new=NEW, old=OLD),
               sha256={p: sha(p) for p in list(NEW.values()) + list(OLD.values())},
               files=files, new={'dC%d' % k: v for k, v in new.items()}, old={'dC%d' % k: v for k, v in old.items()},
               compare={'dC%d' % k: {str(L): v for L, v in c.items()} for k, c in cmp.items()})
json.dump(summary, open(f'{OUT}/{a.tag}_smooth.json', 'w'), indent=1)

# per-L CSV beyond the exact range (new model)
with open(f'{OUT}/{a.tag}_smooth_table.csv', 'w') as f:
    f.write('k,L,median,medoid,floormean,floormedoid,unc_envelope,unc_typ,member_std,in_corrected_sequence\n')
    for k in (6, 7, 8):
        r = new[k]
        for i, L in enumerate(r['L']):
            f.write('%d,%d,%.15g,%.15g,%.15g,%.15g,%.3g,%.3g,%.3g,1\n' % (k, L, r['median'][i], r['medoid'][i], r['floormean'][i],
                                                                     r['floormedoid'][i], r['unc'][i], r['unc_typ'][i], r['member_std'][i]))
        for i, L in enumerate(r['L_ref']):
            f.write('%d,%d,%.15g,%.15g,%.15g,%.15g,%.3g,%.3g,%.3g,0\n' % (k, L, r['median_ref'][i], r['medoid_ref'][i],
                                                                     r['floormean_ref'][i], r['floormedoid_ref'][i], r['unc_ref'][i],
                                                                     r['unc_typ_ref'][i], r['member_std_ref'][i]))

# ------------------------------------------------------------------ printout
for k in (6, 7, 8):
    for nm, r in (('NEW hi=72', new[k]), ('OLD hi=44', old[k])):
        print('dC%d %s: kept %d (floor %d); medoid #%d %s (rms dist/unc %.3g, maxres %.1e)' % (
            k, nm, r['n_kept'], r['n_floor'], r['medoid_member']['member'], r['medoid_member']['label'],
            r['medoid_member']['rms_dist_over_unc'], r['medoid_member']['member_maxres']))
        print('      floor-level medoid #%d %s (maxres %.1e)' % (r['floormedoid_member']['member'], r['floormedoid_member']['label'], r['floormedoid_member']['maxres']))
        print('      seam misfit at L=%d: %s' % (r['hi_exact'], ', '.join('%s %+.1e' % (a_, b_) for a_, b_ in r['seam_misfit_at_hi'].items())))
        print('      noise/misfit vs exact: %s' % json.dumps({n: {kk: (None if v is None else float('%.2g' % v)) for kk, v in d.items()} for n, d in r['noise'].items()}))
        print('      roughness around seam: %s' % ', '.join('%s %.1e' % (a_, b_) for a_, b_ in r['roughness'].items()))
    for L in (92, 118):
        for nm in ('new_hi72', 'old_hi44'):
            c = cmp[k][L][nm]
            if c['median'] is None:
                continue
            print('   L=%3d %-8s median %+.9f medoid %+.9f floormean %+.9f floormedoid %+.9f  unc %.2e typ %.2e std %.2e' % (
                L, nm, c['median'], c['medoid'], c['floormean'], c['floormedoid'], c['unc'], c['unc_typ'], c['member_std']))
print('wrote', json.dumps(files, indent=1))
