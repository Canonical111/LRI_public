"""Two-Barnes-contour expression for general-d Kappa, after extracting the pinch.
Numerical trapezoidal evaluation uses IEEE double; not an interval certificate.
"""
import numpy as np
from scipy.special import loggamma,gammaln,digamma,polygamma,bernoulli
import mpmath as mp
import json,time
from pathlib import Path
B=bernoulli(20)
def trigamma(z):
    z=np.asarray(z,dtype=complex)
    w=z+24
    val=1/w+1/(2*w*w)
    for k in range(1,11):val+=B[2*k]/w**(2*k+1)
    for k in range(24):val+=1/(z+k)**2
    return val

def gamma_part(q):
    A=digamma(2*q)+digamma(1)-2*digamma(q)
    j1=polygamma(1,1);u1=polygamma(1,q);v1=polygamma(1,2*q)
    u2=polygamma(2,q);v2=polygamma(2,2*q);u3=polygamma(3,q);v3=polygamma(3,2*q)
    return A*A*u1-A*A*v1/2-A*u2/2+A*v2/2+j1*u1/2-j1*v1/4+u1*u1/2-u1*v1+u3/24+3*v1*v1/8-7*v3/48

def kappamb(d,step=.025,cutoff=9,block=32):
    q=d/4.;c=-q/3;n=int(np.ceil(cutoff/step));y=np.arange(-n,n+1)*step
    v=c+1j*y[None,:]
    lv=2*loggamma(-v)+loggamma(q+v)-loggamma(q-v)
    total=0j;total0=0j
    for i in range(0,len(y),block):
        u=c+1j*y[i:i+block,None];w=u+v
        lu=2*loggamma(-u)+loggamma(u)-loggamma(2*q-u)
        f=np.exp(lu+lv+loggamma(q+w)+loggamma(q-w))
        e1=(digamma(u)-digamma(q-w)+digamma(2*q-u)-digamma(q+w))/2
        e2=(trigamma(u)+trigamma(q-w)-trigamma(2*q-u)-trigamma(q+w))/4
        total+=np.sum(f*(e1*e1+e2)/2)
        total0+=np.sum(f)
    norm=np.exp(2*gammaln(2*q)-4*gammaln(q))*step**2/(2*np.pi)**2
    v2=norm*total;v0=norm*total0
    return {'K':float(v2.real+gamma_part(q)),'K_integral':float(v2.real),'gamma_part':float(gamma_part(q)),'K_imag':float(v2.imag),'F0':float(v0.real)}

if __name__=='__main__':
    rows=[]
    for d in [1,2,3]:
        for h in [.025,.015]:
            t=time.time();v=kappamb(d,h,9)
            q=d/4;A=digamma(2*q)+digamma(1)-2*digamma(q);T=polygamma(1,q);R=polygamma(1,2*q)-polygamma(1,1)
            cand=2*T*T-3*R*T+A*polygamma(2,q)/2
            v.update(d=d,step=h,cutoff=9,seconds=time.time()-t,naive_candidate=cand,difference=cand-v['K']);rows.append(v);print(v,flush=True)
    Path(__file__).with_name('kappa_mb_checks.json').write_text(json.dumps(rows,indent=2))
