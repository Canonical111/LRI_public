"""Interior check: the Fourier/Taylor representation built from the circle |eps| = rho must reproduce a
direct, independent non-perturbative solution at points INSIDE the circle.  This fails if any circle value
came from a wrong eigenvalue branch (the interpolant would not be the analytic function).

usage: python check_interior.py runs/<scheme>_L<L>_base.json [--procs N]
Prints |Delta_direct - sum_{n<K} c_n eps^n| and |Delta_direct - sum_{n<=8} C_n eps^n| for a few eps.
"""
import sys, os, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_v] = '1'
import mpmath as mp
from flint import ctx, acb, arb
from cauchy import load, series

PTS = [("0.01", "0"), ("-0.012", "0.005"), ("0.0", "-0.014"), ("0.001", "0.0")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    a = ap.parse_args()
    d = load(a.file)
    m = d['meta']
    c = series(d, lambda p: p['Delta'])
    from basis import load_or_build
    from hamil import NumOps
    from solve import solve_point
    ctx.prec = m['prec']
    sp, ops = load_or_build(m['L'], m['cap'], os.path.join(HERE, 'cache'))
    no = NumOps(sp, ops)
    out = []
    for re_, im_ in PTS:
        eps = acb(re_, im_)
        res = solve_point(no, m['scheme'], m['L'], eps)
        z = res['Delta']
        direct = mp.mpc(mp.mpf(z.real.mid().str(90, radius=False)), mp.mpf(z.imag.mid().str(90, radius=False)))
        e = mp.mpc(mp.mpf(re_), mp.mpf(im_))
        full = sum(c[n] * e ** n for n in range(len(c)))
        trunc = sum(c[n].real * e ** n for n in range(9))
        out.append({'eps': [re_, im_], 'Delta_direct': mp.nstr(direct, 40),
                    'abs_diff_full_fourier_series': mp.nstr(abs(direct - full), 3),
                    'abs_diff_C0_to_C8_polynomial': mp.nstr(abs(direct - trunc), 3),
                    'abs_C9_eps9_estimate': mp.nstr(abs(c[9]) * abs(e) ** 9, 3)})
        print(m['scheme'], m['L'], out[-1], flush=True)
    with open(a.file.replace('_base.json', '_interior.json'), 'w') as f:
        json.dump(out, f, indent=1)


if __name__ == '__main__':
    main()
