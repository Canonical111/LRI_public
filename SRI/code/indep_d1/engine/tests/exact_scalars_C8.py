#!/usr/bin/env python3
"""The four tier-C scalars that the mathematics verifier flagged (phase 3, 2026-10-04):

    A3[eps^3 l^1] = 0,   A3[eps^3 l^0] = -5/9,   A5[eps^-2 l^1] = 0,   Z6[eps^-3 l^1] = 0.

All four are COMPUTED BY THE ENGINE inside tier C (specs/production_C8_tierC_sigma3.json: A3_base k=3,
A5_base k=-2 and Z6_base k=-3 with coeffs [0, 1]); collect writes the three l^1 entries as explicit exact zeros
(errors[...]['zero'] = True, 'zeros' list, {"value": "0", "sigma": "0", "exact": true} in framework_input.json),
never as silently absent scalars.  This script documents and checks why that is right, and checks the delivered
values once the tier has run:

  1. pole bound (exact, structural): the engine's Hepp-sector analysis (engine --sectors-info, N = 1, seconds)
     gives for every sector the lowest Laurent order lo_s = -(K_s + Dmu), K_s = number of Taylor-subtracted
     variables.  With the exact Laurent prefactors of the job (py/lri_moments.plan_moment) the lowest Laurent
     order of I~(s) at s0 = -k is olo = (lowest prefactor order) + min_s lo_s (coefficient_map).  eps^k l^j is the
     Laurent order -(j+1), so l^1 (order -2) vanishes identically when olo > -2.  This is the method-of-regions
     statement in sector language: at eps^-2 (A5) and eps^-3 (Z6) only the regions with 2 resp. 3 disjoint
     opposite-charge gaps at scale eps contribute, each giving int_eps dr r^-2 (1 + O(r)) = 1/eps + ..., a pure power;
     a log needs one power less (README section 11i).
  2. A3 closed form (independent of the engine): A3 = int_{r1,r2>=eps, r1+r2<=1} (1-r1-r2)(r1+r2)^2/(r1^2 r2^2)
     (spec sec. 2; framework/review_gate_phase2/check_A3_closed_form.py derived the closed form and checked it
     against 2D quadrature).  Here: the closed form is re-checked against mpmath quadrature at two eps, and its
     eps-expansion is taken with sympy: [eps^3 l^0] = -5/9 and [eps^3 l^1] = 0 exactly.
  3. data (optional, --run RUNDIR ...): the collected engine values (c8val, and the tier-C run once it exists):
     l^1 entries must be exact zeros, A3[eps^3 l^0] must agree with -5/9 within its quoted error (+ 1e-15).
Writes specs/exact_scalars_C8.json (with --write) and prints a report.  Exit 1 on any failure.
usage: python3 tests/exact_scalars_C8.py [--run runs/c8val] [--run runs/c8tierC_s3] [--write]
"""
import argparse, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'py'))
from lri_moments import plan_moment, job_cfg, coefficient_map, ENGINE   # noqa: E402

SCALARS = [  # (framework name, engine group, kind, n, k, j, exact value as a string)
    ('A3[eps^3 l^1]', 'A3_base', 'A', 3, 3, 1, '0'),
    ('A3[eps^3 l^0]', 'A3_base', 'A', 3, 3, 0, '-5/9'),
    ('A5[eps^-2 l^1]', 'A5_base', 'A', 5, -2, 1, '0'),
    ('Z6[eps^-3 l^1]', 'Z6_base', 'Z', 6, -3, 1, '0'),
]


