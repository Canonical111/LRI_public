#!/usr/bin/env python3
"""Package existing results, without recomputing the research numerics."""
from pathlib import Path
import csv,json,hashlib
R=Path(__file__).resolve().parents[1]
def read(name):
    rows=list(csv.DictReader((R/'results'/name).open()))
    return [{k:(float(v) if v else None) if k not in ('mode','method','shape','status') else v for k,v in r.items()} for r in rows]
rows=read('curves.csv');held=read('held_out.csv');ratios=read('ratios.csv')
meta=json.loads((R/'results/metadata.json').read_text())
result=dict(curves=rows,held_out=held,ratios=ratios,metadata=meta)
ht=json.loads((R/'results/ht_l20_comparison.json').read_text())
result['ht_l20']=ht['records']
(R/'inputs/plot_data.json').write_text(json.dumps(result,indent=2,allow_nan=False))
stats={}
for key in ['slope_input_allowance','slope_C8_tenfold_allowance','slope_SR_allowance','slope_E_input_allowance','slope_S_input_allowance']:
    rr=max((r for r in rows if r[key] is not None),key=lambda r:r[key])
    stats[key]=dict(maximum=rr[key],x=rr['Delta_sigma'])
for key in ['slope_PB7','slope_PB8_b0','slope_CB6','slope_CB7','direct_CB8','value_CB8',
            'slope_a0.8','slope_a0.9','slope_a1.1','slope_a1.2']:
    rr=max(rows,key=lambda r:abs(r[key]-r['slope_CB8']))
    stats[key]=dict(max_abs_difference=abs(rr[key]-rr['slope_CB8']),x=rr['Delta_sigma'])
stats['A_epsilon']=meta['A_epsilon']
stats['a_epsilon']=meta['a_epsilon']
stats['key_points']=read('key_points.csv')
stats['candidate_ratio_at_n8']=ratios[-1]
stats['prescription_core_max_width']=max(r['slope_core_high']-r['slope_core_low'] for r in rows)
stats['baseline_monotonic_on_grid']=all(b['slope_CB8']>a['slope_CB8'] for a,b in zip(rows,rows[1:]))
stats['all_expected_columns_finite']=all(v is not None for r in rows for k,v in r.items() if k!='slope_S_input_allowance')
(R/'results/comparison_summary.json').write_text(json.dumps(stats,indent=2))
frozen={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((R/'inputs').rglob('*')) if p.is_file() and p.name!='source_checksums.json'}
(R/'inputs/source_checksums.json').write_text(json.dumps(frozen,indent=2))
print(json.dumps({k:v for k,v in stats.items() if k!='key_points'},indent=2))
for r in stats['key_points']:
    if r['Delta_sigma'] in [.55,.6,.65,.7]:
        print({k:r[k] for k in ['Delta_sigma','slope_CB8','slope_PB7','slope_PB8_b0','slope_SR_lower','slope_SR_upper','slope_core_low','slope_core_high']})
