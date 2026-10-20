#!/usr/bin/env python3
"""One solver process per item owns its lock. Supervisor signals are forwarded, not hidden.

Exit codes: 0 every item accepted; 75 stopped at a safe boundary (resume later);
73 the lane or an item is owned by another live job; 64 this allocation or software
stack does not match the frozen campaign; anything else is a real failure (no blind
retry). The lane journal is read and written only while this process owns the lane.
"""
import os,signal,sys
child=None;stopped=None
def handler(sig,frame):
 global stopped
 stopped=sig
 if child is not None and child.poll() is None:child.send_signal(sig)
# Installed before the numpy/numba imports below, so an early Slurm warning is not lost.
for sig in (signal.SIGUSR1,signal.SIGTERM,signal.SIGINT):signal.signal(sig,handler)
import argparse,json,platform,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_c8 import io
import numpy,numba,scipy
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--lane',type=int,required=True)
p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
manifest=io.read(a.manifest);cid=json.loads(a.manifest.read_text())['sha256'][:16]
if manifest['source_sha256']!=io.source_digest():raise ValueError('Frozen campaign source mismatch')
if not 0<=a.lane<len(manifest['lanes']):raise ValueError('Invalid lane')
out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)

def physical_cores():
 # Distinct cores in this process's CPU affinity (numactl/cgroup), not the node total.
 try:cpus=os.sched_getaffinity(0)
 except AttributeError:return os.cpu_count() or 1
 cores=set()
 for c in cpus:
  t=Path(f'/sys/devices/system/cpu/cpu{c}/topology')
  try:cores.add(((t/'physical_package_id').read_text().strip(),(t/'core_id').read_text().strip()))
  except OSError:cores.add(('cpu',c))
 return len(cores)

def stem(item):return f"{item['scheme']}_L{item['cutoff']}_d8"+('' if item['reference'] is None else f"_ref{item['reference']}")

lane_owner=out/'owners'/'lanes'/f'{cid}_lane_{a.lane}.owner'
try:lane_token=io.acquire_owner(lane_owner)
except io.ClaimBusy as e:
 # Not ours: never touch this lane's journal.
 print(f'[lane {a.lane}] exit 73: {e}',flush=True);raise SystemExit(73)
journal_path=out/'journals'/cid/f'lane_{a.lane}.json'
journal={'campaign':cid,'manifest':str(a.manifest.resolve()),'lane':a.lane,'attempts':[]}
attempt={**io.owner_info(),'binding':os.environ.get('C8_BINDING'),'start':time.time(),'items':[]}
def save_journal():io.atomic_save(journal_path,journal)
def finish(code,reason):
 try:
  attempt.update(end=time.time(),exit=code,reason=reason);save_journal()
 finally:io.release_owner(lane_owner,lane_token)
 print(f'[lane {a.lane}] exit {code}: {reason}',flush=True);raise SystemExit(code)

try:
 if journal_path.exists():
  try:journal=io.read(journal_path)
  except (ValueError,OSError,KeyError):journal_path.rename(journal_path.with_name(journal_path.name+f'.corrupt.{os.urandom(4).hex()}'))
 journal['attempts'].append(attempt);save_journal()  # the attempt is on disk before any work starts
 stack={'python':platform.python_version(),'numpy':numpy.__version__,'numba':numba.__version__,'scipy':scipy.__version__}
 layer=os.environ.get('NUMBA_THREADING_LAYER','default')
 if stack!=manifest.get('stack') or layer!=manifest.get('threading_layer'):
  finish(64,f'stack {stack} / NUMBA_THREADING_LAYER={layer} differ from the campaign {manifest.get("stack")} / {manifest.get("threading_layer")}')
 cores=physical_cores();attempt['physical_cores']=cores
 items=manifest['lanes'][a.lane]
 if items and max(i['threads'] for i in items)>cores:
  finish(64,f'{cores} physical cores in the CPU affinity; frozen items need {max(i["threads"] for i in items)} threads')
 failure=None;busy=0;item_stopped=False
 for item in items:
  if stopped:break
  s=stem(item);rec={'item':item,'start':time.time(),'status':'started'};attempt['items'].append(rec)
  save_journal()  # item start is on disk before the solver is launched
  # The solver itself owns the item (flock + O_EXCL owner in accepted/claims/) and
  # exits 73 if another writer holds it.
  cmd=[sys.executable,'-m','lri_c8','run','--cutoff',str(item['cutoff']),'--scheme',item['scheme'],
       '--outer-backend',item['outer_backend'],'--threads',str(item['threads']),
       '--memory-limit-gib',str(item['memory_limit_gib']),'--output-dir',str(out/'accepted'),'--resume']
  if item['reference'] is not None:cmd+=['--reference',str(item['reference'])]
  env={**os.environ,'PYTHONPATH':os.pathsep.join(x for x in (str(ROOT/'src'),os.environ.get('PYTHONPATH')) if x),
       'OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OMP_NUM_THREADS':'1','NUMBA_NUM_THREADS':str(item['threads'])}
  print(f'[lane {a.lane}] start {s} ({item["outer_backend"]}, {item["threads"]} threads)',flush=True)
  child=subprocess.Popen(cmd,env=env)
  if stopped and child.poll() is None:child.send_signal(stopped)  # signal arrived during Popen
  code=child.wait();child=None
  if code<0:code=128-code
  if code==0:
   status='accepted';path=out/'accepted'/(s+'.json')
   try:
    r=io.read(path);rec.update(output=str(path),output_sha256=json.loads(path.read_text())['sha256'],
                               C8=(r.get('C') or [None]*9)[8],seconds=r.get('seconds'),peak_rss_kib=r.get('peak_rss_kib'))
   except (OSError,ValueError,KeyError) as e:status='accepted_unreadable';rec['detail']=repr(e)
  elif code==75:status='stopped'
  # Death by exactly the signal we forwarded (before the solver's handlers existed) is a
  # stop; any other abnormal exit, e.g. 137 after a warning, stays a failure.
  elif stopped is not None and code==128+stopped:status='stopped'
  elif code==73:status='claim_busy';busy+=1
  else:status='failed'
  rec.update(returncode=code,status=status,end=time.time());save_journal()
  print(f'[lane {a.lane}] {s}: {status} (rc {code})',flush=True)
  if status=='stopped':item_stopped=True;break
  if status in ('failed','accepted_unreadable'):failure=code or 1;break  # no blind retry of memory/correctness failures
 if failure is not None:finish(failure,'item failed; later items in this lane were not started')
 if stopped is not None or item_stopped:finish(75,f'stopped (signal {stopped}); resubmit to resume')
 if busy:finish(73,f'{busy} item(s) owned by another job')
 finish(0,'all items accepted')
except SystemExit:raise
except BaseException as e:finish(1,f'supervisor error: {e!r}')
