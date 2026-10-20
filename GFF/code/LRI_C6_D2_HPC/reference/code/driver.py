"""Frozen sampling experiments. Every output tag is single-use."""
from pathlib import Path
import sys,json,subprocess,time,argparse
import numpy as np
W=Path(__file__).resolve().parents[1]
B=W/'baseline_previous'
sys.path.insert(0,str(B/'code'))
from run_precision import make_net,graph_ids

def run(tag,d,L,counts,replicates=16,seed=8134917,layout=1,rate=1.0,anti=False,method='rqmc',reference=False,bits=52):
    out=W/f'records/{tag}_d{d}_L{L}.json'
    if out.exists(): raise RuntimeError('refusing overwrite '+str(out))
    source=B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt'
    rates=(B/f'baseline/lri_C6_d3_complete_update/inputs/rates_L{L}_0.8.txt') if d==3 else (B/f'inputs/d2_full_rates_c6.txt' if L==6 else B/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{L}.txt')
    _,rows=graph_ids(source)
    if isinstance(counts,dict): counts=np.array([int(counts.get(str(r[0]),counts.get(r[0],0))) for r in rows])
    counts=np.array(counts,dtype=np.int64)
    assert len(counts)==len(rows) and np.all(counts>=0)
    cf=W/f'inputs/{tag}_d{d}_L{L}_counts.txt';cf.write_text(str(len(rows))+'\n'+'\n'.join(f'{r[0]} {n}' for r,n in zip(rows,counts))+'\n')
    nf=W/f'inputs/{tag}_d{d}_L{L}_net.bin'
    nch=make_net(nf,replicates,2*L if layout==2 else 4*L-1,bits,seed+18743*L)
    cmd=[str(W/f'code/{"reference" if reference else "experiment"}_d{d}'),str(source),str(rates),str(cf),str(seed+1279*L),str(nf),str(out),str(B/f'inputs/gamma_d{d}.txt'),method,str(layout),str(int(anti)),str(rate)]
    t=time.time()
    with (W/f'logs/{tag}_d{d}_L{L}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    manifest={'tag':tag,'dimension':d,'L':L,'command':cmd,'seconds':time.time()-t,'net_check':nch,'counts':counts.tolist(),'replicates':replicates,'seed':seed,'layout':layout,'rate_factor':rate,'antithetic':anti,'method':method,'reference_kernel':reference}
    (W/f'inputs/{tag}_d{d}_L{L}_manifest.json').write_text(json.dumps(manifest,indent=2))
    raw=json.load(open(out));y=np.array(raw['batches'])
    if L==6: print(tag,d,L,'N',raw['N'],'seconds',raw['seconds'],'mean C6part',float((y@np.array([-1,3])/2187).mean()),'SE',float((y@np.array([-1,3])/2187).std(ddof=1)/np.sqrt(len(y))),flush=True)
    else:print(tag,d,L,'N',raw['N'],'seconds',raw['seconds'],flush=True)
    return raw

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--d',type=int,required=True);p.add_argument('--L',type=int,default=6);p.add_argument('--counts',required=True);p.add_argument('--reps',type=int,default=16);p.add_argument('--seed',type=int,default=8134917);p.add_argument('--layout',type=int,default=1);p.add_argument('--rate',type=float,default=1);p.add_argument('--anti',action='store_true');p.add_argument('--method',default='rqmc');p.add_argument('--reference',action='store_true');a=p.parse_args()
 run(a.tag,a.d,a.L,json.load(open(a.counts)),a.reps,a.seed,a.layout,a.rate,a.anti,a.method,a.reference)
