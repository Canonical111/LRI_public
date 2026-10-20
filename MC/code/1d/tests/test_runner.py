#!/usr/bin/env python3
"""End-to-end tests: exact small ring, derivatives/reweighting, deterministic resume."""
import hashlib, json, os, signal, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from prepare import couplings
from analyze import collect_group
BIN=ROOT/'bin/lri_mc'

def run(base,n=64,s=.8,beta=.42,measurements=5000,warmup=700,stop=0,seed=739157):
    c=base.parent/f'J_{n}_{s}.bin'
    if not c.exists():couplings(n,s).tofile(c)
    cmd=[str(BIN),'--n',str(n),'--beta',str(beta),'--couplings',str(c),
         '--measurements',str(measurements),'--warmup',str(warmup),'--seed',str(seed),
         '--out',str(base),'--stop-after',str(stop),'--checkpoint-seconds','600']
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode not in (0,75):raise RuntimeError(p.stderr)
    return p,cmd

def main():
  report={}
  with tempfile.TemporaryDirectory(prefix='lri-tests-') as temp:
    tmp=Path(temp)
    run(tmp/'whole');run(tmp/'split',stop=333) # stop inside warmup
    run(tmp/'split',stop=1400) # stop during measurements
    with (tmp/'split/samples.bin').open('ab') as f:f.write(b'x'*77) # crash tail to truncate
    run(tmp/'split')
    whole=(tmp/'whole/samples.bin').read_bytes();split=(tmp/'split/samples.bin').read_bytes()
    assert whole==split,'restart trajectory differs'
    run(tmp/'extend',measurements=2000);run(tmp/'extend',measurements=5000)
    assert (tmp/'extend/samples.bin').read_bytes()==whole,'extension trajectory differs'
    report['restart_bitwise_equal']=True;report['extension_bitwise_equal']=True;report['crash_tail_recovery']=True
    # Actual signal delivery and simultaneous-writer rejection.
    _,cmd=run(tmp/'signal',n=256,measurements=10000000,stop=1)
    cmd[cmd.index('--stop-after')+1]='0'
    active=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    time.sleep(.12)
    other=subprocess.run(cmd,capture_output=True,text=True)
    assert other.returncode==1 and 'lock' in other.stderr,'concurrent writer not rejected'
    active.send_signal(signal.SIGUSR1);out,err=active.communicate(timeout=20)
    assert active.returncode==75,(out,err)
    status=json.loads((tmp/'signal/status.json').read_text())
    assert (tmp/'signal/samples.bin').stat().st_size==32*status['measurements_done']
    report['signal_checkpoint']=True;report['concurrent_writer_rejected']=True
    # Independent exact enumeration on N=8; compare original and reweighted beta.
    n=8;s=.8;beta=.42;j=couplings(n,s)
    assert np.all(j[1:]==j[:0:-1]);states=2*((np.arange(1<<n)[:,None]>>np.arange(n))&1)-1
    jm=j[(np.arange(n)[:,None]-np.arange(n))%n]
    e=-np.einsum('bi,ij,bj->b',states,jm,states)/2;m=states.mean(axis=1)
    run(tmp/'exact',n=n,s=s,beta=beta,measurements=600000,warmup=5000,seed=61304219)
    task=dict(N=n,s=s,beta=beta,raw=str(tmp/'exact/samples.bin'),rows=600000,id=0,replica=0,initialization='hot')
    rows=[]
    for target in [.41,.42,.43]:
        info,blocks,_=collect_group([task],2000,target,False)
        w=np.exp(-target*e);w/=w.sum();e0=w@e;ve=w@(e*e)-e0*e0
        a2=w@(m*m);a4=w@(m**4)
        d2=-(w@(m*m*e)-a2*e0);d4=-(w@(m**4*e)-a4*e0)
        dd2=w@(m*m*(e-e0)**2)-a2*ve;dd4=w@(m**4*(e-e0)**2)-a4*ve
        y=n**(1-s)*a2;q=a4/(3*a2*a2)
        dl=d4/a4-2*d2/a2;ddl=dd4/a4-(d4/a4)**2-2*(dd2/a2-(d2/a2)**2)
        exact=np.array([y,n**(1-s)*d2,n**(1-s)*dd2,1-q,-q*dl,-q*(ddl+dl*dl)])
        mc=np.array(info['data']);err=np.array(info['stderr']);z=(mc-exact)/err
        assert np.all(np.abs(z)<6),f'exact enumeration discrepancy: {z}'
        exact_k=target*(n*j.sum()/2-e0)
        if target==beta:
            bs=blocks[:,0,1];ke=bs.std(ddof=1)/np.sqrt(len(bs));assert abs(info['K_mean']-exact_k)<6*ke
        rows.append(dict(beta=target,exact=exact.tolist(),MC=mc.tolist(),standard_error=err.tolist(),z=z.tolist(),exact_mean_K=float(exact_k),MC_mean_K=info['K_mean']))
    report['exact_enumeration_and_reweighting']=rows
    a=np.fromfile(tmp/'exact/samples.bin',dtype='<f8').reshape(-1,4)
    assert np.all(a[:,0]>=0) and np.all(a[:,1]>=1/n) and np.all(a[:,2]+1e-14>=a[:,1]**2) and np.all(a[:,2]<=1+1e-14)
    report['cluster_moment_invariants']=True
  (ROOT/'tests/test_results.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report,indent=2))
if __name__=='__main__':main()
