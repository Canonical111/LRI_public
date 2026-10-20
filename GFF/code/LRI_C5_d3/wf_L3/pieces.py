#!/usr/bin/env python3
"""Taylor data in gamma (= 3/2 - b/2) of every piece of W_4(3;b), from Cauchy circles.
usage: pieces.py OUT.json DPS N K M RHO [workers]
Values returned at each circle point (all normalized so that Euler's constant cannot appear):
  pref2 = pref^2, pref4 = pref^4, pref = Gamma(3/2)Gamma(gamma)/Gamma(3/2-gamma)
  A,B,C   = pref2*(a,b,c)             ordinary amplitudes  Psi_0 = a + c cos 2pi u, Psi_1 = b sin 2pi u
  V0p,V1p,V0q,V1q = pref2*U_{0,1}(1/4), pref2*U_{0,1}(3/4)
  H0 = pref4*Tp(alpha) (t=0 node),  Hh = pref4*Tp(1/4) (u=1/4 node; t=1/8 at gamma=3/4)
  C0,C1,C2 = pref4*(c0,c1,c2),  W = W_4(3;b)
"""
import sys, json, time, os
import mpmath as mp
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen3 as G

KEYS = ['pref', 'A', 'B', 'C', 'V0p', 'V1p', 'V0q', 'V1q', 'H0', 'Hh', 'C0', 'C1', 'C2', 'W']


def pieces(g, N, K):
    g = mp.mpmathify(g)
    sig = mp.mpf(3) / 2 - g
    d = G.D3(g, N, K)
    pref = mp.gamma(mp.mpf(3) / 2) * mp.gamma(g) / mp.gamma(sig)
    p2, p4 = pref ** 2, pref ** 4
    c0, c1, c2, info = d.cks()
    Bw = G.Bweights(4, sig)
    cs = [c0, c1, c2, 0]
    E4 = -mp.fsum(Bw[k] * cs[k] for k in range(3)) / (mp.pi * mp.sin(mp.pi * sig)) ** 4
    q, h = mp.mpf(1) / 4, mp.mpf(3) / 4
    out = dict(pref=pref, A=p2 * info['a'], B=p2 * info['b'], C=p2 * info['c'],
               V0p=p2 * d.U(0, q), V1p=p2 * d.U(1, q), V0q=p2 * d.U(0, h), V1q=p2 * d.U(1, h),
               H0=p4 * d.Tp(d.al), Hh=p4 * d.Tp(q), C0=p4 * c0, C1=p4 * c1, C2=p4 * c2, W=p4 * E4)
    return [out[k] for k in KEYS]


def job(k):
    c = json.loads(os.environ['L3_CFG'])
    mp.mp.dps = c['dps']
    th = 2 * mp.pi * k / c['M']
    g = mp.mpf(3) / 4 + mp.mpf(c['rho']) * mp.expj(th)
    return k, [str(x) for x in pieces(g, c['N'], c['K'])]


def taylor(vals, M, rho, jmax=3):
    """vals: dict k->list for k=0..M/2 (conjugate symmetry fills the rest)."""
    half = M // 2
    full = {}
    for k in range(M):
        full[k] = vals[k] if k <= half else [mp.conj(x) for x in vals[M - k]]
    res = {}
    for i, key in enumerate(KEYS):
        f = [full[k][i] for k in range(M)]
        res[key] = [mp.fsum(f[k] * mp.expj(-2 * mp.pi * j * k / M) for k in range(M)) / M / rho ** j * mp.factorial(j)
                    for j in range(jmax)]
    return res


if __name__ == '__main__':
    out = sys.argv[1]
    c = dict(dps=int(sys.argv[2]), N=int(sys.argv[3]), K=int(sys.argv[4]), M=int(sys.argv[5]), rho=sys.argv[6])
    workers = int(sys.argv[7]) if len(sys.argv) > 7 else int(os.environ.get('SLURM_CPUS_PER_TASK', 3))
    os.environ['L3_CFG'] = json.dumps(c)
    mp.mp.dps = c['dps']
    st = time.time()
    ks = list(range(c['M'] // 2 + 1))
    with Pool(workers) as pool:
        res = dict(pool.map(job, ks, chunksize=1))
    # centre values too (direct, real)
    centre = [str(x) for x in pieces(mp.mpf(3) / 4, c['N'], c['K'])]
    rec = dict(c, keys=KEYS, seconds=time.time() - st, values={str(k): res[k] for k in ks}, centre=centre)
    json.dump(rec, open(out, 'w'), indent=1)
    mp.mp.dps = c['dps'] + 10
    vals = {k: [mp.mpmathify(x) for x in res[k]] for k in ks}
    T = taylor(vals, c['M'], mp.mpf(c['rho']))
    for key in KEYS:
        print(key, mp.nstr(T[key][0].real, 25), mp.nstr(T[key][1].real, 25), ' imag', mp.nstr(T[key][1].imag, 3))
    print('L3 = -W1/2 =', mp.nstr(-T['W'][1].real / 2, c['dps']))
    print('seconds %.0f' % (time.time() - st))
