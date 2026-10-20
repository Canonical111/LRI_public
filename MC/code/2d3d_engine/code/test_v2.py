#!/usr/bin/env python3
"""Exact-enumeration, bitwise-restart and extended-moment regression tests."""
from pathlib import Path
import json, subprocess, tempfile, hashlib, itertools, sys, time
import numpy as np
from kernel import couplings
ROOT=Path(__file__).resolve().parent

def exact(d,L,s,beta,nn=0):
    N=L**d;j=couplings(d,L,s)
    for a in range(d):j[L**a]+=nn;j[(L-1)*L**a]+=nn
    sites=np.arange(N);coord=np.array([(sites//L**a)%L for a in range(d)]).T
    r=(coord[:,None,:]-coord[None,:,:])%L;idx=r@(L**np.arange(d));J=j[idx]
    spin=2*((np.arange(1<<N)[:,None]>>np.arange(N))&1)-1
    E=.5*np.einsum('bi,ij,bj->b',spin,J,spin,optimize=True);m=spin.mean(1)
    w=np.exp(beta*(E-E.max()));w/=w.sum();mu=beta*(N*j.sum()/2+E)
    vals=[float(w@(m**k)) for k in [2,4,6,8]]
    deriv=[float(w@(m**k*E)-(w@(m**k))*(w@E)) for k in [2,4,6,8]]
    return np.array(vals+[w@mu]+deriv)

def features(a,beta):
    m=a[:,[1,2,4,5]];k=a[:,0];q=k-k.mean()
    return np.r_[m.mean(0),k.mean(),np.mean(m*q[:,None],axis=0)/beta]

def jack(a,beta,block=1000):
    B=len(a)//block;parts=a[:B*block].reshape(B,block,8)
    k0=a[:,0].mean();m=parts[:,:,[1,2,4,5]];q=parts[:,:,0]-k0
    F=np.concatenate([m.mean(1),q.mean(1)[:,None],(m*q[:,:,None]).mean(1)],axis=1)
    def transform(v):return np.concatenate([v[...,:4],(v[...,4]+k0)[...,None],(v[...,5:]-v[...,:4]*v[...,4,None])/beta],axis=-1)
    mean=F.mean(0);val=transform(mean);leave=transform((B*mean-F)/(B-1));cov=(B-1)/B*np.cov(leave,rowvar=False,ddof=0)*B
    return val,np.sqrt(np.diag(cov))

def main():
    out=ROOT.parent/'tests';out.mkdir(exist_ok=True);report={}
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)
        def run(path,extra=[],dim=2,L=4,s=1.4,beta=.18,seed=12345,count=300000,nn=0,binary='lri_mc'):
            cmd=[str(ROOT/'bin'/binary),'--dim',str(dim),'--length',str(L),'--s',str(s),'--beta',str(beta),
                 '--sampler','hybrid','--record','extended','--warmup','10000','--measurements',str(count),
                 '--seed',str(seed),'--out',str(path),'--nn-extra',str(nn)]+extra
            return subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        # Each physical comparison uses a fresh seed, no acceptance tuning.
        for d,L,s,beta,nn in [(2,4,1.4,.18,0),(3,2,1.8,.105,0),(2,4,1.4,.155,.2)]:
            name=f'exact_d{d}_L{L}_nn{nn:g}';p=tmp/name
            r=run(p,dim=d,L=L,s=s,beta=beta,nn=nn,seed=382197+d+int(nn*1000));assert r.returncode==0,r.stderr
            a=np.fromfile(p/'samples.bin',dtype='<f8').reshape(-1,8);v,se=jack(a,beta);ex=exact(d,L,s,beta,nn);z=(v-ex)/se
            report[name]={'labels':['m2','m4','m6','m8','K','dm2','dm4','dm6','dm8'],'exact':ex.tolist(),'MC':v.tolist(),'stderr':se.tolist(),'z':z.tolist()}
            assert np.all(np.abs(z)<5),report[name]
        # Restart in warm-up, restart in measurement, discard uncommitted data,
        # extension. Cached std::poisson states of EVERY near group are saved.
        full=tmp/'full';split=tmp/'split'
        assert run(full,count=700).returncode==0
        assert run(split,extra=['--stop-after','317'],count=400).returncode==75
        assert run(split,extra=['--stop-after','10031'],count=400).returncode==75
        with (split/'samples.bin').open('ab') as f:f.write(b'12345678'*24)
        assert run(split,count=400).returncode==0
        assert run(split,count=700).returncode==0
        assert (full/'samples.bin').read_bytes()==(split/'samples.bin').read_bytes()
        report['restart_and_extension_bitwise']=True
        # Spatial lane operation for all sites/displacements on small tori.
        for d,L in [(2,4),(3,4),(3,8)]:
            n=L**d;b=L.bit_length()-1;M=L-1;ev=M|((M<<(2*b)) if d==3 else 0);odd=M<<b
            for x in range(n):
                r=np.arange(n,dtype=np.uint64);y=(((x&ev)+(r&ev))&ev)|(((x&odd)+(r&odd))&odd)
                check=sum((((x>>(a*b))+(r>>(a*b)))&M)<<(a*b) for a in range(d))
                assert np.all(y==check)
        report['coordinatewise_periodic_addition']=True
    report['source_sha256']=hashlib.sha256((ROOT/'src/lri_mc.cpp').read_bytes()).hexdigest()
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
