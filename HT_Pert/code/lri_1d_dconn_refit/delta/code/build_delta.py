#!/usr/bin/env python3
"""Delta model: complete Dconn window shifts dC_k(L) = C_k^Dconn(L) - C_k^raw(L) beyond the exact range, and the
fully corrected sequences C_k^corr(L) = C_k^raw(L) + dC_k(L).

Exact inputs (never modelled where available):
  k = 0..3 : dC = 0 identically (Dconn leaves C0..C3 unchanged; checked to 4e-14 against the S10 archive).
  k = 4, 5 : dC_reconciled.json, every even L <= 128 (+136, 144, 152).
  k = 6..8 : S10 archive whole_model_coefficients.csv (scheme dconn), even L = 2..44,
             plus optional --extra-dconn CSV rows (e.g. the S10 cluster points L = 46..72), which then count as exact
             and the model is retrained on everything exact.
Modelled (k = 6, 7 for L in thermal_d7 up to 118; k = 8 for L in raw up to 92):
  primary   : ensemble rule 'delta-v1' (ensemble.py) on dC_k itself;
  cross-check: dC_k = g2D_k (exact isolated g^2 D shift, vacuum_only - raw / d7_all, to L = 92) + ensemble(R_k),
               R_k = dC_k - g2D_k (k=8: only L = 4j below 48 exist); for k=6,7 at L > 92, g2D_k is itself extrapolated;
  sensitivity: rule variants (shifts, Q, NPMIN, N4, low edges).
Uncertainty per modelled point:
  unc     = max(ensemble half-range, |cross-check - central|, max |variant median - central|)   [conservative envelope]
  unc_typ = max(0.25 * ensemble half-range, |cross-check - central|, max |variant - central|)   [typical size; the
            validation (validate_rule.py) found |median - truth| <= 0.21 half-range in all 15 test sequences]
Usage: build_delta.py [--extra-dconn CSV] [--out DIR] [--no-sens]
"""
import sys, os, json, time, hashlib, argparse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from load import *
from ensemble import ensemble, RULE

ap = argparse.ArgumentParser()
ap.add_argument('--extra-dconn', default=None)
ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
ap.add_argument('--tag', default='delta_v1')
ap.add_argument('--no-sens', action='store_true')
args = ap.parse_args()
t0 = time.time()
os.makedirs(args.out, exist_ok=True)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


ht = load_ht(); rc = load_recon(); s10 = load_s10(args.extra_dconn); g2d = load_g2d()
TH = ht['thermal_d7']; RAW8 = ht['raw']
Ls_th = sorted(TH); Ls_8 = sorted(RAW8)

# ------------------------------------------------------------------ exact shift sets
exact = {k: {} for k in range(9)}
src = {k: {} for k in range(9)}
for k in range(4):
    for L in set(Ls_th) | set(Ls_8):
        exact[k][L] = 0.0; src[k][L] = 'identically zero (Dconn leaves C0..C3 unchanged)'
for k in (4, 5):
    for L in rc:
        exact[k][L] = rc[L][k]; src[k][L] = 'dC_reconciled.json'
for k in (6, 7, 8):
    for L, ent in s10.items():
        if k in ent:
            exact[k][L] = ent[k]
            src[k][L] = 'extra CSV' if ent.get('extra') else 'S10 whole_model_coefficients.csv'
checks = {}
checks['S10_vs_recon_dC4_maxabs'] = max(abs(s10[L][4] - rc[L][4]) for L in s10 if 4 in s10[L] and L in rc)
checks['S10_vs_recon_dC5_maxabs'] = max(abs(s10[L][5] - rc[L][5]) for L in s10 if 5 in s10[L] and L in rc)
checks['S10_dconn_C0to3_minus_raw_maxabs'] = max(abs(s10[L]['C'][k] - TH[L][k]) for L in s10 if 'C' in s10[L]
                                                 for k in range(4))
checks['S10_raw_vs_HT_raw_maxrel'] = max(abs(s10[L]['C'][k] - s10[L][k] - RAW8[L][k]) / abs(RAW8[L][k])
                                         for L in s10 if 'C' in s10[L] for k in range(4, 9))

# ------------------------------------------------------------------ model k = 6, 7, 8
FORECAST_L = list(range(46, 73, 2))
EXTRA_L = {6: [], 7: [], 8: [94, 96, 98, 100, 102, 104, 106, 108, 110, 112, 114, 116, 118]}  # dC8 beyond 92: report only
SENS = {} if args.no_sens else {
    'shifts-2,0,2': dict(SHIFTS=(-2, 0, 2)), 'Q10': dict(Q=10.0), 'Q1000': dict(Q=1000.0), 'NPMIN5': dict(NPMIN=5),
    'withN4': dict(NONDEC=('N1', 'N2', 'N3', 'N4')), 'lo8-12': dict(LOS=(8, 10, 12)), 'lo16-20': dict(LOS=(16, 18, 20))}
