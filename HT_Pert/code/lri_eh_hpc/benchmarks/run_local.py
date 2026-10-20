#!/usr/bin/env python3
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for threads in (1,2,4):
 for backend in ('old','new'):
  for rep in range(3):
   target=ROOT/'results'/f'{backend}_L50_d7_t{threads}_{rep}.json'
   if not target.exists():subprocess.run([sys.executable,str(ROOT/'bench_item.py'),'--backend',backend,'--cutoff','50','--threads',str(threads),'--output',str(target)],check=True)
for L,d in ((60,7),(118,5)):
 for backend in ('old','new'):
  for rep in range(3):
   target=ROOT/'results'/f'{backend}_L{L}_d{d}_t4_{rep}.json'
   if not target.exists():subprocess.run([sys.executable,str(ROOT/'bench_item.py'),'--backend',backend,'--cutoff',str(L),'--degree',str(d),'--threads','4','--output',str(target)],check=True)
