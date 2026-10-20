#!/usr/bin/env python3
"""End to end (d=3): the ORIGINAL experiment binary (-DSPATIAL_D=3) versus the complete new pipeline (plan, shard, chunk, checkpoint, merge).

A small campaign is planned and executed with the production tools (chunked tasks, cost-ordered blocks, several
shards). For every group the original reference/code/experiment.cpp, built unchanged except for its thread count,
integrates the same counts, net, seed, layout and frozen grid in one run. Merged replicate batches and per-graph
jets must agree (normalized <= 1e-15), and binary128/300-digit fallback counts must be equal.
"""
from __future__ import annotations
import argparse,contextlib,csv,io,json,os,subprocess,sys,tempfile
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
from common import load
import production as p
from validate import build_baseline
B=ROOT/'reference/baseline_previous';TOL=1e-15

def run(points:int,replicates:int,threads:int):
    report=[]
    with tempfile.TemporaryDirectory(prefix='c6_e2e_')as td:
        td=Path(td);d=td/'campaign'
        with contextlib.redirect_stdout(io.StringIO()):
            p.plan(NS(directory=d,seed=6602117,seed_scheme='hashed',points=points,replicates=replicates,multiplier=1,shards=3,shard_policy='uniform',threads=threads,checkpoint_tasks=64,chunk_points=3,primitive_mode='recompute',grid='frozen',sum_mode='compensated'))
            m=load(d/'manifest.json')
            for j in m['jobs']:p.run(NS(directory=d,index=j['id'],threads=threads,scratch=None,max_blocks=None))
            p.merge(NS(directory=d,group=None,scratch=None))
        exe=td/'original';build_baseline(exe);inv=load(ROOT/'inputs/inventory.json')
        for g in m['groups']:
            gd=d/'groups'/g['name'];c=load(gd/'config.json');merged=load(gd/'merged.json');L=c['L'];ids=[r['id']for r in inv[str(L)]]
            cf=td/f'{g["name"]}.counts';cf.write_text(f'{len(ids)}\n'+''.join(f'{i} {c["counts"].get(str(i),0)}\n'for i in ids))
            rate=B/f'baseline/lri_C6_d3_complete_update/inputs/rates_L{L}_0.8.txt'
            out=td/f'{g["name"]}.old.json';env=dict(os.environ,OMP_NUM_THREADS=str(threads))
            if c['grid']:env['GRID_FILE']=str(ROOT/'inputs'/c['grid'])
            cmd=[exe,B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt',rate,cf,c['seed'],gd/'sobol.bin',out,ROOT/'inputs/gamma_d3.txt','rqmc',c['layout'],0,c['rate']]
            cp=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=env)
            if cp.returncode:raise RuntimeError(cp.stderr[-2000:])
            old=json.loads(out.read_text(),parse_float=str);a=np.array(old['batches'],dtype=np.longdouble);b=np.array(merged['batches'],dtype=np.longdouble)
            assert a.shape==b.shape,(g['name'],a.shape,b.shape)
            err=float(np.max(np.abs(a-b)/np.maximum(1,np.abs(a))));idx={gi:i for i,gi in enumerate(old['graph_ids'])};gerr=0.
            with open(gd/'graph_replicates.csv')as f:
                for r in csv.DictReader(f):
                    x=np.array([r[f'jet_{k}']for k in range(2*(7-L))],dtype=np.longdouble);y=np.array(old['graph_batches'][int(r['replicate'])][idx[int(r['graph'])]],dtype=np.longdouble)
                    gerr=max(gerr,float(np.max(np.abs(x-y)/np.maximum(1,np.abs(y)))))
            fb={'quad':old['quad_fallbacks'],'mp':old['mp_fallbacks']}
            assert err<=TOL and gerr<=TOL and fb==merged['fallbacks'],(g['name'],err,gerr,fb,merged['fallbacks'])
            report.append({'group':g['name'],'L':L,'grid':c['grid'],'replicates':len(a),'shards':c['shards'],'tasks':c['tasks'],'max_normalized_batch_difference':err,'max_normalized_graph_difference':gerr,'fallbacks':fb})
            print(report[-1],flush=True)
    return {'status':'passed','test':'e2e_original_vs_pipeline','tolerance':TOL,'groups':report}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--points',type=int,default=8);ap.add_argument('--replicates',type=int,default=4);ap.add_argument('--threads',type=int,default=4);a=ap.parse_args()
    print(json.dumps(run(a.points,a.replicates,a.threads),indent=2))
