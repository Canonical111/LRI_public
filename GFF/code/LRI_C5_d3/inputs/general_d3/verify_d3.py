#!/usr/bin/env python3
"""Recompute the d=3 reductions. Run from any working directory.
No saved primitive values enter formula-side evaluations.
"""
import json,time,sys,platform,signal
from pathlib import Path
import mpmath as mp
from d3_reduction import *
OUT=Path(__file__).resolve().parents[2]/'verification'/'general_d3'
OUT.mkdir(parents=True,exist_ok=True)

def ser(x):
    if isinstance(x,dict):return {k:ser(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [ser(v) for v in x]
    if isinstance(x,(str,int,float,bool)) or x is None:return x
    return str(x)

def save(name,x):(OUT/name).write_text(json.dumps(ser(x),indent=2)+'\n')

runs=[]
for dps,N,K in [(55,80,36),(90,160,64)]:
    mp.mp.dps=dps;start=time.time();a=amplitudes(N,K);v=periods(N,K,a)
    g=gamma_amplitudes()
    row=dict(dps=dps,N=N,K=K,seconds=time.time()-start,values=v,
             gamma_product_error=a['a3']*a['b3']-g['a3b3'],
             Dougall_b4_error=a['b4']-g['b4'])
    runs.append(row);save('period_values.json',dict(scope='formula evaluations with asymptotic numerical tails, not interval bounds',runs=runs))
    print('run',dps,'seconds',row['seconds'],'Q',v['Q3'],'P4',v['P4_3'],'P5',v['P5_3'],flush=True)
mp.mp.dps=75;N=130;K=52;a=amplitudes(N,K);v=periods(N,K,a)
projections=[];modes=[]
for t in [mp.mpc('0.063','0.041'),mp.mpc('-0.082','0.027')]:
    for r in (3,4,7):
        lhs=Xi(r,t,N,K)+(1 if r==3 else -1)*Xi(r,t+mp.mpf('.5'),N,K)
        rhs=expected_product(r,t,a)
        projections.append(dict(r=r,t=t,lhs=lhs,rhs=rhs,residual=lhs-rhs))
for u in [mp.mpc('0.21','0.043'),mp.mpc('0.62','-0.051')]:
    for r,m,eps in [(3,0,1),(3,1,1),(4,1,1),(7,1,-1),(7,3,-1)]:
        got=Psi(r,m,eps,u,N,K)
        if (r,m)==(3,0):pred=a['a3']*mp.cos(mp.pi*u)
        elif (r,m)==(3,1):pred=a['b3']*mp.sin(mp.pi*u)
        elif (r,m)==(4,1):pred=a['b4']*mp.sin(2*mp.pi*u)
        else:pred=sum(a['h1' if m==1 else 'h3'][k-1]*mp.sin(2*mp.pi*k*u) for k in range(1,4))
        modes.append(dict(r=r,m=m,u=u,residual=got-pred))
complex_check=complex_periods(N,K,a)
complex_check.update(P4_difference=complex_check['P4_3_complex']-v['P4_3'],P5_difference=complex_check['P5_3_complex']-v['P5_3'])
for r,key in [(4,'sigma4'),(7,'sigma7')]:
    sigma=complex_check[key];t=-mp.mpf(3)/8+mp.j*sigma
    complex_check[f'Xi{r}_one_Horn_error']=Xi_axis(r,sigma,N,K)-Xi(r,t,N,K)
save('identities.json',dict(dps=75,N=N,K=K,projections=projections,mode_checks=modes,complex_alternatives=complex_check))
print('identities done',flush=True)
# Literal ordinary hypergeometric calls, independent of the tail routine.
mp.mp.dps=40;literal=[]
for r,m,eps,u in [(3,0,1,mp.mpf(1)/8),(3,1,1,mp.mpf(1)/8),
                  (4,0,1,mp.mpf(1)/4),(4,1,1,mp.mpf(3)/4),
                  (7,1,-1,mp.mpf(1)/4),(7,3,-1,mp.mpf(11)/16)]:
    st=time.time();x=U(r,m,eps,u,literal=True);y=U(r,m,eps,u,100,42)
    literal.append(dict(r=r,m=m,epsilon=eps,u=u,literal_value=x,tail_value=y,residual=x-y,seconds=time.time()-st))
    save('literal_hypergeometric.json',dict(dps=40,checks=literal))
    print('literal',r,m,'seconds',time.time()-st,flush=True)
save('environment.json',dict(python=sys.version,mpmath=mp.__version__,platform=platform.platform()))
