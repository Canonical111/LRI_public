#!/usr/bin/env python3
"""K_d from the THREE-node rule (tag topmode): identical to K_general/R_part/kjet_prod.py except that
<t^2 R_tau>_d = sum_{j<3} w_j Xi_R(t_j) with t_j = t0 + j/3 and w_j = (1/3) sum_{|k|<=1} rho_k e^{-2 pi i k t_j}
(rblocks.tR3), which uses c_{+-2} = 0 (PROOF.md).  rblocks.py is used unchanged.
  F(tau) = C(tau) <t^2 R_tau>_d - C(tau)^2 Gamma(q-tau/2)^4/Gamma(q+tau/2)^4,   K_d = -A U/4 + (1/4)[tau^2] F.
usage: kjet3_prod.py d r N K M dps out.json   (workers from env NWORKERS)"""
import sys, os, time, json
import mpmath as mp
from multiprocessing import Pool


def work(args):
    ds, rs, N, K, M, dps, s = args
    mp.mp.dps = dps
    import rblocks as rb
    d = mp.mpf(ds); q = d / 4; r = mp.mpf(rs)
    tau = r * mp.expj(2 * mp.pi * s / N)
    if s == 0 or s == N // 2:
        tau = mp.mpf(mp.re(tau))
    st = time.time()
    tr = rb.tR3(q, tau, K, M)
    C = rb.Cfac(q, tau)
    X = mp.gamma(q - tau / 2) * mp.rgamma(q + tau / 2)
    F = C * tr - C ** 2 * X ** 4
    return s, str(mp.re(F)), str(mp.im(F)), str(mp.re(tr)), str(mp.im(tr)), round(time.time() - st, 1)


if __name__ == '__main__':
    ds, rs, N, K, M, dps, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
    workers = int(os.environ.get('NWORKERS', '3'))
    st = time.time()
    with Pool(workers) as pool:
        res = pool.map(work, [(ds, rs, N, K, M, dps, s) for s in range(N // 2 + 1)], chunksize=1)
    mp.mp.dps = dps
    d = mp.mpf(ds); q = d / 4; r = mp.mpf(rs)
    Fs, taus = {}, {}
    for s, fr, fi, _, _, _ in res:
        Fs[s] = mp.mpc(fr, fi)
        taus[s] = r * mp.expj(2 * mp.pi * s / N)
    for s in range(N // 2 + 1, N):
        Fs[s] = mp.conj(Fs[N - s]); taus[s] = mp.conj(taus[N - s])
    coef = lambda k: mp.re(mp.fsum(Fs[s] * taus[s] ** (-k) for s in range(N)) / N)
    A = mp.psi(0, 2 * q) + mp.psi(0, 1) - 2 * mp.psi(0, q)
    U = mp.psi(2, q)
    Kd = -A * U / 4 + coef(2) / 4
    rec = dict(rule='three-node', d=ds, r=rs, N=N, K=K, M=M, dps=dps, K_d=mp.nstr(Kd, dps - 5), F0=mp.nstr(coef(0), 5),
               tE2=mp.nstr(coef(1), dps - 8), tE2_minus_1p5psi2=mp.nstr(coef(1) - mp.mpf(3) / 2 * U, 5), F3=mp.nstr(coef(3), dps - 10),
               F_taylor_abs={k: mp.nstr(abs(coef(k)), 3) for k in (4, 8, 12, 16, 20, 24)},
               points={s: dict(Re_F=fr, Im_F=fi, Re_tR=tr, Im_tR=ti, sec=sec) for s, fr, fi, tr, ti, sec in res},
               wall=round(time.time() - st, 1))
    json.dump(rec, open(out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k != 'points'}, indent=1))
