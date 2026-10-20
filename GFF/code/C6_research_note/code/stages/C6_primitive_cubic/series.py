"""Literal positive cubic double sum (not an accelerated interval evaluator)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import mpmath as mp

ROOT = Path(__file__).resolve().parent

def harmonic_data(nmax: int):
    if not isinstance(nmax, int) or nmax < 0:
        raise ValueError('nmax must be a nonnegative integer.')
    H = [[mp.mpf(0)] for _ in range(3)]
    for j in range(1, 2*nmax+1):
        inv = mp.mpf(1)/j
        for r in range(3):
            H[r].append(H[r][-1] + inv**(r+1))
    a = [mp.mpf(1)]
    for n in range(nmax):
        a.append(a[-1]*(n+mp.mpf('0.5'))/(n+1))
    h = [mp.log(2)+H[0][n]-H[0][2*n] for n in range(nmax+1)]
    delta = [mp.pi**2/3-4*H[1][2*n]+2*H[1][n] for n in range(nmax+1)]
    return a, h, delta, H

def cubic_polynomial(m: int, n: int, data) -> mp.mpf:
    a, h, delta, H = data
    k = m+n
    t = 8*h[m]+H[0][k]-H[0][m]
    u = 8*h[n]+H[0][k]-H[0][n]
    e = 4*delta[m]+H[1][k]-H[1][m]
    f = 4*delta[n]+H[1][k]-H[1][n]
    return (15*t*u*(t+u)+15*(t*f+u*e)
            +72*mp.pi*(t*u+H[1][k])
            +(30*H[1][k]+7*mp.pi**2)*(t+u)
            +28*mp.pi**3-60*(mp.zeta(3)-H[2][k]))

def pa_tail_bound(N: int) -> mp.mpf:
    if not isinstance(N, int) or N < 2:
        raise ValueError('The tail bound requires integer N>=2.')
    B = 7+mp.log(N-1)
    return 400*mp.pi**2/(3*(N-1))*(B*B+2*B+2)

def partial_sums(cutoffs: list[int], working_digits: int = 45) -> dict:
    if not cutoffs or any(not isinstance(n, int) or n < 1 for n in cutoffs):
        raise ValueError('Supply at least one positive integer cutoff.')
    if working_digits < 20:
        raise ValueError('Use at least 20 working digits.')
    cutoffs = sorted(set(cutoffs))
    with mp.workdps(working_digits):
        data = harmonic_data(max(cutoffs))
        a, _, _, _ = data
        ref = json.loads((ROOT/'inputs/primitive_reference.json').read_text())['Pa']
        mid = (mp.mpf(ref['lower_numerator'])+mp.mpf(ref['upper_numerator']))/mp.power(
            2, ref['denominator_power_of_two']+1)
        total = mp.mpf(0)
        result = []
        for k in range(max(cutoffs)):
            weight = a[k]**4  # m=0, n=k
            shell = mp.mpf(0)
            for m in range(k//2+1):
                n = k-m
                mult = 1 if m == n else 2
                shell += mult*weight*cubic_polynomial(m, n, data)
                if n:
                    weight *= ((m+mp.mpf('0.5'))**4*n**3 /
                               ((m+1)**3*(n-mp.mpf('0.5'))**4))
            total += shell
            N = k+1
            if N in cutoffs:
                pa = 2*mp.pi**2*total
                result.append({
                    'N': N, 'region': 'm+n<N',
                    'Pa_partial': mp.nstr(pa, working_digits),
                    'difference_from_inherited_midpoint': mp.nstr(mid-pa, working_digits),
                    'analytic_tail_bound_for_exact_partial': (
                        mp.nstr(pa_tail_bound(N), working_digits) if N >= 2 else None),
                })
        return {
            'working_digits': working_digits,
            'arithmetic': 'mpmath floating point; not outward-rounded intervals',
            'tail_scope': 'The analytic bound applies to exact partial sums; arithmetic error is not included.',
            'partial_sums': result,
        }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cutoffs', nargs='+', type=int, default=[32,128,512])
    parser.add_argument('--digits', type=int, default=45)
    args = parser.parse_args()
    out = partial_sums(args.cutoffs, args.digits)
    destination = ROOT/'results/partial_sums.json'
    destination.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=2))
