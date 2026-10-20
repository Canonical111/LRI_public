#!/usr/bin/env python3
"""Fresh matched-sample kernel benchmarks, with exact commands and raw logs."""
from pathlib import Path
import argparse,json,os,statistics,struct,subprocess,sys,time,platform,shutil
from decimal import Decimal as D
from common import ROOT,dump,load,digest

def build_reference(path):
    src=ROOT/'reference/src/c7d3_integrate.cpp'
    subprocess.run(['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math','-DC7_USE_GMP',str(src),'-lquadmath','-lgmp','-o',str(path)],check=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--repeats',type=int,default=3);a=ap.parse_args();P=a.output.resolve();P.mkdir(parents=True,exist_ok=False);build_reference(P/'reference')
    trial=P/'quotient_candidate';trial.mkdir();shutil.copyfile(ROOT/'src/c7d3_integrate.cpp',trial/'c7d3_integrate.cpp');shutil.copyfile(ROOT/'experiments/quotient_reuse/kernel.hpp',trial/'kernel.hpp')
    candidate=trial/'worker'
    subprocess.run(['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math','-DC7_USE_GMP',str(trial/'c7d3_integrate.cpp'),'-lquadmath','-lgmp','-o',str(candidate)],check=True)
    from prepare_benchmarks import prepare_benchmarks
    fixtures=prepare_benchmarks();profile=ROOT/'benchmarks/fixtures';records=[];comparisons=[]
    for sector in ('free','power'):
      for L in (6,7):
        inv=ROOT/'reference/inputs'/sector
        ids=fixtures['records'][f'{sector}_L{L}']['ids'];n=4096 if L==6 else 512
        nf=P/f'{sector}_L{L}.net';nf.write_bytes((profile/f'{sector}_L{L}.net').read_bytes())
        tasks=P/f'{sector}_L{L}.tasks';tasks.write_text(f'C7D3TASKS1 {L} {2*len(ids)}\n'+''.join(f'{i} {r} {g} 0 {n} {n}\n'for i,(r,g)in enumerate((r,g)for r in range(2)for g in ids)))
        outputs={}
        variants=[('reference',P/'reference',1),('gmp',candidate,1)]
        if L==7:variants += [('gmp',candidate,2),('gmp',candidate,4)]
        for tag,exe,threads in variants:
            times=[];memory=[];integrations=[];loads=[]
            for rep in range(a.repeats):
                stem=P/f'{sector}_L{L}_{tag}_t{threads}_r{rep}';out=stem.with_suffix('.json');mem=stem.with_suffix('.time');log=stem.with_suffix('.log')
                cmd=list(map(str,[exe,inv,ROOT/'inputs/gamma_d3_7.txt',nf,tasks,out,5461981,0,.8,threads,'compensated','-']))
                before=time.perf_counter();cp=subprocess.run(['/usr/bin/time','-v','-o',str(mem)]+cmd,capture_output=True,text=True,check=True,env=dict(os.environ,OMP_PROC_BIND='close',OMP_PLACES='cores'))
                times.append(time.perf_counter()-before);log.write_text(cp.stderr);data=load(out);memory.append(int(next(l.rsplit(':',1)[1]for l in mem.read_text().splitlines()if'Maximum resident'in l))/1024);integrations.append(data['integration_seconds']);loads.append(data['load_seconds']);outputs[(tag,threads)]=data
                print(sector,L,tag,threads,rep,'wall',times[-1],flush=True)
            records.append(dict(sector=sector,L=L,variant=tag,threads=threads,graphs=len(ids),samples=n*len(ids)*2,median_wall_s=statistics.median(times),median_integration_s=statistics.median(integrations),median_load_s=statistics.median(loads),max_rss_mib=max(memory),wall_s=times,rss_mib=memory,command=cmd))
        ref=outputs[('reference',1)]
        for (tag,t),dat in outputs.items():
            if tag=='reference':continue
            error=max(abs(D(x)-D(y))/max(D(1),abs(D(x)))for r,s in zip(ref['rows'],dat['rows'])for x,y in zip(r['values'],s['values']))
            counts_equal=all(r[k]==s[k]for r,s in zip(ref['rows'],dat['rows'])for k in ('quad','mp'))
            if error>D('1e-12')or not counts_equal:raise AssertionError((sector,L,tag,error,counts_equal))
            comparisons.append(dict(sector=sector,L=L,backend=tag,threads=t,normalized_error=str(error),fallback_counts_match=counts_equal))
    env=dict(platform=platform.platform(),python=platform.python_version(),compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],cpu_quota=Path('/sys/fs/cgroup/cpu.max').read_text().strip()if Path('/sys/fs/cgroup/cpu.max').exists()else None,processor_count=os.cpu_count())
    dump(P/'benchmarks.json',dict(records=records,comparisons=comparisons,environment=env,scope='Selected expensive classes; matched points. Local timings, NOT a multi-node measurement.'))
if __name__=='__main__':main()
