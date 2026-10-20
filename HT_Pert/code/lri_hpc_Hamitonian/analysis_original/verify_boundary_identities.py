#!/usr/bin/env python3
"""Exact rational checks of second-order shells and the vacuum omega3 correction."""
from fractions import Fraction as F
from math import comb,pi,log,sqrt
from pathlib import Path
import json
D=Path(__file__).resolve().parent

def harmonic(n):return sum((F(1,k) for k in range(1,n+1)),F(0))
def v(n):return F(comb(2*n,n),4**n)
def c2(L):
    s=F(0)
    for n in range(0,L,2):
        s+=v(n)*(F(2,81)/(F(n)-F(1,2))+F(2,9)/(F(n)+F(1,2))+F(2,81)/(n+1))
        if n:s+=v(n)*F(2,9*n)
    return s

def g2(L):
    return c2(L)+(harmonic(L)-F(1,L)+2*sum((1/(F(k)+F(1,4)) for k in range(L//2)),F(0)))/9

def delta_w3(L):
    return -g2(L)/9+(2*harmonic(L-1)-2-F(1,L-1))/54

if __name__=='__main__':
    rows=[]
    for name in ('phi6_validation.json','phi6_production.json','phi6_extension.json','phi6_thin3.json','phi6_thin3_extension.json'):
        for r in json.loads((D/name).read_text()):
            L=r['cutoff'];a=r['raw'];b=r['vacuum_subtracted']
            rows.append(dict(cutoff=L,C2_residual=a['C'][2]-float(c2(L)),g2_residual=a['g'][2]-float(g2(L)),
                             vacuum_w3_shift_residual=b['D6'][3]-a['D6'][3]-float(delta_w3(L))))
    out=dict(checks=rows,exact_infinite_vacuum_shifts={'omega2':-1/54,'omega3':-(2*(pi+4*log(2))+3)/81},
             leading_gap_tail_amplitude=208/(9*sqrt(pi)),leading_phi6_local_only_amplitude=200/(9*sqrt(pi)),
             boundary_extra_amplitude=8/(9*sqrt(pi)))
    (D/'boundary_identity_checks.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:max(abs(r[k]) for r in rows) for k in ('C2_residual','g2_residual','vacuum_w3_shift_residual')},indent=2))
