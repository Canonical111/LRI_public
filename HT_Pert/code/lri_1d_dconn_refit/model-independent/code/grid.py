#!/usr/bin/env python3
"""50-digit e-subtracted LSQ grid (model-independent lens) on the Dconn-corrected HT sequences, with the raw sequences
run through the identical machinery for comparison (kept separate, labelled kind='dconn' / kind='raw').

Per configuration (tail set, lead T2 or x=L^-1/2, lo, hi):
  mode E  : lower limits = reference values (exact C2..C6, diagrammatic C7). For kind='dconn' these are the consistent
            limits (corrected data converge to the physical values); for kind='raw' they are the known-to-fail naive ones.
  mode S  : self-consistent chain; lower limits are this configuration's own fits at orders 4..n-1 (same level, same
            omega set); only exact C2, C3 and the gap omegas enter.
  mode H  : kind='raw' only: the earlier lens's HT-consistent targets tau = ref - Dconn_guess (reproduction check).
  levels  : full (omega_1..omega_{n-3} fixed, top omega free), full3 (+ l^2 T2), lev2 (only omega1, omega2), free (none).
  omega sets: wf (window-free, primary for dconn), raw (raw-HT gap set = earlier lens 'ext').
  eff     : T2-lead, level full, mode E: omega3..5 replaced by this configuration's fitted effective top omegas.
Stores the intercept weights of every design (for linear propagation of the delta-model variants) and, for kind=dconn,
mode E, level full/full3, omega wf, the max residual under the delta-model extreme variants and envelope edges.
usage: grid.py OUTDIR [NPROC]
"""
import sys, os, json, time, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from multiprocessing import Pool

LOS = (8, 10, 12, 16, 20, 24, 32, 40, 50)
HIS = (44, 60, 72, 92, 118)
LEADS = ('T2', 'x')
DCONN_GUESS = {4: 0.0803, 5: 0.717, 6: 2.3, 7: 2.8, 8: 84.0}     # earlier lens (mode H, raw data)

D = load_corrected()
V = load_variants()
LS_ALL, ROWS = {}, {}
for kind in ('dconn', 'raw'):
    LS_ALL[kind], ROWS[kind] = table(D, kind)


def lims_ref(n, kind, mode):
    out = {2: C2_mp, 3: C3_mp}
    for k in range(4, n):
        v = REF[k] - (DCONN_GUESS[k] if mode == 'H' else 0.0)
        out[k] = mp.mpf(v)
    return out


def variant_rows(kind_rows, Ls, k, dc_seq):
    """copy of rows with dC_k replaced at modelled L by dc_seq (dict L -> value)."""
    new = {}
    for L in Ls:
        r = list(kind_rows[L])
        if L in dc_seq and r[k] is not None:
            r[k] = mp.mpf(D['raw'][k][L]) + mp.mpf(dc_seq[L])
        new[L] = r
    return new


