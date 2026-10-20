"""Independent numerical assembly check using full, contour-deformed kite integrals.
Run alongside the other files in this bundle. Requires numpy scipy mpmath.
"""
import json
from pathlib import Path
import mpmath as mp
from full_kite_checks import full
from full_amplitude_checks import J,chain,coeffs
from check_integrals import gamma_ratio,k4_selberg

mp.mp.dps=70

def effective_a4(d,e,T):
    A,R,M,b3,a2,a3,a4=coeffs(d,T)
    kap=mp.pi**(d/2)/mp.gamma(d/2);u=(d-e)/4
    J2=J(d,u,3*u);J3=J(d,u,5*u-d/2);J4=J(d,u,7*u-d)
    H=mp.gamma(d/2)*gamma_ratio([e/2,e/2,d/2-e],[2*u,2*u,e])
    k2=full(float(d),float(e),2,h=.01 if d==1 else .02)
    k4=full(float(d),float(e),4,h=.01 if d==1 else .02)
    total=chain(d,[3*u,u,3*u])/36+k2/4+chain(d,[2*u]*3)/8+k4/4+chain(d,[u,3*u,u])/12
    f2=J2/(6*kap**2)
    f3=(J2/e-H*J3/4)/kap**2
    f4=((mp.mpf(9)/(2*e**2)-A/e)*J2-9*H*J3/(4*e)+total*J4)/kap**2
    g=e/3+2*A/9*e**2+(8*A*A/27-b3/81)*e**3
    return (f2*g*g+f3*g**3+f4*g**4-a2*e**2-a3*e**3)/e**4

def extrapolate(xs,ys):
    return sum(ys[i]*mp.fprod(-xs[j]/(xs[i]-xs[j]) for j in range(len(xs)) if j!=i) for i in range(len(xs)))

rows=[]
for ds in ('1','2','3'):
    d=mp.mpf(ds)
    T=(6*mp.gamma(mp.mpf(1)/4)**4/mp.pi if d==1 else (mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4))**4 if d==2 else mp.mpf('30.10261538732325'))
    target=coeffs(d,T)[-1]
    es=[mp.mpf('0.0001')/2**n for n in range(5)]
    values=[effective_a4(d,e,T) for e in es]
    fit4=extrapolate(es[:4],values[:4]);fit5=extrapolate(es,values)
    row={'d':ds,'target':mp.nstr(target,30),'full_integral_4point_extrapolation':mp.nstr(fit4,25),'full_integral_5point_extrapolation':mp.nstr(fit5,25),'absolute_residual':mp.nstr(abs(fit5-target),10),'sampling_points':[{'epsilon':mp.nstr(e,15),'effective_a4':mp.nstr(v,25)} for e,v in zip(es,values)]}
    print(row,flush=True);rows.append(row)
    assert abs(fit5-target)<mp.mpf('1e-9')
selberg=[]
for es in ('0.04','0.02','0.01'):
    e=mp.mpf(es)
    diff=full(2,float(e),4)-k4_selberg(e)
    selberg.append({'epsilon':es,'full_MB_minus_exact_Selberg':mp.nstr(diff,15)})
    assert abs(diff)<mp.mpf('1e-10')
Path('verification_results.json').write_text(json.dumps({'description':'Full two-loop kite MB integration plus full Gamma chain diagrams, counterterm subtraction, fixed point insertion, and epsilon extrapolation. Shared diagram enumeration and RG input remain assumptions; this is not an external validation.','a4_assembly':rows,'d2_symmetric_kite_check':selberg},indent=2)+'\n')
print('PASS: full-integral extrapolation and complex-Selberg checks.')
