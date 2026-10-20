#!/usr/bin/env python3
"""Matched-sample kernel benchmarks. These are not end-to-end production timings."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, statistics, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from workloads import files
import toolchain

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--repeats',type=int,default=3);p.add_argument('--scaling',action='store_true');p.add_argument('--resume',action='store_true');a=p.parse_args();out=a.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()) and not a.resume:raise FileExistsError('Use an empty benchmark directory or --resume')
    if not (ROOT/'bin/reference_power').exists():subprocess.run([sys.executable,ROOT/'tools/build_reference.py'],check=True)
    inputs=ROOT/'reference/inputs';records=[]
    workloads=[('continuous',7,'qmc',1024,4,0),('power_degree1',7,'power',256,1,1),('power_degree3',7,'power',2,1,3),('power_degree6',7,'power',2,1,6)]
    data={name:files(out/name,inputs,L,mode,n,B) for name,L,mode,n,B,N in workloads}
    def run(name,L,mode,n,B,N,impl,threads,repeat):
        w=data[name];tag=f'{name}_{impl}_t{threads}_{repeat}';dest=out/(tag+'.json');timing=out/(tag+'.time')
        if impl=='reference':
            if mode=='qmc':cmd=[ROOT/'bin/reference_qmc',inputs,L,n,B,41927510,w['net'],dest,'.8','free',w['counts']]
            else:cmd=[ROOT/'bin/reference_power',inputs,L,N,n,B,41927510,dest,'power','.8',w['counts']]
        else:
            cmd=[ROOT/'bin/c7_integrate','--mode',mode,'--inputs',inputs,'--L',L,'--tasks',w['tasks'],'--seed',41927510,'--rate','.8','--output',dest,'--threads',threads,'--tile',128]
            cmd+=['--net',w['net']] if mode=='qmc' else ['--degree',N]
        if not (a.resume and dest.exists() and timing.exists() and timing.stat().st_size):
          with (out/(tag+'.log')).open('w') as f:
            subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(timing),*map(str,cmd)],check=True,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_NUM_THREADS=str(threads),OMP_DYNAMIC='FALSE',OPENBLAS_NUM_THREADS='1'))
        wall,rss=map(float,timing.read_text().split());d=json.loads(dest.read_text());secs=d.get('integration_seconds',d.get('seconds'))
        records.append(dict(workload=name,implementation=impl,threads=threads,repeat=repeat,wall_seconds=wall,integration_seconds=secs,peak_rss_kib=int(rss),samples=n*B*len(w['info']['selected_graphs']),output=dest.name,command=list(map(str,cmd))))
        print(tag,wall,'s',rss,'KiB',flush=True)
    for repeat in range(a.repeats):
        for args in workloads:
            for impl in (['reference','optimized'] if repeat%2==0 else ['optimized','reference']):run(*args,impl,1,repeat)
    if a.scaling:
        for args in [workloads[0],workloads[3]]:
            for nt in (2,4):
                for repeat in range(a.repeats):run(*args,'optimized',nt,repeat)
    summaries=[]
    for args in workloads:
        name=args[0];d={}
        for impl in ('reference','optimized'):
            xs=[x for x in records if x['workload']==name and x['threads']==1 and x['implementation']==impl]
            d[impl]={k:statistics.median(x[k] for x in xs) for k in ['wall_seconds','integration_seconds','peak_rss_kib']}
        d['workload']=name;d['wall_speedup']=d['reference']['wall_seconds']/d['optimized']['wall_seconds'];d['integration_speedup']=d['reference']['integration_seconds']/d['optimized']['integration_seconds'];d['rss_ratio']=d['reference']['peak_rss_kib']/d['optimized']['peak_rss_kib'];summaries.append(d)
    scaling=[]
    for name in ('continuous','power_degree6'):
        ts={}
        for nt in (1,2,4):
            xs=[x['integration_seconds'] for x in records if x['workload']==name and x['implementation']=='optimized' and x['threads']==nt]
            if xs:ts[nt]=statistics.median(xs)
        scaling.append({'workload':name,'median_integration_seconds':ts,'speedup_vs_one':{k:ts[1]/v for k,v in ts.items()}})
    cpu=subprocess.check_output(['lscpu'],text=True);(out/'lscpu.txt').write_text(cpu)
    report={'scope':'matched-sample micro/meso workloads from 12 actual graphs spanning forest term-count quantiles; not whole-production speedups; no multi-node test','repeats':a.repeats,'hardware':{'platform':platform.platform(),'cpu_max':Path('/sys/fs/cgroup/cpu.max').read_text().strip() if Path('/sys/fs/cgroup/cpu.max').exists() else None,'memory_max':Path('/sys/fs/cgroup/memory.max').read_text().strip() if Path('/sys/fs/cgroup/memory.max').exists() else None},'compiler':toolchain.compiler_version(),'optimized_binary_sha256':hashlib.sha256((ROOT/'bin/c7_integrate').read_bytes()).hexdigest(),'summary':summaries,'local_scaling':scaling,'runs':records}
    (out/'benchmarks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
