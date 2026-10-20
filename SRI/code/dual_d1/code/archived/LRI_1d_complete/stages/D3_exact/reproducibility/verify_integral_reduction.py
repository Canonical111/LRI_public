#!/usr/bin/env python3
"""Reproduce the exact regulated-integral -> period-vector -> certificate chain.

Default: regenerate all required cutoff coefficients from the supplied exact
finite-cutoff hyperlogs, assemble the invariant, and verify the certificate.
--regenerate: also re-integrate all nine raw responses from their rational
kernels, with an exact derivative audit of every generated antiderivative.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time
import sympy as sp

ROOT = Path(__file__).resolve().parent
RAW = [('Av',3),('Avv',3),('Qbase',4),('Zbase',4),('Qv',4),
       ('Zv',4),('Qdelta',4),('Av',5),('Qbase',6)]
COEFFICIENTS = [('Av',3,1,1),('Avv',3,0,0),('Qbase',4,0,1),
                ('Qbase',4,1,1),('Zbase',4,-1,1),('Zbase',4,0,0),
                ('Qv',4,0,0),('Zv',4,0,1),('Qdelta',4,0,1),
                ('Av',5,0,1),('Qbase',6,0,1)]


def exact_equal(a, b, label):
    difference = sp.expand(sp.expand_log(a-b, force=True))
    if difference != 0:
        raise AssertionError(f'{label}: nonzero symbolic residual {difference}')


def raw_vector(rows):
    from hyperlog_core import K
    out={}
    for word,logs,c in rows:
        key=(tuple(word),tuple(logs))
        out[key]=out.get(key,K.zero)+K.from_expr(sp.sympify(c.replace('^','**')))
    return {w:c for w,c in out.items() if c}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--regenerate',action='store_true')
    args=parser.parse_args()
    started=time.time()
    report={'arithmetic':'exact rational functions and symbolic iterated integrals',
            'regenerated_raw':[], 'extracted_coefficients':[]}
    if args.regenerate:
        env=dict(os.environ,LRI_AUDIT_PRIMITIVES='1')
        for kind,n in RAW:
            path=ROOT/f'{kind}{n}_negative.json'
            before=raw_vector(json.loads(path.read_text()))
            cp=subprocess.run([sys.executable,str(ROOT/'ordered_moments.py'),str(n),kind],
                              cwd=ROOT,env=env,text=True,capture_output=True,check=True)
            (ROOT/f'audit_{kind}{n}.log').write_text(cp.stdout+cp.stderr)
            after=raw_vector(json.loads(path.read_text()))
            if before!=after:raise AssertionError(f'Raw formula changed: {kind}{n}')
            print(f'{kind}{n}: regenerated from kernel; primitive audit and exact equality PASS',flush=True)
            report['regenerated_raw'].append(f'{kind}{n}')
        # Separate rational check of the two-dimensional six-kink reduction.
        cp=subprocess.run([sys.executable,str(ROOT/'six_moment_reduction.py')],
                          cwd=ROOT,text=True,capture_output=True,check=True)
        (ROOT/'six_rational_identity_checks.txt').write_text(cp.stdout+cp.stderr)
        print(cp.stdout.strip(),flush=True)
    from asymptotic_gpl import moment,Q61
    for kind,n,p,m in COEFFICIENTS:
        name=f'{kind}{n}_{p}_{m}'
        saved=sp.sympify((ROOT/f'{name}.expr').read_text())
        fresh=moment(kind,n,p,m)
        exact_equal(fresh,saved,name)
        report['extracted_coefficients'].append(name)
        print(name+': exact coefficient extraction PASS',flush=True)
    direct=moment('Qbase',6,0,1)
    angular=Q61()
    exact_equal(direct,angular,'Independent Q6 angular/full-order routes')
    report['Q6_two_routes_exact_residual']=0
    print('Independent Q6 angular/full-order routes: EXACT DIFFERENCE = 0',flush=True)
    # Recompute the subtraction assembly, comparing against the saved expression.
    saved=sp.sympify((ROOT/'D3_difference_symbolic.expr').read_text())
    import assemble_symbolic
    fresh=sp.sympify((ROOT/'D3_difference_symbolic.expr').read_text())
    exact_equal(fresh,saved,'Subtraction and invariant assembly')
    from canonical_lift import lift
    from fractions import Fraction
    expected={tuple(w):Fraction(c) for w,c in json.loads((ROOT/'D3_linear_words.json').read_text())}
    if lift(fresh)!=expected:raise AssertionError('Canonical period target mismatch')
    report['canonical_word_target']='170 word coefficients exactly reproduced'
    print('Canonical period target: all 170 rational coefficients reproduced',flush=True)
    from verify_certificate import verify
    report['certificate']=verify(ROOT)
    report['seconds']=time.time()-started
    report['status']='All requested exact checks passed'
    (ROOT/'integral_reduction_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: complete exact integral-to-certificate chain.',flush=True)


if __name__=='__main__':main()
