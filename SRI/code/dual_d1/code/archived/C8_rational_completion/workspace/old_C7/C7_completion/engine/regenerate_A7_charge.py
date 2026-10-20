"""Regenerate the difficult A7 charge derivative with bounded-memory stages.
Use a NEW destination. No old moment, cutoff series, beta coefficient,
numerical period, or exponent candidate is copied into the calculation.
GNU sort must be available for the external exact grouping.
"""
from pathlib import Path
import argparse,subprocess,sys,os,shutil,json,time
SOURCE=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--destination',required=True,type=Path)
 ap.add_argument('--dry-run',action='store_true')
 a=ap.parse_args();dst=a.destination.resolve()
 jobs=[([sys.executable,'run_moment.py','7','A','v'],{'LRI_SECTOR':str(i),'LRI_STOP_AFTER':'3'}) for i in range(4)]
 jobs.extend([([sys.executable,'merge_sector_stages.py','7','A','v','3','4'],{}),([sys.executable,'finish_A7_partitioned.py','--stop-after-four'],{}),([sys.executable,'finish_A7_external.py'],{})])
 if a.dry_run:
  print(json.dumps({'destination':str(dst),'jobs':jobs,'source_inputs':'Python code only; raw kernels generated afresh'},indent=2));return
 if dst.exists() and any(dst.iterdir()):raise SystemExit('Destination must be absent or empty. Existing results are never overwritten.')
 dst.mkdir(parents=True,exist_ok=True);logs=dst.parent/'logs';logs.mkdir(exist_ok=True)
 for p in SOURCE.glob('*.py'):shutil.copy2(p,dst/p.name)
 records=[]
 for index,(cmd,extra) in enumerate(jobs):
  print('RUN',cmd,extra,flush=True);st=time.time()
  with (logs/f'A7_regeneration_{index}.log').open('w') as fp:
   proc=subprocess.run(cmd,cwd=dst,stdout=fp,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1',**extra})
  records.append({'command':cmd,'environment':extra,'returncode':proc.returncode,'seconds':time.time()-st})
  (dst/'A7_regeneration_commands.json').write_text(json.dumps(records,indent=2))
  if proc.returncode:raise SystemExit(proc.returncode)
 assert (dst/'A7_v_negative.json').exists() and (dst/'A7_v_audit.json').exists()
 print('Complete finite-cutoff A7_v integral regenerated. Numerical period evaluation is a separate stage.',flush=True)
if __name__=='__main__':main()
