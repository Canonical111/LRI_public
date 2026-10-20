#!/usr/bin/env python3
"""Two-endpoint 3d LRI resummation. Numerical execution belongs inside Slurm.

All choices are fixed in inputs/protocol.json; reference data do not select them.
No principal-value treatment of positive-real Padé Borel poles is used.
"""
import csv
import hashlib
import json
import math
import platform
import os
from functools import lru_cache
from pathlib import Path
import mpmath as mp
import numpy as np
import scipy
from scipy.linalg import eigh_tridiagonal
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"results"
OUT.mkdir(exist_ok=True)
P = json.loads((ROOT/"inputs/protocol.json").read_text())
mp.mp.dps = P["working_digits"]
A = mp.mpf(9)/4*(mp.gamma(mp.mpf(9)/4)/mp.gamma(mp.mpf(3)/4))**2
S = mp.mpf(P["S"])
E = 3-4*S # epsilon at the SR endpoint, not the SR energy dimension
ESR = mp.mpf(P["E_SR"])
SR = json.loads((ROOT/"inputs/sri_summary.json").read_text())
CSR = mp.mpf(str(SR["retained"]["C1"]))
q = mp.mpf(3)/4
psiA = mp.digamma(2*q)+mp.digamma(1)-2*mp.digamma(q)
psiR = mp.polygamma(1,2*q)-mp.polygamma(1,1)
psiU = mp.polygamma(2,q)
psiV = mp.polygamma(2,1)+mp.polygamma(2,2*q)
Q3 = mp.mpf(P["Q3"])
C = [mp.mpf(3)/2,-mp.mpf(1)/6,psiA/9,(psiA**2+psiR-8*Q3)/108,
     (16*mp.mpf(P["P4"])-psiA**3-8*psiA*Q3-3*psiA*psiR+mp.mpf(53)/2*psiU-3*psiV)/648,
     *[mp.mpf(P["C"+str(k)]) for k in (5,6,7,8)]]
MODES = ("direct","value","slope")
KEYX = [float(S),.52,.53,.54,.55,.575,.6,.625,.65,.675,.7,.725,.74,.75]
X = np.unique(np.r_[np.linspace(float(S),.75,751),KEYX])
CHECKS = []
CURVES = {}

def conv(a,b,n):
    return [sum(a[j]*b[k-j] for j in range(k+1) if j<len(a) and k-j<len(b)) for k in range(n+1)]

def qp(p,n):
    return [(-1)**k*mp.binomial(p,k)/E**k for k in range(n+1)]

def compose(a,z,n):
    out=[mp.mpf(0)]*(n+1)
    power=[mp.mpf(1)]+[mp.mpf(0)]*n
    for v in a:
        out=[u+v*w for u,w in zip(out,power)]
        power=conv(power,z,n)
    return out

def epdata(mode,n):
    power={"direct":0,"value":1,"slope":2}[mode]
    ss=[mp.mpf(0)]*(n+1)
    if mode!="direct": ss[0]=ESR
    if mode=="slope": ss=[u+CSR*(E/4)*v for u,v in zip(ss,qp(1,n))]
    return ss,power

def series(mode,n,c=None):
    c=(C if c is None else c)[:n+1]
    if mode=="direct": return c
    s,power=epdata(mode,n)
    h=conv([u-v for u,v in zip(c,s)],qp(-power,n),n)
    restored=[u+v for u,v in zip(s,conv(h,qp(power,n),n))]
    assert max(abs(u-v)/(1+abs(v)) for u,v in zip(restored,c))<mp.mpf("1e-55")
    return h

def base_factor(mode,x):
    x=np.asarray(x,dtype=float)
    q=(x-float(S))/float(E/4)
    if mode=="direct": return np.zeros_like(x),np.ones_like(x)
    base=np.full_like(x,float(ESR))
    if mode=="slope": base+=float(CSR)*(x-float(S))
    return base,q**{"value":1,"slope":2}[mode]

