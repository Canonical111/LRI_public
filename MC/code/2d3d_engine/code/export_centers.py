#!/usr/bin/env python3
"""Export measured crossing temperatures as provisional centers, never beta_c claims."""
import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('results',type=Path,nargs='+');p.add_argument('--out',type=Path,required=True)
a=p.parse_args();rows=[]
for path in a.results:
 r=json.loads(path.read_text());ok=[v for v in r['rows'] if not v.get('precision_flags')]
 if not ok:raise ValueError(f'no unflagged crossings in {path}')
 for v in ok:rows.append(dict(d=r['d'],s=r['s'],L=v['L2'],beta=v['values'][0]))
 last=max(ok,key=lambda v:v['L2']);rows.append(dict(d=r['d'],s=r['s'],L='',beta=last['values'][0]))
with a.out.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['d','s','L','beta']);w.writeheader();w.writerows(rows)
print('Provisional measured crossings, NOT thermodynamic critical temperatures:',a.out)
