"""Summaries of measured timings; never infer physical accuracy from residuals."""
from pathlib import Path
import json,csv,statistics as st
R=Path(__file__).resolve().parents[1]
rows=[dict(json.loads(p.read_text()),record=p.name) for p in sorted((R/'results/benchmarks').glob('*.json'))]
out=R/'results/tables';out.mkdir(parents=True,exist_ok=True)
def write(name,data):
 if not data:return
 with (out/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
solves=[];numeric=[]
for L,x in sorted(set((r['L'],r['x']) for r in rows if r['task']=='solve' and not r.get('profile_file') and r['cache_dir'] is None)):
 rec={'L':L,'x':x}
 rr={}
 for impl in ('baseline','optimized'):
  group=[r for r in rows if r['L']==L and r['x']==x and r['implementation']==impl and r['task']=='solve' and not r.get('profile_file') and r['cache_dir'] is None]
  rr[impl]=group;times=[r['total_seconds'] for r in group]
  rec[impl+'_n']=len(group);rec[impl+'_seconds_median']=st.median(times);rec[impl+'_seconds_min']=min(times);rec[impl+'_seconds_max']=max(times)
  rec[impl+'_setup_median']=st.median(r['setup_seconds'] for r in group)
  rec[impl+'_rss_mib_median']=st.median(r['peak_rss_kib']/1024 for r in group)
  rec[impl+'_operator_array_mib']=st.median(r['static_array_bytes']/1024**2 for r in group)
 rec['speedup']=rec['baseline_seconds_median']/rec['optimized_seconds_median'];solves.append(rec)
 for r in rr['optimized']:
  base=next(b for b in rr['baseline'] if b['record'].split('_r')[-1]==r['record'].split('_r')[-1]);a=r['solve'];b=base['solve']
  gaps=max(abs(v-w) for key in ('even_gaps','odd_gaps') for v,w in zip(a[key],b[key]))
  wa=a['window_correction'];wb=b['window_correction']
  numeric.append({'L':L,'x':x,'rep':r['record'].split('_r')[-1][:-5],
   'thermal_difference':abs(a['Delta_thermal']-b['Delta_thermal']),'max_ten_gap_difference':gaps,
   'max_coupling_difference':max(abs(v-w) for v,w in zip(a['theta'],b['theta'])),
   'optimized_tuning_residual':a['tuning_residual'],'optimized_eigen_residual':a['max_eigenvector_residual'],
   'optimized_orthogonality':a['max_orthogonality_residual'],
   'optimized_vacuum_residual':max([wa['top_fixed_point_residual'],*wa['sublevel_fixed_point_residuals'].values()]),
   'baseline_record':base['record'],'optimized_record':r['record']})
write('full_solve_timings.csv',solves);write('numerical_comparisons.csv',numeric)
operators=[]
for r in rows:
 if r['task']=='operator':
  operators.append({k:r[k] for k in ('implementation','L','J','threads','full_bath_states','sector_bath_states','sector_dimension','setup_seconds','median_apply_seconds','static_array_bytes','peak_rss_kib','record')})
write('operator_timings.csv',operators)
setup=[]
for L in sorted(set(r['L'] for r in rows if r['task']=='setup' and r['cache_dir'] is None)):
 for impl in ('baseline','optimized'):
  g=[r for r in rows if r['task']=='setup' and r['L']==L and r['implementation']==impl and r['cache_dir'] is None]
  if not g:continue
  d={'L':L,'implementation':impl,'n':len(g),'full_bath_states':g[0]['full_bath_states'],'sector_bath_states':g[0]['sector_bath_states']}
  for k in ('basis_seconds','projector_seconds','vertex_seconds','setup_seconds','static_array_bytes','peak_rss_kib'):d[k+'_median']=st.median(r[k] for r in g)
  setup.append(d)
write('setup_scaling.csv',setup)
cache=[]
for r in rows:
 if r.get('cache_dir'):
  d={k:r[k] for k in ('task','L','x','record','setup_seconds','peak_rss_kib')}
  d.update(total_seconds=r.get('total_seconds'),**r['cache_counters']);cache.append(d)
write('cache_timings.csv',cache)
summary={'benchmark_records':len(rows),'solves':solves,'max_thermal_difference':max((r['thermal_difference'] for r in numeric),default=0),
 'max_ten_gap_difference':max((r['max_ten_gap_difference'] for r in numeric),default=0),
 'max_tuning_residual':max((r['optimized_tuning_residual'] for r in numeric),default=0),
 'max_eigen_residual':max((r['optimized_eigen_residual'] for r in numeric),default=0),
 'max_vacuum_residual':max((r['optimized_vacuum_residual'] for r in numeric),default=0),'setup':setup}
(R/'results/SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