model = {}
variants_out = {}
for k in (6, 7, 8):
    seq = exact[k]
    hi = max(seq)
    targets = Ls_th if k <= 7 else Ls_8
    Lmod = sorted(set(L for L in targets if L not in seq) | set(L for L in FORECAST_L if L not in seq)
                  | set(L for L in EXTRA_L[k] if L not in seq))
    if not Lmod:
        continue
    prim = ensemble(seq, hi, Lmod, rule=RULE)
    # cross-check through exact g2D
    gk = g2d[k]
    Rk = {L: seq[L] - gk[L] for L in seq if L in gk}
    rr = dict(RULE)
    if k == 8 and max(L for L in Rk) <= 44:
        rr.update(LOS=(4, 8), DOFMIN=3)       # R8 only at L = 4j below 48 (10 points from L=8), as validated on g2D8
    xR = ensemble(Rk, max(Rk), Lmod, rule=rr)
    gmax = max(gk)
    Lg_ext = [L for L in Lmod if L not in gk]   # beyond 92 (k=6,7) or missing L=46 (k=8)
    gext = ensemble(gk, gmax, Lg_ext, rule=RULE) if Lg_ext else None
    gval = np.array([gk[L] if L in gk else gext['median'][Lg_ext.index(L)] for L in Lmod])
    gexact = np.array([L in gk for L in Lmod])
    X = gval + xR['median']
    sens = {}
    for name, upd in SENS.items():
        r = dict(RULE); r.update(upd)
        e = ensemble(seq, hi, Lmod, rule=r)
        sens[name] = e['median']
    cen = prim['median']
    u_env = prim['spread']
    u_x = np.abs(X - cen)
    u_s = np.max(np.abs(np.array(list(sens.values())) - cen), axis=0) if sens else np.zeros_like(cen)
    unc = np.maximum.reduce([u_env, u_x, u_s])
    unc_typ = np.maximum.reduce([0.25 * u_env, u_x, u_s])
    model[k] = dict(L=Lmod, central=cen, unc=unc, unc_typ=unc_typ, u_env=u_env, u_xchk=u_x, u_sens=u_s,
                    lo=prim['lo'], hi=prim['hi'], xchk=X, xchk_g2D_exact=gexact, n_kept=prim['n_kept'],
                    n_all=prim['n_all'], hi_exact=hi, sens={n: v.tolist() for n, v in sens.items()})
    variants_out[k] = dict(L=Lmod, labels=['%s|lo=%d|s=%d|np=%d' % (m, lo, s, n) for (m, lo, s, n, _) in prim['kept']],
                           maxres=[float(x[4]) for x in prim['kept']], pred=prim['preds'].tolist())
    print('dC%d: exact to L=%d, %d modelled L, kept %d/%d fits (%.1fs)' % (k, hi, len(Lmod), prim['n_kept'],
                                                                          prim['n_all'], time.time() - t0))
    for L in (46, 60, 72, 92, 118):
        if L in Lmod:
            i = Lmod.index(L)
            print('   L=%3d  dC=%+.7f  unc=%.2e  (env %.2e, xchk %+.2e, sens %.2e)  typ=%.2e' % (
                L, cen[i], unc[i], u_env[i], X[i] - cen[i], u_s[i], unc_typ[i]))

# ------------------------------------------------------------------ assemble per-L records
def dC_at(k, L):
    if L in exact[k]:
        return exact[k][L], 0.0, 0.0, True, src[k][L]
    m = model[k]; i = m['L'].index(L)
    return float(m['central'][i]), float(m['unc'][i]), float(m['unc_typ'][i]), False, 'modelled (delta-v1)'

seqs = {}
for k in range(9):
    rows = []
    Ls = Ls_th if k <= 7 else Ls_8
    for L in Ls:
        raw = float(TH[L][k]) if k <= 7 else float(RAW8[L][k])
        d, u, ut, ex, s = dC_at(k, L)
        rows.append(dict(L=L, raw=raw, dC=d, dC_unc=u, dC_unc_typ=ut, exact=ex, dC_source=s, corrected=raw + d))
    seqs['C%d' % k] = rows
raw_src = {('C%d' % k): ('thermal_d7 (lri_hpc_Hamitonian Expanse campaign), L=2..118' if k <= 7 else
                          'raw (lri_c8: L<=50 original package, 52..92 symmetry campaign), L=2..92') for k in range(9)}

