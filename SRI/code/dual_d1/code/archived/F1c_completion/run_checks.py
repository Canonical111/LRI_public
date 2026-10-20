#!/usr/bin/env python3
"""Verify F1c algebra/data, and optionally perform fresh constant-period evaluations."""
from pathlib import Path
import argparse,subprocess,sys,hashlib,json
ROOT=Path(__file__).resolve().parent
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--numerical',action='store_true')
 ap.add_argument('--reintegrate',choices=['Q4_vvd','EQ4_vd'])
 args=ap.parse_args()
 manifest=json.loads((ROOT/'MANIFEST.json').read_text())
 for name,h in manifest.items():
  path=ROOT/name
  if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=h:
   raise RuntimeError('Missing or changed distributed input: '+name)
 print('All distribution hashes agree.',flush=True)
 # Use a writable copy, preserving the originally delivered record.
 work=ROOT/'replay'
 if work.exists(): raise RuntimeError('Rename or remove the previous replay directory before a fresh run.')
 import shutil
 shutil.copytree(ROOT/'engine',work/'engine')
 shutil.copytree(ROOT/'data',work/'data')
 (work/'logs').mkdir()
 def run(*cmd):
  subprocess.run([sys.executable,*cmd],cwd=work/'engine',check=True)
 if args.reintegrate:
  tag=args.reintegrate
  kind,der=tag.split('_');n=4;kind=kind[:-1]
  run('run_moment.py',str(n),kind,der)
  run('extract_new.py',tag)
  for suffix in ('_negative.json',):
   original=(ROOT/'engine'/(tag+suffix)).read_bytes()
   new=(work/'engine'/(tag+suffix)).read_bytes()
   assert original==new,'Reintegrated raw expression differs'
 run('assemble_F1c.py')
 run('check_Leibniz.py')
 run('check_full_derivative.py')
 run('check_two_kink.py')
 run('extract_finite_exact.py','Q4_vvd','EQ4_vd')
 for x in (ROOT/'data').glob('*.expr'):
  y=work/'data'/x.name
  if y.exists():
   assert x.read_bytes()==y.read_bytes(),'Expression differs: '+x.name
 if args.numerical:
  run('evaluate_F1c.py','--label','replay70','--dps','70','--radius','100',
      '--taylor','240','--asymptotic','135','--step','.3')
 print('F1c checks completed. Fresh files are in replay/.',flush=True)
if __name__=='__main__':main()
