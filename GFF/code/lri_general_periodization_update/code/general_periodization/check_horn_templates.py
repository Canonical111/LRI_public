import mpmath as mp, sympy as sp, json
from pathlib import Path
from horn_templates import q,t,right_templates,middle_template,primitive_templates
mp.mp.dps=65

def evaluator(term):
    pref=sp.lambdify((q,t),term.pref,'mpmath')
    upper=[(sp.lambdify((q,t),sp.sympify(a),'mpmath'),v) for a,v in term.upper]
    lower=[(sp.lambdify((q,t),sp.sympify(a),'mpmath'),v) for a,v in term.lower]
    def run(qv,tv,idx):
        v=pref(qv,tv)
        for f,w in upper:v*=mp.rf(f(qv,tv),sum(a*b for a,b in zip(w,idx)))
        for f,w in lower:v/=mp.rf(f(qv,tv),sum(a*b for a,b in zip(w,idx)))
        for a,z in zip(idx,term.z):v*=z**a/mp.factorial(a)
        return v
    return run

def degeneracy(qv,l):
    if l==0:return mp.mpf(1)
    return 4*qv*mp.rf(2*qv+1,l-1)*mp.rf(4*qv-1,l-1)/(mp.rf(2*qv,l-1)*mp.factorial(l))

def raw(qv,r,l,n,tv,theta=None,weighted=False):
    a=(l+qv)/2;b=a+qv;s=a+n+tv
    g=mp.gamma(a+s)*mp.gamma(a-s)/(mp.gamma(b+s)*mp.gamma(b-s))
    v=degeneracy(qv,l)*g**r
    if theta is not None:
        v*=(-1)**l*mp.gamma(theta+2*s)*mp.gamma(theta-2*s)/(mp.gamma(2*s)*mp.gamma(-2*s))
    if weighted:v*=l*(l+4*qv-2)
    return v

rows=[]
for qv in [mp.mpf('.25'),mp.mpf('.5'),mp.mpf('.63'),mp.mpf('.75')]:
    tv=mp.mpc('.071','.137')
    for r in [3,4]:
        z,p=right_templates(r);c=middle_template(r)
        for term,idx,l,n in [(z,(2,),0,2),(p,(1,2),2,2),(c,(2,1),4,-3)]:
            val=evaluator(term)(qv,tv,idx);exact=raw(qv,r,l,n,tv)
            rows.append({'q':str(qv),'r':r,'block':term.name,'indices':idx,'relative_residual':str(abs(val-exact)/max(1,abs(exact)))})
    rr,cc=primitive_templates()
    for term,idx,l,n,th,w in [(rr[0],(2,),0,2,2*qv,False),(rr[1],(1,2),2,2,2*qv,False),(rr[2],(1,2),2,2,2*qv-1,True),(cc[0],(2,1),4,-3,2*qv,False),(cc[1],(2,1),4,-3,2*qv-1,True)]:
        val=evaluator(term)(qv,tv,idx);exact=raw(qv,7,l,n,tv,th,w)
        rows.append({'q':str(qv),'r':7,'block':term.name,'indices':idx,'relative_residual':str(abs(val-exact)/max(1,abs(exact)))})
# Exact Fourier orthogonality (numerical high-precision algebra, not graph validation).
orth=[]
for r in [3,4,7]:
    N=2*r-1;eta=1/(8*mp.pi*r)
    for power in range(r):
        ys=[mp.cos(2*mp.pi*power*j/N)*mp.cosh(2*mp.pi*power*eta) for j in range(r)]
        c=[(ys[0]+2*sum(ys[1:]))/N]
        for k in range(1,r):c.append(2*(ys[0]+2*sum(ys[j]*mp.cos(2*mp.pi*k*j/N) for j in range(1,r)))/(N*mp.cosh(2*mp.pi*k*eta)))
        orth.append(max(abs(c[k]-(k==power)) for k in range(r)))
out={'working_digits':mp.mp.dps,'array_checks':rows,'max_array_residual':str(max(mp.mpf(r['relative_residual']) for r in rows)),'max_fourier_residual':str(max(orth))}
Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/horn_template_checks.json').write_text(json.dumps(out,indent=2))
print(out['max_array_residual'],out['max_fourier_residual'])
