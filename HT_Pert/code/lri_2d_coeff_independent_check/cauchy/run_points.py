"""Solve the tuning problem at the K points eps_k = rho exp(2 pi i k/K) and write all point values.

usage: python run_points.py --scheme raw --L 4 --rho 1/32 --K 64 --prec 256 --cap 19 --out file.json
       [--procs 64] [--tsteps 0.25,0.5,0.75,1] [--half]
"""
import argparse, json, os, sys, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
           'NUMEXPR_NUM_THREADS'):
    os.environ[_v] = '1'  # one BLAS thread per worker process (the K points are the parallel dimension)
from fractions import Fraction
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from flint import ctx, acb, arb  # noqa: E402

G = {}


def cstr(z, digits):
    z = acb(z)
    return [z.real.mid().str(digits, radius=False), z.imag.mid().str(digits, radius=False)]


def init(args_dict, cache_dir):
    from basis import load_or_build
    from hamil import NumOps
    ctx.prec = args_dict['prec']
    sp, ops = load_or_build(args_dict['L'], args_dict['cap'], cache_dir)
    G['no'] = NumOps(sp, ops)
    G['a'] = args_dict


def eps_point(rho, K, k):
    fr = Fraction(rho)
    r = arb(fr.numerator) / fr.denominator
    return acb(arb(2 * k) / K).exp_pi_i() * r


def work(k):
    from solve import solve_point
    a = G['a']
    t0 = time.time()
    eps = eps_point(a['rho'], a['K'], k)
    res = solve_point(G['no'], a['scheme'], a['L'], eps, tsteps=a['tsteps'])
    dg = int(a['prec'] * 0.30103) + 3
    out = {
        'k': k,
        'eps': cstr(res['eps'], dg),
        'r': cstr(res['r'], dg),
        'g': cstr(res['g'], dg),
        'E': {str(p): cstr(v, dg) for p, v in res['E'].items()},
        'Delta': cstr(res['Delta'], dg),
        'vacua': ({str(l): cstr(v, dg) for l, v in res['vacua'].items()} if res['vacua'] else None),
        'diag': res['diag'],
        'E0_minus_EvL': res['E0_minus_EvL'],
        'seconds': time.time() - t0,
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scheme', required=True, choices=['raw', 'consistent', 'literal'])
    ap.add_argument('--L', type=int, required=True)
    ap.add_argument('--rho', required=True)
    ap.add_argument('--K', type=int, required=True)
    ap.add_argument('--prec', type=int, default=256)
    ap.add_argument('--cap', type=int, default=19)
    ap.add_argument('--procs', type=int, default=1)
    ap.add_argument('--tsteps', default='0.25,0.5,0.75,1')
    ap.add_argument('--half', action='store_true',
                    help='compute k=0..K/2 only and fill the rest by conjugation symmetry')
    ap.add_argument('--cache', default=os.path.join(HERE, 'cache'))
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ad = {'scheme': a.scheme, 'L': a.L, 'rho': a.rho, 'K': a.K, 'prec': a.prec, 'cap': a.cap,
          'tsteps': tuple(float(t) for t in a.tsteps.split(','))}
    # build the operator cache once in the parent
    from basis import load_or_build
    t0 = time.time()
    sp, ops = load_or_build(a.L, a.cap, a.cache)
    dims = {par: sp.dim(par) for par in (0, 1)}
    print(f"basis L={a.L} cap={a.cap} dims={dims} built/loaded in {time.time()-t0:.1f}s", flush=True)
    ks = list(range(a.K // 2 + 1)) if a.half else list(range(a.K))
    t0 = time.time()
    with Pool(a.procs, initializer=init, initargs=(ad, a.cache)) as pool:
        pts = []
        for res in pool.imap_unordered(work, ks):
            pts.append(res)
            print(f"k={res['k']} done in {res['seconds']:.1f}s; Delta={res['Delta'][0][:20]} "
                  f"newton={[len(d['newton']) for d in res['diag']]} wts={res['diag'][-1]['wts']}",
                  flush=True)
    pts.sort(key=lambda d: d['k'])
    meta = dict(ad)
    meta.update({'dims': dims, 'half': a.half, 'wall_seconds': time.time() - t0,
                 'host': os.uname().nodename, 'slurm_job': os.environ.get('SLURM_JOB_ID')})
    with open(a.out, 'w') as f:
        json.dump({'meta': meta, 'points': pts}, f)
    print("wrote", a.out, flush=True)


if __name__ == '__main__':
    main()
