"""Parallel phase-grid Cauchy coefficients; same formulas as fast_coefficients.py."""
import json,time,os,sys
from pathlib import Path
import multiprocessing as mp
import numpy as np
from scipy.fft import fftn,irfft,next_fast_len
from math import pi
ROOT=Path(__file__).parent
G={}
def one_slice(i):
 M=G['M'];K=G['K'];z=G['z'];v=G['v'];w=G['w'];ids=G['ids'];sq=G['sq'];pw=G['pw'];sqvw=G['sqvw'];base=G['base'];tmp=G['tmp']
 u=z[i];idx=(ids+i)%M;j=(np.arange(M)+i)%M
 s=sq[2][j][:,None]*sqvw;t=sq[1][:,None]*sq[3][idx]
 D=pw[1][i]*base*pw[2][j][:,None]*pw[3][idx]
 R=np.sqrt((s+t)/2);Q=sq[1][i]*sq[1][None,:]
 A=s*(1+u*w);B=t*(u+w);uvw=u*v*w
 sk=(u+uvw)-(1+u*v);ik=(1/u+1/uvw)-(1+1/(u*v))
 sl=(u+u*v)-(1+uvw);il=(1/u+1/(u*v))-(1+1/uvw)
 k=uvw*(1-sk*ik/4);l=uvw*(1-sl*il/4)
 f=np.array([D*R,.5*D*Q/R,.25*D*(A+B)/R,.5*D*R/Q*(A-B),.25*D*(A*k+B*l)/R,.5*D*R/Q*(A*k-B*l)])
 tmp[:,i]=fftn(f,axes=(1,2),workers=1)[:,:K,:K]/(M*M)
 return i

def compute(K=385,oversample=4,rc=4.5,workers=3):
 start=time.time();M=next_fast_len(oversample*K)
 if M%2:M=next_fast_len(M+1)
 r=np.exp(-rc/K);ph=np.exp(2j*pi*np.arange(M)/M);z=r*ph
 sq=[None]+[np.sqrt(1-r**d*ph) for d in [1,2,3]]
 pw=[None]+[(1-r**d*ph)**(-.125) for d in [1,2,3]]
 ids=(np.arange(M)[:,None]+np.arange(M)[None,:])%M
 sqvw=sq[2][ids];base=pw[1][:,None]*pw[1][None,:]*pw[2][ids]
 fn=ROOT/f'parallel_tmp_K{K}.dat';tmp=np.memmap(fn,mode='w+',dtype=np.complex128,shape=(6,M//2+1,K,K))
 G.update(M=M,K=K,z=z,v=z[:,None],w=z[None,:],ids=ids,sq=sq,pw=pw,sqvw=sqvw,base=base,tmp=tmp)
 ctx=mp.get_context('fork')
 with ctx.Pool(workers) as pool:
  for done,i in enumerate(pool.imap_unordered(one_slice,range(M//2+1)),1):
   if done%max(1,M//20)==0 or done==M//2+1:
    tmp.flush();print('PARALLEL',K,done,M//2+1,round(time.time()-start,2),flush=True)
 tmp.flush();G.clear();del z,ph,sq,pw,ids,sqvw,base
 outpath=ROOT/f'parallel_coeff4_K{K}_o{oversample}_r{rc}.npy';out=np.lib.format.open_memmap(outpath,mode='w+',dtype=float,shape=(6,K,K,K))
 for field in range(6):
  for lo in range(0,K,8):
   hi=min(lo+8,K);a=irfft(np.conj(tmp[field,:,lo:hi,:]),n=M,axis=0,workers=workers)[:K]
   sc=np.exp(rc*(np.arange(K)[:,None,None]+np.arange(lo,hi)[None,:,None]+np.arange(K)[None,None,:])/K)
   out[field,:,lo:hi,:]=a*sc
  out.flush();print('FFT U',K,field,round(time.time()-start,2),flush=True)
 del tmp,out;fn.unlink()
 meta=dict(K=K,M=M,oversample=oversample,radius_cost=rc,radius=r,workers=workers,elapsed=time.time()-start,method='parallel_phase_lookup_conjugate_half_grid')
 outpath.with_suffix('.json').write_text(json.dumps(meta,indent=2));return str(outpath),meta
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=384);p.add_argument('--oversample',type=int,default=4);p.add_argument('--radius-cost',type=float,default=4.5);p.add_argument('--workers',type=int,default=3);a=p.parse_args();print(compute(a.size+1,a.oversample,a.radius_cost,a.workers),flush=True)
