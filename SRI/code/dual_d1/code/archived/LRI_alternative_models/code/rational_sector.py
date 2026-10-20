#!/usr/bin/env python3
"""Post-hoc rational-sector pattern. NOT a formula for the full LRI coefficients."""
import argparse,json
from pathlib import Path
import sympy as s
from alternative_models import input_coeffs, Z, num


def rational_coefficients(N):
    # delta=2t^2. Sqrt branches normalized by -2t at the origin.
    m=(N+1)//2
    T=[s.Integer(0)]+[s.Rational(3**j-1,4) for j in range(1,m+1)]
    D=[s.Integer(0),s.Integer(-2)]+[s.Rational(3**j+2**j+7,8) for j in range(2,m+1)]
    u=[s.Integer(1)]
    C={1:s.Integer(-2)}
    for j in range(1,m):
        q=sum(T[i]*T[j+1-i] for i in range(1,j+1))/8-D[j+1]/2
        u.append(s.expand((q-sum(u[i]*u[j-i] for i in range(1,j)))/2))
        if 2*j+1<=N:C[2*j+1]=-2**(j+1)*u[j]
    for j in range(1,m+1):
        if 2*j<=N:C[2*j]=2**(j-1)*T[j]
    return C


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--order',type=int,default=12);p.add_argument('--output',type=Path,default=Path('rational_sector.json'));args=p.parse_args()
    C=rational_coefficients(args.order)
    for j in range(1,8):assert C[j]==input_coeffs()[j].subs({v:0 for v in Z.values()})
    t=s.Symbol('t');d=s.Symbol('d')
    T=d/(2*(1-d)*(1-3*d))
    D=-2*d+d*d/8*(9/(1-3*d)+4/(1-2*d)+7/(1-d))
    A=(T*T/4-D)/(2*d)
    # independent direct binomial expansion of the rational discriminant
    f=1+T.subs(d,2*t*t)/2-2*t*s.sqrt(s.cancel(A).subs(d,2*t*t))
    poly=s.series(f,t,0,min(args.order,10)+1).removeO().expand()
    for j in range(1,min(args.order,10)+1):assert poly.coeff(t,j)==C[j]
    out={'status':'post-hoc rational-sector conjecture, not a full coefficient rule', 'T0':str(T),'D0':str(D),'coefficients':{str(j):str(e) for j,e in C.items()},'all_seven_rational_inputs_match':True,'direct_rational_square_root_check':True}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
