"""Joint-lens C8 grid (hi=92, lo>=24, both low-order windows, all bases/modes/shifts/gaps) on a list of tables, unweighted
(whitened criteria) and weighted, with the verifier's own fitter. Tables: baselines, my continuation (central + members
spliced beyond 72) and synthetic S10-like noise realizations added to the smooth s46 table at L=46..72."""
import sys, os, json, itertools, time, pickle
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mytabs import get, weights
from myjoint2 import fit2
LOS = (24, 32, 40, 50, 60, 70)
BASES = ('A', 'B', 'C', 'D', 'Dj', 'E', 'F', 'BD', 'S', 'Bp', 'A+tower1', 'B+tower1', 'A+tower15', 'A+L075', 'B+L075', 'D+L075', 'E+L075', 'E+p25')
MODES = ('fixed', 'free', 'FL', 'FL5'); SHIFTS = (-2., 0., 2.); GAPS = ('orig', 'ext', 'wf')
CFG = list(itertools.product(('same', 'th118'), LOS, BASES, MODES, SHIFTS, GAPS))
L, raw, T = get(); W = weights(L, T)
TABS = {}

def build():
    cl = (L >= 46) & (L <= 72)
    real = T['fmean'] - T['s46']
    sig = {k: float(np.sqrt(np.mean(real[cl, k] ** 2))) for k in (6, 7, 8)}
    TABS['s46'] = T['s46']; TABS['fmean'] = T['fmean']; TABS['mine'] = T['mine']
    my = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'mycont_dC678.json')))
    Lp = list(range(74, 119, 2)); Ls = list(L.astype(int))
    for k in (6, 7, 8):
        K = [m for m in my[str(k)]['members'] if m['kept']]
        P = np.array([m['pred'] for m in K]); j = Lp.index(92)
        for tag, q in (('p16', 16), ('p84', 84)):
            i = int(np.argmin(np.abs(P[:, j] - np.percentile(P[:, j], q))))
            Tt = T['mine'].copy()
            for a, l in enumerate(Lp):
                ii = Ls.index(l)
                if np.isfinite(raw[ii, k]): Tt[ii, k] = raw[ii, k] + P[i, a]
            TABS['my%d_%s' % (k, tag)] = Tt
    for s in range(int(os.environ.get('NREAL', '20'))):
        rng = np.random.default_rng(9000 + s)
        Tn = T['s46'].copy()
        for k in (6, 7, 8):
            Tn[cl, k] += rng.normal(size=cl.sum()) * sig[k]
        TABS['noise%02d' % s] = Tn
    return sig

def work(arg):
    tname, wt, ci = arg
    low, lo, b, mode, sh, gap = CFG[ci]
    try:
        o = fit2(L, TABS[tname], lo, 92, b, mode, sh, gap, hi_low=118 if low == 'th118' else None, wrel=W, weighted=(wt == 'w'))
    except ValueError:
        return None
    return (tname, wt, ci, [o[n]['lim'] for n in range(4, 9)], o[8]['erms'], o[8]['rms'], o[8]['stat'], o[8]['npts'] - o[8]['ncol'],
            [o[n]['erms'] for n in range(4, 8)], [o[n]['npts'] - o[n]['ncol'] for n in range(4, 8)])

if __name__ == '__main__':
    sig = build()
    names = sys.argv[1].split(',') if len(sys.argv) > 1 and sys.argv[1] != 'all' else list(TABS)
    P = int(os.environ.get('P', '8'))
    jobs = [(t, wt, ci) for t in names for wt in ('u', 'w') for ci in range(len(CFG))]
    print('tables', names, 'configs', len(CFG), 'jobs', len(jobs), 'P', P, 'sig', sig, flush=True)
    t0 = time.time(); out = []
    with Pool(P) as pool:
        for k, r in enumerate(pool.imap_unordered(work, jobs, chunksize=64)):
            if r is not None: out.append(r)
            if k % 20000 == 0: print(k, '%.0fs' % (time.time() - t0), flush=True)
    pickle.dump(dict(cfg=CFG, res=out, sig=sig), open(sys.argv[2] if len(sys.argv) > 2 else 'jmc_out.pkl', 'wb'))
    print('done', len(out), '%.0fs' % (time.time() - t0))
