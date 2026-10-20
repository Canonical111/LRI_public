"""Timing probe: build operator caches and time single points (cluster only)."""
import sys, os, time
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from flint import ctx, acb, arb

def one(args):
    L, scheme, cap, prec = args
    from basis import load_or_build
    from hamil import NumOps
    from solve import solve_point
    ctx.prec = prec
    t = time.time(); sp, ops = load_or_build(L, cap, os.path.join(HERE, 'cache')); tb = time.time() - t
    t = time.time(); no = NumOps(sp, ops); tn = time.time() - t
    eps = acb(arb(2) * 5 / 128).exp_pi_i() / 64
    t = time.time(); res = solve_point(no, scheme, L, eps); tp = time.time() - t
    return (L, scheme, cap, prec, sp.dim(0), sp.dim(1), round(tb, 1), round(tn, 1), round(tp, 1),
            [len(d['newton']) for d in res['diag']], res['diag'][-1]['wts'])

if __name__ == '__main__':
    L = int(sys.argv[1])
    from basis import load_or_build
    t = time.time(); load_or_build(L, 19, os.path.join(HERE, 'cache')); print('build', L, time.time() - t, flush=True)
    jobs = [(L, s, 19, 256) for s in ('raw', 'consistent', 'literal')]
    with Pool(len(jobs)) as p:
        for r in p.imap_unordered(one, jobs):
            print(r, flush=True)
