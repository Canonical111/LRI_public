"""C8 update audit. Run within the numerical Slurm allocation."""
from calculate import *
old=list(csv.DictReader((ROOT/'inputs/previous_curves.csv').open()))
new=list(csv.DictReader((OUT/'curves.csv').open()))
mode=P['baseline']['mode']; baseline=mode+'_CB8'
assert len(old)==len(new)
compare=[]
for a,b in zip(old,new):
 assert abs(float(a['Delta_sigma'])-float(b['Delta_sigma']))<1e-14
 compare.append(dict(Delta_sigma=float(b['Delta_sigma']),CB7_previous=float(a[mode+'_CB7']),CB8_updated=float(b[baseline]),CB8_minus_CB7=float(b[baseline])-float(a[mode+'_CB7']),PB7_previous=float(a[mode+'_PB7']),PB8_updated=float(b[mode+'_PB8']) if mode+'_PB8' in b else None,PB8_b0_updated=float(b[mode+'_PB8_b0']) if mode+'_PB8_b0' in b else None,input_allowance=float(b[mode+'_input_allowance'])))
writecsv('update_comparison.csv',compare)
old7=cb(mode,7)
reg=max(abs(float(a[mode+'_CB7'])-v) for a,v in zip(old,old7))
# Until an updated endpoint changes numerics, this is an exact regression.
assert reg<2e-12
forecasts=list(csv.DictReader((ROOT/'inputs/previous_C8_forecasts.csv').open()))
for f in forecasts:
 f.update(observed_C8=float(C[8]),absolute_relative_error=abs(float(f['predicted_C8'])/float(C[8])-1),status='Historical seventh-order forecast assessed against new measured C8; never fitted')
writecsv('C8_forecast_assessment.csv',forecasts)
stats={'dimension':P['dimension'],'date':'2026-10-12','new_C8':P['C8'],'C8_allowance':P['C8_allowance'],'old_CB7_regression_max':reg,'max_abs_CB8_minus_CB7':max(abs(r['CB8_minus_CB7']) for r in compare),'max_abs_CB8_minus_PB8':max((abs(r['CB8_updated']-r['PB8_updated']) for r in compare if r['PB8_updated'] is not None),default=None),'max_abs_CB8_minus_PB8_b0':max((abs(r['CB8_updated']-r['PB8_b0_updated']) for r in compare if r['PB8_b0_updated'] is not None),default=None),'max_input_allowance':max(r['input_allowance'] for r in compare),'endpoint_source_status':'User confirmed on 2026-10-12 that the unchanged SRI summaries are current.','job_id':os.getenv('SLURM_JOB_ID')}
(OUT/'update_summary.json').write_text(json.dumps(stats,indent=2))
print('UPDATE SUMMARY',json.dumps(stats),flush=True)
