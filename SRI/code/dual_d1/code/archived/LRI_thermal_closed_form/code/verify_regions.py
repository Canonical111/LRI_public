#!/usr/bin/env python3
"""Regenerate all bulk/lower/upper constant integrands from the exact kernels.

This symbolic check may take a few minutes. It uses no stored expressions.
Factoring each Laurent term before coefficient extraction is important:
1/(e*(t+1)) must be recognized as e**(-1)/(t+1).
"""
import sympy as s

def lc(expr,var,n):
    out=0
    for term in s.Add.make_args(s.expand(expr)):
        term=s.factor_terms(term)
        power=term.as_powers_dict().get(var,0)
        if power==n:
            out+=term/var**n
    return out

def check(expr,target,label):
    residual=s.factor(s.together(s.expand(expr-target)))
    if residual!=0:
        raise AssertionError((label,residual))
    print(label+': PASS',flush=True)

w,e,t,l=s.symbols('w e t l',positive=True)
L=s.symbols('L')
p=s.log(w);q=s.log(1-w)
B5=p*p*(16/(w+1)+8/(w+1)**2-8/w+8/w**2)
B5+=p*q*(-16/(w-1)+8/(w-1)**2+8/w+8/w**2)
B5+=p*(4/(w+1)-4/(w+1)**2+4/(w+1)**3-4/(w-1)**2)
B5+=q*(4/(w-1)-4/(w-1)**2-4/(w-1)**3-4/w)
B5+=-6-2/(w+1)+4/(w+1)**2+6/(w-1)-4/(w-1)**2+2/(w-1)**3-4/w-6/w**2
L5=-8/t*s.log(t-1)*s.log(t+1)+(4-4/(t+1)-8/t)*s.log(t-1)+(-4+4/(t-1))*s.log(t+1)-4+4/(t-1)
U5=(4-12/t-8/t**2)*s.log(t-1)-6+10/(t-1)-8/t
J=1/e-1/(w-e)
coeff=[2*(w-2*e)/(w-1)**2-4*L/(w-1)+2*J,
       2*(w-2*e)/(w+1)**2-4*L/(w+1)+2*J,
       4*(w*w-3*w+1)*(w-2*e)/(w*(w-1)**3)+(-8/w+8/(w*w*(w-1)**2))*L+4*J,
       4*(w*w+3*w+1)*(w-2*e)/(w*(w+1)**3)+(-8/w-8/(w*w*(w+1)**2))*L+4*J]
regions=[
 ('bulk',w,1,s.log(w)-l-sum(e**k/(k*w**k) for k in range(1,5)),[
 1/e-1/(1-w-e),1/(w+e)-1/(1-e),
 s.log(1-w)-l-sum(e**k/(k*(1-w)**k) for k in range(1,5)),
 -s.log(w)-sum(e**k/k for k in range(1,5))+sum((-1)**k*e**k/(k*w**k) for k in range(1,5))],B5),
 ('lower',e*t,e,s.log(t-1),[
 1/e-1/(1-e*(1+t)),1/(e*(t+1))-1/(1-e),
 -l-sum(e**k*(1+t)**k/k for k in range(1,5)),
 -l-s.log(t+1)-sum(e**k/k for k in range(1,5))],L5),
 ('upper',1-e*t,e,-l-sum(e**k*(t+1)**k/k for k in range(1,5)),[
 1/e-1/(e*(t-1)),1/(1-e*(t-1))-1/(1-e),s.log(t-1),
 sum(e**k*((t-1)**k-1)/k for k in range(1,5))],U5)]
for name,sub,jac,Le,functions,target in regions:
    total=0
    for c,fun in zip(coeff,functions):
        cs=s.series((jac*c.subs(w,sub).subs(L,Le)).expand(),e,0,3).removeO()
        fs=s.series(fun,e,0,4).removeO()
        total+=lc(cs*fs,e,0)
    check(s.expand(total).subs(l,0),target,'Five-insertion '+name+' region')

B4=p*q*(4+16/(w-1)-8/(w-1)**2-16/w-4/w**2)
B4+=p*(-2-8/(w-1)+4/(w-1)**2+8/w-2/w**2)
B4+=q*q*(-4-16/(w-1)+8/w+4/w**2)+q*(8/(w-1)-4/w)
L4=(-8+12/t+8/t**2)*s.log(t)-4
U4=16/t*s.log(t)*s.log(t-1)+(8-8/(t-1))*s.log(t)+8/t*s.log(t-1)+4-4/(t-1)
E=1/e-1/(1-w-e)
M=(1+1/w)*E+(w+1)*(w*w+1)/(w*w*(1-w))*L
N=2/(1-w)*E+4*(w*w-w+1)/(w*(1-w)**2)*L+(1-w)*(1-w-2*e)/w**2
regions=[
 ('bulk',w,1,s.log(1-w)-l-sum(e**k/(k*(1-w)**k) for k in range(1,4)),s.log(w),s.log(1-w),B4),
 ('lower',e*t,e,-l-sum(e**k*(1+t)**k/k for k in range(1,4)),l+s.log(t),-sum(e**k*t**k/k for k in range(1,4)),L4),
 ('upper',1-e*t,e,s.log(t-1),-sum(e**k*t**k/k for k in range(1,4)),l+s.log(t),U4)]
for name,sub,jac,Lexp,logw,log1w,target in regions:
    total=0
    for c,fun in [(4*M,log1w-logw),(-2*N,logw)]:
        cs=s.series((jac*c.subs(w,sub).subs(L,Lexp)).expand(),e,0,3).removeO()
        total+=lc(cs*fun,e,0)
    check(s.expand(total).subs(l,0),target,'Four-insertion '+name+' region')
print('All six region expansions agree with the independently written formulas.')
