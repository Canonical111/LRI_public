"""Cutoff-offset test of the window correction (theoretical-skeptic check).

The frozen cutoff N + P/4 <= Lam is moved OFF the even integers, Lam = L + k/4.
Vacuum levels sit at half-integers with period 2 in their type (E = 0, 1/2, 1, 3/2 mod 2),
so any level-local (window) defect makes C_k(Lam) oscillate with period 2 in Lam, with a
NON-decaying amplitude; genuine continuum tails are smooth in Lam.  If Dconn is the
complete correction, the corrected C4(Lam) must be smooth (no non-decaying period-2 part)
and its limit must not depend on the offset.

Two schemes, each with FULL order-by-order retuning of r_k, g_k (k=2,3,4) because for
Lam mod 2 in [1,2) the reference windows contain an odd shell already at eps^2:
 raw  : H = H0 + eps F1 + r M + g V on {4N+P <= 4 Lam}
 corr : + package operator g(eps)^2 D(eps) (windows (Lam-E0, Lam]) on every state,
        and on the model state Dconn = [E_vac(Lam)-E_vac(Lam-E0)] + R(Lam) - R(Lam-E0)
        (R = bubble-bubble pairs already restored by the g^2D response; A's Rclosed).
Usage: offset_c4.py Lam [Lam ...]   (Lam multiple of 1/4)
"""
import sys, os, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ht4 import *   # Space, block_rs, vacuum_table, find, np, math


def Rclosed(Lp, g1=1 / 3):
    s = 0.
    top = int(math.floor(Lp + 1e-9))
    for E in range(1, top + 1, 2):
        n = sum(1 for k in range(1, top + 1) if k % 2 == 1 and Lp - E < k <= Lp)
        s += n / E
    return -(g1 ** 4 / 36) * s


def run(Lam, pm=11, qm=9, schemes=('raw', 'corr')):
    t0 = time.time()
    Lint = 2 * int(math.ceil(Lam / 2 - 1e-12))
    sp = Space(Lint, pm, qm, 3)
    q4 = int(round(4 * Lam)); assert abs(q4 - 4 * Lam) < 1e-9
    E4 = 4 * sp.N.astype(np.int64) + sp.P.astype(np.int64)
    allowed = E4 <= q4
    seeds = {p: find(sp, p, 0)[0] for p in range(4)}
    masks = {p: (sp.N % 2 == 0) & (sp.P % 2 == p % 2) & allowed for p in range(4)}
    # 'd' = level-1 descendant of phi: a_1^dagger|0>, E0 = 5/4, sector N odd / P odd
    seeds['d'] = find(sp, 1, 1)[0]
    masks['d'] = (sp.N % 2 == 1) & (sp.P % 2 == 1) & allowed
    e0 = {0: 0., 1: .25, 2: .5, 3: .75, 'd': 1.25}
    vmask = lambda Lp: (sp.N % 2 == 0) & (sp.P % 2 == 0) & (E4 <= int(math.floor(4 * Lp + 1e-9)))
    sums = vacuum_table(Lint, 4)
    top = int(math.floor(Lam + 1e-9))
    up = np.clip((q4 - E4) // 4, 0, top)          # floor(Lam - E0)
    Dbase = np.stack([-(sums[top, k] - sums[up, k]) / 6 for k in range(5)], 1)
    out = {'Lam': Lam, 'dim': int(sp.dim), 'Ndim_allowed': int(allowed.sum())}
    for scheme in schemes:
        r = np.zeros(5); g = np.zeros(5); g[1] = 1 / 3
        E = {}; first = {}; dc = {}
        for K in (2, 3, 4):
            diag = None; dat = {p: None for p in e0}
            if scheme == 'corr':
                gg = np.convolve(g, g)[:5]
                diag = np.zeros((sp.dim, 5))
                for a in range(5):
                    for b in range(5 - a):
                        if gg[a] != 0.: diag[:, a + b] += gg[a] * Dbase[:, b]
                ev = {}
                for p in e0:
                    Lp = Lam - e0[p]
                    if Lp not in ev:
                        ev[Lp] = block_rs(sp, [0], K, r, g, vmask(Lp))[0][:, 0, 0].copy()
                for p in e0:
                    d = np.zeros(K + 1); d[:] = ev[Lam] - ev[Lam - e0[p]]
                    if K >= 4: d[4] += Rclosed(Lam) - Rclosed(Lam - e0[p])
                    dc[p] = d.copy()
                    dat[p] = d - diag[seeds[p], :K + 1]
            for p in ((0, 1, 3) if K < 4 else (0, 1, 2, 3, 'd')):
                h, f1, spect, _ = block_rs(sp, [seeds[p]], K, r, g, masks[p], diag,
                                           None if dat[p] is None else {0: dat[p]})
                assert len(spect) == 0
                E[p] = np.zeros(5); E[p][:K + 1] = h[:, 0, 0]; first[p] = f1[0, 0]
            rK = -(E[1][K] - E[0][K]) / first[1][0]
            gK = (-(E[3][K] - E[0][K]) - first[3][0] * rK) / first[3][1]
            r[K] = rK; g[K] = gK
            for p in E: E[p][K] += rK * first[p][0] + gK * first[p][1]
        vd = E['d'] - E[1]; vd[0] -= 1
        out[scheme] = {'r': r.tolist(), 'g': g.tolist(), 'C': (E[2] - E[0]).tolist(), 'v_dphi': vd.tolist(),
                       'tune_res': [float(E[1][k] - E[0][k] - [0.25, -0.25, 0, 0, 0][k]) for k in range(5)]
                       + [float(E[3][k] - E[0][k] - [0.75, 0.25, 0, 0, 0][k]) for k in range(5)],
                       'E': {str(p): E[p].tolist() for p in E}}
        if scheme == 'corr':
            out[scheme]['Dconn_ref'] = {str(p): dc[p].tolist() for p in dc}
            out[scheme]['g2D_ref'] = {str(p): diag[seeds[p]].tolist() for p in e0}
    out['seconds'] = time.time() - t0
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    tag = [a for a in sys.argv[1:] if a.startswith('--tag=')]
    res = []
    for a in args:
        Lam = float(a)
        o = run(Lam)
        res.append(o)
        print(f"Lam={Lam:7.2f} dim={o['dim']:>9d} raw C2..C4={np.round(o['raw']['C'][2:],9).tolist()} "
              f"corr C2..C4={np.round(o['corr']['C'][2:],9).tolist()} v_dphi raw/corr e2..e4={np.round(o['raw']['v_dphi'][2:],7).tolist()} {np.round(o['corr']['v_dphi'][2:],7).tolist()} ({o['seconds']:.1f}s)", flush=True)
    name = tag[0][6:] if tag else '_'.join(args)
    json.dump(res, open(os.path.join(HERE, f'offset_{name}.json'), 'w'))
