#!/usr/bin/env python3
from pathlib import Path
import sys,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import load,dump
inv=load(ROOT/'inputs/inventory.json');paths=[]
for sector,loops in inv.items():
 for L,rows in loops.items():
  selected={r['id']for r in rows[:2]+sorted(rows,key=lambda r:-r['cost'])[:2]}
  source=ROOT/'reference/inputs'/sector
  paths += [str(source/f'L{L}/G{g}.txt')for g in sorted(selected)]
results=[]
with tempfile.TemporaryDirectory(prefix='c7d3_points_')as temp:
 t=Path(temp);f=t/'list';f.write_text('\n'.join(paths)+'\n')
 for backend in ('decimal','gmp'):
  exe=t/backend;cmd=['g++','-O2','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math']
  if backend=='gmp':cmd+=['-DC7_USE_GMP']
  cmd += [str(ROOT/'tests/point_checks.cpp'),'-lquadmath']
  if backend=='gmp':cmd+=['-lgmp']
  subprocess.run(cmd+['-o',str(exe)],check=True);cp=subprocess.run([exe,f],capture_output=True,text=True,check=True);results.append(json.loads(cp.stdout));print(cp.stdout,flush=True)
p=ROOT/'benchmarks/point_checks.json'
if not p.exists():dump(p,results)
