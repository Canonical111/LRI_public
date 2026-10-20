#!/usr/bin/env python3
"""Run exactly one checked coefficient task. Never consumes the old curve manifests.

In a cluster job (cluster/job.sbatch) the thread count comes from the allocation (LRI_COEFF_THREADS), the
manifest bytes must still have the SHA-256 recorded at submission (LRI_COEFF_MANIFEST_SHA256), and with
LRI_COEFF_LOCAL_CHECKPOINT set the solver checkpoints to that node-local directory while scripts/ckpt_sync.py
restores and publishes the task's checkpoint as one archive, TASK_CHECKPOINT_DIR/task-<digest16>.tar.
Thread count is not part of the result identity. The solver imports only the staged src (PYTHONPATH is exactly
ROOT/src, PYTHONSAFEPATH=1 so the working directory is never searched).
"""
from pathlib import Path
import argparse,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parents[1]

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--index',type=int,default=int(os.environ.get('SLURM_ARRAY_TASK_ID','-1')));a=p.parse_args()
 raw=a.manifest.read_bytes();want=os.environ.get('LRI_COEFF_MANIFEST_SHA256')
 if want and hashlib.sha256(raw).hexdigest()!=want:raise ValueError('Campaign manifest changed after submission')
 wrap=json.loads(raw);payload=wrap.get('payload')
 if wrap.get('schema')!='lri-coeff-v1' or hashlib.sha256(canonical(payload)).hexdigest()!=wrap.get('sha256'):raise ValueError('Invalid campaign checksum')
 if payload.get('kind')!='lri-2d-coefficient-array-v1':raise ValueError('Wrong campaign schema: not a coefficient array')
 if not 0<=a.index<len(payload['tasks']):raise ValueError('Array task index outside manifest')
 source=hashlib.sha256(canonical({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src/lri_coeff').iterdir()) if p.suffix in ('.py','.cpp')})).hexdigest()
 if source!=payload['source_digest']:raise ValueError('Source changed after campaign creation; build a new manifest')
 task=payload['tasks'][a.index];data={k:v for k,v in task.items() if k!='task_digest'}
 if hashlib.sha256(canonical(data)).hexdigest()!=task['task_digest']:raise ValueError('Task digest mismatch')
 threads=int(os.environ.get('LRI_COEFF_THREADS') or task['threads'])
 if threads<1:raise ValueError('threads must be positive')
 local=os.environ.get('LRI_COEFF_LOCAL_CHECKPOINT')
 args=['-m','lri_coeff','run','--cutoff',str(task['cutoff']),'--degree',str(task['degree']),'--scheme',task['scheme'],'--threads',str(threads),'--backend',task['backend'],'--max-states',str(task['max_states']),'--memory-gib',str(task['memory_gib']),'--output',task['output'],'--checkpoint',local or task['checkpoint'],'--resume']
 # Older manifests always name a shared graph cache; cache=None runs without one. Cluster jobs never use one
 # (it would put a tree of memory-mapped arrays on the shared filesystem; submit.py refuses such manifests).
 if task.get('cache') and local:raise ValueError('Shared graph cache in a cluster job; make the manifest with --cache-mode none')
 if task.get('cache'):args+=['--cache',task['cache']]
 if task.get('checkpoint_seconds') is not None:args+=['--checkpoint-seconds',str(task['checkpoint_seconds'])]
 print(f"run_task: index {a.index} L={task['cutoff']} degree={task['degree']} scheme={task['scheme']} threads={threads} output={task['output']}",flush=True)
 env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONSAFEPATH='1')
 if local:
  sys.path.insert(0,str(ROOT/'scripts'));from ckpt_sync import supervise
  archive=Path(task['checkpoint'])/f"task-{task['task_digest'][:16]}.tar"
  raise SystemExit(supervise([sys.executable,*args],env,Path(local),archive,os.environ.get('SLURM_JOB_ID') or str(os.getpid())))
 os.execve(sys.executable,[sys.executable,*args],env)
if __name__=='__main__':main()
