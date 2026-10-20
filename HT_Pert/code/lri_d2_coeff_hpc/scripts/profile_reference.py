from pathlib import Path
import os, sys, time, cProfile, pstats, json, argparse, resource, io
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reference/lri_d2_perturbative_C8/code'))
from circle_jets import Engine
from numba import set_num_threads

def main():
 p=argparse.ArgumentParser();p.add_argument('--L',type=int,default=16);p.add_argument('--scheme',default='consistent');p.add_argument('--degree',type=int,default=8);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 set_num_threads(1)
 w=Engine(2,4,'raw');w.solve(False);del w
 prof=cProfile.Profile();prof.enable();t=time.perf_counter()
 e=Engine(a.L,a.degree,a.scheme,max_states=10000000);times={'basis_and_init':time.perf_counter()-t}
 for name in ['lower','moments','upper']:
  t=time.perf_counter();getattr(e,name)(False) if name!='moments' else e.moments();times[name]=time.perf_counter()-t
 prof.disable()
 out={'L':a.L,'degree':a.degree,'scheme':a.scheme,'times':times,'total_seconds':sum(times.values()),'rss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'states':e.s.n,'edges':e.s.nnz,'graph_bytes':sum(x.data.nbytes+x.indices.nbytes+x.indptr.nbytes for x in e.s.C),'wave_bytes':sum(c.psi.nbytes for c in e.channels),'C':(e.E[:,e.nv+2]-e.E[:,e.nv]).tolist(),'r':e.r.tolist(),'g':e.g.tolist()}
 ss=io.StringIO();pstats.Stats(prof,stream=ss).strip_dirs().sort_stats('cumulative').print_stats(45);out['profile']=ss.getvalue()
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='profile'},indent=2));print(out['profile'])
if __name__=='__main__':main()
