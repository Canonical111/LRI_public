#!/usr/bin/env python3
"""Repeat full edge-subgraph forest comparison for every power class, L3..8."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from generate_graphs import ROOT,compile_program,read,save

def core(path,terms):
 with Path(path).open('rb')as f:return b''.join(f.readline()for _ in range(terms+2))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--threads',type=int,default=8);p.add_argument('--inputs',type=Path,default=ROOT/'inputs');p.add_argument('--output',type=Path,default=ROOT/'verification/all_edge_recheck.json');p.add_argument('--cxx',default=os.environ.get('CXX','g++'));a=p.parse_args()
 if a.threads<1:raise ValueError('threads must be positive')
 inputs=a.inputs.resolve();induced={L:{g['id']:g for g in read(inputs/f'complete_inventory_L{L}.json')}for L in range(3,9)}
 with tempfile.TemporaryDirectory(prefix='.all-edge-audit-',dir=ROOT)as temporary:
  temp=Path(temporary);builder=temp/'build_forests';compile_program(ROOT/'src/build_forests.cpp',builder,a.cxx,True);power_jobs=[];missing_jobs=[]
  for L in range(3,9):
   for line in (ROOT/f'regeneration/jobs_L{L}.txt').read_text().splitlines():
    g=induced[L][int(line.split()[1])]
    if g['sector']=='power':
     power_jobs.append(line)
     if g['terms']and not g['file']:missing_jobs.append(line)
  jobs=temp/'power_jobs.txt';jobs.write_text('\n'.join(power_jobs)+'\n');raw=temp/'all_edge';subprocess.run([str(builder),str(jobs),str(raw),'--all-edge','--threads',str(a.threads)],check=True)
  missing={}
  if missing_jobs:
   jobs2=temp/'omitted_jobs.txt';jobs2.write_text('\n'.join(missing_jobs)+'\n');extra=temp/'induced_omitted';subprocess.run([str(builder),str(jobs2),str(extra),'--threads',str(a.threads)],check=True);missing={(g['L'],g['id']):extra/g['file']for g in read(extra/'complete_inventory.json')}
  records=read(raw/'complete_inventory.json');report={'method':'Exhaustive proper-edge-subset and unreduced compatible-forest enumeration, exact integer-map comparison','loops':{}}
  for L in range(3,9):
   gs=[g for g in records if g['L']==L];checked=0;noninduced_logs=0;affected=0
   for g in gs:
    old=induced[L][g['id']]
    for k in ['terms','masks','power_subgraphs']:
     if g[k]!=old[k]:raise AssertionError((L,g['id'],k,'mismatch'))
    delta=g['log_subgraphs']-old['log_subgraphs']
    if delta<0:raise AssertionError('Lost logarithmic subgraph')
    noninduced_logs+=delta;affected+=delta>0
    if g['terms']:
     source=inputs/old['file']if old['file']else missing[(L,g['id'])]
     if (raw/g['file']).read_bytes()!=core(source,g['terms']):raise AssertionError((L,g['id'],'exact forest map differs'))
     checked+=1
   report['loops'][str(L)]={'power_classes_checked':len(gs),'nonzero_maps_exactly_matched':checked,'zero_maps_exactly_matched':len(gs)-checked,'proper_edge_subsets_enumerated':len(gs)*((1<<(2*L))-2),'graphs_with_noninduced_log_subgraphs':affected,'noninduced_log_subgraphs':noninduced_logs,'unreduced_forests_enumerated':sum(g['forests']for g in gs)}
  baseline=read(ROOT/'verification/all_edge_validation.json')
  if report['loops']!=baseline['loops']:raise AssertionError('Audit census differs from delivered exact certificate')
  report.update(all_checks_passed=True,total_power_classes_checked=len(records),total_proper_edge_subsets_enumerated=sum(r['proper_edge_subsets_enumerated']for r in report['loops'].values()),total_unreduced_forests_enumerated=sum(r['unreduced_forests_enumerated']for r in report['loops'].values()),total_noninduced_logs=sum(r['noninduced_log_subgraphs']for r in report['loops'].values()))
  a.output.parent.mkdir(parents=True,exist_ok=True);save(a.output,report)
 print(json.dumps({k:v for k,v in report.items()if k!='loops'},indent=2))
if __name__=='__main__':main()
