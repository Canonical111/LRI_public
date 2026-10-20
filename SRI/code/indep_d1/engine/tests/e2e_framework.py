#!/usr/bin/env python3
"""End-to-end (v2, 2026-10-03): engine coefficients (campaign.py collect -> results.json) -> sibling framework
module (../../framework/lri_framework.py) -> beta inputs, D2..D4, T2, T3, C3..C7, with three error estimates:

  sigma_rep   the framework is run once per shift replicate r on the coefficient vector x_r of that replicate
              (all jobs' replicates are i.i.d. and independent across jobs), sigma = std_r(X_r)/sqrt(R);
              the (diagonal) error floor is added in quadrature through the exact gradient.
  sigma_cov   linear propagation with the full covariance: block diagonal over independent jobs (moment, k),
              each block = replicate covariance of its coefficients / R (any R per block), plus the floor.
  sigma_indep phase-1 style (every raw coefficient independent) -- shown for comparison only.

The point value is the framework at the replicate means.  Fails (exit 2) when a raw coefficient required by
the framework (fw.required_inputs(), live) is absent from results.json, or when an output is MISSING.
Structural zeros are supplied explicitly by collect (value 0, no error).

usage: e2e_framework.py RESULTS.json [--out OUT.json] [--grad-out FILE] [--no-rep] [--dps 30]
"""
import argparse, json, math, os, random, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.abspath(os.path.join(HERE, '..', '..', 'framework'))
sys.path.insert(0, FW)
import mpmath as mp
import lri_framework as L

RAW_RE = re.compile(r'^([AZQ])(\d+)(?:_([vdE]+))?\[eps\^(-?\d+) l\^(\d+)\]$')


def flat_name(group, key):
    k, j = key.split(',')
    return f"{re.sub(r'_N[0-9]+$', '', group).replace('_base', '')}[eps^{k} l^{j}]"


def deriv_factor(name):
    """d(raw derivative)/d(framework internal input): the framework divides derivative-convention inputs by
    i! j! (i = #v, j = #d) before tracking them"""
    m = RAW_RE.match(name)
    ds = m.group(3) or ''
    return math.factorial(ds.count('v')) * math.factorial(ds.count('d'))