def pole_bound(kind, n, k):
    """(olo, per-sector lo list, max K) for the base atom (kind, n) at eps^k with all logs (jmin 0)"""
    job = plan_moment(kind, n, 0, 0, 0, [k], None, 0)[0]
    cfg = job_cfg(job, N=1, shifts=1, korobov_a=1)
    fd, path = tempfile.mkstemp(suffix='.cfg', prefix='lri_exact_')
    os.write(fd, cfg.encode())
    os.close(fd)
    try:
        r = subprocess.run([ENGINE, path, '--sectors-info'], capture_output=True, text=True, check=True)
    finally:
        os.remove(path)
    info = json.loads(r.stdout)
    los = [s['lo'] for s in info['sectors']]
    lo = min(los)
    orders = {c: list(range(lo, job['etarget'] + 1)) for c, _ in job['chans']}
    cmap, olo = coefficient_map(job, orders)
    kmax = max(len(s['Nsub']) for s in info['sectors'])
    return job, olo, los, kmax, cmap


def a3_closed_expansion():
    """sympy: eps^3 coefficients of the A3 closed form (gate-review derivation), split into log powers"""
    import sympy as sp
    e, L = sp.symbols('epsilon L')            # L stands for log(eps)
    c = 1 - e
    lc = sp.log(1 - e)
    Li2 = sum(e ** m / m ** 2 for m in range(1, 9))          # Li2(eps) to eps^8 (enough for eps^3)
    Ia = (c ** 2 / e - 2 * c * lc + 2 * c * L - e) / 2
    G = -sp.zeta(2) + L * lc + 2 * Li2 + e * L + 1 - 2 * e - c * lc
    Ib = -L * lc + L ** 2 + L * (1 - 2 * e) + G - c * (lc - L) + (1 - 2 * e)
    A3 = sp.expand(sp.series(2 * Ia + 2 * Ib, e, 0, 5).removeO())
    co = sp.Poly(A3.coeff(e, 3), L)
    return {j: sp.nsimplify(co.coeff_monomial(L ** j)) for j in range(0, 3)}, A3


def a3_quad_check():
    """closed form vs 2D quadrature (mpmath) at two eps (the gate script did four)"""
    import mpmath as mp
    mp.mp.dps = 25

    def quad(eps):
        def inner(r1):
            cc = 1 - r1
            f = lambda r2: (cc - r2) * (r1 + r2) ** 2 / (r1 ** 2 * r2 ** 2)
            pts = [eps] + [x for x in (2 * eps, 10 * eps, mp.mpf(1) / 4) if x < cc] + [cc]
            return mp.quad(f, pts)
        pts = [eps] + [x for x in (2 * eps, 10 * eps, mp.mpf(1) / 4, mp.mpf(1) / 2) if x < 1 - eps] + [1 - eps]
        return mp.quad(inner, pts)

    def closed(eps):
        c, l, lc = 1 - eps, mp.log(eps), mp.log(1 - eps)
        Ia = (c ** 2 / eps - 2 * c * lc + 2 * c * l - eps) / 2
        G = -mp.zeta(2) + l * lc + 2 * mp.polylog(2, eps) + eps * l + 1 - 2 * eps - c * lc
        Ib = -l * lc + l ** 2 + l * (1 - 2 * eps) + G - c * (lc - l) + (1 - 2 * eps)
        return 2 * Ia + 2 * Ib
    return float(max(abs(quad(mp.mpf(x)) - closed(mp.mpf(x))) / abs(closed(mp.mpf(x))) for x in ("0.1", "0.01")))


