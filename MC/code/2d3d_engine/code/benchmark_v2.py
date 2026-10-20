#!/usr/bin/env python3
"""Serial throughput/RSS benchmark, NOT an equilibrated physics run."""
from pathlib import Path
import argparse,csv,hashlib,json,platform,subprocess,time
from kernel import save_kernel
ROOT=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--dim',type=int,choices=[2,3],required=True);p.add_argument('--s',type=float,required=True)
 p.add_argument('--beta',type=float,required=True);p.add_argument('--sizes',type=int,nargs='+',required=True)
 p.add_argument('--engines',nargs='+',default=['reference','flat','hybrid'])
 p.add_argument('--seconds-per-case',type=float,default=3);p.add_argument('--repeats',type=int,default=3)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--core-radius',type=int,default=16)
 p.add_argument('--near-radius',type=int,default=1);p.add_argument('--record',choices=['basic','extended'],default='basic')
 a=p.parse_args()
 if a.repeats<1 or a.seconds_per_case<=0:p.error('positive repeats and duration required')
 if 'reference' in a.engines and a.record!='basic':p.error('matched reference comparisons require basic records')
 if any(e not in ('reference','flat','core','lattice','hybrid') for e in a.engines):p.error('unknown engine')
 a.out.mkdir(parents=True,exist_ok=True);rows=[]
 for L in a.sizes:
  n=L**a.dim
  if any(e in ('reference','flat','core') for e in a.engines):
   kp=a.out/f'J_d{a.dim}_L{L}.bin'
   if not kp.exists():
    start=time.perf_counter();save_kernel(kp,a.dim,L,a.s)
    print(f'kernel L={L}: {time.perf_counter()-start:.3f}s',flush=True)
  for rep in range(a.repeats):
   for e in a.engines[::(-1 if rep%2 else 1)]:
    dr=a.out/f'L{L}_{e}_{rep}';dr.mkdir(exist_ok=True)
    count=max(16,int(a.seconds_per_case/(max(n,1)*4e-8)));warmup=min(128,max(4,count//10))
    binary=ROOT/'bin'/('lri_reference' if e=='reference' else 'lri_mc')
    cmd=[str(binary),'--dim',str(a.dim),'--length',str(L),'--beta',str(a.beta),'--seed',str(819731+rep),
         '--warmup',str(warmup),'--measurements',str(count),'--out',str(dr)]
    if e=='reference':cmd+=['--couplings',str(kp)]
    else:
     cmd+=['--sampler',e,'--s',str(a.s),'--record',a.record,'--core-radius',str(a.core_radius),'--near-radius',str(a.near_radius)]
     if e in ('flat','core'):cmd+=['--couplings',str(kp)]
    tf=dr/'time.txt'
    with (dr/'stdout.txt').open('w') as f:subprocess.run(['/usr/bin/time','-f','%e %M %U %S','-o',str(tf)]+cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    z=json.loads((dr/'DONE.json').read_text());tim=tf.read_text().split();seconds=z['last_invocation_seconds'];sweeps=z['last_invocation_sweeps']
    row=dict(d=a.dim,s=a.s,L=L,N=n,engine=e,repeat=rep,seconds=seconds,sweeps=sweeps,
             ms_per_sweep=1e3*seconds/sweeps,ns_per_spin_sweep=1e9*seconds/sweeps/n,
             peak_RSS_MiB=int(tim[1])/1024,process_wall_seconds=float(tim[0]),record=a.record,
             binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    rows.append(row);print(json.dumps(row),flush=True)
    (a.out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    with (a.out/'results.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 env={'platform':platform.platform(),'cpuinfo':Path('/proc/cpuinfo').read_text().split('\n')[:30],
      'cpu_quota':Path('/sys/fs/cgroup/cpu.max').read_text() if Path('/sys/fs/cgroup/cpu.max').exists() else None,
      'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
      'note':'Short throughput tests, not equilibrium or finite-size precision measurements.'}
 (a.out/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
if __name__=='__main__':main()