def pol(c,b,alpha,A0=A):
    return [sum(c[j]*(4*A0)**j/mp.gamma(j+b+1)*(-1)**(k-j)*
                mp.binomial(mp.mpf(alpha)-2*j,k-j) for j in range(k+1)) for k in range(len(c))]

def cb_back(p,b,alpha,A0,n):
    w=[mp.mpf(0)]+[(-1)**(k-1)*mp.binomial(2*k,k)/(k+1)/(4*A0)**k for k in range(1,n+1)]
    bp=conv(p,[(-1)**k*mp.binomial(-mp.mpf(alpha),k) for k in range(n+1)],n)
    bt=compose(bp,w,n)
    return [v*mp.gamma(k+b+1) for k,v in enumerate(bt)]

@lru_cache(None)
def lag(n,b):
    k=np.arange(n,dtype=float); j=np.arange(1,n,dtype=float)
    t,v=eigh_tridiagonal(2*k+b+1,np.sqrt(j*(j+b)))
    weights=math.gamma(b+1)*v[0,:]**2
    assert abs(weights.sum()/math.gamma(b+1)-1)<2e-13
    return t,weights

def cb(mode,n,b=4,alpha=0,afactor=1,x=X,c=None,nquad=240):
    a0=A/mp.mpf(str(afactor)); p=pol(series(mode,n,c),b,alpha,a0)
    t,weights=lag(nquad,b)
    z=(3-4*np.asarray(x))[:,None]*t[None,:]/float(a0)
    w=z/(np.sqrt(1+z)+1)**2
    y=(np.polynomial.polynomial.polyval(w,np.asarray(p,dtype=float))/(1-w)**alpha).dot(weights)
    base,factor=base_factor(mode,x)
    return base+factor*y

def rational_back(p,q,b,n):
    out=[]
    for k in range(n+1):
        out.append(((p[k] if k<len(p) else 0)-sum(q[j]*out[k-j] for j in range(1,min(k,len(q)-1)+1)))/q[0])
    return [v*mp.gamma(k+b+1) for k,v in enumerate(out)]

