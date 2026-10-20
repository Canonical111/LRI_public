#!/usr/bin/env python3
"""Exact (50-digit) propagation of every kept delta-model member through every LSQ configuration.

For each configuration (tails, lead, lo, hi in HIS), level full/full3, omega set wf:
  base   : medoid-central corrected data, intercept c_n and residual vector (mode E: reference lower limits;
           mode S: own chain), n = 3..8;
  members: for k = 6, 7, 8 and every kept member i, data shifted by delta dC_k = member_i - medoid, either
           'seam' (only at modelled L > hi_exact) or 'smooth' (at every L), giving the new intercept and max residual
           at n = k..8 (linear in the shift: delta S_n = e_{n-k} delta dC_k [- sum_j e_j delta lim_{n-j} in mode S]).
Output: OUTDIR/members_prop.npz (arrays dc_<mode>_<type>_<level>_hi<hi>_k<k> [ncfg, nmem, 9] and the matching mr_...)
and members_prop_index.json (configuration list, base values).
usage: members_prop.py MEMBERS_FULL.json OUTDIR NPROC
"""
import sys, os, json, time, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from multiprocessing import Pool

HIS = (72, 92, 118)
LOS = (8, 10, 12, 16, 20, 24, 32, 40, 50)
MF = json.load(open(sys.argv[1]))
D = load_corrected()          # medoid central (default)
LS, ROWS = table(D, 'dconn')
MEM = {}
for k in (6, 7, 8):
    m = MF[str(k)]
    P = np.array(m['pred']); Lf = m['L']
    med = D['central_members'][k]['member']
    MEM[k] = dict(L=Lf, dev={L: [mp.mpf(P[i, a]) - mp.mpf(P[med, a]) for i in range(len(P))] for a, L in enumerate(Lf)},
                  hi_exact=m['hi_exact'], n=len(P))
ECache = {}


def evec(L, n):
    if (L, n) not in ECache:
        ECache[(L, n)] = eseries(mp.log(L), omegas_for('full', n, 'wf'), n - 2)
    return ECache[(L, n)]


def lims_ref(n):
    out = {2: C2_mp, 3: C3_mp}
    for k in range(4, n):
        out[k] = mp.mpf(REF[k])
    return out


def run(cfg):
    tname, terms, lead, lo, hi = cfg
    Lw = [L for L in LS if lo <= L <= hi]
    out = dict(cfg=dict(tails=tname, lead=lead, lo=lo, hi=hi), base={}, arr={})
    for level in ('full', 'full3'):
        nl = nlead(level, 8)
        Dd = {}
        for nmax, Ls in ((7, Lw), (8, [L for L in Lw if L <= 92])):
            if len(Ls) < 1 + nl + len(terms) + 3:
                Dd[nmax] = None
            else:
                Dd[nmax] = (MPDesign(design(Ls, ROWS, terms, lead, nl)), Ls)
        if Dd[7] is None:
            continue

        def get(n):
            return Dd[7] if n <= 7 else (Dd[8] if hi <= 92 else None)
        base = {}
        for mode in ('E', 'S'):
            lims = {2: C2_mp, 3: C3_mp}
            for n in range(3, 9):
                g = get(n)
                if g is None:
                    continue
                Dm, Ls = g
                ll = lims_ref(n) if mode == 'E' else dict(lims)
                S = ssub(Ls, ROWS, n, omegas_for(level, n, 'wf'), ll)
                yv = mp.matrix(S); ps = Dm.P * yv
                p = [ps[j] / Dm.sc[j] for j in range(len(Dm.sc))]
                res = Dm.X * mp.matrix(p) - yv
                base[(mode, n)] = (p[0], res)
                if mode == 'S' and n >= 4:
                    lims[n] = p[0]
        out['base'][level] = {'%s%d' % mn: [float(v[0]), float(max(abs(x) for x in v[1]))] for mn, v in base.items()}
        for k in (6, 7, 8):
            M = MEM[k]
            for typ in ('seam', 'smooth'):
                for mode in (('E', 'S') if typ == 'seam' else ('E',)):
                    dc = np.full((M['n'], 9), np.nan); mr = np.full((M['n'], 9), np.nan)
                    for i in range(M['n']):
                        dlim = {}
                        for n in range(k, 9):
                            g = get(n)
                            if g is None or (mode, n) not in base:
                                continue
                            Dm, Ls = g
                            dS = []
                            for L in Ls:
                                d = M['dev'][L][i] if (typ == 'smooth' or L > M['hi_exact']) else mp.mpf(0)
                                e = evec(L, n)
                                s = e[n - k] * d
                                if mode == 'S':
                                    for j in range(1, n - 3):
                                        if n - j >= max(k, 4):
                                            s -= e[j] * dlim.get(n - j, 0)
                                dS.append(s)
                            yv = mp.matrix(dS); ps = Dm.P * yv
                            p = [ps[j] / Dm.sc[j] for j in range(len(Dm.sc))]
                            dres = Dm.X * mp.matrix(p) - yv
                            r0 = base[(mode, n)][1]
                            dc[i, n] = float(p[0]); mr[i, n] = float(max(abs(r0[a] + dres[a]) for a in range(len(dS))))
                            if mode == 'S':
                                dlim[n] = p[0]
                    out['arr']['%s_%s_%s_hi%d_k%d' % (mode, typ, level, hi, k)] = (dc, mr)
    return out


if __name__ == '__main__':
    outdir = sys.argv[2]; nproc = int(sys.argv[3])
    os.makedirs(outdir, exist_ok=True)
    CF = []
    for (tname, terms), lead, lo, hi in itertools.product(TAILSETS, ('T2', 'x'), LOS, HIS):
        npts = len([L for L in LS if lo <= L <= hi])
        if lo < hi and npts >= 1 + 2 + len(terms) + 3:
            CF.append((tname, terms, lead, lo, hi))
    if os.environ.get('MI_ONLY'):
        CF = CF[:int(os.environ['MI_ONLY'])]
    print('configs', len(CF), 'central', D['central_rule'], D['central_members'], flush=True)
    t0 = time.time(); res = []
    with Pool(nproc) as pool:
        for i, r in enumerate(pool.imap_unordered(run, CF, chunksize=1)):
            res.append(r)
            if i % 50 == 0:
                print(i, r['cfg'], '%.0fs' % (time.time() - t0), flush=True)
    index = []; arrs = {}
    for ci, r in enumerate(res):
        index.append(dict(cfg=r['cfg'], base=r['base']))
        for key, (dc, mr) in r['arr'].items():
            arrs.setdefault('dc_' + key, {})[ci] = dc; arrs.setdefault('mr_' + key, {})[ci] = mr
    npz = {}
    for key, d in arrs.items():
        k = int(key.split('_k')[-1]); nm = MEM[k]['n']
        A = np.full((len(res), nm, 9), np.nan)
        for ci, v in d.items():
            A[ci] = v
        npz[key] = A
    np.savez_compressed(os.path.join(outdir, 'members_prop.npz'), **npz)
    json.dump(dict(index=index, central=D['central_members'], labels={k: MF[str(k)]['labels'] for k in (6, 7, 8)}),
              open(os.path.join(outdir, 'members_prop_index.json'), 'w'))
    print('done %.0fs' % (time.time() - t0))
