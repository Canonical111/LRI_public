#!/usr/bin/env python3
"""Local thread scaling of the final production default; no physics production."""
import argparse,json,os,statistics,subprocess
from pathlib import Path
from common import ROOT,load,dump,digest
from prepare_benchmarks import prepare_benchmarks
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--repeats',type=int,default=3);a=p.parse_args()
P=a.output.resolve();P.mkdir(parents=True,exist_ok=False);fixtures=prepare_benchmarks();exe=ROOT/'bin/c7d3_gmp';records=[];agreement=[]
for sector in ('free','power'):
    outputs={}
    for threads in (1,2,4):
        wall=[];integ=[];rss=[]
        for rep in range(a.repeats):
            stem=P/f'{sector}_t{threads}_r{rep}';out=stem.with_suffix('.json');tim=stem.with_suffix('.time');log=stem.with_suffix('.log')
            cmd=list(map(str,[exe,ROOT/f'reference/inputs/{sector}',ROOT/'inputs/gamma_d3_7.txt',ROOT/f'benchmarks/fixtures/{sector}_L7.net',ROOT/f'benchmarks/fixtures/{sector}_L7.tasks',out,5461981,0,.8,threads,'compensated','-']))
            import time
            t=time.perf_counter();c=subprocess.run(['/usr/bin/time','-v','-o',str(tim)]+cmd,capture_output=True,text=True,check=True,env={**os.environ,'OMP_PROC_BIND':'close','OMP_PLACES':'cores'})
            wall.append(time.perf_counter()-t);log.write_text(c.stderr);d=load(out);outputs[threads]=d
            integ.append(d['integration_seconds']);rss.append(int(next(l.rsplit(':',1)[1]for l in tim.read_text().splitlines()if'Maximum resident'in l))/1024)
        records.append(dict(sector=sector,L=7,threads=threads,samples=sum(r['end']-r['begin']for r in d['rows']),median_wall_s=statistics.median(wall),median_integration_s=statistics.median(integ),max_rss_mib=max(rss),wall_s=wall,integration_s=integ,command=cmd));print(records[-1],flush=True)
    scientific=lambda d:[{k:v for k,v in row.items()if k!='seconds'}for row in d['rows']]
    assert scientific(outputs[1])==scientific(outputs[2])==scientific(outputs[4])
    agreement.append(dict(sector=sector,threads=[1,2,4],scientific_rows_identical=True))
dump(P/'production_scaling.json',dict(records=records,checks=agreement,build=json.loads(subprocess.check_output([exe,'--describe'],text=True)),kernel_sha256=digest(ROOT/'src/kernel.hpp'),native_source_sha256=digest(ROOT/'src/c7d3_integrate.cpp'),cpu_quota=Path('/sys/fs/cgroup/cpu.max').read_text().strip()if Path('/sys/fs/cgroup/cpu.max').exists()else None,scope='Actual final production default, selected 16 costly graphs/sector, 16384 samples/sector. Local thread scaling, not a new kernel speedup or multi-node result.'))
