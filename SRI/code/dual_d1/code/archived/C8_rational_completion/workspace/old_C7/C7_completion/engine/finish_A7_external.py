"""Memory-bounded, checkpointed exact completion of the A7 charge derivative.
An already evaluated one-quarter of stage four is reused; the remainder is
partitioned into small contiguous blocks. External grouping performs exact
coefficient cancellation before the last integral. No numerical values enter.
"""
from pathlib import Path
import json,subprocess,sys,os,time,hashlib,gc
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs'
original=ROOT/'A7_v_stage4.json';rows=json.loads(original.read_text());total_rows=len(rows);reuse=(ROOT/'A7_v_tail1_partial_audit.json').exists() and (ROOT/'A7_v_tail1_stage5.json').exists()
# Completed tail 1 contains exactly row indices i == 1 mod 4.
indices=[i for i in range(len(rows)) if not reuse or i%4!=1];chunks=[indices[j:j+200] for j in range(0,len(indices),200)]
meta=[]
for k,inds in enumerate(chunks):
 tag=f'A7_v_block{k:03d}';fp=ROOT/f'{tag}_stage4.json';fp.write_text(json.dumps([rows[i] for i in inds]));meta.append({'tag':tag,'source_indices':inds,'source_sha256':hashlib.sha256(fp.read_bytes()).hexdigest()})
del rows;gc.collect();running={};nexti=0;complete=[]
while nexti<len(chunks) or running:
 while nexti<len(chunks) and len(running)<3:
  k=nexti;nexti+=1;tag=meta[k]['tag']
  if (ROOT/f'{tag}_partial_audit.json').exists():complete.append(k);continue
  f=(LOG/f'{tag}.log').open('w');p=subprocess.Popen([sys.executable,'run_moment.py','7','A','v','--resume','4'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'LRI_TAG_SUFFIX':f'_block{k:03d}','LRI_STOP_AFTER':'5','OPENBLAS_NUM_THREADS':'1'})
  running[k]=(p,f,time.time());print('START',k,'pid',p.pid,flush=True)
 time.sleep(1)
 for k,(p,f,st) in list(running.items()):
  if p.poll() is not None:
   f.close();assert p.returncode==0,(k,p.returncode)
   complete.append(k);meta[k]['seconds']=time.time()-st;del running[k]
   print('DONE',k,'completed',len(complete),'/',len(chunks),'seconds',meta[k]['seconds'],flush=True)
 (ROOT/'A7_v_external_progress.json').write_text(json.dumps({'completed':complete,'running':list(running),'total':len(chunks)},indent=2))
files=(['A7_v_tail1_stage5.json'] if reuse else [])+[f"{m['tag']}_stage5.json" for m in meta]
(ROOT/'A7_v_external_inputs.json').write_text(json.dumps({'original_stage4_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'reused_indices':('1 mod 4' if reuse else 'none'),'block_map':meta,'files':files,'all_indices_covered_once':sorted([i for m in meta for i in m['source_indices']]+(list(range(1,total_rows,4)) if reuse else []))==list(range(total_rows))},indent=2))
os.chdir(ROOT);os.execv(sys.executable,[sys.executable,'merge_A7_external.py'])
