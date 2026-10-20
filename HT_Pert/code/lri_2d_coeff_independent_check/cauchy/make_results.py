"""Aggregate the point files of all variants into results/<scheme>_L<L>.json with error estimates.

Point files: <runs>/<scheme>_L<L>_<variant>.json, variant in
  base   rho=1/64, K=128, prec=256 bit, cap=19, radial steps 0.25,0.5,0.75,1
  rhoK   rho=1/40, K=96                         (aliasing / Cauchy-radius check)
  prec   prec=352 bit                           (rounding / solver-tolerance check)
  path   radial steps 0.1,0.2,...,1             (branch-tracking check)
  cap21, cap23                                  (particle cap raised: must not change C_0..C_8)
  cap17, cap18                                  (negative controls: cap below the exact one)
Error estimate of every coefficient = max over {rhoK, prec, path, cap21, cap23} of |Re difference to base|,
together with |Im| of the base and of the variants (all coefficients are real).
"""
import json, os, sys, glob
from fractions import Fraction
import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cauchy import load, all_series  # noqa: E402

ACC_VARIANTS = ['rhoK', 'prec', 'path', 'cap21', 'cap23']
CTRL_VARIANTS = ['cap17', 'cap18']
NMAX = 9


def rational_candidate(x, err, maxden=10 ** 20):
    """best rational with denominator <= maxden; accepted only if |x - p/q| < err and q^2 * err < 1e-6
    (so that a random real would essentially never pass)."""
    if err <= 0:
        return None
    q = Fraction(mp.nstr(x, int(-mp.log10(err)) + 10, strip_zeros=False)).limit_denominator(maxden)
    if abs(mp.mpf(q.numerator) / q.denominator - x) < err and mp.mpf(q.denominator) ** 2 * err < mp.mpf('1e-6'):
        return f"{q.numerator}/{q.denominator}"
    return None


def fmt(x, err):
    if err == 0:
        nd = 50
    else:
        rel = err / max(abs(x), mp.mpf('1e-300'))
        nd = int(max(6, min(60, -mp.log10(rel) + 1)))
    return mp.nstr(x, nd, strip_zeros=False)


def main(runs, outdir):
    mp.mp.prec = 600
    files = [f for f in glob.glob(os.path.join(runs, '*_L*_*.json')) if not f.endswith('_interior.json')]
    keys = sorted({(os.path.basename(f).split('_')[0], int(os.path.basename(f).split('_')[1][1:])) for f in files})
    os.makedirs(outdir, exist_ok=True)
    summary = {}
    for scheme, L in keys:
        S = {}
        meta = {}
        for f in files:
            b = os.path.basename(f)[:-5].split('_')
            if b[0] == scheme and int(b[1][1:]) == L:
                d = load(f)
                var = '_'.join(b[2:])
                meta[var] = d['meta']
                S[var] = all_series(d, None if var == 'base' else NMAX)
        if 'base' not in S:
            continue
        base = S['base']
        mb = meta['base']
        quantities = list(base.keys())
        res = {'scheme': scheme, 'L': L, 'rho': mb['rho'], 'K': mb['K'], 'digits': int(mb['prec'] * 0.30103),
               'precision_bits': mb['prec'], 'particle_cap': mb['cap'],
               'particle_cap_meaning': 'P <= cap in both parity sectors (even sector P <= cap-1)',
               'dims_at_cutoff_L': mb['dims'], 'radial_steps': mb['tsteps'],
               'variants_used_for_errors': {v: {k: meta[v][k] for k in ('rho', 'K', 'prec', 'cap', 'tsteps')}
                                            for v in ACC_VARIANTS if v in S},
               'error_definition': 'max over variants of |Re(C_variant - C_base)|, and |Im C| of all runs',
               'exactness': ('numerical (non-perturbative Cauchy integral); each number is given to the digits '
                             'supported by its error estimate; rational_candidate = continued-fraction '
                             'identification consistent with that error (not proven)')}

        def block(q):
            out = []
            for n in range(NMAX):
                x = base[q][n].real
                err = abs(base[q][n].imag)
                for v in ACC_VARIANTS:
                    if v in S and q in S[v]:
                        err = max(err, abs(S[v][q][n].real - x), abs(S[v][q][n].imag))
                ent = {'n': n, 'value': fmt(x, err), 'err': mp.nstr(err, 3)}
                rc = rational_candidate(x, err)
                if rc:
                    ent['rational_candidate'] = rc
                out.append(ent)
            return out

        res['C'] = block('Delta')
        res['check_C0_minus_1'] = mp.nstr(abs(base['Delta'][0] - 1), 3)
        res['check_C1_plus_1/6'] = mp.nstr(abs(base['Delta'][1] + mp.mpf(1) / 6), 3)
        res['r'] = block('r')
        res['g'] = block('g')
        res['E'] = {str(p): block(f'E{p}') for p in range(4)}
        if scheme in ('consistent', 'literal'):
            res['vacua'] = {q[2:]: block(q) for q in quantities if q.startswith('Ev')}
            res['vacua_meaning'] = ('E_v(l) of the consistent Hamiltonians' if scheme == 'consistent'
                                    else 'E_v^raw(l) of the raw Hamiltonians')
        # cap controls
        ctrl = {}
        for v in CTRL_VARIANTS:
            if v in S:
                ctrl[v] = {str(n): mp.nstr(S[v]['Delta'][n].real - base['Delta'][n].real, 5) for n in range(NMAX)}
        res['cap_controls_C_minus_base'] = ctrl
        devs = {}
        for v in ACC_VARIANTS:
            if v in S:
                devs[v] = {str(n): mp.nstr(abs(S[v]['Delta'][n] - base['Delta'][n]), 3) for n in range(NMAX)}
        res['variant_deviations_C'] = devs
        # tail of the discrete Fourier coefficients (decay => analytic, aliasing small)
        K = mb['K']
        rho = mp.mpf(Fraction(mb['rho']).numerator) / Fraction(mb['rho']).denominator
        c = base['Delta']
        tail = {str(n): mp.nstr(abs(c[n]) * rho ** n, 3) for n in (8, 16, 32, 48, 64, K // 2, K - 1) if n < K}
        res['fourier_tail_abs_c_n_rho_n'] = tail
        res['growth_ratio_c_n+1_over_c_n_at_n=K/4'] = mp.nstr(c[K // 4 + 1].real / c[K // 4].real, 6)
        res['newton_and_tracking'] = {
            'min_reference_weight': min(min(p['diag'][-1]['wts'].values()) for p in load(os.path.join(runs, f'{scheme}_L{L}_base.json'))['points']),
        }
        fi = os.path.join(runs, f'{scheme}_L{L}_interior.json')
        if os.path.exists(fi):
            res['interior_check'] = json.load(open(fi))
        with open(os.path.join(outdir, f'{scheme}_L{L}.json'), 'w') as f:
            json.dump(res, f, indent=1)
        summary[(scheme, L)] = res
        print(f"{scheme} L={L}:")
        for e in res['C']:
            print(f"   C{e['n']} = {e['value']}  +- {e['err']}  {e.get('rational_candidate', '')}")
        print("   cap controls (C_n(cap)-C_n(19)):", {v: {n: d for n, d in ctrl[v].items() if abs(mp.mpf(d)) > 1e-30} for v in ctrl})
    return summary


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'runs'),
         sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'results'))
