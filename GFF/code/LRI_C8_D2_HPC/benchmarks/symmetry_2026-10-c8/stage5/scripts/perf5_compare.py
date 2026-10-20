#!/usr/bin/env python3
"""A-PERF-5 on symmetry: the final default binary's speedup over the Stage-3 baseline per (campaign, sector, L), from two
cost models measured on the SAME node on the SAME test-only subset (same plan arguments and seed, identical points):
  perf5_compare.py BASE_MODEL FINAL_MODEL OUT.json
speedup(c, s, L) = sum over the common graphs of baseline seconds per point / the same sum for the final binary (every
graph has the same points, so this is the ratio of total task seconds); also per (sector, L) over both campaigns and the
total, and the L8 cost-weighted share."""
import json,sys
from collections import defaultdict
b=json.load(open(sys.argv[1]));f=json.load(open(sys.argv[2]));out=sys.argv[3]
sb,sf=b['seconds_per_point'],f['seconds_per_point'];keys=sorted(set(sb)&set(sf))
acc=defaultdict(lambda:[0.,0.,0]);acc2=defaultdict(lambda:[0.,0.,0]);tot=[0.,0.,0]
for k in keys:
    c,s,L,g=k.split(':');x=acc[(c,s,int(L))];x[0]+=sb[k];x[1]+=sf[k];x[2]+=1
    y=acc2[(s,int(L))];y[0]+=sb[k];y[1]+=sf[k];y[2]+=1;tot[0]+=sb[k];tot[1]+=sf[k];tot[2]+=1
doc={'rule':'speedup = sum of baseline seconds per point / sum of final seconds per point over the common graphs (equal points per graph); same node, same subset, same seed',
     'baseline':{k:b.get(k)for k in('executable_sha256','cpu_models','hosts','job_ids','source_campaign','keys')},
     'final':{k:f.get(k)for k in('executable_sha256','cpu_models','hosts','job_ids','source_campaign','keys')},'common_keys':len(keys),
     'by_campaign_sector_L':{f'{c}:{s}:{L}':{'graphs':v[2],'baseline_s_per_pt_sum':v[0],'final_s_per_pt_sum':v[1],'speedup':v[0]/v[1]}for (c,s,L),v in sorted(acc.items())},
     'by_sector_L':{f'{s}:{L}':{'graphs':v[2],'speedup':v[0]/v[1]}for (s,L),v in sorted(acc2.items())},
     'total':{'graphs':tot[2],'speedup':tot[0]/tot[1]}}
open(out,'w').write(json.dumps(doc,indent=1)+'\n')
for k,v in doc['by_sector_L'].items():print(k,v['graphs'],round(v['speedup'],3))
print('total',round(doc['total']['speedup'],3))
