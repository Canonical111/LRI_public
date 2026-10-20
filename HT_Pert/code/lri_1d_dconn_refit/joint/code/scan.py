#!/usr/bin/env python3
"""Joint linked-tail-model scan on the raw and the fully Dconn-corrected HT data (lens 'joint-model').

kind o8 : orders 4..8, order 8 on [lo, hi], hi in HI8; orders 4..7 either on the same window ('same') or on [lo, 118]
          of the thermal data ('th118'); omega6 free at order 8.
kind o7 : orders 4..7 only, all on [lo, hi], hi in HI7 (window-stability / pre-registered checks).
Grid: lo in LOS; tail bases BASES; modes fixed (gap omegas), free (omega3..omega5 freed at orders 5..7, fed upward),
FL (freed leading tail L^-1/2, L^-1/2 log L at orders 4..7), FL5 (same at orders 5..7 only); shifts -2, 0, 2; gap inputs
orig, ext, wf (window-free sensitivity: omega2 = -5A, omega3 = ext - 0.14603).
For the corrected data every fit also carries the exact first-order response of C6..C8 to the delta-model
perturbations of data.py (envelope edges, every kept delta-v1 curve spliced / everywhere, alternative prescriptions).
256-bit arb least squares (cond^2 <= 1e34 for every fit here; 512-bit spot checks in check_prec.py).
Usage: scan.py KIND [--workers P] [--out FILE] [--part i/n] [--limit N]"""
import sys, os, json, gzip, time, itertools, argparse
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import fitcore as F
from data import load

LOS = (16, 24, 32, 40, 50, 60, 70)
HI8 = (50, 60, 70, 72, 80, 92)                 # refit72: + 72 (every dC exact on [lo, 72]: delta-free windows)
HI7 = (50, 60, 70, 72, 80, 92, 104, 118)
BASES = ('A', 'B', 'C', 'D', 'Dj', 'E', 'F', 'BD', 'S', 'Bp', 'A+tower1', 'B+tower1', 'A+tower15', 'A+L075', 'B+L075',
         'D+L075', 'E+L075', 'E+p25')
MODES = ('fixed', 'free', 'FL', 'FL5')
SHIFTS = (-2., 0., 2.)
GAPS = ('orig', 'ext', 'wf')
# refit72 datasets: raw; dconn = primary (exact dC to 72 incl. the noisy S10 cluster rows 46..72, floor-mean curve beyond);
# dconn_s46 = smooth sensitivity (exact to 44, floor-mean curve from 46); dconn_old = the run1 primary (delta-v1 hi=44)
# dconn_w = the dconn table fitted by WEIGHTED least squares (rows / data.wrel: the S10 cluster rows down-weighted by their noise)
DATASETS = ('raw', 'dconn', 'dconn_s46', 'dconn_old', 'dconn_w')
DSEL = os.environ.get('JOINT_DATASETS')          # optional comma list restricting the scanned datasets
OLD_CORR = os.environ.get('DCONN_OLD_CORRECTED')
OLD_VFULL = os.environ.get('DCONN_OLD_VARIANTS_FULL')
FAMS = ('spl', 'evw')


def configs(kind):
    out = []
    if kind == 'o8':
        for ds, hi, low, lo, b, mode, sh, gap in itertools.product(DATASETS, HI8, ('same', 'th118'), LOS, BASES, MODES, SHIFTS, GAPS):
            if lo >= hi:
                continue
            out.append(dict(kind=kind, ds=ds, hi=hi, low=low, lo=lo, base=b, mode=mode, sh=sh, gap=gap))
        if DSEL:
            out = [c for c in out if c['ds'] in DSEL.split(',')]
    else:
        for ds, hi, lo, b, mode, sh, gap in itertools.product(DATASETS, HI7, LOS, BASES, MODES, SHIFTS, GAPS):
            if lo >= hi:
                continue
            out.append(dict(kind=kind, ds=ds, hi=hi, low='same', lo=lo, base=b, mode=mode, sh=sh, gap=gap))
        if DSEL:
            out = [c for c in out if c['ds'] in DSEL.split(',')]
    return out


D = None
PN = None


def init():
    global D, PN
    F.set_prec(256)
    D = load()
    PN = list(D['perts'])
    if OLD_CORR:
        Do = load(OLD_CORR, OLD_VFULL, with_perts=False)
        assert np.array_equal(Do['L'], D['L'])
        m = np.isfinite(D['raw'])
        assert np.array_equal(np.isfinite(Do['raw']), m) and np.array_equal(Do['raw'][m], D['raw'][m]), 'raw tables differ'
        D['dconn_old'] = Do['dconn']


