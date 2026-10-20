#!/usr/bin/env python3
"""Exact finite algebra and Horn-array checks for the dimension-three reduction.
No stored periods, floating point numbers, numerical fits, or integral data.
"""
from __future__ import annotations
import json
from pathlib import Path
import sympy as s

OUT=Path(__file__).resolve().parents[2]/'verification'/'general_d3'
OUT.mkdir(parents=True,exist_ok=True)
R=s.Rational; sqrt2=s.sqrt(2); I=s.I
checks=[]
def check(name,expression):
    residual=s.simplify(s.expand(expression))
    if residual!=0:
        raise AssertionError(f'{name}: {residual}')
    checks.append({'name':name,'residual':'0'})

def E(xs):
    es=[s.S.One]
    for m in range(1,len(xs)+1):
        es.append(s.expand(sum(xs[h-1]*es[m-h]/s.factorial(h-1) for h in range(1,m+1))/m))
    return es[-1]

# Strip pi^h from u_h; cot(3*pi/4)=-1.
u_base=[1,R(7,3),4,R(242,15),80,R(32272,63)]
# Last entry is 1024/63+136+240+120 = 32272/63.
expected={3:[8,-6*sqrt2,12],4:[32,-24*sqrt2,40,-40*sqrt2],
          7:[2624,-1904*sqrt2,2912,-2352*sqrt2,4032,-3696*sqrt2,7392]}
weights={}
for r in (3,4,7):
    vals=[]
    for k in range(r):
        u=[r*x for x in u_base[:r-1]]
        plus=u.copy();minus=u.copy();plus[0]+=2*I*k;minus[0]-=2*I*k
        phase=s.cos(3*s.pi*k/4)+I*s.sin(3*s.pi*k/4)
        val=s.simplify((phase*E(plus)+s.conjugate(phase)*E(minus))/2)
        check(f'residue weight r={r}, k={k}',val-expected[r][k]); vals.append(val)
    weights[r]=vals

# Fourier-to-Chebyshev polynomial checks and residue normalizations.
z,u=s.symbols('z u',real=True)
a,b=s.symbols('alpha beta',real=True)
a3b3,ab4,x30,x40,x4h=s.symbols('a3b3 ab4 x30 x40 x4h',real=True)
odd=16*z*(1-z*z)*(-a-3*b+4*b*z*z)
codd={1:-4*a-4*b,3:4*a+8*b,5:-4*b}
check('odd-sector Chebyshev expansion',odd-sum(v*s.chebyshevt(k,z) for k,v in codd.items()))
check('odd residue functional',sum(weights[7][k]*v for k,v in codd.items())-1792*sqrt2*(2*b-a))
# r3 has c0=-a3b3 and c2=0, with cos(3*pi/4)=-1/sqrt(2).
c31=-sqrt2*(x30+a3b3)
qfunctional=-sqrt2*s.sqrt(s.pi)/12*(-8*a3b3-6*sqrt2*c31)
qanswer=sqrt2*s.sqrt(s.pi)/3*(-a3b3-3*x30)
check('Q3 sample formula',qfunctional-qanswer)
G=s.symbols('Gquarter',positive=True)
H3=s.symbols('H3')
check('Q3 Gamma and Horn formula',qanswer.subs({a3b3:G**10/(16*sqrt2*s.pi**4),x30:-2*sqrt2*s.pi**R(3,2)*H3})-(4*s.pi**2*H3-G**10/(48*s.pi**R(7,2))))
# r4: c1=2ab4, c3=0; x(0)=c0-sqrt2*ab4, x(1/8)=c0-2ab4+c2.
c40=x40+sqrt2*ab4;c42=x4h-c40+2*ab4
p4functional=-s.pi/4*(32*c40-24*sqrt2*2*ab4+40*c42)
p4answer=2*s.pi*x40-10*s.pi*x4h+(14*sqrt2-20)*s.pi*ab4
check('P4 real-node formula',p4functional-p4answer)
# complex cos theta = 3/(2sqrt2), cos 2theta=5/4.
xaxis=c40+3*sqrt2*ab4/2+R(5,4)*c42
check('P4 complex-node formula',p4functional-8*s.pi*(3*sqrt2*ab4-xaxis))

