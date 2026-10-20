"""Reassemble C7 in a clean directory from saved exact raw moment expressions.
This is NOT a reintegration of the original kernels. The old beta expressions
are preceding-order inputs; all nine NEW beta coefficients are rebuilt.
No saved new beta, exponent, or candidate expression is copied.
"""
from pathlib import Path
import argparse,subprocess,sys,os,shutil,json,time,hashlib
SOURCE=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--destination',required=True,type=Path)
 ap.add_argument('--dry-run',action='store_true')
 ap.add_argument('--no-numerical',action='store_true')
 a=ap.parse_args();dst=a.destination.resolve()
 req=json.loads((SOURCE/'C7_raw_requirements.json').read_text());raws=sorted({t for vs in req['all'].values() for t in vs})
 old='a_check p_check A_check E_check c_check f_check q_check b_check G_check k_check V R J L M N'.split()
 jobs=[['extract_A7_bounded.py','--extract-only'],['assemble_C7.py','alpha','beta','gamma','Phi','Psi','Qnew','Pnew','Knew','Omega'],['derive_D4.py'],['assemble_C7_invariants.py'],['check_Q8_toplogs_fresh.py'],['check_A7v_toplogs_fresh.py']]
 if not a.no_numerical:jobs.append(['evaluate_final_decimal.py','--label','regenerated','--dps','95','--radius','110','--taylor','280','--asymptotic','140','--step','.35','C7','D4_value','Omega'])
 if a.dry_run:
  print(json.dumps({'destination':str(dst),'raw_moments':len(raws),'old_beta_inputs':old,'jobs':jobs},indent=2));return
 if dst.exists() and any(dst.iterdir()):raise SystemExit('Destination must be absent or empty.')
 dst.mkdir(parents=True,exist_ok=True);(dst/'series').mkdir();logs=dst.parent/'logs';logs.mkdir(exist_ok=True)
 for p in SOURCE.glob('*.py'):shutil.copy2(p,dst/p.name)
 used=[]
 for tag in raws:
  p=SOURCE/f'{tag}_negative.json';shutil.copy2(p,dst/p.name);used.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 for tag in old:
  p=SOURCE/f'{tag}_symbolic.expr';shutil.copy2(p,dst/p.name)
 for p in [SOURCE/'C7_raw_requirements.json']:
  shutil.copy2(p,dst/p.name)
 (dst/'reassembly_source_raws.json').write_text(json.dumps(used,indent=2));records=[]
 for i,args in enumerate(jobs):
  cmd=[sys.executable,*args];print('RUN',' '.join(cmd),flush=True);st=time.time()
  with (logs/f'C7_raw_reassembly_{i}.log').open('w') as fp:
   pr=subprocess.run(cmd,cwd=dst,stdout=fp,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
  records.append({'command':cmd,'returncode':pr.returncode,'seconds':time.time()-st});(dst/'C7_raw_reassembly_commands.json').write_text(json.dumps(records,indent=2))
  if pr.returncode:raise SystemExit(pr.returncode)
 print('C7 assembled from raw moment expressions.',flush=True)
if __name__=='__main__':main()
