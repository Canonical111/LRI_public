#!/usr/bin/env python3
"""Summarize retained fresh-process measurements, not extrapolated cluster timings."""
from pathlib import Path
import json,statistics
ROOT=Path(__file__).resolve().parent
rows=[json.loads(p.read_text()) for p in (ROOT/'results').glob('*.json')]
summary=[]
for L,d,t in sorted({(r['cutoff'],r['degree'],r['threads']) for r in rows}):
    groups={b:[r for r in rows if (r['cutoff'],r['degree'],r['threads'],r['backend'])==(L,d,t,b)] for b in ('old','new')}
    if not all(groups.values()):continue
    a,b=groups['old'],groups['new'];ma=statistics.median(x['wall_seconds'] for x in a);mb=statistics.median(x['wall_seconds'] for x in b)
    summary.append(dict(cutoff=L,degree=d,threads=t,n_old=len(a),n_new=len(b),old_median_seconds=ma,new_median_seconds=mb,speedup=ma/mb,
                        old_median_mib=statistics.median(x['peakrss_kib']/1024 for x in a),new_median_mib=statistics.median(x['peakrss_kib']/1024 for x in b),
                        max_coefficient_difference=max(abs(x-y) for ra in a for rb in b for k in ('delta_C','delta_r','delta_g') for x,y in zip(ra[k],rb[k])),
                        new_warmup_seconds=[x['warmup_seconds'] for x in b],
                        optimized_sources=sorted(set(x['optimized_source_sha256'] for x in b))))
obj=dict(scope='Local four-CPU-quota container, fresh processes, warmed compilation. Three trials/configuration; not an Expanse or distributed scaling benchmark.',results=summary)
(ROOT/'SUMMARY.json').write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps(obj,indent=2))
