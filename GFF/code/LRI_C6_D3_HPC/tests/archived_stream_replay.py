#!/usr/bin/env python3
"""Replay the ARCHIVED fresh d=3 production streams with the built worker (make test-replay).

For each of reference/records/new_{a,b}_d3_L3..L6.json the worker runs the archived stream exactly: the archived Sobol
net (reference/inputs/new_*_d3_L*_net.bin), counts file and native seed, layout 0, rate 1, no grid, legacy summation,
every (replicate, graph) stratum with a nonzero count as one task. Requirements:
  * binary128 and 300-digit fallback totals equal the archived record in every stream;
  * per-graph jets agree to normalized <= 1e-12 (the archived code summed prob*v/n per point in long double; the
    difference is summation rounding, measured <= 2.2e-13);
  * per-replicate batches agree to normalized <= 1e-14;
  * the fresh-only C6(3) assembled from the replayed batches equals the published value to relative <= 1e-13
    (bitwise equality is recorded; it held on a personal desktop and is not required).
Everything is written to a temporary directory; nothing in the package changes. About 2 minutes at 16 threads.
"""
from __future__ import annotations
import argparse,json,math,os,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from assemble import coefficients,jacobians,verified_inputs
from common import dump
R=ROOT/'reference'
GRAPH_TOL=1e-12;BATCH_TOL=1e-14;C6_TOL=1e-13

def normalized(a,b):return float(np.max(np.abs(a-b)/np.maximum(1,np.abs(b))))

def replay(td:Path,camp:str,L:int,threads:int):
    rec=json.loads((R/f'records/new_{camp}_d3_L{L}.json').read_text(),parse_float=str)
    if rec.get('dimension')!=3 or rec.get('L')!=L or rec.get('layout')!=0 or rec.get('method')!='rqmc':raise AssertionError(f'unexpected archived record new_{camp} L{L}')
    lines=(R/f'inputs/new_{camp}_d3_L{L}_counts.txt').read_text().split('\n');n=int(lines[0])
    counts={int(a):int(b)for a,b in (l.split()for l in lines[1:1+n])}
    ids=[int(g)for g in rec['graph_ids']]
    if [int(c)for c in rec['counts_per_replicate']]!=[counts[g]for g in ids]:raise AssertionError('archived counts file and record disagree')
    rows=[];uid=0
    for rep in range(int(rec['replicates'])):
        for g in ids:
            if counts[g]>0:rows.append((uid,rep,g,0,counts[g],counts[g]));uid+=1
    tf=td/f'tasks_{camp}{L}.txt';tf.write_text(f'C6TASKS3D1 {L} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows));out=td/f'new_{camp}{L}.json'
    cmd=[ROOT/'bin/c6_integrate',ROOT/'inputs/graphs',ROOT/'inputs/gamma_d3.txt',R/f'inputs/new_{camp}_d3_L{L}_net.bin',tf,out,int(rec['seed']),0,1,threads,'legacy','-']
    t0=time.time();cp=subprocess.run(list(map(str,cmd)),capture_output=True,text=True)
    if cp.returncode:raise RuntimeError(cp.stderr[-3000:])
    new=json.loads(out.read_text());idx={g:k for k,g in enumerate(ids)};gerr=0.
    if new['bits']!=int(rec['bits']):raise AssertionError('net bit width differs from the record')
    batches=np.zeros((int(rec['replicates']),2*(7-L)),dtype=np.longdouble)
    for r in new['rows']:
        v=np.array(r['values'],dtype=np.longdouble);gerr=max(gerr,normalized(v,np.array(rec['graph_batches'][r['rep']][idx[r['graph']]],dtype=np.longdouble)));batches[r['rep']]+=v
    q=sum(r['quad']for r in new['rows']);m=sum(r['mp']for r in new['rows'])
    batches=batches.astype(float);berr=normalized(batches,np.array(rec['batches'],dtype=float))
    rec_q,rec_m=int(rec['quad_fallbacks']),int(rec['mp_fallbacks'])
    info={'campaign':camp,'L':L,'seed':int(rec['seed']),'bits':new['bits'],'tasks':len(rows),'samples':sum(r[5]for r in rows),'quad':[q,rec_q],'mp':[m,rec_m],
          'max_normalized_graph_jet_difference':gerr,'max_normalized_batch_difference':berr,'native_seconds':new['integration_seconds'],'wall_seconds':time.time()-t0,'threads':threads}
    if q!=rec_q or m!=rec_m:raise AssertionError(f'fallback counts differ from the archive: {info}')
    if gerr>GRAPH_TOL or berr>BATCH_TOL:raise AssertionError(f'replay differs from the archive beyond tolerance: {info}')
    out.unlink();tf.unlink();return info,batches

def c6(ar,B2):
    w={'a':.5,'b':.5};means={L:sum(w[t]*ar[(t,L)].mean(0)for t in w)for L in range(3,7)};J=jacobians(means,B2)
    cov=sum(J[L]@sum(w[t]**2*np.cov(ar[(t,L)],rowvar=False,ddof=1)/len(ar[(t,L)])for t in w)@J[L].T for L in means)
    return float(coefficients(means,B2)[6]),float(cov[6,6]**.5)

def run(threads:int):
    B2=verified_inputs()['B2'];streams=[];replayed={}
    with tempfile.TemporaryDirectory(prefix='c6_stream_replay_')as td:
        for camp in 'ab':
            for L in range(3,7):
                info,b=replay(Path(td),camp,L,threads);streams.append(info);replayed[(camp,L)]=b;print(json.dumps(info),flush=True)
    ref=json.loads((R/'verification/method_precision_results.json').read_text())['3']['fresh_only']
    C,S=c6(replayed,B2)
    if not math.isclose(C,ref['C6'],rel_tol=C6_TOL,abs_tol=0):raise AssertionError(f'replayed fresh-only C6 {C!r} vs published {ref["C6"]!r}')
    return {'status':'passed','test':'archived_stream_replay','streams':streams,'samples_total':sum(s['samples']for s in streams),'replayed_fresh_only_C6':C,'replayed_SE':S,'published_fresh_only':[ref['C6'],ref['sampling_standard_error']],
            'C6_bitwise_identical':C==ref['C6'],'tolerances':{'graph':GRAPH_TOL,'batch':BATCH_TOL,'C6_relative':C6_TOL}}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--threads',type=int,default=int(os.environ.get('SLURM_CPUS_PER_TASK',os.cpu_count()or 4)));p.add_argument('--output',type=Path)
    a=p.parse_args();x=run(a.threads)
    if a.output:dump(a.output,x)  # optional record; the shipped benchmarks/ evidence is never rewritten
    print(json.dumps(x,indent=2))
