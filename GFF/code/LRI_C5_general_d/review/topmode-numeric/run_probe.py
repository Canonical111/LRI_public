#!/usr/bin/env python3
"""Production driver (review key topmode-numeric).

For each configuration (d, b, r, kernel variant) evaluate S_r at
  * N = 2r+1 points t_j = x0 + j/N + i y0 on a generic horizontal line (DFT -> modes |m| <= r),
  * the off-grid point t* and its images -sigma-t* and t*+1 (reflection / periodicity),
with every S_r(t) = R(t) + R(1-sigma-t) + M(t) assembled from independently computed quadrant sums.
Writes raw values + analysis to probe_<tag>.json.
usage: run_probe.py TAG DPS K P H M [config-keys...]
"""
import sys, os, time, json
import multiprocessing as mproc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mpmath as mp
from xi_direct import Wheel, dft_modes, residue_W, explicit_W, bell_W

# ---------------------------------------------------------------- configurations
CONFIGS = {}


def _add(key, d, b, r, g=None, mult='so', ref=None):
    CONFIGS[key] = dict(d=d, b=b, r=r, g=g, mult=mult, ref=ref)


REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reference_values.json')
if not os.path.exists(REF):
    REF = '<PROJECT>/LRI_C5_general_d/references/reference_values.json'
for r in (3, 4, 5):
    _add('A1r%d' % r, '1.3', ('0.6', '0.1'), r)          # complex b, non-integer d
    _add('A2r%d' % r, '2.4', ('1.1', '0'), r)
    _add('A3r%d' % r, '3.2', ('1.5', '0'), r)
for r in (3, 4):
    _add('D1r%d' % r, '1.5', ('0.8', '0'), r, ref=('d=1.5', '0.8', 'W%d' % r))
    _add('D2r%d' % r, '2.5', ('1.3', '0'), r, ref=('d=2.5', '1.3', 'W%d' % r))
# stress points beyond the requested set
for r in (3, 4):
    _add('A4r%d' % r, '2.7', ('1.2', '-0.3'), r)          # complex b with d>2
for r in (3, 4):
    _add('A5r%d' % r, '0.8', ('0.3', '0.05'), r)          # d<1: negative multiplicities, complex b
    _add('D3r%d' % r, '0.8', ('0.37', '0'), r, ref=('d=0.8', '0.37', 'W%d' % r))
_add('A1r2', '1.3', ('0.6', '0.1'), 2)                   # r=2: Xi_2 must be constant; Re alpha = 0.7
_add('A1r6', '1.3', ('0.6', '0.1'), 6)
_add('A2r6', '2.4', ('1.1', '0'), 6)
# controls
for r in (3, 4, 5):
    _add('U1r%d' % r, '1.3', ('0.6', '0.1'), r, g=('0.45', '-0.05'))   # balanced g = 0.35-0.05i
_add('U2r4', '2.4', ('1.1', '0'), 4, g=('0.55', '0'))                    # balanced g = 0.65
_add('N1r4', '2.4', ('1.1', '0'), 4, mult='noplus')                     # multiplicity without (1+z)
for tag_, dl in (('a', '0.01'), ('b', '0.0001'), ('c', '0.000001')):   # imbalance scan: g = 0.65 + delta
    _add('U3%sr4' % tag_, '2.4', ('1.1', '0'), 4, g=(str(mp.mpf('0.65') + mp.mpf(dl)), '0'))

X0, Y0 = '0.0731', '0.0417'
TSTAR = ('0.2371', '0.0917')


def make_wheel(cfg):
    g = None if cfg['g'] is None else mp.mpc(*cfg['g'])
    return Wheel(cfg['d'], mp.mpc(*cfg['b']), cfg['r'], g=g, mult=cfg['mult'])


def points(cfg):
    """returns dict name -> t (mp numbers at current precision)."""
    w = make_wheel(cfg)
    r = cfg['r']
    N = 2 * r + 1
    pts = {}
    for j in range(N):
        pts['g%d' % j] = mp.mpc(mp.mpf(X0) + mp.mpf(j) / N, mp.mpf(Y0))
    ts = mp.mpc(*TSTAR)
    pts['star'] = ts
    pts['refl'] = -w.sigma - ts
    pts['per'] = ts + 1
    return pts


