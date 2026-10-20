"""Single clean-process benchmark. Warmup and measured construction are separate."""
from pathlib import Path
import argparse,sys,time,json,resource,cProfile,pstats,io,gc
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'reference/lri_d2_perturbative_C8/code'))
import numpy as np
from numba import set_num_threads,get_num_threads

def main():
 p=argparse.ArgumentParser();p.add_argument('--backend',choices=['reference','optimized'],required=True);p.add_argument('--L',type=int,default=16);p.add_argument('--degree',type=int,default=8);p.add_argument('--scheme',default='consistent');p.add_argument('--threads',type=int,default=1);p.add_argument('--out',type=Path,required=True);p.add_argument('--profile',action='store_true');a=p.parse_args()
 set_num_threads(a.threads)
 if a.backend=='reference':from circle_jets import Engine
 else:from lri_coeff.engine import Engine
 t=time.perf_counter();warm=Engine(10,4,'raw',max_states=3000000);warm.solve(False);del warm;gc.collect();warmtime=time.perf_counter()-t
 prof=cProfile.Profile();prof.enable() if a.profile else None
 t=time.perf_counter();e=Engine(a.L,a.degree,a.scheme,max_states=3000000);bt=time.perf_counter()-t
 result=e.solve(False);elapsed=time.perf_counter()-t;prof.disable()
 from lri_coeff.storage import source_digest
 out=dict(source_digest=source_digest(),backend=a.backend,threads=get_num_threads(),warmup_seconds=warmtime,total_seconds=elapsed,basis_and_init=bt,peak_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,result=result)
 if a.profile:
  text=io.StringIO();pstats.Stats(prof,stream=text).strip_dirs().sort_stats('cumulative').print_stats(40);out['profile']=text.getvalue()
 refp=ROOT/f'reference/lri_d2_perturbative_C8/results/coefficients/{a.scheme}_L{a.L}_d{a.degree}.json'
 if refp.exists():
  old=json.loads(refp.read_text());out['errors']={}
  for name in ['C','r','g','energies','vacuum_coefficients']:
   aa=np.asarray(result[name]);bb=np.asarray(old[name]);diff=abs(aa-bb);out['errors'][name]={'absolute':float(diff.max()),'scaled':float((diff/np.maximum(1,abs(bb))).max())}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:v for k,v in out.items() if k not in ('result','profile')},indent=2));print(result.get('timings'));print(out.get('profile',''))
if __name__=='__main__':main()
