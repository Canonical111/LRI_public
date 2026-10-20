"""Four-worker exact, fully checkpointed, disjoint boundary integration."""
from pathlib import Path
import json,hashlib,time,os,gc,sys
from concurrent.futures import ProcessPoolExecutor,as_completed
import multiprocessing as mp
os.environ.setdefault('R6_ACCEL','1');os.environ.setdefault('R6_NATIVE','1' if Path(__file__).with_name('poly_multiply.so').exists() else '0');os.environ['OPENBLAS_NUM_THREADS']='1'
from finish_boundaries import worker
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'boundary_batches';OUT.mkdir(exist_ok=True)

def prepare():
 manifest=[]
 for face,stage in [(1,2),(2,1),(3,1)]:
  src=ROOT/'boundary'/f'B6_vd_f{face}_stage{stage}.jsonl'
  digest=hashlib.sha256(src.read_bytes()).hexdigest();n=0;part=0;buf=[]
  for line in src.open():
   buf.append(line);n+=1
   if len(buf)==60:
    fp=OUT/f'f{face}_b{part:04d}.jsonl';fp.write_text(''.join(buf));manifest.append({'face':face,'stage':stage,'path':str(fp),'start':n-len(buf),'stop':n,'source_sha256':digest});buf=[];part+=1
  if buf:
   fp=OUT/f'f{face}_b{part:04d}.jsonl';fp.write_text(''.join(buf));manifest.append({'face':face,'stage':stage,'path':str(fp),'start':n-len(buf),'stop':n,'source_sha256':digest})
  print('SHARD',face,'rows',n,'batches',part+bool(buf),flush=True)
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));return manifest

def main():
 st=time.time();man=prepare();done=[];failed=[]
 with ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('fork')) as pool:
  fut={pool.submit(worker,m['path'],m['stage']):m for m in man}
  for f in as_completed(fut):
   m=fut[f]
   try:r=f.result();done.append(m['path'])
   except Exception as e:
    failed.append({'file':m['path'],'error':repr(e)});print('FAIL',m,repr(e),flush=True)
   if len(done)%10==0 or failed:
    print('TOTAL',len(done),'/',len(man),'failed',len(failed),'seconds',time.time()-st,flush=True)
    (OUT/'progress.json').write_text(json.dumps({'complete':len(done),'total':len(man),'failed':failed,'seconds':time.time()-st},indent=2))
 assert not failed,failed
 print('ALL_BOUNDARY_BATCHES_COMPLETE',len(done),'seconds',time.time()-st,flush=True)
if __name__=='__main__':main()