def data_check(rundir):
    rows = []
    R = json.load(open(os.path.join(rundir, 'results.json')))
    for nm, g, kind, n, k, j, ex in SCALARS:
        for grp, co in R['results'].items():
            if grp.split('_N')[0] != g:
                continue
            key = f'{k},{j}'
            if key not in co:
                continue
            v, err = co[key]
            e = R['errors'][grp][key]
            exv = eval(ex.replace('/', '/1.0/') if '/' in ex else ex)
            ok = (e.get('zero') is True and v == 0.0) if ex == '0' else abs(v - exv) <= err + 1e-15
            rows.append({'run': os.path.basename(os.path.normpath(rundir)), 'scalar': nm, 'value': v, 'err': err,
                         'structural_zero': bool(e.get('zero')), 'exact': ex, 'ok': ok})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='append', default=[])
    ap.add_argument('--write', action='store_true', help='write specs/exact_scalars_C8.json')
    a = ap.parse_args()
    fail = 0
    out = {'note': 'tests/exact_scalars_C8.py: the four tier-C scalars flagged by the phase-3 mathematics verifier; '
                   'computed by the engine in tier C, values and proofs documented here', 'scalars': []}
    bounds = {}
    for nm, g, kind, n, k, j, ex in SCALARS:
        if (kind, n, k) not in bounds:
            bounds[(kind, n, k)] = pole_bound(kind, n, k)
        job, olo, los, kmax, cmap = bounds[(kind, n, k)]
        ent = {'name': nm, 'engine_group': g, 'eps_power': k, 'log_power': j, 'exact': ex,
               'tier_C_job': f'{g} k={k}, coeffs [0, 1] (specs/production_C8_tierC_sigma3.json)',
               'engine_pole_bound': {'sectors': len(los), 'min_sector_lo': min(los), 'max_subtracted_vars': kmax,
                                     'lowest_laurent_order_olo': olo, 'laurent_order_of_this_coeff': -(j + 1)}}
        if j >= 1:
            zero = olo is not None and -(j + 1) < olo
            ent['proof'] = ('structural zero: Laurent order %d lies below the lowest order olo = %d of the job '
                            '(engine Hepp-sector pole bound; every sector has at most %d subtracted variable(s))'
                            % (-(j + 1), olo, kmax))
            ent['status'] = 'PASS' if zero else 'FAIL'
            fail += not zero
            if g == 'A3_base':
                ent['proof'] += '; also exact from the A3 closed form (log terms 2 l^2 + 6 l - 6 eps l)'
            else:
                ent['proof'] += ('; region argument: the leading pole comes only from %d disjoint opposite-charge gaps '
                                 'at scale eps, each a pure power 1/eps' % (-k))
        out['scalars'].append(ent)
    co3, _ = a3_closed_expansion()
    qd = a3_quad_check()
    for ent in out['scalars']:
        if ent['engine_group'] == 'A3_base':
            v = co3[ent['log_power']]
            ok = str(v) == ent['exact'] and qd < 1e-15
            ent['closed_form'] = {'sympy_coefficient': str(v), 'closed_form_vs_quadrature_max_rel': float(qd)}
            if ent['log_power'] == 0:
                ent['proof'] = 'A3 closed form, sympy expansion: [eps^3 l^0] = %s; engine value cross-checked' % v
                ent['status'] = 'PASS' if ok else 'FAIL'
            fail += not ok
    out['A3_eps3_logs_closed_form'] = {str(j): str(v) for j, v in co3.items()}
    rows = []
    for rd in a.run:
        rows += data_check(rd)
    out['data'] = rows
    fail += sum(not r['ok'] for r in rows)
    print('four tier-C scalars (exact values; computed by the engine in tier C):')
    for e in out['scalars']:
        print(f"  {e['name']:16s} = {e['exact']:5s}  {e['status']}  olo {e['engine_pole_bound']['lowest_laurent_order_olo']}"
              f" (sectors {e['engine_pole_bound']['sectors']}, max K {e['engine_pole_bound']['max_subtracted_vars']}): "
              f"{e['proof']}")
    print(f"  A3 closed form vs quadrature: max rel diff {qd:.1e}; eps^3 coefficients by log power: "
          f"{out['A3_eps3_logs_closed_form']}")
    for r in rows:
        print(f"  data {r['run']:14s} {r['scalar']:16s} value {r['value']!r:24s} err {r['err']:.1e} "
              f"structural zero {r['structural_zero']}  {'ok' if r['ok'] else 'FAIL'}")
    if a.write:
        json.dump(out, open(os.path.join(ROOT, 'specs', 'exact_scalars_C8.json'), 'w'), indent=1)
        print('wrote specs/exact_scalars_C8.json')
    print('RESULT:', 'PASS' if not fail else f'FAIL ({fail})')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
