#!/usr/bin/env python3
"""Freeze explicit items, exact plans and a passing validation receipt."""
from pathlib import Path
import argparse,json,os,platform,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy,numba,scipy
from lri_c8 import io
from lri_c8.planning import plan
p=argparse.ArgumentParser();p.add_argument('--cutoffs',type=int,nargs='+',required=True)
p.add_argument('--schemes','--scheme',nargs='+',choices=['raw','vacuum_only'],default=['raw'])
p.add_argument('--outer-backend',choices=['stored','ranked','auto'],default='auto',
               help='auto: stored when its conservative plan fits the memory limit, else ranked')
p.add_argument('--threads',type=int,required=True);p.add_argument('--memory-limit-gib',type=float,required=True)
p.add_argument('--split-references',action='store_true')
p.add_argument('--lanes',type=int,help='number of lanes (array tasks); default one item per lane')
p.add_argument('--receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--allow-local-receipt',action='store_true',help='tests only: accept a non-compute-node or partial receipt')
# A production receipt must cover every step, including the original-solver comparison
# inside the production range (validate_release --full, default --compare-cutoff 60).
REQUIRED_STEPS=('manifest','pytest','grid_replay','original_comparison','fs_probe');MIN_COMPARE_CUTOFF=60
a=p.parse_args();receipt=io.read(a.receipt)
if receipt.get('status')!='pass' or receipt['source_sha256']!=io.source_digest():raise ValueError('Passing receipt for current source required')
stack={'python':platform.python_version(),'numpy':numpy.__version__,'numba':numba.__version__,'scipy':scipy.__version__}
layer=os.environ.get('NUMBA_THREADING_LAYER','default')
if not a.allow_local_receipt:
 if receipt.get('kind')!='compute-node' or not receipt.get('full'):raise ValueError('Full compute-node validation receipt required')
 steps=receipt.get('steps',{})
 if any(steps.get(k,{}).get('returncode')!=0 for k in REQUIRED_STEPS) or (receipt.get('compare_cutoff') or 0)<MIN_COMPARE_CUTOFF:
  raise ValueError(f'Receipt lacks production coverage: steps {REQUIRED_STEPS} must pass and compare_cutoff >= {MIN_COMPARE_CUTOFF}')
 t=steps['pytest'];n=t.get('collected') or 0
 if n<1 or t.get('counts',{}).get('passed')!=n:raise ValueError(f'Receipt pytest did not pass the complete suite: {t.get("counts")} of {n}')
 if {k:receipt.get('stack',{}).get(k) for k in stack}!=stack:
  raise ValueError(f"Receipt stack {receipt.get('stack')} differs from this interpreter {stack}")
 if receipt.get('numba_threading_layer_setting')!=layer:
  raise ValueError(f"Receipt threading layer {receipt.get('numba_threading_layer_setting')} differs from NUMBA_THREADING_LAYER={layer}")
if a.output.exists():raise FileExistsError('Campaign already exists')
if a.threads<1 or (a.lanes is not None and a.lanes<1):raise ValueError('Invalid threads/lanes')
if len(set(a.cutoffs))!=len(a.cutoffs) or len(set(a.schemes))!=len(a.schemes):raise ValueError('Duplicate cutoff or scheme')
items=[];plans={};backend={}
for L in a.cutoffs:
 options=('stored','ranked') if a.outer_backend=='auto' else (a.outer_backend,)
 plans[str(L)]={b:plan(L,b) for b in options}
 fits=[b for b in options if plans[str(L)][b]['conservative_gib']<=a.memory_limit_gib]
 if not fits:raise MemoryError(f'Cutoff {L} exceeds the supplied budget for {options}; inspect/calibrate planner')
 backend[L]=fits[0]
for scheme in a.schemes:
 for L in a.cutoffs:
  for r in (0,1,3,2) if a.split_references else (None,):
   items.append({'cutoff':L,'scheme':scheme,'outer_backend':backend[L],'threads':a.threads,
                 'memory_limit_gib':a.memory_limit_gib,'reference':r})
size=lambda x:plans[str(x['cutoff'])][x['outer_backend']]['full_residual']['dim']
nl=len(items) if a.lanes is None else a.lanes
lanes=[[] for _ in range(nl)];loads=[0]*nl
# Largest tasks first (lower array indices start first); references at a cutoff have
# different costs, so this is an approximate balance by dimension, not a time guarantee.
for item in sorted(items,key=size,reverse=True):
 k=min(range(nl),key=lambda k:loads[k]);lanes[k].append(item);loads[k]+=size(item)
payload={'source_sha256':io.source_digest(),'receipt':receipt,'items':items,'lanes':lanes,'plans':plans,'stack':stack,
         'threading_layer':layer,
         'scope':'Independent single-process reference/cutoff tasks; no MPI distributed basis.'}
with io.publication(a.output):io.atomic_save(a.output,payload)
if io.read(a.output)!=json.loads(json.dumps(payload)):raise RuntimeError('Campaign manifest does not read back')
cid=json.loads(a.output.read_text())['sha256'][:16]
print(f'{len(items)} items, {nl} lanes written to {a.output} (campaign {cid}); backends: '+
      ', '.join(f'L{L}:{b}' for L,b in backend.items()))
