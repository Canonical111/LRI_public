from pathlib import Path
import sys,os,json,time
os.environ['OPENBLAS_NUM_THREADS']='1'
R=Path(__file__).parent
sys.path.insert(0,str(R/'source'))
import ising_five_loop as old
import mpmath as mp
N=int(sys.argv[1]);mp.mp.dps=80
if not 8 <= N <= 48: raise ValueError('Use lower-loop degree from 8 through 48')
(R/'records').mkdir(exist_ok=True)
old.SECTOR_CACHE={n:old.sectors(n,old.graphs(n))for n in range(3,6)}
for cutoff in ['span','maxgap']:
 out={};start=time.time()
 for L in [2,3,4]:
  out[L]=[{str(k):str(v)for k,v in d.items()}for d in old.integrate(L+1,N,cutoff)]
  print('DONE',N,cutoff,L,flush=True)
  (R/'records'/f'lower_{cutoff}_{N}.json').write_text(json.dumps(out,indent=2))
 print('elapsed',time.time()-start,flush=True)
