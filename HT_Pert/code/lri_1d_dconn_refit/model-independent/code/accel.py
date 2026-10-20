#!/usr/bin/env python3
"""Sequence accelerators on the e-subtracted sequences (model-independent lens).

S_n(L; w) = S0_n(L) + w * l T2(L), S0 with omega_1..omega_{n-3} (top omega free), w = -omega_{n-2} chosen to minimise
the spread of the estimates over settings (as in the earlier lens).
  Neville: polynomial in x = L^-1/2 through N points with stride `step` ending at `top`, evaluated at x = 0.
           Families 'all' (step 1-4, N 4-8), 'step>=2', 'N>=6,step>=2' (primary, as before). First point L >= 16.
  BST:     h = 1/L, exponent 1/2, step 2-4, N 5-8.
Kinds/modes: dconn E (exact lower limits; omega wf primary, raw variant), dconn S (self-consistent chain, w by
stability at every order), raw E, raw H (earlier lens targets; reproduction check). Tops 84, 88, 92 (n <= 8) and 100,
110, 118 (n <= 7). Neville weights are stored so the delta-model variants can be propagated exactly (linear) offline;
BST is re-run here on the delta-model extremes (vmin/vmax at the top point and the +-envelope, per order k = 6, 7, 8).
usage: accel.py OUTDIR [NPROC]
"""
import sys, os, json, time, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from multiprocessing import Pool

mp.mp.dps = 30
D = load_corrected()
V = load_variants()
LS, ROWS = {}, {}
for kind in ('dconn', 'raw'):
    LS[kind], ROWS[kind] = table(D, kind)
DCONN_GUESS = {4: 0.0803, 5: 0.717, 6: 2.3, 7: 2.8, 8: 84.0}
TOPS = tuple(int(x) for x in os.environ.get('MI_ACC_TOPS', '84,88,92,100,110,118').split(','))   # refit72: env override (adds delta-free tops 60, 72)


def lims_ref(n, mode):
    out = {2: C2_mp, 3: C3_mp}
    for k in range(4, n):
        out[k] = mp.mpf(REF[k] - (DCONN_GUESS[k] if mode == 'H' else 0.0))
    return out


def neville_w(xs):
    n = len(xs); nu = []
    for i in range(n):
        v = mp.mpf(1)
        for j in range(n):
            if j != i:
                v *= (0 - xs[j]) / (xs[i] - xs[j])
        nu.append(v)
    return nu


def bst(hs, ys, om=mp.mpf('0.5')):
    n = len(ys); prev2 = [mp.mpf(0)] * (n + 1); prev = list(ys)
    for m in range(1, n):
        cur = []
        for i in range(n - m):
            d = prev[i + 1] - prev[i]; den2 = prev[i + 1] - prev2[i + 1]
            if den2 == 0:
                den2 = mp.mpf('1e-40')
            fac = (hs[i] / hs[i + m]) ** om * (1 - d / den2) - 1
            cur.append(prev[i + 1] + d / fac)
        prev2, prev = prev, cur
    return prev[0]


def settings(Ls, top, steps, Ns):
    it = Ls.index(top); out = []
    for step in steps:
        for N in Ns:
            idx = list(range(it, it - step * N, -step))[::-1]
            if idx[0] < 0 or Ls[idx[0]] < 16:
                continue
            out.append(((step, N), [Ls[i] for i in idx]))
    return out


REFW = {3: 3.5, 4: -30., 5: 450., 6: -14000., 7: 360000., 8: -1.05e7}


def bst_est(S0, G, sets):
    def ests(w):
        return np.array([float(bst([1 / mp.mpf(L) for L in Lset], [S0[L] + w * G[L] for L in Lset])) for _, Lset in sets])
    def spread(w):
        return float(np.std(ests(w)))
    ref = REFW[S0['_n']]
    grid = np.linspace(0.6 * ref, 1.4 * ref, 33) if ref > 0 else np.linspace(1.4 * ref, 0.6 * ref, 33)
    sp = [spread(w) for w in grid]; k = int(np.argmin(sp))
    a, b = grid[max(k - 1, 0)], grid[min(k + 1, len(grid) - 1)]
    for _ in range(22):
        m1 = a + (b - a) * 0.382; m2 = a + (b - a) * 0.618
        if spread(m1) < spread(m2):
            b = m2
        else:
            a = m1
    w = (a + b) / 2; e = ests(w)
    return dict(w=float(w), est_med=float(np.median(e)), spread=float(np.std(e)), ests=e.tolist())


