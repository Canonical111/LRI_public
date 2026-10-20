"""Aggregate measured timings only; never fit the physical thermal curve."""
from pathlib import Path
import csv,json,statistics
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
records=[json.loads(p.read_text()) for p in sorted((ROOT/'results/benchmarks').glob('*.json')) if not p.name.startswith('profile_')]
out=ROOT/'results/tables';out.mkdir(exist_ok=True,parents=True)

def table(name,rows):
 if not rows:return
 with (out/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
solves=[];differences=[]
for L,x in sorted({(d['L'],d['x']) for d in records if d['task']=='solve'}):
 pair={}
 for imp in ['original','optimized']:
  ds=[d for d in records if d['task']=='solve' and (d['L'],d['x'],d['implementation'])==(L,x,imp)]
  if not ds:continue
  pair[imp]=ds
  solves.append({'L':L,'x':x,'implementation':imp,'backend':ds[0]['backend'],'threads':ds[0]['threads'],
   'independent_processes':len(ds),'median_seconds':statistics.median(d['elapsed_seconds'] for d in ds),
   'minimum_seconds':min(d['elapsed_seconds'] for d in ds),'maximum_seconds':max(d['elapsed_seconds'] for d in ds),
   'median_peak_RSS_MiB':statistics.median(d['peak_rss_kib']/1024 for d in ds),
   'Delta_thermal':ds[0]['result']['Delta_thermal']})
 if len(pair)==2:
  ref=pair['original'][0]['result'];new=pair['optimized'][0]['result']
  differences.append({'L':L,'x':x,'speed_ratio':statistics.median(d['elapsed_seconds'] for d in pair['original'])/statistics.median(d['elapsed_seconds'] for d in pair['optimized']),
   'thermal_difference':abs(new['Delta_thermal']-ref['Delta_thermal']),
   'max_five_level_difference':max(np.max(abs(np.array(new[k])-ref[k])) for k in ['even_gaps','odd_gaps']),
   'max_coupling_coordinate_difference':max(abs(np.array(new['theta'])-ref['theta'])),
   'max_window_difference':max(abs(new['window_correction']['D_by_N'][k]-v) for k,v in ref['window_correction']['D_by_N'].items()),
   'optimized_tuning_residual':new['tuning_residual'],'optimized_eigenvector_residual':new['max_eigenvector_residual']})
table('full_solve_timings.csv',solves);table('numerical_comparisons.csv',differences)
ops=[]
for d in records:
 if d['task']=='operator':
  ops.append({'L':d['L'],'implementation':d['implementation'],'backend':d['backend'],'threads':d['threads'],
   'full_bath_dimension':d['full_dimension'],'scalar_bath_dimension':d['scalar_bath_dimension'],
   'median_matvec_ms':1000*statistics.median(d['matvec_seconds']),
   'operator_arrays_MiB':d['operator_storage_bytes']/1024**2,'process_peak_RSS_MiB':d['peak_rss_kib']/1024,
   'basis_seconds':d['basis_seconds'],'operator_setup_seconds':d['operator_setup_seconds']})
table('operator_timings.csv',ops)
bases=[]
for d in records:
 if d['task']=='basis':bases.append({'L':d['L'],'implementation':d['implementation'],'bath_dimension':d['full_dimension'],
    'basis_seconds':d['elapsed_seconds'],'numeric_arrays_MiB':d['numeric_array_bytes']/1024**2,'process_peak_RSS_MiB':d['peak_rss_kib']/1024})
table('basis_scaling.csv',bases)
summary={'full_solves':solves,'comparisons':differences,'operators':ops,'basis':bases,'record_count':len(records),
 'scope':'Implementation performance and finite-problem equality. Not physical continuum accuracy or target-cluster performance.'}
(ROOT/'results/SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print('Aggregated',len(records),'independent process records')