p0,p1,p2=s.symbols('p0 p1 p2');pol=p0+p1*u+p2*u*u
ct=s.symbols('c0:4')
cheb=sum(ct[k]*s.chebyshevt(k,u) for k in range(4))
sol=s.solve(s.Poly(cheb-(1-u)*pol,u).coeffs(),ct,dict=True)[0]
check('r7 even residue functional',sum(weights[7][2*k]*sol[ct[k]] for k in range(4))+32*(9*p0+13*p1+22*p2))
check('quadratic real-node quadrature',-35*pol.subs(u,0)+(22+13/sqrt2)*pol.subs(u,1/sqrt2)+(22-13/sqrt2)*pol.subs(u,-1/sqrt2)-(9*p0+13*p1+22*p2))
check('quadratic complex-node quadrature',R(29,22)*pol.subs(u,0)+R(169,22)*pol.subs(u,R(22,13))-(9*p0+13*p1+22*p2))
p5functional=-sqrt2*s.pi**R(3,2)/8*(-32*(9*p0+13*p1+22*p2)+1792*sqrt2*(2*b-a))
p5answer=4*sqrt2*s.pi**R(3,2)*(9*p0+13*p1+22*p2)-448*s.pi**R(3,2)*(2*b-a)
check('P5 normalization',p5functional-p5answer)
p5complex=2*sqrt2*s.pi**R(3,2)/11*(29*p0-R(2197,9)*(1-R(22,13))*pol.subs(u,R(22,13)))-448*s.pi**R(3,2)*(2*b-a)
check('P5 complex-node formula',p5complex-p5functional)

# Explicit parameter arrays, including all factorial conventions.
e=(1,0);f=(0,1);c=(1,1);v=(1,2)
def arrays(r,t):
    upper=[(s.S.One,e),(s.S.One,f),(R(3,2),e)]+[(R(3,4)+t,c)]*r+[(R(1,4)+t,f)]*r
    lower=[(R(1,2),e)]+[(R(3,2)+t,c)]*r+[(1+t,f)]*r
    if r==7:
        x=t+R(5,8);y=t+R(1,8);vv=2*t+R(3,4)
        upper += [(1+x,c),(1+y,f),(1+vv,v)]
        lower += [(x,c),(y,f),(vv,v)]
    return upper,lower,((-1,1) if r==7 else (1,1))

def rowprod(rows,l,n):
    return s.prod(s.rf(p,w[0]*l+w[1]*n) for p,w in rows)

nodes={3:[R(0)],4:[R(0),R(1,8)],7:[R(0),R(1,16),-R(1,16),R(3,16),R(5,16)]}
records=[];nchecks=0
for r,ts in nodes.items():
    for t in ts:
        up,lo,args=arrays(r,t)
        assert all(p>0 for p,_ in up+lo)
        for l in range(6):
            for n in range(6):
                got=rowprod(up,l,n)/rowprod(lo,l,n)/s.factorial(l)/s.factorial(n)*args[0]**l*args[1]**n
                ratio=(s.rf(R(3,4)+t,l+n)/s.rf(R(3,2)+t,l+n)*s.rf(R(1,4)+t,n)/s.rf(1+t,n))**r
                target=(2*l+1)*ratio
                if r==7:
                    x=t+R(5,8);y=t+R(1,8);vv=2*t+R(3,4)
                    target*=(-1)**l*(x+l+n)*(y+n)*(vv+l+2*n)/(x*y*vv)
                if s.cancel(got-target)!=0:raise AssertionError((r,t,l,n))
                nchecks+=1
        records.append({'r':r,'t':str(t),'arguments':list(args),
                        'upper':[{'a':str(p),'vector':list(w)} for p,w in up],
                        'lower':[{'a':str(p),'vector':list(w)} for p,w in lo],
                        'factorial_convention':'divide each summand by ell! n!; the two upper unit rows cancel these factors',
                        'all_parameters_positive_rational':True})
(OUT/'horn_arrays.json').write_text(json.dumps({'convention':'H[upper;lower;arguments]; parameter with vector(v1,v2) means (a)_(v1 ell+v2 n)',
 'prefactors':'V_r=G_r H_r for r=3,4; V_7=4(t+5/8)(t+1/8)(2t+3/4)G_7 H_7; see appendix for fixed Gamma G_r',
 'arrays':records},indent=2)+'\n')
(OUT/'exact_algebra.json').write_text(json.dumps({'symbolic_checks':checks,'all_passed':True,
 'horn_coefficient_checks':nchecks,'horn_arrays':len(records),
 'residue_weights_without_pi':{str(r):[str(x) for x in row] for r,row in weights.items()},
 'scope':'Exact finite residue algebra, sample rules and literal rational Horn coefficients; not an independent graph calculation.'},indent=2)+'\n')
print(f'{len(checks)} symbolic checks; {nchecks} rational Horn coefficients; all passed.')