def run_config(cfg):
    tname, terms, lead, lo, hi = cfg
    t0 = time.time()
    out = dict(cfg=dict(tails=tname, lead=lead, lo=lo, hi=hi), rows=[], weights={}, varres=[])
    Lw = [L for L in LS_ALL['dconn'] if lo <= L <= hi]
    L8 = [L for L in Lw if L <= 92]
    des = {}

    def getD(nl, Ls):
        key = (nl, len(Ls))
        if key not in des:
            if len(Ls) < 1 + nl + len(terms) + 3:
                des[key] = None
            else:
                des[key] = MPDesign(design(Ls, ROWS['dconn'], terms, lead, nl))
                out['weights']['%d_%d' % key] = dict(L=Ls, w=[float(x) for x in des[key].w],
                                                     gain=des[key].gain, cond=des[key].cond)
        return des[key]

    def fit(kind, n, level, lims, omset, rows=None):
        Ls = Lw if n <= 7 else L8
        if n == 8 and hi > 92:
            return None
        Dd = getD(nlead(level, n), Ls)
        if Dd is None:
            return None
        rws = rows if rows is not None else ROWS[kind]
        if n == 2:
            S = [rws[L][2] for L in Ls]
        else:
            S = ssub(Ls, rws, n, omegas_for(level, n, omset), lims)
        p, mres = Dd.solve(S)
        return dict(c=p[0], p=p, maxres=float(mres), gain=Dd.gain, cond=Dd.cond, npar=len(p), npts=len(Ls))

    def rec(kind, mode, level, omset, n, r, extra=None):
        if r is None:
            return
        row = dict(kind=kind, mode=mode, level=level, om=omset, n=n, c=float(r['c']), c_str=mp.nstr(r['c'], 25),
                   maxres=r['maxres'], gain=r['gain'], cond=r['cond'], npar=r['npar'], npts=r['npts'],
                   wkey='%d_%d' % (nlead(level, n), r['npts']))
        if level in ('full', 'full3') and n >= 3:
            row['top_coef'] = float(r['p'][2])       # coefficient of l*T2 (= -omega_{n-2} for lead T2)
        if extra:
            row.update(extra)
        out['rows'].append(row)

    for kind in ('dconn', 'raw'):
        # n = 2 control (lead must be x: T2 is C2 itself)
        if lead == 'x':
            rec(kind, 'E', 'full', 'wf', 2, fit(kind, 2, 'full', {}, 'wf'))
        modes = ('E', 'S', 'H') if kind == 'raw' else ('E', 'S')
        for mode in modes:
            levels = ('full', 'full3', 'lev2', 'free') if mode == 'E' else ('full', 'full3')
            if mode == 'H':
                levels = ('full',)
            omsets = ('wf', 'raw') if kind == 'dconn' else ('raw', 'wf')
            if mode == 'H':
                omsets = ('raw',)
            for level, omset in itertools.product(levels, omsets):
                if level in ('lev2', 'free') and omset != omsets[0]:
                    continue
                if mode in ('E', 'H'):
                    for n in range(3, 9):
                        if level == 'lev2' and n < 4:
                            continue
                        rec(kind, mode, level, omset, n, fit(kind, n, level, lims_ref(n, kind, mode), omset))
                else:   # self-consistent chain
                    lims = {2: C2_mp, 3: C3_mp}
                    for n in range(3, 9):
                        r = fit(kind, n, level, dict(lims), omset)
                        if r is None:
                            break
                        rec(kind, mode, level, omset, n, r)
                        if n >= 4:
                            lims[n] = r['c']
        # effective-omega chain (T2 lead, level full, mode E)
        if lead == 'T2':
            for omset in (('wf',) if kind == 'dconn' else ('raw',)):
                om = dict(OMSETS[omset])
                effs = {}
                for n in range(5, 9):
                    r = fit(kind, n, 'full', lims_ref(n, kind, 'E'), om)
                    if r is None:
                        break
                    rec(kind, 'E', 'full', omset + '_eff', n, r, dict(omega_eff_in={j: float(om[j]) for j in range(3, n - 2)}))
                    if n <= 7:
                        om[n - 2] = -r['p'][2]
                        effs[n - 2] = float(om[n - 2])
    # residual response to the delta-model extremes (dconn, mode E, omega wf, levels full/full3)
    for k in (6, 7, 8):
        Vk = V[k]
        Lmod = [L for L in Vk['L'] if lo <= L <= min(hi, 92 if k == 8 else 118)]
        if not Lmod:
            continue
        iL = Vk['L'].index(max(Lmod))
        Lin = [L for L in Vk['L'] if L in D['dC'][k] and not D['exact'][k][L]]
        cen = {L: D['dC'][k][L] for L in Lin}
        cands = {'vmin': int(np.argmin(Vk['pred'][:, iL])), 'vmax': int(np.argmax(Vk['pred'][:, iL]))}
        seqs = {name: {L: Vk['pred'][i][a] for a, L in enumerate(Vk['L']) if L in cen} for name, i in cands.items()}
        seqs['env+'] = {L: cen[L] + D['unc'][k][L] for L in Lin}
        seqs['env-'] = {L: cen[L] - D['unc'][k][L] for L in Lin}
        for name, seq in seqs.items():
            rws = variant_rows(ROWS['dconn'], LS_ALL['dconn'], k, seq)
            for level in ('full', 'full3'):
                for n in range(k, 9):
                    r = fit('dconn', n, level, lims_ref(n, 'dconn', 'E'), 'wf', rows=rws)
                    if r is None:
                        continue
                    out['varres'].append(dict(k=k, var=name, level=level, n=n, c=float(r['c']), maxres=r['maxres']))
    out['secs'] = time.time() - t0
    return out


def configs():
    cf = []
    for (tname, terms), lead, lo, hi in itertools.product(TAILSETS, LEADS, LOS, HIS):
        if lo >= hi:
            continue
        npts = len([L for L in LS_ALL['dconn'] if lo <= L <= hi])
        if npts < 1 + 2 + len(terms) + 3:
            continue
        cf.append((tname, terms, lead, lo, hi))
    return cf


if __name__ == '__main__':
    outdir = sys.argv[1]
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    only = os.environ.get('MI_ONLY')          # e.g. "3" -> first 3 configs (smoke test)
    os.makedirs(outdir, exist_ok=True)
    CF = configs()
    if only:
        CF = CF[:int(only)]
    print('configs', len(CF), 'data', D['path'], 'tag', D['tag'], flush=True)
    t0 = time.time()
    res = []
    with Pool(nproc) as pool:
        for i, r in enumerate(pool.imap_unordered(run_config, CF, chunksize=1)):
            res.append(r)
            if i % 50 == 0:
                print(i, r['cfg'], '%.1fs' % r['secs'], 'elapsed %.0fs' % (time.time() - t0), flush=True)
    json.dump(dict(meta=dict(corrected=D['path'], variants=VAR_PATH, tag=D['tag'], dps=DPS, central_rule=D['central_rule'], central_members=D.get('central_members'), LOS=LOS, HIS=HIS,
                             omsets={k: {j: mp.nstr(v, 20) for j, v in om.items()} for k, om in OMSETS.items()}),
                   results=res), open(os.path.join(outdir, 'grid.json'), 'w'))
    print('done', len(res), 'configs in %.0fs' % (time.time() - t0))
