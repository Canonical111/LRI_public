#!/usr/bin/env python3
"""Convert HPC per-cutoff outputs to list JSONs and CSVs. No extrapolation changes.

Thermal rows can be loaded with the previous analysis scripts' load() helper.
Use --degree 7 for thermal, --degree 5 (or 3 separately) for phi6.
"""
import argparse,csv,json
from pathlib import Path
from lri_hpc.validate import check_result
p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--task',choices=['thermal','phi6'],required=True)
p.add_argument('--degree',type=int,required=True);p.add_argument('--prefix',type=Path,required=True)
p.add_argument('--source',help='required source_sha256 of every row (campaign export; stale or mixed-source rows are refused)')
a=p.parse_args()
rows=[]
for file in sorted(a.input.glob(f'{a.task}_d{a.degree}_L*.json')):
 r=json.loads(file.read_text())
 if (r['task'],r['degree'])!=(a.task,a.degree):raise ValueError('mixed task/degree')
 if file.name!=f"{r['task']}_d{r['degree']}_L{r['cutoff']}.json":raise ValueError(f'{file}: file name does not match the result identity')
 check_result(r)   # only results passing the acceptance gates are exported
 if a.source and r.get('source_sha256')!=a.source:raise ValueError(f"{file}: source {r.get('source_sha256')} != required {a.source}")
 rows.append(r)
rows.sort(key=lambda r:r['cutoff'])
if not rows:raise SystemExit('No matching completed outputs')
if len({r['cutoff'] for r in rows})!=len(rows):raise ValueError('duplicate cutoff')
a.prefix.parent.mkdir(parents=True,exist_ok=True)
a.prefix.with_suffix('.json').write_text(json.dumps(rows,indent=2)+'\n')
with a.prefix.with_suffix('.csv').open('w',newline='') as f:
 w=csv.writer(f)
 if a.task=='thermal':
  w.writerow(['cutoff']+[f'C{k}' for k in range(a.degree+1)])
  for r in rows:w.writerow([r['cutoff']]+r['C'])
 else:
  w.writerow(['cutoff','prescription']+[f'd{k}' for k in range(a.degree+1)]+[f'C{k}' for k in range(a.degree+1)])
  for r in rows:
   for prescription in ['raw','vacuum_subtracted']:w.writerow([r['cutoff'],prescription]+r[prescription]['D6']+r[prescription]['C'])
print(f'Wrote {len(rows)} cutoff results to {a.prefix}.json and .csv')
