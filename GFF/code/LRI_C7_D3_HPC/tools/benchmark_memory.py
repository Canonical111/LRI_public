#!/usr/bin/env python3
"""Matched all-power-seven-loop points: monolithic reference vs bounded blocks.
This is an execution/memory test, not a usable integration estimate.
"""
from pathlib import Path
import argparse,json,subprocess,time
from decimal import Decimal as D
from common import ROOT,load,dump
from prepare_benchmarks import prepare_benchmarks
prepare_benchmarks()
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();P=args.output.resolve();P.mkdir(parents=True,exist_ok=False);inv=load(ROOT/'inputs/inventory.json')['power']['7'];ids=[r['id']for r in inv];rows=[(i,r,g,0,1,1)for i,(r,g)in enumerate((r,g)for r in range(2)for g in ids)]
net=ROOT/'benchmarks/fixtures/power_L7.net';source=ROOT/'reference/inputs/power';baseline=P/'reference';new=ROOT/'bin/c7d3_gmp'
from benchmark import build_reference
build_reference(baseline)
def execute(exe,items,name):
 tasks=P/f'{name}.tasks';tasks.write_text(f'C7D3TASKS1 7 {len(items)}\n'+''.join(' '.join(map(str,r))+'\n'for r in items));dest=P/f'{name}.json';tim=P/f'{name}.time'
 cmd=list(map(str,[exe,source,ROOT/'inputs/gamma_d3_7.txt',net,tasks,dest,5461981,0,.8,1,'compensated','-']))
 cp=subprocess.run(['/usr/bin/time','-v','-o',str(tim)]+cmd,capture_output=True,text=True,check=True);(P/f'{name}.log').write_text(cp.stderr)
 rss=int(next(l.rsplit(':',1)[1]for l in tim.read_text().splitlines()if'Maximum resident'in l))/1024
 return load(dest),rss
base,rss0=execute(baseline,rows,'reference_full');parts=[];rss=[]
for i in range(0,len(rows),32):
 d,r=execute(new,rows[i:i+32],f'optimized_{i:04d}');parts+=d['rows'];rss.append(r)
e=max(abs(D(a)-D(b))/max(D(1),abs(D(a)))for x,y in zip(base['rows'],parts)for a,b in zip(x['values'],y['values']))
if e>D('1e-13'):raise AssertionError(e)
dump(P/'memory.json',dict(reference_loaded_graphs=len(ids),optimized_task_block=32,reference_peak_rss_mib=rss0,optimized_max_peak_rss_mib=max(rss),max_normalized_point_difference=str(e),points=len(rows),scope='Same complete 590 graph set; monolithic original power producer versus sequential bounded native blocks. 1 point/stratum: memory test, NOT production precision or a timing benchmark.'))