out = dict(
    tag=args.tag, created=datetime.datetime.now().isoformat(timespec='seconds'),
    description=('Fully window-corrected (complete consistent disconnected-vacuum correction Dconn) HT thermal '
                 'coefficients C0..C8. corrected = raw + dC, one prescription at every order. dC exact where '
                 'flagged, otherwise modelled by the delta-v1 ensemble (dC6, dC7 beyond L=%d; dC8 beyond L=%d).' % (
                     model[6]['hi_exact'] if 6 in model else -1, model[8]['hi_exact'] if 8 in model else -1)),
    conventions=dict(epsilon='2s-1', gap='Delta_thermal = 1/2 - eps/6 + sum C_n eps^n',
                     log_convention='full: dC4 keeps its +log(L)/17496 and dC5 its ~4.4e-4 log L (no MS subtraction)',
                     dC_unc='conservative envelope: max(ensemble half-range, |g2D cross-check - central|, max rule-variant shift)',
                     dC_unc_typ='typical error: max(0.25 * half-range, cross-check, variant shift); validation max |err|/half-range = 0.21',
                     corrected_unc='equal to dC_unc (raw data are exact to ~1e-14 relative)'),
    sources={p: sha(p) for p in (DATA_JSON, RECON_JSON, S10_CSV, D5_JSON, D7_JSON)},
    extra_dconn_csv=(dict(path=os.path.abspath(args.extra_dconn), sha256=sha(args.extra_dconn)) if args.extra_dconn else None),
    raw_sources=raw_src, rule=dict(RULE), sensitivity_variants={n: {kk: list(v) if isinstance(v, tuple) else v for kk, v in u.items()} for n, u in SENS.items()},
    checks=checks,
    model_summary={('dC%d' % k): dict(hi_exact=m['hi_exact'], n_kept=m['n_kept'], n_all=m['n_all'],
                                       L=m['L'], central=m['central'].tolist(), unc=m['unc'].tolist(),
                                       unc_typ=m['unc_typ'].tolist(), env_lo=m['lo'].tolist(), env_hi=m['hi'].tolist(),
                                       u_env=m['u_env'].tolist(), xchk_g2D_plus_R=m['xchk'].tolist(),
                                       xchk_g2D_exact=m['xchk_g2D_exact'].tolist(), sens_medians=m['sens'])
                   for k, m in model.items()},
    note_dC8_beyond_92='dC8 at L=94..118 is modelled for reference only (no raw C8 there); not part of the corrected C8 sequence.',
    sequences=seqs)
json.dump(out, open(os.path.join(args.out, '%s_corrected.json' % args.tag), 'w'), indent=1)
json.dump({('dC%d' % k): v for k, v in variants_out.items()},
          open(os.path.join(args.out, '%s_variants.json' % args.tag), 'w'))
# compact CSV of the modelled shifts
with open(os.path.join(args.out, '%s_dC_table.csv' % args.tag), 'w') as f:
    f.write('L,k,dC,dC_unc,dC_unc_typ,exact,source\n')
    for k in range(4, 9):
        for r in seqs['C%d' % k]:
            f.write('%d,%d,%.15g,%.3g,%.3g,%d,%s\n' % (r['L'], k, r['dC'], r['dC_unc'], r['dC_unc_typ'], r['exact'], r['dC_source']))
        if k == 8 and 8 in model:
            for L in EXTRA_L[8]:
                if L in model[8]['L']:
                    i = model[8]['L'].index(L)
                    f.write('%d,8,%.15g,%.3g,%.3g,0,modelled reference only (no raw C8)\n' % (L, model[8]['central'][i], model[8]['unc'][i], model[8]['unc_typ'][i]))
# frozen forecast of the S10 points still to be computed (only when made from L<=44 data)
if not args.extra_dconn:
    ff = dict(made_from='S10 exact dC6..dC8 at even L<=44 only (rule delta-v1)', created=out['created'],
              forecast={('dC%d' % k): {str(L): [float(model[k]['central'][model[k]['L'].index(L)]),
                                               float(model[k]['unc'][model[k]['L'].index(L)]),
                                               float(model[k]['unc_typ'][model[k]['L'].index(L)])]
                                       for L in FORECAST_L} for k in (6, 7, 8)},
              columns=['central', 'unc_envelope', 'unc_typ'])
    p = os.path.join(args.out, 'frozen_forecast_L46_72.json')
    json.dump(ff, open(p, 'w'), indent=1)
    open(p + '.sha256', 'w').write(sha(p) + '  frozen_forecast_L46_72.json\n')
print('checks', json.dumps(checks))
print('done %.1fs' % (time.time() - t0))
