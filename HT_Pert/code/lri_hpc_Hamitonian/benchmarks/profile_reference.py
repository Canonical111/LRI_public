import os
for v in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:
    os.environ[v]='1'
import argparse,cProfile,pstats,io,json,time,resource,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reference'))
p=argparse.ArgumentParser();p.add_argument('--cutoff',type=int,default=24);p.add_argument('--task',choices=['thermal','phi6'],default='thermal');p.add_argument('--out',required=True);a=p.parse_args()
if a.task=='thermal':
 from check_lri_C7 import compute
else:
 from compute_phi6 import compute
pr=cProfile.Profile();t=time.perf_counter();pr.enable();r=compute(a.cutoff);pr.disable();total=time.perf_counter()-t
pr.dump_stats(a.out+'.prof')
s=io.StringIO();pstats.Stats(pr,stream=s).sort_stats('cumulative').print_stats(45)
Path(a.out+'.txt').write_text(s.getvalue());print(s.getvalue())
Path(a.out+'.json').write_text(json.dumps({'result':r,'profiled_seconds':total,'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2))
