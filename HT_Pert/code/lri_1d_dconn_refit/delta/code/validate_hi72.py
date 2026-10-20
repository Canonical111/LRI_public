#!/usr/bin/env python3
"""Validation of the delta-v1 rule and of the smooth centrals at the new training edge hi = 72.

part 'seq'  : sequences known exactly far beyond 72 (train even L <= 72, predict to 152/118/92):
              Dconn4, Dconn5 (to 152); g2D4, g2D5 (to 118); g2D6, g2D7, g2D8 (to 92; g2D8 training is L=4j <= 48 plus
              every even 50..72); R4, R5 = Dconn - g2D (to 118).
part 'hold' : dC6..dC8 themselves, train hi = 58 and 60, predict to 72 (truth carries the S10 cluster noise);
              plus the frozen hi = 44 model (archived variants) against the exact 46..72.
part 'noise:k' : noise injection for dC_k: Gaussian noise of the measured size (rms residual of the floor-mean curve at
              46..72) added to the exact L = 46..72 points, ensemble rerun; spread of the predictions at 92/118.
For every case: the rule median, the floor-mean (QF = 3 per window, joint lens), the floor-level medoid (floor member
closest to the floor-mean) and the all-kept medoid (member closest to the median, scaled by the half-range).
Errors are reported as |err| / half-range (the envelope) and |err| / unc_typ-proxy (0.25 half-range)."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from load import load_s10, load_recon, load_g2d
from ensemble import ensemble, RULE

CSV = '<PROJECT>/lri_1d_coefficient_flow_review/s10_production/dconn_minus_raw_L46_72.csv'
ARCH = '<PROJECT>/lri_1d_coefficient_flow_review/step1_dconn_refit'
OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'validation_hi72'))
os.makedirs(OUT, exist_ok=True)
QF = 3.0
part = sys.argv[1] if len(sys.argv) > 1 else 'seq'
t0 = time.time()


def centrals(e):
    """median, floor-mean, floor-medoid, all-kept medoid from an ensemble result (prediction rows e['preds'])."""
    P = e['preds']; kept = e['kept']
    lo = np.array([c[1] for c in kept]); mr = np.array([c[4] for c in kept])
    best = {l: mr[lo == l].min() for l in set(lo)}
    fl = np.array([mr[i] <= QF * best[lo[i]] for i in range(len(mr))])
    med = np.median(P, 0); fm = P[fl].mean(0); sc = np.maximum(e['spread'], 1e-300)
    fi = np.where(fl)[0]
    fmed = P[fi[np.argmin(np.sqrt(np.mean(((P[fi] - fm) / sc) ** 2, 1)))]]
    amed = P[np.argmin(np.sqrt(np.mean(((P - med) / sc) ** 2, 1)))]
    return dict(median=med, floormean=fm, floormedoid=fmed, medoid=amed), int(fl.sum())


def report(name, seq, hi, Lt, rule=RULE):
    e = ensemble(seq, hi, Lt, rule=rule)
    C, nfl = centrals(e)
    truth = np.array([seq[L] for L in Lt])
    hr = np.maximum(e['spread'], 1e-300)
    out = dict(L=Lt, n_kept=e['n_kept'], n_floor=nfl, halfrange=e['spread'].tolist(),
               inside=bool(np.all((truth >= e['lo']) & (truth <= e['hi']))))
    line = '%-16s hi=%d kept %3d floor %2d in-env %-5s' % (name, hi, e['n_kept'], nfl, out['inside'])
    for nm, c in C.items():
        err = c - truth
        out[nm] = dict(err=err.tolist(), max_ratio=float(np.max(np.abs(err) / hr)))
        line += ' | %s %.2f' % (nm, out[nm]['max_ratio'])
    print(line)
    for L in (74, 92, 118, 152):
        if L in Lt:
            i = Lt.index(L)
            print('      L=%3d halfrange %.2e  err: median %+.2e floormean %+.2e floormedoid %+.2e medoid %+.2e' % (
                L, hr[i], *(C[nm][i] - truth[i] for nm in ('median', 'floormean', 'floormedoid', 'medoid'))))
    return out


rep = {}
if part == 'seq':
    rc = load_recon(); g = load_g2d()
    cases = [('Dconn4', {L: rc[L][4] for L in rc}), ('Dconn5', {L: rc[L][5] for L in rc})]
    for k in (4, 5, 6, 7, 8):
        cases.append(('g2D%d' % k, dict(g[k])))
    for k in (4, 5):
        cases.append(('R%d' % k, {L: rc[L][k] - g[k][L] for L in rc if L in g[k]}))
    for name, seq in cases:
        Lt = [L for L in sorted(seq) if 72 < L <= 152]
        rep[name] = report(name, seq, 72, Lt)
elif part == 'hold':
    s10 = load_s10(CSV)
    for k in (6, 7, 8):
        seq = {L: ent[k] for L, ent in s10.items() if k in ent}
        for hi in (58, 60):
            Lt = [L for L in sorted(seq) if hi < L <= 72]
            rep['dC%d_hi%d' % (k, hi)] = report('dC%d hold' % k, {L: v for L, v in seq.items() if L <= hi} | {L: seq[L] for L in Lt}, hi, Lt)
    # frozen hi = 44 model (archived kept fits at L >= 46) against the exact 46..72
    V = json.load(open(ARCH + '/delta/out/delta_v1_variants.json'))
    pub = json.load(open(ARCH + '/delta/out/delta_v1_corrected.json'))
    for k in (6, 7, 8):
        seq = {L: ent[k] for L, ent in s10.items() if k in ent}
        b = V['dC%d' % k]; P = np.array(b['pred']); Lv = b['L']; Lt = list(range(46, 73, 2)); it = [Lv.index(L) for L in Lt]
        kept = [(lab.split('|')[0], int(lab.split('lo=')[1].split('|')[0]), 0, 0, mr) for lab, mr in zip(b['labels'], b['maxres'])]
        e = dict(preds=P[:, it], kept=kept, spread=(P[:, it].max(0) - P[:, it].min(0)) / 2, lo=P[:, it].min(0), hi=P[:, it].max(0), n_kept=len(kept))
        C, nfl = centrals(e)
        truth = np.array([seq[L] for L in Lt]); hr = e['spread']
        ms = pub['model_summary']['dC%d' % k]; ut = np.array([ms['unc_typ'][ms['L'].index(L)] for L in Lt])
        out = dict(L=Lt, n_floor=nfl, halfrange=hr.tolist(), unc_typ=ut.tolist())
        line = 'dC%d frozen hi=44 -> 46..72: floor %d' % (k, nfl)
        for nm, c in C.items():
            err = c - truth
            out[nm] = dict(err=err.tolist(), max_ratio=float(np.max(np.abs(err) / hr)), max_over_typ=float(np.max(np.abs(err) / ut)))
            line += ' | %s %.3f (typ %.2f)' % (nm, out[nm]['max_ratio'], out[nm]['max_over_typ'])
        print(line)
        print('      L=72 err: ' + ' '.join('%s %+.2e' % (nm, C[nm][-1] - truth[-1]) for nm in C) + '  halfrange %.2e' % hr[-1])
        rep['dC%d_frozen44' % k] = out
elif part.startswith('noise'):
    k = int(part.split(':')[1]); ndraw = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    sm = json.load(open(os.path.join(OUT, '..', 'delta_v1_hi72_smooth.json')))
    sigma = sm['new']['dC%d' % k]['noise']['floormean']['rms_46_72']
    s10 = load_s10(CSV)
    seq = {L: ent[k] for L, ent in s10.items() if k in ent}
    Lt = [74, 92, 118]
    rng = np.random.default_rng(20261009 + k)
    base = ensemble(seq, 72, Lt, rule=RULE); Cb, _ = centrals(base)
    D = {nm: [] for nm in Cb}
    for d in range(ndraw):
        s2 = {L: v + (rng.normal(0, sigma) if L >= 46 else 0.0) for L, v in seq.items()}
        e = ensemble(s2, 72, Lt, rule=RULE); C, _ = centrals(e)
        for nm in C:
            D[nm].append(C[nm] - Cb[nm])
    out = dict(sigma=sigma, ndraw=ndraw, L=Lt, base_halfrange=base['spread'].tolist())
    for nm, v in D.items():
        v = np.array(v); out[nm] = dict(std=v.std(0).tolist(), maxabs=np.abs(v).max(0).tolist())
        print('dC%d noise sigma %.1e (%d draws) %-11s std at 74/92/118: %s   (halfrange %s)' % (
            k, sigma, ndraw, nm, ' '.join('%.2e' % x for x in v.std(0)), ' '.join('%.2e' % x for x in base['spread'])))
    rep['noise_dC%d' % k] = out
json.dump(rep, open(os.path.join(OUT, 'validate_%s.json' % part.replace(':', '')), 'w'), indent=1, default=float)
print('time %.1fs' % (time.time() - t0))