SET = {}


def task(args):
    key, part, re_, im_, st = args
    SET.update(st)
    mp.mp.dps = SET['dps']
    SET['h'] = mp.mpf(SET['hs'].split('/')[0]) / mp.mpf(SET['hs'].split('/')[1])
    cfg = CONFIGS[key]
    w = make_wheel(cfg)
    t = mp.mpc(re_, im_)
    t0 = time.time()
    kw = dict(K=SET['K'], P=SET['P'], h=SET['h'], M=SET['M'])
    if part == 'R':
        pr, Q = w._right(t)
        v = pr * Q.total(**kw)
    else:
        v = w._middle(t).total(**kw)
    return (key, part, re_, im_, mp.nstr(v.real, SET['dps'] + 5), mp.nstr(v.imag, SET['dps'] + 5), time.time() - t0)


def argstr(z, n):
    return (mp.nstr(z.real, n, strip_zeros=False), mp.nstr(z.imag, n, strip_zeros=False))


def main():
    tag, dps, K, P, H, M = sys.argv[1:7]
    keys = sys.argv[7:] or list(CONFIGS)
    SET.update(dps=int(dps), K=int(K), P=int(P), M=int(M), hs=H)
    num, den = H.split('/')
    mp.mp.dps = SET['dps'] + 20
    SET['h'] = mp.mpf(num) / mp.mpf(den)
    nstr_args = SET['dps'] + 15
    # ---- build task list (deduplicated by exact argument string)
    tasks = {}
    plan = {}
    for key in keys:
        cfg = CONFIGS[key]
        mp.mp.dps = SET['dps'] + 20
        w = make_wheel(cfg)
        pts = points(cfg)
        plan[key] = {}
        for name, t in pts.items():
            a1 = argstr(t, nstr_args)
            a2 = argstr(1 - w.sigma - t, nstr_args)
            plan[key][name] = dict(t=a1, R1=a1, R2=a2, M=a1)
            tasks[(key, 'R') + a1] = 1
            tasks[(key, 'R') + a2] = 1
            tasks[(key, 'M') + a1] = 1
    st = dict(dps=SET['dps'], K=SET['K'], P=SET['P'], M=SET['M'], hs=H)
    tl = [k + (st,) for k in sorted(tasks)]
    # heaviest first (larger r / slower convergence) is not critical; just interleave
    nproc = int(os.environ.get('SLURM_CPUS_PER_TASK', '8'))
    t0 = time.time()
    with mproc.Pool(nproc) as pool:
        res = pool.map(task, tl, chunksize=1)
    wall = time.time() - t0
    vals = {}
    cpu = 0.0
    for key, part, re_, im_, vr, vi, dt in res:
        vals[(key, part, re_, im_)] = (vr, vi)
        cpu += dt
    # ---- assemble + analyse
    mp.mp.dps = SET['dps']
    out = dict(settings=dict(dps=SET['dps'], K=SET['K'], P=SET['P'], h=H, M=SET['M']),
               wall=wall, cpu=cpu, configs={})
    for key in keys:
        cfg = CONFIGS[key]
        w = make_wheel(cfg)
        r = cfg['r']
        S = {}
        Xi = {}
        tpt = {}
        for name, p in plan[key].items():
            R1 = mp.mpc(*vals[(key, 'R') + p['R1']])
            R2 = mp.mpc(*vals[(key, 'R') + p['R2']])
            Mm = mp.mpc(*vals[(key, 'M') + p['M']])
            t = mp.mpc(*p['t'])
            tpt[name] = t
            S[name] = R1 + R2 + Mm
            Xi[name] = w.D(t) ** r * S[name]
        N = 2 * r + 1
        ts = [tpt['g%d' % j] for j in range(N)]
        xs = [Xi['g%d' % j] for j in range(N)]
        modes = dft_modes(ts, xs, r)
        gmax = max(abs(v) for v in modes.values())
        rel = {m: abs(modes[m]) / gmax for m in modes}
        refl_modes = max(abs(modes[m] - modes[-m] * mp.expjpi(2 * m * w.sigma)) for m in range(1, r + 1)) / gmax
        recon = mp.fsum(modes[m] * mp.expjpi(2 * m * tpt['star']) for m in modes)
        offgrid = abs(recon - Xi['star']) / abs(Xi['star'])
        per = abs(S['per'] - S['star']) / abs(S['star'])
        refl = abs(S['refl'] - S['star']) / abs(S['star'])
        refl_vs_per = abs(S['refl'] - S['per']) / abs(S['star'])
        ck = {0: modes[0]}
        for k in range(1, r + 1):
            ck[k] = 2 * modes[k] * mp.expjpi(-k * w.sigma)
        res_c = dict(r=r, d=cfg['d'], b=cfg['b'], g=cfg['g'], mult=cfg['mult'],
                     modes={m: [mp.nstr(modes[m].real, SET["dps"] + 5), mp.nstr(modes[m].imag, SET["dps"] + 5)] for m in modes},
                     rel={m: mp.nstr(rel[m], 4) for m in rel},
                     c={k: [mp.nstr(ck[k].real, SET["dps"] + 5), mp.nstr(ck[k].imag, SET["dps"] + 5)] for k in ck},
                     top_rel=mp.nstr(max(rel[r - 1], rel[1 - r]), 4),
                     boundary_rel=mp.nstr(max(rel[r], rel[-r]), 4),
                     refl_modes=mp.nstr(refl_modes, 4), offgrid=mp.nstr(offgrid, 4),
                     periodicity=mp.nstr(per, 4), reflection=mp.nstr(refl, 4),
                     refl_vs_per=mp.nstr(refl_vs_per, 4),
                     S={n: [mp.nstr(S[n].real, SET["dps"] + 5), mp.nstr(S[n].imag, SET["dps"] + 5)] for n in S})
        if cfg['g'] is None and cfg['mult'] == 'so':
            # residue functional (only meaningful for the balanced wheel); modes |m|<=r-2 by theorem,
            # but we use all computed modes (|m|<=r) so that nothing is assumed
            Nb = w.Nb()
            Wres = residue_W(modes, w.sigma, r, Nb)
            res_c['W_residue'] = [mp.nstr(Wres.real, SET["dps"] + 5), mp.nstr(Wres.imag, SET["dps"] + 5)]
            Wb = bell_W(modes, w.sigma, r, Nb)
            res_c['W_bell'] = [mp.nstr(Wb.real, SET["dps"] + 5), mp.nstr(Wb.imag, SET["dps"] + 5)]
            res_c['bell_vs_residue'] = mp.nstr(abs(Wb - Wres) / abs(Wres), 4)
            # functional restricted to the theorem's modes |m|<=r-2 (top & boundary dropped)
            Wtrunc = residue_W({m: modes[m] for m in modes if abs(m) <= r - 2}, w.sigma, r, Nb)
            res_c['W_trunc_vs_full'] = mp.nstr(abs(Wtrunc - Wres) / abs(Wres), 4)
            if r in (3, 4):
                Wex = explicit_W(modes, w.b, r, Nb)
                res_c['W_explicit'] = [mp.nstr(Wex.real, SET["dps"] + 5), mp.nstr(Wex.imag, SET["dps"] + 5)]
            if cfg['ref'] is not None and os.path.exists(REF):
                refj = json.load(open(REF))
                dkey, bval, wk = cfg['ref']
                for od in refj['values'][dkey]['offdiag']:
                    if od['b'] == bval:
                        rv = mp.mpf(od[wk])
                        res_c['ref'] = od[wk]
                        res_c['dev_residue'] = mp.nstr(abs(Wres - rv) / rv, 4)
                        if r in (3, 4):
                            res_c['dev_explicit'] = mp.nstr(abs(Wex - rv) / rv, 4)
        out['configs'][key] = res_c
        print(key, 'top', res_c['top_rel'], 'bnd', res_c['boundary_rel'], 'rel', res_c['rel'],
              'refl', res_c['refl_modes'], 'off', res_c['offgrid'], 'per', res_c['periodicity'],
              'S-refl', res_c['refl_vs_per'], res_c.get('dev_residue', ''), res_c.get('dev_explicit', ''),
              flush=True)
    json.dump(out, open('probe_%s.json' % tag, 'w'), indent=1)
    print('wall %.0fs cpu %.0fs' % (wall, cpu))


if __name__ == '__main__':
    main()
