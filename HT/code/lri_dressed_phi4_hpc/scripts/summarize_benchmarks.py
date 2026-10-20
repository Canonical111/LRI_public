#!/usr/bin/env python3
import json,statistics,csv,platform,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
rows=[json.loads(p.read_text()) for p in sorted((ROOT/'benchmarks/runs').glob('*.json'))]
summary=[];worst=0.;worstcoupling=0.
for N in sorted(set(r['N'] for r in rows)):
    old=[r for r in rows if r['N']==N and r['implementation']=='reference']
    baseline=statistics.median(r['wall_setup_and_solve_seconds'] for r in old)
    old_result=old[0]['result']
    for impl,t in [('reference',1),('tensor',1),('tensor',2),('tensor',4),('ladder',1),('ladder',4)]:
        r=[r for r in rows if r['N']==N and r['implementation']==impl and r['threads']==t]
        if not r:continue
        med=statistics.median(x['wall_setup_and_solve_seconds'] for x in r)
        diff=0.;cdiff=0.
        for rr in r:
            for key in ('Delta_thermal','Delta_sigma_measured','Delta_shadow_measured','even_gaps','odd_gaps'):
                diff=max(diff,float(np.max(abs(np.asarray(rr['result'][key])-old_result[key]))))
            for key in ('r','g'):cdiff=max(cdiff,abs(rr['result'][key]-old_result[key]))
        worst=max(worst,diff);worstcoupling=max(worstcoupling,cdiff)
        summary.append({'bath_cut':N,'nz':r[0]['nz'],'osc':r[0]['osc'],'delta':r[0]['delta'],'implementation':impl,'threads':t,'repetitions':len(r),'median_seconds':med,'min_seconds':min(x['wall_setup_and_solve_seconds'] for x in r),'max_seconds':max(x['wall_setup_and_solve_seconds'] for x in r),'max_peak_rss_mib':max(x['peak_rss_mib'] for x in r),'speedup':baseline/med,'max_gap_difference':diff,'max_coupling_difference':cdiff})
record={'scope':'Local four-CPU-quota measurements; medians of independent processes. Timing includes basis/delta setup and tuning from the same perturbed saved seed, excludes JIT warmup. Peak RSS includes the entire process and warmup. No cluster or MPI speedup claimed.','rows':summary,'maximum_observed_gap_difference':worst,'maximum_observed_coupling_difference':worstcoupling,'large_cutoff_runs':[json.loads(p.read_text()) for p in sorted((ROOT/'benchmarks').glob('large_N*.json'))]}
(ROOT/'benchmarks/SUMMARY.json').write_text(json.dumps(record,indent=2,allow_nan=False))
with (ROOT/'benchmarks/summary.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
print(json.dumps({k:v for k,v in record.items() if k not in ['large_cutoff_runs']},indent=2))