def spec_of(c):
    return c['base'] + ('+FL' if c['mode'] == 'FL' else '+FL5' if c['mode'] == 'FL5' else '')


def r7(x):
    return float('%.7g' % x)


def run(c):
    L = D['L']; C = D['dconn' if c['ds'] == 'dconn_w' else c['ds']]
    maxorder = 8 if c['kind'] == 'o8' else 7
    hl = 118 if c['low'] == 'th118' else None
    perts = D['perts'] if c['ds'] in ('dconn', 'dconn_w') else None
    noisy = c['ds'] in ('dconn', 'dconn_w')
    try:
        r = F.fit(L, C, c['lo'], c['hi'], spec_of(c), c['sh'], F.GAPS[c['gap']], maxorder=maxorder,
                  free_orders=((5, 6, 7) if c['mode'] == 'free' else ()), hi_low=hl, sigraw=SIGRAW, perts=perts,
                  wrel=(D['wrel'] if noisy else None), sigx=(D['sigx'] if noisy else None),
                  wfit=(D['wrel'] if c['ds'] == 'dconn_w' else None))
    except (ValueError, ZeroDivisionError) as e:
        return dict(c, err=str(e))
    o = r['orders']
    rec = dict(c, lim={n: o[n]['lim'] for n in o}, om={k: r['omega'][k] for k in (3, 4, 5, 6)},
               o={n: [o[n]['rms'], o[n]['maxres'], o[n]['cond'], o[n]['gain'], o[n]['stat'], o[n]['npts'], o[n]['ncol'],
                      o[n]['erms'], o[n]['emax'], o[n]['stat_x']] for n in o})
    if perts is not None:
        dl = r['dlim']
        rec['e'] = {f'{p}{k}_{n}': r7(dl[n][f'{p}{k}']) for p in ('unc', 'typ') for k in (6, 7, 8) for n in range(k, maxorder + 1)}
        rec['P'] = {f'{p}_{n}': r7(dl[n]['P:' + p]) for p in ('dconn_med', 'dconn_mean', 'dconn_model', 'dconn_s46') for n in range(6, maxorder + 1)}
        v = {}
        for fam in FAMS:
            for k in (6, 7, 8):
                names = [p for p in PN if p.startswith(f'{fam}{k}_')]
                idx = [int(p.split('_')[1]) for p in names]
                fl = set(D['floor_idx'][k])
                for n in range(k, maxorder + 1):
                    a = np.array([dl[n][p] for p in names])
                    af_ = np.array([dl[n][p] for p, i in zip(names, idx) if i in fl])
                    for tag, arr in ((fam, a), (fam + 'F', af_)):
                        v[f'{tag}{k}_{n}'] = [r7(x) for x in (arr.min(), np.percentile(arr, 16), np.median(arr), np.percentile(arr, 84), arr.max(), arr.std())]
        rec['v'] = v
    return rec


SIGRAW = {2: 6.5e-15, 3: 8.4e-14, 4: 2.9e-13, 5: 3.3e-12, 6: 1.25e-11, 7: 1.4e-10, 8: 1.4e-8}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=('o8', 'o7'))
    ap.add_argument('--workers', type=int, default=1)
    ap.add_argument('--out', default=None)
    ap.add_argument('--part', default='0/1')
    ap.add_argument('--limit', type=int, default=None)
    a = ap.parse_args()
    cf = configs(a.kind)
    i, n = map(int, a.part.split('/'))
    cf = cf[i::n]
    if a.limit:
        cf = cf[:a.limit]
    out = a.out or f'scan_{a.kind}_{i}of{n}.jsonl.gz'
    t0 = time.time()
    print(f'{a.kind}: {len(cf)} configs, {a.workers} workers -> {out}', flush=True)
    if a.workers > 1:
        import multiprocessing as mp
        with mp.Pool(a.workers, initializer=init) as pool, gzip.open(out, 'wt') as fh:
            for k, rec in enumerate(pool.imap_unordered(run, cf, chunksize=8)):
                fh.write(json.dumps(rec) + '\n')
                if k % 2000 == 0:
                    print(f'  {k}/{len(cf)} {time.time() - t0:.0f}s', flush=True)
    else:
        init()
        with gzip.open(out, 'wt') as fh:
            for rec in map(run, cf):
                fh.write(json.dumps(rec) + '\n')
    print(f'done {len(cf)} in {time.time() - t0:.1f}s; inputs {json.dumps(load(with_perts=False)["sources"])}; old {OLD_CORR} {OLD_VFULL}', flush=True)
