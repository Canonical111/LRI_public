#!/usr/bin/env python3
"""Run reproducible endpoint exclusion checks. See README for scope."""
import argparse,json,subprocess,sys,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--minimal',action='store_true',help='Standard-library interval verification using saved exact expressions only')
 p.add_argument('--numeric',action='store_true',help='Also compare exact jets to independent direct Gamma differentiation')
 a=p.parse_args();root=Path(__file__).resolve().parent
 scripts=['verify_exclusion.py'] if a.minimal else ['exact_endpoint.py','verify_integral_bound.py','verify_exclusion.py']
 if a.numeric:scripts.append('check_direct_gamma.py')
 records=[];(root/'verification').mkdir(exist_ok=True)
 for script in scripts:
  start=time.monotonic()
  r=subprocess.run([sys.executable,str(root/script)],cwd=root,text=True,capture_output=True)
  (root/'verification'/f'{Path(script).stem}.stdout.txt').write_text(r.stdout)
  (root/'verification'/f'{Path(script).stem}.stderr.txt').write_text(r.stderr)
  records.append({'script':script,'exit_code':r.returncode,'seconds':time.monotonic()-start})
  print(('PASS' if r.returncode==0 else 'FAIL')+': '+script,flush=True)
  if r.returncode:break
 report={'scope':'Exact exclusion of the stated global Gamma-family; not a C8 calculation or an all-orders coefficient exclusion without extra assumptions.','checks':records,'all_pass':all(r['exit_code']==0 for r in records)}
 (root/'verification'/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
 if not report['all_pass']:sys.exit(1)
if __name__=='__main__':main()
