"""One fresh process per measurement. Imports excluded; complete trajectory timed."""
from pathlib import Path
import argparse,json,sys,resource,platform,time
import numpy as np
from threadpoolctl import threadpool_info
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'src'),str(root/'reference')]
from lri_spin import Config,run,run_tangent
from lri_spin.io import source_hash
from nrg import run as original_flow
from nrg_tangent import run_tangent as original_tangent

p=argparse.ArgumentParser();p.add_argument('--implementation',choices=['reference','ordered','dense'],required=True)
p.add_argument('--task',choices=['flow','tangent'],required=True);p.add_argument('--keep',type=int,default=64)
p.add_argument('--nb',type=int,default=10);p.add_argument('--nsites',type=int,default=32)
p.add_argument('--threads',type=int,default=1);p.add_argument('--output',required=True)
a=p.parse_args();c=Config(s=.8,Lambda=3,keep=a.keep,nb=a.nb,nsites=a.nsites,threads=a.threads)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lri_spin.campaign import refuse_campaign_destination
refuse_campaign_destination(a.output)   # never write benchmark output into campaign state
alpha=.43977045457263714;tangent=a.task=='tangent'
f=(original_tangent if tangent else original_flow) if a.implementation=='reference' else (run_tangent if tangent else run)
st=time.perf_counter()
r=f(alpha,c) if a.implementation=='reference' else f(alpha,c,backend=a.implementation)
elapsed=time.perf_counter()-st
out={'source_sha256':source_hash(),'implementation':a.implementation,'task':a.task,'config':c.asdict(),'seconds':elapsed,
     'rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
     'cpu_quota':Path('/sys/fs/cgroup/cpu.max').read_text().strip() if Path('/sys/fs/cgroup/cpu.max').exists() else None,
     'platform':platform.platform(),'blas':threadpool_info(),'result':r}
path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(a.implementation,a.task,a.keep,a.nb,a.nsites,a.threads,elapsed,out['rss_mib'],flush=True)
