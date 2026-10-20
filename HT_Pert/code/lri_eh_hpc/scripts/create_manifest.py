#!/usr/bin/env python3
"""Greedy state-count balancing; does not submit jobs or guess site partitions."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lri_eh.planner import plan
from lri_eh.runtime import fingerprint,atomic_json,require_receipt
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--cutoffs',type=int,nargs='+',required=True);ap.add_argument('--degree',type=int,choices=[4,5,6,7],default=7)
ap.add_argument('--lanes',type=int,required=True);ap.add_argument('--threads',type=int,required=True)
ap.add_argument('--memory-limit-gib',type=float,required=True);ap.add_argument('--output-dir',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True)
ap.add_argument('--validation-receipt',type=Path,required=True)
a=ap.parse_args()
receipt=require_receipt(a.validation_receipt)
if a.lanes<1 or a.threads<1:raise ValueError('positive lanes/threads required')
if a.manifest.exists():raise FileExistsError(a.manifest)
if len(set(a.cutoffs))!=len(a.cutoffs):raise ValueError('Duplicate cutoff')
items=[plan(L,a.degree,a.memory_limit_gib) for L in a.cutoffs]
rejected=[x for x in items if not x['fits_budget']]
if rejected:raise MemoryError('Items exceed conservative budget: '+str([(x['cutoff'],x['recommended_request_gib']) for x in rejected]))
lanes=[dict(cutoffs=[],threads=a.threads,memory_limit_gib=a.memory_limit_gib) for _ in range(a.lanes)];load=[0]*a.lanes
for item in sorted(items,key=lambda x:x['basis_dimension'],reverse=True):
 i=min(range(a.lanes),key=lambda j:load[j]);lanes[i]['cutoffs'].append(item['cutoff']);load[i]+=item['basis_dimension']
obj=dict(source_sha256=fingerprint(),validation_receipt=str(a.validation_receipt.resolve()),validation_receipt_sha256=receipt['payload_sha256'],degree=a.degree,output_dir=str(a.output_dir.resolve()),max_attempts=3,lanes=lanes,
         planning=items,assignment='Greedy balance by state count, not a measured runtime prediction')
atomic_json(a.manifest,obj);print(json.dumps(dict(lanes=a.lanes,items=len(items),slurm_array=f'0-{a.lanes-1}',source_sha256=obj['source_sha256']),indent=2))