def pade_candidates(mode,n,b,c=None):
    cs=series(mode,n,c)
    bt=[v/mp.gamma(k+b+1) for k,v in enumerate(cs)]
    ms=sorted(range(max(1,n//2-1),min(n,n//2+1+n%2)+1),key=lambda m:(abs(n-2*m),m))
    records=[]; choice=None
    for m in ms:
        try:
            pp,qq=mp.pade(bt,n-m,m)
            roots=np.roots(np.array(qq[::-1],dtype=float))
            bad=any(z.real>0 and abs(z.imag)<1e-8*max(1,abs(z)) for z in roots)
            back=rational_back(pp,qq,b,n)
            err=max(abs(u-v)/(1+abs(v)) for u,v in zip(back,cs))
            assert err<mp.mpf("1e-48")
            selected=not bad and choice is None
            if selected: choice=(pp,qq)
            records.append(dict(mode=mode,N=n,b=b,L=n-m,M=m,admissible=not bool(bad),selected=selected,
                                poles=[[float(z.real),float(z.imag)] for z in roots],roundtrip=float(err)))
        except (ZeroDivisionError,ValueError) as exc:
            records.append(dict(mode=mode,N=n,b=b,L=n-m,M=m,admissible=False,selected=False,error=str(exc)))
    return choice,records

def pb_integral(pp,qq,b,arg):
    pp=np.array(pp,dtype=float); qq=np.array(qq,dtype=float)
    def f(t):
        if t==0: return pp[0]/qq[0] if b==0 else 0.
        logw=-t+b*math.log(t)
        if logw < -740: return 0.
        z=arg*t
        return math.exp(logw)*np.polynomial.polynomial.polyval(z,pp)/np.polynomial.polynomial.polyval(z,qq)
    return quad(f,0,np.inf,epsabs=2e-11,epsrel=2e-11,limit=400)

def pb(mode,n,b=4,x=X):
    choice,records=pade_candidates(mode,n,b)
    if choice is None: return None,records
    pp,qq=choice
    # Adaptive integration handles admissible poles near but off the positive ray.
    vals=[pb_integral(pp,qq,b,3-4*x0) for x0 in x]
    base,factor=base_factor(mode,x)
    err=float(np.max(factor*np.array([v[1] for v in vals])))
    assert err<1e-8
    CHECKS.append(dict(check="PB adaptive reported error",mode=mode,N=n,b=b,max_error=err))
    return base+factor*np.array([v[0] for v in vals]),records

def writecsv(name,rows):
    with (OUT/name).open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def validate_cb(mode):
    cs=series(mode,8); p=pol(cs,4,0)
    back=cb_back(p,4,0,A,8)
    err=float(max(abs(u-v)/(1+abs(v)) for u,v in zip(back,cs)))
    assert err<1e-48
    CHECKS.append(dict(check="CB formal roundtrip",mode=mode,error=err))
    for x in [float(S),.53,.575,.625,.7,.75]:
        arg=mp.mpf(str(3-4*x)); base,factor=base_factor(mode,[x])
        def integrand(t):
            z=arg*t/A; w=z/(mp.sqrt(1+z)+1)**2
            return mp.exp(-t)*t**mp.mpf("4")*mp.polyval(p[::-1],w)
        high=mp.quad(integrand,[0,1,4,12,40,mp.inf])
        yy=cb(mode,8,x=[x])[0]
        e=float(abs(yy-(base[0]+factor[0]*high)))
        step=float(abs(yy-cb(mode,8,x=[x],nquad=120)[0]))
        assert e<2e-9
        CHECKS.append(dict(check="CB 65-digit integration",mode=mode,x=x,error=e,GL120_to_240=step))

def main():
    print("START 3d LRI; supplied SRI slope",mp.nstr(CSR,24),flush=True)
    print("GFF coefficients",[mp.nstr(v,24) for v in C],flush=True)
    scans=[]; pade=[]; summary={}
    for mode in MODES:
        core=[]; wide=[]
        for n in P["wide_scan"]["orders"]:
            for b in P["wide_scan"]["b"]:
                for alpha in P["wide_scan"]["alpha"]:
                    yy=cb(mode,n,b,alpha)
                    wide.append(yy)
                    if n in P["core_scan"]["orders"] and b in P["core_scan"]["b"] and alpha in P["core_scan"]["alpha"]: core.append(yy)
                    scans.append(dict(mode=mode,N=n,b=b,alpha=alpha,
                                      **{"x_"+str(x):float(yy[np.searchsorted(X,x)]) for x in KEYX}))
                    if b==4 and alpha==0: CURVES[f"{mode}_CB{n}"]=yy
                    if n==8 and alpha==0: CURVES[f"{mode}_b{b}"]=yy
        CURVES[mode+"_core_low"]=np.min(core,axis=0)
        CURVES[mode+"_core_high"]=np.max(core,axis=0)
        CURVES[mode+"_wide_low"]=np.min(wide,axis=0)
        CURVES[mode+"_wide_high"]=np.max(wide,axis=0)
        for fac in P["a_factors"]: CURVES[f"{mode}_a{fac}"]=cb(mode,8,afactor=fac)
        for n in (6,7,8):
            vals,records=pb(mode,n)
            pade.extend(records)
            if vals is not None: CURVES[f"{mode}_PB{n}"]=vals
        shifts=[]
        for k in (6,7,8):
            c=C.copy(); c[k]+=mp.mpf(P[f"C{k}_allowance"])
            dy=cb(mode,8,c=c)-CURVES[mode+"_CB8"]
            CURVES[f"{mode}_shift_C{k}"]=dy
            shifts.append(abs(dy))
        CURVES[mode+"_input_allowance"]=sum(shifts)
        CURVES[mode+"_C8_tenfold_allowance"]=sum(shifts[:-1])+shifts[-1]/10
        CURVES[mode+"_C8_exact_allowance"]=sum(shifts[:-1])
        validate_cb(mode)
        yy=CURVES[mode+"_CB8"]; i=int(np.argmin(yy))
        summary[mode]={"minimum_x":float(X[i]),"minimum_dimension":float(yy[i]),"SRI_endpoint":float(yy[0]),
                       "GFF_endpoint":float(yy[-1]),"max_input_allowance":float(np.max(sum(shifts)))}
        print("Completed",mode,summary[mode],flush=True)
    # Frozen low-order holdouts. Hidden coefficients never affect construction or pole selection.
    hold=[]
    for mode in ("direct","slope"):
        for n in (4,5,6,7):
            cs=series(mode,n); s,power=epdata(mode,n+1)
            pc=pol(cs,4,0)
            nextcb=cb_back(pc,4,0,A,n+1)
            choice,records=pade_candidates(mode,n,4)
            for method,hs in [("CB",nextcb),("PB",None if choice is None else rational_back(*choice,4,n+1))]:
                if hs is None: continue
                prediction=hs[-1] if mode=="direct" else s[-1]+conv(hs,qp(power,n+1),n+1)[-1]
                hold.append(dict(mode=mode,method=method,training_order=n,predict_C=n+1,
                                 predicted=float(prediction),observed=float(C[n+1]),
                                 relative_error=float((prediction-C[n+1])/C[n+1]),
                                 absolute_relative_error=float(abs((prediction-C[n+1])/C[n+1])),
                                 shape="conformal" if method=="CB" else next(f'{r["L"]}/{r["M"]}' for r in records if r["selected"])))
    # Raw local expansions are retained as local comparisons, not global predictions.
    CURVES["SRI_linear"]=float(ESR)+float(CSR)*(X-float(S))
    for n in (3,5,7,8):
        CURVES[f"GFF_truncated{n}"]=np.polynomial.polynomial.polyval(3-4*X,np.array(C[:n+1],dtype=float))
    rows=[dict(Delta_sigma=float(x),s=float(3-2*x),epsilon=float(3-4*x),delta_SR=float(x-float(S)),
               **{k:float(v[i]) for k,v in CURVES.items()}) for i,x in enumerate(X)]
    writecsv("curves.csv",rows)
    writecsv("key_points.csv",[rows[np.searchsorted(X,x)] for x in KEYX])
    writecsv("parameter_scan.csv",scans); writecsv("held_out.csv",hold)
    ratios=[dict(n=n,raw_ratio=float(-C[n]/C[n-1]),power_corrected=float(-C[n]/C[n-1]/(n+4)),
                 candidate_limit=float(1/A)) for n in range(2,9)]
    writecsv("ratios.csv",ratios)
    (OUT/"validation.json").write_text(json.dumps(CHECKS,indent=2))
    (OUT/"pade_poles.json").write_text(json.dumps(pade,indent=2))
    selected=[r for r in pade if r["selected"]]
    meta=dict(protocol=P,coefficients=[str(v) for v in C],C_SR=str(CSR),S=str(S),E_SR=str(ESR),epsilon_star=str(E),A_epsilon=str(A),a_epsilon=str(1/A),
              summary=summary,pade_selected=selected,curve_rows=len(X),versions=dict(python=platform.python_version(),
              numpy=np.__version__,scipy=scipy.__version__,mpmath=mp.__version__),job_id=os.getenv("SLURM_JOB_ID"),
              script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              validations_passed=True)
    (OUT/"metadata.json").write_text(json.dumps(meta,indent=2))
    print("KEY: x baselineCB8 baselinePB8 directCB8 core_min core_max allowance",flush=True)
    for x in KEYX:
        r=rows[np.searchsorted(X,x)]
        print(x,*[r.get(k) for k in ["slope_CB8","slope_PB8","direct_CB8","slope_core_low","slope_core_high","slope_input_allowance"]],flush=True)
    print("HELD OUT",json.dumps(hold),flush=True)
    print("FINISHED: all scientific checks passed",flush=True)

if __name__=="__main__": main()