def outputs(fw, res):
    out = {}
    for nm in fw.beta_names:
        out[nm] = res.beta[nm]
    for nm, v in res.inv.items():
        out[nm] = v
    for n, v in res.C.items():
        out[f'C{n}'] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('results')
    ap.add_argument('--out')
    ap.add_argument('--grad-out')
    ap.add_argument('--no-rep', action='store_true')
    ap.add_argument('--dps', type=int, default=30)
    a = ap.parse_args()
    R = json.load(open(a.results))
    if R.get('engine_pipeline') != 'v2':
        sys.exit('results.json is not a v2 (replicate) collect output; run py/campaign.py collect with the v2 engine')
    fw = L.Framework('D4', dps=a.dps)
    need = sorted({x for v in fw.required_inputs().values() for x in v})
    flat, err, floor, reps, block = {}, {}, {}, {}, {}
    for grp, coeffs in R['results'].items():
        for key, (v, e) in coeffs.items():
            nm = flat_name(grp, key)
            if nm not in need:
                continue
            if nm in flat:
                sys.exit(f'duplicate raw coefficient {nm} (groups {grp})')
            ex = R['errors'][grp][key]
            flat[nm], err[nm], floor[nm] = v, e, ex['floor']
            reps[nm] = R['replicates'].get(grp, {}).get(key) or [v]   # structural zeros: exact, no replicates
            block[nm] = ex['block']
    missing = [n for n in need if n not in flat]
    print(f'{len(flat)} of {len(need)} required raw coefficients supplied '
          f'({sum(1 for z in R.get("zeros", []) if z in flat)} structural zeros)')
    if missing:
        print('MISSING required raw coefficients:', missing)
        sys.exit(2)
    if not R.get('complete', True):
        print('WARNING: results.json reports problems:', R.get('problems'))
    t0 = time.time()
    res0 = fw.from_raw({n: mp.mpf(flat[n]) for n in need})
    out0 = outputs(fw, res0)
    bad = [k for k, v in out0.items() if v.is_missing]
    if bad:
        print('framework outputs MISSING:', bad)
        sys.exit(2)
    for w in fw.warnings:
        print('framework WARNING:', w)
    # gradients with respect to the RAW (derivative-convention) coefficients: Result.gradient (input
    # convention) when the framework provides it, else the internal gradient divided by i! j!; the
    # finite-difference check below verifies whichever is used
    if hasattr(res0, 'gradient'):
        G = {}
        for o, v in out0.items():
            gr = res0.gradient(v) or {}
            G[o] = {n: float(gr.get(n, 0)) for n in need}
    else:
        G = {o: {n: float(v.g.get(n, 0)) / deriv_factor(n) for n in need} for o, v in out0.items()}
    # directional finite-difference check of the gradient convention (one random +-sigma direction)
    rnd = random.Random(12345)
    dirv = {n: (err[n] if err[n] > 0 else 1e-12 * (1 + abs(flat[n]))) * rnd.choice((-1, 1)) for n in need}
    h = 1e-3
    rp = outputs(fw, fw.from_raw({n: mp.mpf(flat[n]) + h * mp.mpf(dirv[n]) for n in need}))
    rm = outputs(fw, fw.from_raw({n: mp.mpf(flat[n]) - h * mp.mpf(dirv[n]) for n in need}))
    fdcheck = {}
    for o in ('C6', 'C7', 'D4'):
        fd = float((rp[o].v - rm[o].v) / (2 * h))
        lin = sum(G[o][n] * dirv[n] for n in need)
        fdcheck[o] = (fd, lin)
    # sigma_cov: block covariance from replicates
    blocks = {}
    for n in need:
        if len(reps[n]) > 1:          # fixed scalars (structural zeros) carry no replicate scatter
            blocks.setdefault(block[n], []).append(n)
    sig_cov, sig_ind, sig_floor = {}, {}, {}
    for o in out0:
        g = G[o]
        var = 0.0
        for b, names in blocks.items():
            Rb = len(reps[names[0]])
            if Rb < 2:
                continue
            mean = {n: sum(reps[n]) / Rb for n in names}
            D = [sum(g[n] * (reps[n][r] - mean[n]) for n in names) for r in range(Rb)]
            var += sum(x * x for x in D) / (Rb * (Rb - 1))
        fl = sum((g[n] * floor[n]) ** 2 for n in need)
        sig_cov[o] = math.sqrt(var + fl)
        sig_floor[o] = math.sqrt(fl)
        sig_ind[o] = math.sqrt(sum((g[n] * err[n]) ** 2 for n in need))
    # sigma_rep: framework per replicate
    Rs = sorted({len(reps[n]) for n in need if len(reps[n]) > 1})
    sig_rep, Xr = {}, {}
    if not a.no_rep and len(Rs) == 1:
        Rr = Rs[0]
        for r in range(Rr):
            x = {n: mp.mpf(reps[n][r] if len(reps[n]) == Rr else flat[n]) for n in need}
            o_r = outputs(fw, fw.from_raw(x))
            for o, v in o_r.items():
                Xr.setdefault(o, []).append(float(v.v))
        for o, xs in Xr.items():
            m = sum(xs) / Rr
            sig_rep[o] = math.sqrt(sum((x - m) ** 2 for x in xs) / (Rr - 1) / Rr + sig_floor[o] ** 2)
    elif not a.no_rep:
        print(f'per-replicate framework runs skipped: blocks have different replicate counts {Rs}')
    print(f'framework runs: {time.time() - t0:.1f} s')
    beta_cf, tgt = L.closed_forms(a.dps)
    beta_cf = dict(beta_cf)
    # independent 1D boundary-integral values of the framework agent (b3 sector; not archive data)
    vlo = os.path.join(FW, 'out', 'validate_low_order.json')
    if os.path.exists(vlo):
        b3 = json.load(open(vlo)).get('three_kink_b3_sector', {})
        for nm in ('V', 'alpha', 'beta', 'gamma'):
            if nm in b3 and nm not in beta_cf:
                beta_cf[nm] = mp.mpf(b3[nm]['value'])
    print('%-7s %30s %11s %11s %11s %11s   %s' % ('output', 'value', 'sigma_rep', 'sigma_cov', 'sig_indep',
                                                 'sig_floor', 'vs closed form (pull, sigma_cov)'))
    table = {}
    for o, v in out0.items():
        val = v.v
        ref = tgt.get(o, beta_cf.get(o))
        cmp_ = ''
        if ref is not None:
            d = float(val - ref)
            s = sig_cov[o]
            cmp_ = f'diff {d: .3e}' + (f'  pull {d / s: .2f}' if s > 0 else '')
        print('%-7s %30s %11.3e %11.3e %11.3e %11.3e   %s' % (
            o, mp.nstr(val, 20), sig_rep.get(o, float('nan')), sig_cov[o], sig_ind[o], sig_floor[o], cmp_))
        table[o] = {'value': mp.nstr(val, 25), 'sigma_rep': sig_rep.get(o), 'sigma_cov': sig_cov[o],
                    'sigma_indep': sig_ind[o], 'sigma_floor': sig_floor[o],
                    'closed_form': None if ref is None else mp.nstr(ref, 25),
                    'replicates': Xr.get(o)}
    print('gradient convention check (central difference along a random +-sigma direction, vs g.dx):')
    for o, (fd, lin) in fdcheck.items():
        print(f'   {o}: fd {fd: .6e}  linear {lin: .6e}  rel.diff {abs(fd - lin) / max(abs(lin), 1e-300):.1e}')
    res = {'results_file': os.path.abspath(a.results), 'n_inputs': len(need), 'table': table,
           'fd_check': fdcheck, 'R': Rs, 'framework_warnings': fw.warnings}
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)
    if a.grad_out:
        json.dump({'note': 'signed gradients d(output)/d(raw coefficient, derivative convention) of the framework, '
                           f'evaluated at the engine point {os.path.abspath(a.results)} (not the archive)',
                   'gradients': {o: G[o] for o in ('C6', 'C7', 'D4')}}, open(a.grad_out, 'w'), indent=1)
    fdbad = [o for o, (fd, lin) in fdcheck.items() if abs(fd - lin) > 1e-6 * max(abs(lin), 1e-300) + 1e-14]
    if fdbad:
        print('GRADIENT CONVENTION CHECK FAILED for', fdbad)
        sys.exit(3)


if __name__ == '__main__':
    main()
