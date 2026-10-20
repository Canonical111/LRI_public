import sys,json,cProfile,pstats,time,resource,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'reference'))
from fast_response import FastDressedZero
import numpy as np
p=cProfile.Profile();p.enable();t=time.perf_counter()
h=FastDressedZero(12,20,160);h.set_delta(.1)
seed=json.loads((root/'inputs/N12_z20_o160_d0.10000000.json').read_text())['theta']
seed=np.array(seed)+[.03,.001]
a=h.solve(seed)
p.disable();a['wall_including_setup']=time.perf_counter()-t;a['rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
(root/'benchmarks/reference_profile_result.json').write_text(json.dumps(a,indent=2))
p.dump_stats(str(root/'benchmarks/reference.prof'))
with (root/'benchmarks/reference_profile.txt').open('w') as f:pstats.Stats(p,stream=f).strip_dirs().sort_stats('cumulative').print_stats(40)
print('time',a['wall_including_setup'],'rss',a['rss_mib'],'answer',a['Delta_thermal'])
print((root/'benchmarks/reference_profile.txt').read_text())
