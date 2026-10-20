#!/usr/bin/env python3
"""Exploratory cutoff extrapolation; NOT physical matching or a C8 error bar.
Known C2/C3 are control variates. C4..C8 are fitted sequentially. The prior
phi6 spectral inputs through omega5 are conditional. omega6 is unknown and
is a fitted nuisance parameter at order eight. No physical C4..C8 is a target.
"""
from pathlib import Path
import json,math
import numpy as np
from scipy.special import gamma
ROOT=Path(__file__).resolve().parents[1]
A=np.pi+4*np.log(2)
C2=A/9
C3=(np.pi**2+6*np.pi*np.log(2)+12*np.log(2)**2-6*gamma(.25)**4/np.pi)/81
OMEGA=[0.,3.5,-29.552388360629354,556.2143040434153,-13457.689278726075,376964.56135577295,0.]


def data():
    rows=sorted([json.loads(p.read_text()) for p in (ROOT/'results/raw').glob('*_d8.json')],key=lambda r:r['cutoff'])
    return np.array([r['cutoff'] for r in rows],float),np.array([r['C'] for r in rows])


def eval_basis(L,T2,model,shift=0.,n8=False):
    # shifts are tail reparametrizations, not changes in actual Hamiltonian cutoff.
    z=L+shift;ell=np.log(z)
    X=[np.ones(len(L)),T2,z**-1,z**-1.5,ell*z**-1.5]
    if model=='A':X+=[z**-2]
    if model=='B':X+=[z**-2,ell*z**-2]
    if model=='C':X+=[ell/z]
    if model=='D':X+=[z**-2,z**-2.5]
    if n8:X+=[ell*T2]
    return np.array(X).T


def ls(X,y,mp_dps=None):
    scale=np.linalg.norm(X,axis=0);Xs=X/scale
    if mp_dps:
        import mpmath as mp
        with mp.workdps(mp_dps):
            aa=mp.matrix([[mp.mpf(float(v)) for v in row] for row in Xs]);bb=mp.matrix([mp.mpf(float(v)) for v in y])
            z,_=mp.qr_solve(aa,bb)
            b=np.array([float(v) for v in z])/scale
    else:b=np.linalg.lstsq(Xs,y,rcond=None)[0]/scale
    return b,float(np.linalg.cond(Xs))


def fit(L,C,lo=16,hi=50,model='A',shift=0.,fixed_omega6=None,mp_dps=None):
    mask=(L>=lo)&(L<=hi)
    a=L[mask];d=C[mask];ell=np.log(a+shift)
    e=[np.ones(len(a))]
    for n in range(1,7):e.append(ell/n*sum(j*OMEGA[j]*e[n-j] for j in range(1,n+1)))
    limits=[.5,-1/6,C2,C3];details=[]
    for n in range(4,9):
        Y=d[:,n].copy()
        for j in range(1,n-1):Y+=e[j]*(d[:,n-j]-limits[n-j])
        if n==8 and fixed_omega6 is not None:Y+=fixed_omega6*ell*(d[:,2]-C2)
        X=eval_basis(a,d[:,2]-C2,model,shift,n==8 and fixed_omega6 is None)
        if len(a)<=X.shape[1]:raise ValueError('Insufficient fit points')
        b,cond=ls(X,Y,mp_dps)
        limits.append(float(b[0]))
        details.append(dict(order=n,max_residual=float(np.max(abs(X@b-Y))),scaled_condition=cond,
                            fitted_omega6=float(-b[-1]) if n==8 and fixed_omega6 is None else fixed_omega6,
                            coefficients=b.tolist()))
    return dict(lo=lo,hi=hi,model=model,shift=shift,limits=limits,details=details,
                status='Exploratory raw-cutoff intercept, not physical C8',mp_dps=mp_dps)


def main():
    L,C=data();rows=[]
    for hi in (40,44,48,50):
        for lo in (8,12,16,20,24):
            for model in ('A','B','C','D'):
                for shift in (-2.,0.,2.):
                    try:r=fit(L,C,lo,hi,model,shift);rows.append(r)
                    except ValueError:pass
    (ROOT/'results/extrapolation_models.json').write_text(json.dumps(rows,indent=2)+'\n')
    ref=[fit(L,C,16,50,m,mp_dps=70) for m in ('A','B','C')]
    (ROOT/'results/extrapolation_reference.json').write_text(json.dumps(ref,indent=2)+'\n')
    for r in ref:print(r['model'],r['limits'][4:],r['details'][-1])
    print('All end50 ranges')
    for lo in (8,12,16,20,24):
        subset=[r['limits'][8] for r in rows if r['hi']==50 and r['lo']==lo]
        print(lo,min(subset),max(subset))
if __name__=='__main__':main()
