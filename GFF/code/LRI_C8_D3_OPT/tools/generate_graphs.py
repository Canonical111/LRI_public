#!/usr/bin/env python3
"""Rebuild all graph inputs and require exact delivered census/payload hashes."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def jobs_from_census(graphs):
 return ''.join(' '.join(map(str,[g['L'],g['id'],g['denominator'],g['mass_numerator'],g['automorphisms'],*(v for e in g['edges']for v in e)]))+'\n' for g in graphs)
def compile_program(source,target,cxx,openmp=False):
 args=[cxx,'-O3','-std=c++17']+(['-fopenmp']if openmp else[])+[str(source),'-o',str(target)]
 subprocess.run(args,check=True)
def stage_loop(loop,generated,destination,inventory):
 gs=read(generated/'complete_inventory.json');active=[]
 for g in gs:
  if not g['file']:continue
  source=generated/g['file'];target=destination/g['file'];target.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(source,target)
  except OSError:shutil.copyfile(source,target)
  row={k:g[k]for k in ['id','primitive','terms','denominator','mass_numerator','automorphisms','file','rate_clamped_subsets','minimum_rate_quarters']}
  row.update(monomials=g['masks'],cost=max(1,g['terms']*g['masks']),sha256=digest(source),bytes=source.stat().st_size,wa_numerator=24,wb_numerator=2*g['mass_numerator'])
  inventory[g['sector']][str(loop)].append(row);active.append([g['sector'],loop,g['id'],row['sha256']])
 save(destination/f'complete_inventory_L{loop}.json',gs)
 sectors={s:{'all':sum(g['sector']==s for g in gs),'exact_zero_kernel':sum(g['sector']==s and not g['terms']for g in gs),'nonzero_kernel':sum(g['sector']==s and bool(g['terms'])for g in gs),'integrated':len(inventory[s][str(loop)])}for s in ['free','power']}
 return {'all_classes':len(gs),'sectors':sectors,'primitive':sum(g['primitive']for g in gs),'zero_top_channel':sum(g['zero_top_channel']for g in gs),'zero_kernel':sum(not g['terms']for g in gs),'zero_kernel_and_top_channel':sum(not g['terms']and g['zero_top_channel']for g in gs),'grouped_forest_terms':sum(g['terms']for g in gs),'forests':sum(g['forests']for g in gs),'payloads_sha256':hashlib.sha256(json.dumps(sorted(active),separators=(',',':')).encode()).hexdigest()}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'regenerated_graph_inputs');p.add_argument('--threads',type=int,default=8);p.add_argument('--cxx',default=os.environ.get('CXX','g++'));a=p.parse_args()
 if a.threads<1:raise ValueError('threads must be positive')
 out=a.output.resolve()
 if out.exists() and any(out.iterdir()):raise FileExistsError('Destination must be absent or empty; active inputs are never overwritten')
 out.mkdir(parents=True,exist_ok=True)
 expected=read(ROOT/'regeneration/expected_graph_census.json');inventory={s:{str(L):[]for L in range(3,9)}for s in ['free','power']};census={}
 with tempfile.TemporaryDirectory(prefix='.graph-generation-',dir=out)as temporary:
  temp=Path(temporary);enum=temp/'enumerate_graphs';build=temp/'build_forests'
  compile_program(ROOT/'src/enumerate_graphs.cpp',enum,a.cxx);compile_program(ROOT/'src/build_forests.cpp',build,a.cxx,True)
  for n in range(3,10):
   target=temp/f'graphs_n{n}.json';subprocess.run([str(enum),str(n),str(target)],check=True)
   if digest(target)!=digest(ROOT/f'regeneration/graphs_n{n}.json'):raise AssertionError(f'Canonical enumeration differs at {n} vertices')
  for L in range(3,9):
   jobs=temp/f'jobs_L{L}.txt'
   if L==8:jobs.write_text(jobs_from_census(read(temp/'graphs_n9.json')))
   else:shutil.copyfile(ROOT/f'regeneration/jobs_L{L}.txt',jobs)
   if digest(jobs)!=digest(ROOT/f'regeneration/jobs_L{L}.txt'):raise AssertionError(f'Graph identities or weights differ at L{L}')
   generated=temp/f'generated_L{L}';cmd=[str(build),str(jobs),str(generated),'--rates','--threads',str(a.threads)]+(['--topzero']if L==8 else[]);subprocess.run(cmd,check=True)
   census[str(L)]=stage_loop(L,generated,out,inventory)
   if census[str(L)]!=expected[str(L)]:raise AssertionError(f'Census or exact payloads differ at L{L}')
   shutil.rmtree(generated)
   print(f'L{L}: exact graph, forest and rate reproduction passed',flush=True)
  save(out/'inventory.json',inventory)
  if digest(out/'inventory.json')!=digest(ROOT/'inputs/inventory.json'):raise AssertionError('Final inventory identity differs')
  coverage=read(ROOT/'inputs/coverage.json')
  if not coverage.get('complete') or coverage['inventory_sha256']!=digest(out/'inventory.json'):raise AssertionError('Delivered coverage identity is not valid')
  save(out/'coverage.json',coverage)
 print(json.dumps({'complete':True,'output':str(out),'inventory_sha256':digest(out/'inventory.json'),'graph_payloads':sum(len(v)for s in inventory.values()for v in s.values())},indent=2))
if __name__=='__main__':main()
