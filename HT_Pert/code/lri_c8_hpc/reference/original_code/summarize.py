#!/usr/bin/env python3
"""Export raw data without fitting in epsilon; audit lower orders and replays."""
from pathlib import Path
import csv,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def main():
    raw=sorted([json.loads(p.read_text()) for p in (ROOT/'results/raw').glob('*_d8.json')],key=lambda r:r['cutoff'])
    vac=sorted([json.loads(p.read_text()) for p in (ROOT/'results/vacuum_only').glob('*_d8.json')],key=lambda r:r['cutoff'])
    rb={r['cutoff']:r for r in raw}
    prior=list(csv.DictReader((ROOT/'inputs/thermal_coefficients_through_C7.csv').open()))
    lower=[]
    for row in prior:
        L=int(row['cutoff'])
        if L in rb:lower.append(np.array(rb[L]['C'][:8])-np.array([float(row[f'C{i}']) for i in range(8)]))
    with (ROOT/'results/coefficients.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['scheme','cutoff','basis_dimension']+[f'C{i}' for i in range(9)])
        for r in raw+vac:w.writerow([r['scheme'],r['cutoff'],r['basis_dimension']]+r['C'])
    with (ROOT/'results/partial_vacuum_shifts.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['cutoff']+[f'delta_C{i}' for i in range(9)])
        for r in vac:w.writerow([r['cutoff']]+(np.array(r['C'])-rb[r['cutoff']]['C']).tolist())
    old={r['cutoff']:r for r in json.loads((ROOT/'inputs/initial_C8_records.json').read_text())}
    summary={'raw_points':len(raw),'vacuum_only_points':len(vac),
       'max_completed_cutoff':max(rb),'C8_at_50':rb[50]['C'][8],
       'max_abs_lower_order_differences':np.max(np.abs(lower),axis=0).tolist(),
       'max_abs_C8_initial_vs_release':max(abs(r['C'][8]-old[r['cutoff']]['C'][8]) for r in raw),
       'max_abs_shell_residual':max(abs(r['second_order_shell_residual']) for r in raw+vac),
       'max_abs_tuning_residual':max(abs(r['tuning_residual']) for r in raw+vac),
       'max_abs_low_order_residual':max(abs(r['low_order_residual']) for r in raw+vac),
       'scope':'Finite-cutoff coefficients, not a matched physical C8. Partial vacuum correction is not Dconn.'}
    summary['delta_C8_at_50']=next(r['C'][8] for r in vac if r['cutoff']==50)-rb[50]['C'][8]
    (ROOT/'results/SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
