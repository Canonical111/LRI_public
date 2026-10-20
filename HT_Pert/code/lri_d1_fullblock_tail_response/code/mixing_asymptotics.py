"""Analytic overlap subtractions, constructed from exact phase Wick weights.
The auxiliary cutoff mu is not the outer UV cutoff Lambda.
"""
from pathlib import Path
from fractions import Fraction as F
import json,csv,math
import sympy as s
import numpy as np
from phase_response_shell import weights
ROOT=Path(__file__).resolve().parents[1]

def derive():
    terms,_=weights();rows=[];A=s.S(0);Q=s.S(0);B=s.S(0)
    for (a,b,c,d,e),v in terms.items():
        if c==2:a,c=c,a;d,e=e,d
        av=qv=bv=s.S(0)
        if (a,b,c)==(1,3,1):av=4*(s.pi-2)/s.pi**s.Rational(3,2)
        elif (a,b,c)==(2,2,0):
            qv=s.Rational(1,8);bv=-(s.log(2)+s.polygamma(0,s.Rational(e.numerator,2*e.denominator)))/4
        elif (a,b,c)==(2,1,0):bv=(s.pi/2+s.log(1+s.sqrt(2)))/2
        elif (a,b,c)==(2,0,0):bv=s.S(1)/(2*s.Rational(e.numerator,e.denominator))
        elif (a,b,c)==(1,2,1):bv=s.pi/4
        elif (a,b,c) in [(1,3,0),(0,3,1),(0,4,0)]:bv=s.Rational(1,2)
        w=s.Rational(v.numerator,v.denominator);A+=w*av;Q+=w*qv;B+=w*bv
        rows.append(dict(edges=f'{a},{b},{c}',left_shift=str(d),right_shift=str(e),weight=str(v),sqrt_mu=str(s.simplify(w*av)),log_squared=str(s.simplify(w*qv)),log=str(s.simplify(w*bv))))
    A,Q,B=map(s.simplify,(A,Q,B))
    assert s.simplify(A-32*(s.pi-2)/(729*s.pi**s.Rational(3,2)))==0
    assert Q==s.Rational(1,81)
    want=(41+42*s.pi+12*s.EulerGamma+24*s.log(2)+48*s.log(1+s.sqrt(2)))/486
    assert s.simplify(B-want)==0
    # Dirichlet scaling integral producing the power divergence.
    z=s.symbols('z',positive=True)
    integral=s.integrate(8*z*z*s.sin(z),(z,0,s.pi/2))
    assert s.simplify(integral-8*(s.pi-2))==0
    return dict(sqrt_mu=str(A),log_squared=str(Q),log=str(B),numeric=[float(s.N(x,30)) for x in (A,Q,B)],group_rows=rows,exact_integral=str(integral))

def main():
    out=derive()
    finite=json.loads((ROOT/'results/phase_finite_part_N512_O6.json').read_text())
    C=float(finite['finite_part']);out.update(finite_part_estimate=finite['finite_part'],finite_part_method='independent convergent series and finite integrals, no cutoff fitting',scope='Complete fourth-order response of the phase operator, not the full thermal C4 or C6--C8 cutoff polynomial.')
    (ROOT/'results/phase_overlap_asymptotics.json').write_text(json.dumps(out,indent=2)+'\n')
    with (ROOT/'results/phase_overlap_topologies.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out['group_rows'][0]));w.writeheader();w.writerows(out['group_rows'])
    a,q,b=out['numeric'];rows=[]
    for r in json.loads((ROOT/'results/phase_response_shells.json').read_text()):
        mu=r['cutoff'];value=r['response4'];sub=a*math.sqrt(mu)+q*math.log(mu)**2+b*math.log(mu)
        rows.append(dict(mu=mu,complete_response4=value,sqrt_subtraction=a*math.sqrt(mu),log_squared_subtraction=q*math.log(mu)**2,log_subtraction=b*math.log(mu),renormalized_finite_part=value-sub,finite_part_comparison=C,remainder=value-sub-C))
    with (ROOT/'results/phase_overlap_convergence.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print({k:v for k,v in out.items() if k!='group_rows'})
if __name__=='__main__':main()