def job(args):
    kind, mode, omset, top, rows_override, tag = args
    rows = rows_override if rows_override is not None else ROWS[kind]
    Ls = [L for L in LS[kind] if L <= top]
    G = {L: mp.log(L) * (rows[L][2] - C2_mp) for L in Ls}
    nsets = settings(Ls, top, (1, 2, 3, 4), (4, 5, 6, 7, 8))
    bsets = settings(Ls, top, (2, 3, 4), (5, 6, 7, 8))
    res = dict(kind=kind, mode=mode, om=omset, top=top, tag=tag, n={})
    lims = {2: C2_mp, 3: C3_mp}
    for n in range(3, 9):
        if n == 8 and top > 92:
            break
        if mode in ('E', 'H'):
            lims = lims_ref(n, mode)
        w = omegas_for('full', n, omset)
        S0 = dict(zip(Ls, ssub(Ls, rows, n, w, lims)))
        S0['_n'] = n
        ent = {}
        if tag == 'central':
            A, B, keys, nus = [], [], [], []
            for key, Lset in nsets:
                nu = neville_w([mp.mpf(L) ** mp.mpf(-0.5) for L in Lset])
                A.append(float(mp.fsum(nu[a] * S0[L] for a, L in enumerate(Lset))))
                B.append(float(mp.fsum(nu[a] * G[L] for a, L in enumerate(Lset))))
                keys.append(key); nus.append(dict(L=Lset, nu=[float(x) for x in nu]))
            ent['neville'] = dict(A=A, B=B, keys=keys, nu=nus)
        ent['bst'] = bst_est(S0, G, bsets)
        if mode in ('S', 'Sb'):   # self-consistent: own Neville(N>=6,step>=2) estimate feeds the next order
            nev = ent.get('neville')
            if nev is None:
                raise RuntimeError('S chain needs central')
            a = np.array(nev['A']); b = np.array(nev['B'])
            sel = [i for i, kk in enumerate(nev['keys']) if kk[0] >= 2 and kk[1] >= 6]
            am = a[sel] - a[sel].mean(); bm = b[sel] - b[sel].mean()
            wopt = -np.dot(am, bm) / np.dot(bm, bm)
            est_nev = float(np.median(a[sel] + wopt * b[sel]))
            ent['seq_lim_neville'] = est_nev
            ent['seq_lim_bst'] = ent['bst']['est_med']
        res['n'][n] = ent
        if mode in ('S', 'Sb') and n >= 4:
            lims[n] = mp.mpf(ent['seq_lim_neville'] if mode == 'S' else ent['seq_lim_bst'])
    return res


def variant_rows(k, seq):
    new = {}
    for L in LS['dconn']:
        r = list(ROWS['dconn'][L])
        if L in seq and r[k] is not None:
            r[k] = mp.mpf(D['raw'][k][L]) + mp.mpf(seq[L])
        new[L] = r
    return new


if __name__ == '__main__':
    if os.environ.get('ACC_SMOKE'):
        t0 = time.time(); r = job(('dconn', 'E', 'wf', 92, None, 'central'))
        for n, e in r['n'].items():
            a = np.array(e['neville']['A']); b = np.array(e['neville']['B'])
            sel = [i for i, kk in enumerate(e['neville']['keys']) if kk[0] >= 2 and kk[1] >= 6]
            am = a[sel] - a[sel].mean(); bm = b[sel] - b[sel].mean(); w = -np.dot(am, bm) / np.dot(bm, bm)
            est = np.median(a[sel] + w * b[sel])
            print(n, 'nev', est, rel(est, n), 'w', w, '| bst', e['bst']['est_med'], rel(e['bst']['est_med'], n), e['bst']['w'])
        print('%.1fs' % (time.time() - t0)); sys.exit()
    outdir = sys.argv[1]; nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    os.makedirs(outdir, exist_ok=True)
    jobs = []
    for top in TOPS:
        jobs += [('dconn', 'E', 'wf', top, None, 'central'), ('dconn', 'E', 'raw', top, None, 'central'),
                 ('dconn', 'S', 'wf', top, None, 'central'), ('dconn', 'Sb', 'wf', top, None, 'central'),
                 ('raw', 'E', 'raw', top, None, 'central'),
                 ('raw', 'H', 'raw', top, None, 'central')]
    # BST on delta-model extremes (dconn E wf, tops 84/88/92 and 118)
    for k in (6, 7, 8):
        Vk = V[k]
        Lin = [L for L in Vk['L'] if L in D['dC'][k] and not D['exact'][k][L]]
        for top in (84, 88, 92, 118):
            if k == 8 and top > 92:
                continue
            iL = Vk['L'].index(min(top, max(Lin)))
            cands = {'vmin': int(np.argmin(Vk['pred'][:, iL])), 'vmax': int(np.argmax(Vk['pred'][:, iL]))}
            seqs = {nm: {L: Vk['pred'][i][a] for a, L in enumerate(Vk['L']) if L in Lin} for nm, i in cands.items()}
            seqs['env+'] = {L: D['dC'][k][L] + D['unc'][k][L] for L in Lin}
            seqs['env-'] = {L: D['dC'][k][L] - D['unc'][k][L] for L in Lin}
            for nm, seq in seqs.items():
                jobs.append(('dconn', 'E', 'wf', top, variant_rows(k, seq), 'k%d_%s' % (k, nm)))
    print('jobs', len(jobs), flush=True)
    t0 = time.time(); out = []
    with Pool(nproc) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs, chunksize=1)):
            out.append(r)
            print(i, r['kind'], r['mode'], r['om'], r['top'], r['tag'], '%.0fs' % (time.time() - t0), flush=True)
    json.dump(dict(meta=dict(corrected=D['path'], tag=D['tag'], central_rule=D['central_rule'], central_members=D.get('central_members')), results=out), open(os.path.join(outdir, 'accel.json'), 'w'))
    print('done %.0fs' % (time.time() - t0))
