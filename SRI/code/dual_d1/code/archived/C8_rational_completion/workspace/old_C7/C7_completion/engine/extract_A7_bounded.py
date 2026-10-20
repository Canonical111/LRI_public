"""Memory-bounded exact extraction of A7_v's cutoff coefficient.
Each independent chunk is a finite exact sum. Final coefficient merging uses
rational monomial keys; no period is evaluated numerically.
"""
from pathlib import Path
import sys,json,time,subprocess,os,hashlib
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs'
if len(sys.argv)>1 and sys.argv[1] != '--extract-only':
 import sympy as s
 from asymptotic_gpl import extract_rows
 j=int(sys.argv[1]);rows=json.loads((ROOT/'A7_v_negative.json').read_text());chunk=rows[j*400:(j+1)*400];st=time.time()
 out=extract_rows(chunk,6,0,None)
 (ROOT/f'A7_v_p0_chunk{j:03d}.expr').write_text(s.sstr(out, order="none"))
 print('CHUNK',j,'rows',len(chunk),'terms',len(s.Add.make_args(out)),'seconds',time.time()-st,flush=True)
else:
 rows=json.loads((ROOT/'A7_v_negative.json').read_text());n=(len(rows)+399)//400;del rows
 running={};nxt=0;complete=[];start=time.time()
 while nxt<n or running:
  while nxt<n and len(running)<3:
   j=nxt;nxt+=1
   if (ROOT/f'A7_v_p0_chunk{j:03d}.expr').exists():complete.append(j);continue
   f=(LOG/f'A7_v_p0_chunk{j:03d}.log').open('w');p=subprocess.Popen([sys.executable,__file__,str(j)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
   running[j]=(p,f,time.time());print('START',j,p.pid,flush=True)
  time.sleep(1)
  for j,(p,f,st) in list(running.items()):
   if p.poll() is not None:
    f.close();assert p.returncode==0,(j,p.returncode)
    complete.append(j);del running[j];print('DONE',j,len(complete),'/',n,time.time()-st,flush=True)
  (ROOT/'A7_v_p0_progress.json').write_text(json.dumps({'completed':complete,'running':list(running),'total':n},indent=2))
 import sympy as s
 from read_expression import load
 acc={};records=[]
 for j in range(n):
  fp=ROOT/f'A7_v_p0_chunk{j:03d}.expr';ex=load(fp)
  for mon in s.Add.make_args(ex):
   co,base=mon.as_coeff_Mul(rational=True);acc[base]=acc.get(base,s.S.Zero)+co
  records.append({'file':fp.name,'sha256':hashlib.sha256(fp.read_bytes()).hexdigest()})
  del ex
 out=s.Add(*(co*base for base,co in acc.items() if co));dst=ROOT/'series'/'A7_v_p0.expr';dst.write_text(s.sstr(out, order="none"))
 (ROOT/'A7_v_p0_extraction_audit.json').write_text(json.dumps({'method':'exact linear chunk decomposition and rational monomial sum','input_sha256':hashlib.sha256((ROOT/'A7_v_negative.json').read_bytes()).hexdigest(),'chunks':records,'terms':len(s.Add.make_args(out)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'seconds':time.time()-start},indent=2))
 print('EXTRACTION COMPLETE',len(s.Add.make_args(out)),time.time()-start,flush=True)
 if '--extract-only' not in sys.argv:
  os.execv(sys.executable,[sys.executable,str(ROOT/'finish_Omega_and_C7.py')])
