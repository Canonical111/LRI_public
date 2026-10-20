"""Leading missing coefficient-box tail from exact one-face block singularities.
Derives the N^(-7/4) coefficient independently of the cutoff-sequence values.
No physical C2 input. The residual expansion is still to be controlled.
"""
import json,os,time
import numpy as np
from math import pi,gamma
from pathlib import Path
from mixed_sequence import make_matrix
from resummed import coeff,CHI,ROOT
from improved_regulator import trunc_exp
import resummed_improved as r

DEFAULT_TAIL_CUTOFF=2048

def configured_tail_cutoff():
    """Two-index cutoff for leading-tail evaluations made by the analysis scripts.
    Historical value 2048 unless LRI_TAIL_CUTOFF is set (an integer >= 64).
    Only the auxiliary cutoff changes; the tail formula is unchanged.
    """
    text=os.environ.get('LRI_TAIL_CUTOFF','').strip()
    if not text:return DEFAULT_TAIL_CUTOFF
    if not text.isdigit() or int(text)<64:
        raise ValueError(f'LRI_TAIL_CUTOFF must be an integer >= 64; got {text!r}.')
    return int(text)

def poly_col(B,co):
    out=np.zeros_like(B)
    for i,c in enumerate(co):
        if i==0:out+=c*B
        else:out[:,i:]+=c*B[:,:-i]
    return out

def poly_diag(B,co):
    out=np.zeros_like(B)
    for i,c in enumerate(co):
        if i==0:out+=c*B
        else:out[i:,i:]+=c*B[:-i,:-i]
    return out

def evaluate(lam,order,N=2048,two_point=None):
    K=N+1;nn=np.arange(K);q=np.exp(-lam)
    H=coeff(CHI,K)*q**nn*trunc_exp(lam*(nn+CHI/2),order)
    aa=coeff(1/8,K)
    B=make_matrix(H,aa,H)
    E=poly_col(B,[.5,.5]);D=poly_col(B,[.125,.375,.375,.125])
    n=np.arange(N);ev=1/(2*n+2);ee=1/(2*n+1);mid=1/(2*n+2*CHI)
    e=E[:N,:N];d=D[:N,1:];v=B[:N,:N]
    outer=float(np.sum(((2*e-d)*e*ee[None,:]-v*v*ev[None,:])*mid[:,None]))
    del B,E,D,e,d,v
    A=make_matrix(H,H,aa,True)
    E=poly_diag(A,[.5,.5]);D=poly_diag(A,[.125,.375,.375,.125])
    e=E[:N,:N];d=D[1:,1:];v=A[:N,:N]
    midd=float(np.sum((2*e-d)*e*ee[:,None]*ee[None,:]-v*v*ev[:,None]*ev[None,:]))
    del A,E,D,e,d,v
    if two_point is None:
        r.ORDER=order;two_point=r.two_point(lam,200000)
    normx=2*two_point['states'][1]['norm']-two_point['states'][2]['norm']-two_point['states'][0]['norm']
    nested=float(np.sum(H)**2*normx/((2*pi)**2*q**CHI))
    combination=4*outer+2*midd+nested
    fac=-(2*pi)**4*q**(2*CHI)
    pref=2/(7*gamma(1/8)**2)
    tail=fac*pref*combination
    return dict(lam=lam,order=order,N=N,outer=outer,middle_adjacent=midd,middle_nested=nested,
        face_sum=combination,asymptotic_tail_coefficient=tail,
        convention='X_chain(infinity)-X_chain(N) = coefficient*N^(-7/4)+subleading',
        independent_of_cutoff_sequence=True)

if __name__=='__main__':
    rows=[]
    for k,a in [(1,.25),(1,.15),(1,.125),(1,.1),(2,.175),(2,.25),(3,.35),(3,.5)]:
        for N in [512,1024,2048]:
            st=time.time();x=evaluate(a,k,N);rows.append(x);print(k,a,N,x['asymptotic_tail_coefficient'],x['outer'],x['middle_adjacent'],x['middle_nested'],time.time()-st,flush=True)
            (ROOT/'exact_leading_tail.json').write_text(json.dumps(rows,indent=2))
