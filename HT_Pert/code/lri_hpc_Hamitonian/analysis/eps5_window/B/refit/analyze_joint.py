#!/usr/bin/env python3
"""Separate phi6-gap fits and joint thermal extrapolations through C7.
No thermal C4-C7 continuum reference values are used as fit inputs.
All intervals from basis/window variations are empirical, not confidence bounds.
"""
from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np
import mpmath as mp
D=Path(__file__).resolve().parent
A=math.pi+4*math.log(2);C2=A/9;C3=-3.71985632290183342249
MODELS={
 'minimal':[(1,0),(1.5,0)],
 'A':[(1,0),(1.5,0),(1.5,1),(2,0)],
 'B':[(1,0),(1.5,0),(1.5,1),(2,0),(2,1)],
 'C':[(1,0),(1,1),(1.5,0),(1.5,1)],
 'D':[(1,0),(1,1),(1.5,0),(1.5,1),(2,0)],
 'E':[(1,0),(1,1),(1.5,0),(1.5,1),(2,0),(2,1)],
 'F':[(1,0),(1.5,0),(1.5,1),(1.5,2),(2,0)],
}

def load(paths):
    out={}
    for path in paths:
        path=D/path
        if path.exists():
            for row in json.loads(path.read_text()):out[row['cutoff']]=row
    return [out[k] for k in sorted(out)]

def ls(X,y,mpqr=False):
    scale=np.linalg.norm(X,axis=0);XX=X/scale
    if len(y)<X.shape[1]+2:raise ValueError('Insufficient residual data.')
    if mpqr:
        with mp.workdps(65):
            p,_=mp.qr_solve(mp.matrix([[float(a) for a in r] for r in XX]),mp.matrix(y.tolist()))
            p=np.array(list(p),float).ravel()/scale
    else:p=np.linalg.lstsq(XX,y,rcond=1e-14)[0]/scale
    weights=np.linalg.pinv(XX,rcond=1e-14)[0]/scale[0]
    return p,dict(condition=float(np.linalg.cond(XX)),residual=float(max(abs(X@p-y))),intercept_gain_l1=float(sum(abs(weights))))

def eseries(L,w,kmax):
    z=np.log(np.asarray(L,float));e=np.zeros((kmax+1,len(z)));e[0]=1
    for k in range(1,kmax+1):
        for j in range(1,k+1):e[k]+=z*j*w[j]*e[k-j]/k
    return e

def design(L,x,terms,free_log=False):
    z=np.log(L)
    return np.column_stack([np.ones(len(L)),x]+([z*x] if free_log else [])+[L**(-p)*z**j for p,j in terms])

class GapModel:
    def __init__(self,terms,scheme='raw',free_log=False,shift=0,fixed_omega3=None):
        self.terms=terms;self.scheme=scheme;self.free_log=free_log;self.shift=shift;self.fixed_omega3=fixed_omega3
        self.w2=-5*A+(1/54 if scheme=='raw' else 0)
    def fit(self,L,Y,order=5):
        L=np.asarray(L,float)+self.shift;z=np.log(L)
        self.par={};self.diag={};self.lim={2:self.w2};x=Y[:,2]-self.w2
        for k in range(3,order+1):
            w={1:3.5,2:self.w2,3:self.lim.get(3,0),4:self.lim.get(4,0),5:0}
            e=eseries(L,w,k-2)
            offset=np.zeros(len(L))
            for j in range(1,k-1):offset-=e[j]*(Y[:,k-j]-self.lim[k-j])
            X=design(L,x,self.terms,self.free_log)
            if k==3 and self.fixed_omega3 is not None:
                pp,self.diag[k]=ls(X[:,1:],Y[:,k]-offset-self.fixed_omega3)
                self.par[k]=np.r_[self.fixed_omega3,pp]
            else:
                self.par[k],self.diag[k]=ls(X,Y[:,k]-offset)
            self.lim[k]=float(self.par[k][0])
        return self
    def predict(self,L,Y2):
        L=np.asarray(L,float)+self.shift;x=Y2-self.w2
        out={2:Y2};w={1:3.5,2:self.w2,3:self.lim.get(3,0),4:self.lim.get(4,0),5:0}
        e=eseries(L,w,3)
        for k in sorted(self.par):
            y=design(L,x,self.terms,self.free_log)@self.par[k]
            for j in range(1,k-1):y-=e[j]*(out[k-j]-self.lim[k-j])
            out[k]=y
        return np.column_stack([out[k] for k in sorted(self.par)])

