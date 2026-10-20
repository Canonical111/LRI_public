#!/usr/bin/env python3
"""Fresh matched-sample timings; independent of the physical estimator."""
from __future__ import annotations
import argparse,json,os,re,shlex,statistics,struct,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np
from common import ROOT,dump,load,cxx_command
sys.path.insert(0,str(ROOT/'tests'))
from validate import build_baseline
from production import make_net

def timed(cmd,log:Path,threads:int):
    with log.open('w')as f:subprocess.run(['/usr/bin/time','-v']+list(map(str,cmd)),stdout=f,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OMP_NUM_THREADS=str(threads),OMP_PROC_BIND='true',OMP_PLACES='cores'))
    text=log.read_text();rss=int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',text).group(1));wall=re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)',text).group(1);parts=list(map(float,wall.split(':')));seconds=sum(x*60**i for i,x in enumerate(parts[::-1]));return {'wall_seconds':seconds,'rss_KiB':rss}

def cpu_quota():
    """CPU quota if a cgroup file is visible (v2 cpu.max, else v1 cfs quota/period), else None."""
    for path in ('/sys/fs/cgroup/cpu.max',):
        try:return Path(path).read_text().strip()
        except OSError:pass
    try:return Path('/sys/fs/cgroup/cpu/cpu.cfs_quota_us').read_text().strip()+' '+Path('/sys/fs/cgroup/cpu/cpu.cfs_period_us').read_text().strip()
    except OSError:return None

def cpu_model():
    try:return next(l.split(':',1)[1].strip()for l in Path('/proc/cpuinfo').read_text().splitlines()if l.startswith('model name'))
    except (OSError,StopIteration):return None

def run(out:Path):
    out=out.resolve()
    if out.exists():raise FileExistsError('Use a new benchmark directory; the shipped benchmarks/ evidence is never rewritten')
    out.mkdir(parents=True);baseline=out/'baseline';build_baseline(baseline)
    R=ROOT/'reference';B=R/'baseline_previous';inv=load(ROOT/'inputs/inventory.json');records=[]
    workloads=[('five_loop',5,12,2048),('six_loop',6,16,4096)]
    for name,L,ng,n in workloads:
        rows=inv[str(L)];selected={r['id']for r in sorted(rows,key=lambda r:(-r['additions'],r['id']))[:ng]};net=out/f'{name}.net';
        if not net.exists():make_net(net,4,4*L-1,60,81632+L)
        counts=out/f'{name}.counts';counts.write_text(str(len(rows))+'\n'+''.join(f'{r["id"]} {n if r["id"]in selected else 0}\n'for r in rows));tasks=[(len(selected)*rep+i,rep,g,0,n,n)for rep in range(4)for i,g in enumerate(sorted(selected))];tf=out/f'{name}.tasks';tf.write_text(f'C6TASKS1 {L} {len(tasks)}\n'+''.join(' '.join(map(str,t))+'\n'for t in tasks));rate=B/'inputs/d2_full_rates_c6.txt'if L==6 else B/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{L}.txt'
        oldout=out/f'{name}_old.json';newout=out/f'{name}_new.json';seed=9128077
        old=[baseline,B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt',rate,counts,seed,net,oldout,ROOT/'inputs/gamma_d2.txt','rqmc',0,0,1]
        new=[ROOT/'bin/c6_integrate',ROOT/'inputs/graphs',ROOT/'inputs/gamma_d2.txt',net,tf,newout,seed,0,1,1,'compensated','-']
        raw={};values={}
        for label,cmd in [('reference_1',old),('optimized_1',new)]+([('optimized_2',new.copy()),('optimized_4',new.copy())]if L==6 else[]):
            threads=int(label.split('_')[-1]);runs=[]
            if label.startswith('optimized'):cmd[9]=threads
            for k in range(3):
                r=timed(cmd,out/f'{name}_{label}_{k}.log',threads);d=load(newout if label.startswith('optimized')else oldout);r['integration_seconds']=d.get('integration_seconds',d.get('seconds'));runs.append(r)
            raw[label]={'median_wall_seconds':statistics.median(r['wall_seconds']for r in runs),'median_integration_seconds':statistics.median(r['integration_seconds']for r in runs),'max_rss_KiB':max(r['rss_KiB']for r in runs),'runs':runs}
        olddata=json.loads(oldout.read_text(),parse_float=str);newdata=load(newout);indices={g:i for i,g in enumerate(olddata['graph_ids'])};er=0
        for row in newdata['rows']:
            a=np.array(olddata['graph_batches'][row['rep']][indices[row['graph']]],np.longdouble);b=np.array(row['values'],np.longdouble);er=max(er,float(max(abs(a-b)/np.maximum(1,abs(a)))))
        assert er<1e-13
        r={'name':name,'L':L,'graphs_sampled':ng,'graphs_in_reference_load':len(rows),'points':4*ng*n,'quad_fallbacks_reference':olddata['quad_fallbacks'],'quad_fallbacks_optimized':sum(x['quad']for x in newdata['rows']),'mp_fallbacks_reference':olddata['mp_fallbacks'],'mp_fallbacks_optimized':sum(x['mp']for x in newdata['rows']),'max_normalized_jet_difference':er,'timings':raw};r['one_thread_wall_speedup']=raw['reference_1']['median_wall_seconds']/raw['optimized_1']['median_wall_seconds'];r['one_thread_kernel_speedup']=raw['reference_1']['median_integration_seconds']/raw['optimized_1']['median_integration_seconds'];records.append(r);print(name,r['one_thread_wall_speedup'],r['one_thread_kernel_speedup'],flush=True)
    result={'scope':'Fresh matched seeds, directions, graphs, counts, strict build; median of 3; no multi-node claim. Reference loads whole inventory, optimized loads selected graphs.','hardware':{'cpu_quota':cpu_quota(),'slurm_cpus_per_task':os.environ.get('SLURM_CPUS_PER_TASK'),'machine':os.uname().machine,'cpu_model':cpu_model(),'cxx':shlex.split(os.environ.get('CXX','g++')),'compiler':subprocess.check_output([*shlex.split(os.environ.get('CXX','g++')),'--version'],text=True).splitlines()[0]},'records':records};dump(out/'benchmarks.json',result)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True,help='new directory (never the shipped benchmarks/matched)');a=p.parse_args();run(a.output)
