#!/usr/bin/env python3
"""Create a source-fingerprinted, de-duplicated Slurm-array manifest; no submission."""
from pathlib import Path
import argparse,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_coeff.basis import plan
from lri_coeff.storage import atomic_json,envelope,source_digest,digest,read_envelope

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cutoffs',type=int,nargs='+',required=True);p.add_argument('--degrees',type=int,nargs='+',default=[8]);p.add_argument('--schemes',nargs='+',choices=['raw','consistent','literal'],default=['raw','consistent']);p.add_argument('--threads',type=int,default=4);p.add_argument('--backend',choices=['native','numba'],default='native');p.add_argument('--output-root',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
 # Cluster defaults: no shared graph cache (each job builds its graph in memory, so no multi-GB arrays are
 # memory-mapped from Lustre/BeeGFS), and complete-stage checkpoints at most every 30 minutes.
 p.add_argument('--cache-mode',choices=['none','shared'],default='none',help='shared: graph cache under OUTPUT_ROOT/graph_cache');p.add_argument('--checkpoint-seconds',type=float,default=1800);a=p.parse_args()
 if a.threads<1:p.error('threads must be positive')
 if a.checkpoint_seconds<=0:p.error('checkpoint seconds must be positive')
 tasks=[];output=a.output_root.resolve()
 for d in sorted(set(a.degrees)):
  for L in sorted(set(a.cutoffs)):
   pl=plan(L,d)
   for scheme in sorted(set(a.schemes)):
    task=dict(cutoff=L,degree=d,scheme=scheme,threads=a.threads,backend=a.backend,max_states=pl['auxiliary_states'],memory_gib=max(1.,math.ceil(pl['recommended_memory_bytes']/2**30*1.1*4)/4),output=str(output/f'd{d}/{scheme}_L{L}.json'),checkpoint=str(output/'checkpoints'),cache=str(output/'graph_cache') if a.cache_mode=='shared' else None,checkpoint_seconds=a.checkpoint_seconds,plan=pl)
    task['task_digest']=digest(task);tasks.append(task)
 payload=dict(kind='lri-2d-coefficient-array-v1',source_digest=source_digest(),tasks=tasks)
 # Submitted jobs check the manifest's SHA-256, so an existing manifest is never rewritten with new content.
 if a.manifest.exists() and read_envelope(a.manifest)!=payload:raise SystemExit(f'{a.manifest} exists with different content; choose a new manifest path')
 atomic_json(a.manifest,envelope(payload));print(f'{len(tasks)} tasks -> {a.manifest}')
 print('Largest planned job memory:',max(t['memory_gib'] for t in tasks),'GiB')
if __name__=='__main__':main()