class ThermalModel:
    def __init__(self,terms,w,free_exponents=False,shift=0,mpqr=False):
        self.terms=terms;self.w=dict(w);self.free=free_exponents;self.shift=shift;self.mpqr=mpqr
    def fit(self,L,C,maxorder=7):
        L=np.asarray(L,float)+self.shift;x=C[:,2]-C2
        self.lim={2:C2,3:C3};self.par={};self.diag={}
        for k in range(4,maxorder+1):
            free=self.free and k>=5
            if free:self.w[k-2]=0
            e=eseries(L,self.w,k-2)
            off=np.zeros(len(L))
            for j in range(1,k-1):off-=e[j]*(C[:,k-j]-self.lim[k-j])
            X=design(L,x,self.terms)
            if free:X=np.column_stack([X,-np.log(L)*x])
            self.par[k],self.diag[k]=ls(X,C[:,k]-off,self.mpqr)
            self.lim[k]=float(self.par[k][0])
            if free:self.w[k-2]=float(self.par[k][-1])
        return self
    def predict(self,L,c2,c3):
        L=np.asarray(L,float)+self.shift;x=c2-C2
        y={2:c2,3:c3};e=eseries(L,self.w,5)
        for k in sorted(self.par):
            X=design(L,x,self.terms)
            pars=self.par[k]
            if self.free and k>=5:
                # The fitted exponent's contribution is already included in e.
                pars=pars[:-1]
            v=X@pars
            for j in range(1,k-1):v-=e[j]*(y[k-j]-self.lim[k-j])
            y[k]=v
        return np.column_stack([y[k] for k in sorted(self.par)])

if __name__=='__main__':
    gaps=load(['phi6_validation.json','phi6_production.json','phi6_extension.json'])
    L=np.array([r['cutoff'] for r in gaps],float)
    gmodels=[]
    for scheme in ('raw','vacuum_subtracted'):
      Y=np.array([r[scheme]['D6'] for r in gaps])
      for name,terms in MODELS.items():
       for lo in (12,16,20,24):
        for free in (False,True):
         m=L>=lo
         try:gm=GapModel(terms,scheme,free).fit(L[m],Y[m])
         except ValueError:continue
         row=dict(scheme=scheme,model=name,lo=lo,hi=float(max(L)),free_leading_log=free,omega={str(k):v for k,v in gm.lim.items()},diagnostics=gm.diag,parameters={str(k):p.tolist() for k,p in gm.par.items()})
         gmodels.append(row)
    (D/'gap_extrapolations.json').write_text(json.dumps(gmodels,indent=2)+'\n')
    th=load(['prior_c7/C7_completed_runs.json','C7_extension.json'])
    LL=np.array([r['cutoff'] for r in th],float);CC=np.array([r['C'] for r in th])
    out=[]
    # Reference independent gap input: later stress tests use all gap variants.
    gr=next(r for r in gmodels if r['scheme']=='raw' and r['model']=='A' and r['lo']==16 and not r['free_leading_log'])
    w={1:3.5,**{int(k):v for k,v in gr['omega'].items()}}
    for name,terms in MODELS.items():
     for lo in (10,12,16,20,24):
      for hi in sorted(set([40,44,48,int(max(LL))])):
       if hi>max(LL):continue
       m=(LL>=lo)&(LL<=hi)
       for free in (False,True):
        try:mod=ThermalModel(terms,w,free_exponents=free).fit(LL[m],CC[m])
        except ValueError:continue
        h=LL>hi
        err=np.max(abs(mod.predict(LL[h],CC[h,2],CC[h,3])-CC[h,4:8]),axis=0).tolist() if h.any() else None
        out.append(dict(model=name,lo=lo,hi=hi,free_exponents=free,C={str(k):v for k,v in mod.lim.items()},omega=mod.w,diagnostics=mod.diag,heldout=err,parameters={str(k):v.tolist() for k,v in mod.par.items()}))
    (D/'joint_extrapolations.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(gap_count=len(gaps),thermal_count=len(th),selected_gap=gr,
       selected_thermal=[r for r in out if r['lo']==16 and r['hi']==max(LL) and r['model'] in ('A','B','C')]),indent=2))
