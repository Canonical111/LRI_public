#!/usr/bin/env python3
"""Fast tests of LRI_C5_d2_simplify (about 30 s, Python with mpmath and sympy; any OS). Run: make -f public.mk test.

Every shipped script runs unchanged in a work copy under public/out/work/.
- factor_L2.py and factor_K2.py regenerate the exact square-lattice factorizations. The JSON must be byte-identical to the
  shipped one (checked with sympy 1.11.1); with another sympy the term sets and the coefficients are compared after
  sympify.
- parallel_eval.py 18 recomputes all 50 single sums and every identity at 18 digits from scratch. The result must equal
  confirm_dps18.json: singles, L2 and K2 to 1e-15 relative, and every residual below 1e-15. The recorded run took 7.6 s.
  It uses a process pool of size os.cpu_count().
- proof/synth/synth_checks.py and synth_checks_K2.py are the exact sympy checks and the 70-digit checks of the further
  d = 2 proofs, now written out in note Section 18. Their output must equal the shipped logs.
- public/closed_forms_d2.py at 30 digits must agree with the owned 70-digit values to 1e-25.
"""
import argparse, json, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'public'))
import mpmath as mp  # noqa: E402
from cf2common import row, run_pinned, report, versions, load, same_text  # noqa: E402
from closed_forms_d2 import evaluate  # noqa: E402


def same_factorization(new, old):
    import sympy as sp
    a, b = load(new), load(old)
    key = lambda t: (t.get('mw'), tuple(t['m']), t.get('nw'), tuple(t['n']))
    A = {key(t): t['coef'] for t in a['terms']}; B = {key(t): t['coef'] for t in b['terms']}
    return set(A) == set(B) and all(sp.simplify(sp.sympify(A[k]) - sp.sympify(B[k])) == 0 for k in A)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--results', type=Path, default=PKG / '../../results/closed_forms_2/closed_forms_2.json')
    ap.add_argument('--out', type=Path, default=PKG / 'public/out')
    a = ap.parse_args()

    for s, f, n in (('factor_L2.py', 'L2_factorized.json', 48), ('factor_K2.py', 'K2_factorized.json', 81)):
        rc, out, wd, secs, _ = run_pinned(PKG, s, work=s[:-3])
        ident = (wd / f).read_bytes() == (PKG / f).read_bytes()
        ok = rc == 0 and (ident or same_factorization(wd / f, PKG / f))
        row(f'{s} regenerates {f}', 'byte-identical' if ident else ('equal terms' if ok else 'differs'), 'identical', ok,
            f'{out.split(";")[0].strip()}; {secs:.1f} s')

    rc, out, wd, secs, _ = run_pinned(PKG, 'parallel_eval.py', ['18'], work='parallel_eval_dps18')
    new, ref = load(wd / 'confirm_dps18.json'), load(PKG / 'confirm_dps18.json')
    mp.mp.dps = 30
    worst = max(abs(mp.mpf(new['singles'][k]) / mp.mpf(v) - 1) if mp.mpf(v) else abs(mp.mpf(new['singles'][k]))
                for k, v in ref['singles'].items())
    row('parallel_eval.py 18: 50 single sums = confirm_dps18.json', mp.nstr(worst, 2), '<= 1e-15',
        rc == 0 and len(new['singles']) == 50 and worst <= mp.mpf('1e-15'), f'{secs:.1f} s (record {ref["seconds"]:.1f} s)')
    for k in ('L2', 'K2'):
        d = abs(mp.mpf(new['checks'][k]) / mp.mpf(ref['checks'][k]) - 1)
        row(f'parallel_eval.py 18: {k} = record', mp.nstr(d, 2), '<= 1e-15', d <= mp.mpf('1e-15'))
    big = max(abs(mp.mpf(x)) for k, x in new['checks'].items() if k not in ('L2', 'K2'))
    row('parallel_eval.py 18: every identity residual', mp.nstr(big, 2), '<= 1e-15', big <= mp.mpf('1e-15'))

    for s, log in (('synth_checks.py', 'synth_checks.log'), ('synth_checks_K2.py', 'synth_checks_K2.log')):
        rc, out, wd, secs, nsub = run_pinned(PKG, f'proof/synth/{s}', work=s[:-3])
        ok = rc == 0 and same_text(out, (PKG / 'proof/synth' / log).read_text())
        row(f'proof/synth/{s} output = {log}', 'same' if ok else 'differs', 'same', ok, f'{secs:.1f} s; {nsub} path(s) mapped')

    v = evaluate(30); res = load(a.results); mp.mp.dps = 40
    for k in ('L2', 'K2', 'C5_2'):
        d = abs(v[k] / mp.mpf(res['values_70_digits'][k]) - 1)
        row(f'closed form {k} at 30 digits = owned value', mp.nstr(d, 2), '<= 1e-25', d <= mp.mpf('1e-25'))
    return report(a.out, 'test', versions())


if __name__ == '__main__':
    sys.exit(main())
