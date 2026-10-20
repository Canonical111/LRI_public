#!/usr/bin/env python3
"""Exact rational certificates for the two one-dimensional angular reductions.

Integrate rational functions by their simple and double pole coefficients.
The real logarithmic endpoint differences are kept as independent symbols,
so this check neither invokes numerical integration nor guesses constants.
"""
import sympy as s

def require_zero(e,label):
    r=s.factor(s.cancel(e))
    if r!=0:raise AssertionError((label,r))
    print(label+': PASS',flush=True)

def pole_coeffs(F,x,p):
    reg=s.cancel((x-p)**2*F)
    c2=s.cancel(reg.subs(x,p))
    c1=s.cancel(s.diff(reg,x).subs(x,p))
    return c1,c2

x,w,e=s.symbols('x w e',positive=True)
E0,E1,Lm,Lp,L,J=s.symbols('E0 E1 Lm Lp L J')
P=lambda x:x*x*(1-x)**2
Pp=lambda x:2*x*(1-x)*(1-2*x)
F=1/(P(x)*P(x+w))
G=(Pp(x)-Pp(x+w))*F
H=1/P(x)+1/P(x+w)
pol={s.S(0):(Lm,E0),s.S(1):(-Lp,E1),-w:(Lp,E1),1-w:(-Lm,E0)}
integrated=[]
for name,fun in [('F',F),('G',G),('H',H)]:
    rational=0; val=0
    for pole,(ld,qd) in pol.items():
        c1,c2=pole_coeffs(fun,x,pole)
        rational+=c1/(x-pole)+c2/(x-pole)**2
        val+=c1*ld+c2*qd
    require_zero(fun-rational,'Five-insertion rational decomposition '+name)
    integrated.append(s.cancel(val))
If=w*w*(w-2*e)*integrated[0]+L*(integrated[1]+2*integrated[2]/w)+J*integrated[2]
I=E0*(2*(w-2*e)/(w-1)**2-4*L/(w-1)+2*J)+E1*(2*(w-2*e)/(w+1)**2-4*L/(w+1)+2*J)
I+=Lm*(4*(w*w-3*w+1)*(w-2*e)/(w*(w-1)**3)+(-8/w+8/(w*w*(w-1)**2))*L+4*J)
I+=Lp*(4*(w*w+3*w+1)*(w-2*e)/(w*(w+1)**3)+(-8/w-8/(w*w*(w+1)**2))*L+4*J)
require_zero(If-I,'Full one-dimensional five-insertion kernel')

r,E,LL=s.symbols('r E LL',positive=True)
Qouter=(r+x)*(1-r)**2*(1-x)**2/(r*r*x*x*(1-r-x)**2)
Qmiddle=(1-r)*(1-x)**2*(r+x)**2/(x*x*r*r*(1-r-x)**2)
vals=[]
for name,fun,poly in [('outer',Qouter,0),('middle',Qmiddle,(1-r)/r**2)]:
    approx=poly; val=poly*(1-r-2*e)
    for pole,ls in [(s.S(0),LL),(1-r,-LL)]:
        c1,c2=pole_coeffs(fun,x,pole)
        approx+=c1/(x-pole)+c2/(x-pole)**2
        val+=c1*ls+c2*E
    require_zero(fun-approx,'Four-insertion rational decomposition '+name)
    vals.append(val)
M=(1+1/r)*E+(r+1)*(r*r+1)/(r*r*(1-r))*LL
N=2*E/(1-r)+4*(r*r-r+1)/(r*(1-r)**2)*LL+(1-r)*(1-r-2*e)/r**2
require_zero(vals[0]-M,'Exact outer-gap integral M')
require_zero(vals[1]-N,'Exact middle-gap integral N')
print('All angular reductions certified by rational identities.')

# Independent finite-cutoff quadrature, before any asymptotic subtraction.
import mpmath as mp
mp.mp.dps=50
Lexpr=s.log((w-e)/e)
Jexpr=1/e-1/(w-e)
exact_kernel=I.subs({E0:1/e-1/(1-e-w),E1:1/(w+e)-1/(1-e),
    Lm:s.log((1-e-w)/e),Lp:s.log((1-e)/(w+e)),L:Lexpr,J:Jexpr})
postcentral=w*w*(w-2*e)*F+Lexpr*(G+2*H/w)+Jexpr*H
num_kernel=s.lambdify((w,e),exact_kernel,'mpmath')
num_post=s.lambdify((x,w,e),postcentral,'mpmath')
for cutoff,separation in [('0.03','0.37'),('0.07','0.58')]:
    ee,ww=mp.mpf(cutoff),mp.mpf(separation)
    end=1-ee-ww
    integrated=mp.quad(lambda xx:num_post(xx,ww,ee),[ee,(ee+end)/2,end])
    reference=num_kernel(ww,ee)
    residual=abs(integrated-reference)/max(1,abs(reference))
    assert residual<mp.mpf('1e-40'),residual
    print(f'Five-insertion finite-cutoff quadrature e={cutoff}, w={separation}: PASS')

Mexpr=M.subs({E:1/e-1/(1-r-e),LL:s.log((1-r-e)/e)})
num_M=s.lambdify((r,e),Mexpr,'mpmath')
for cutoff in ['0.02','0.06','0.12']:
    ee=mp.mpf(cutoff); zz=ee/(1-ee); ll=mp.log((1-2*ee)/ee)
    hq=(2*ll+1)/ee-4*ll/(1-ee)-2*(1-ee)*ll-2-3*ee
    hq+=4*mp.log(zz)**2-4*mp.zeta(2)+8*mp.polylog(2,zz)
    direct=mp.quad(lambda rr:num_M(rr,ee),[ee,(1-ee)/2,1-2*ee])
    residual=abs(hq-direct)/max(1,abs(hq))
    assert residual<mp.mpf('1e-40'),residual
    print(f'Four-insertion exact H_Q finite-cutoff check e={cutoff}: PASS')
