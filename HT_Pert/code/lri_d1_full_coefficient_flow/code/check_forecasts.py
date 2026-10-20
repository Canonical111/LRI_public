"""Evaluate frozen forecasts only; never changes their designs or training data."""
from pathlib import Path
import json,csv,hashlib
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'results/frozen_forecasts.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()==(ROOT/'results/forecast_sha256.txt').read_text().split()[0]
records=json.loads(p.read_text());new={int(f.stem.split('_L')[1].split('_')[0]):json.loads(f.read_text()) for f in (ROOT/'results/new_coefficients').glob('dconn_L*_d8.json')}
rows=[]
for r in records:
 if r['status']!='completed':continue
 for cut,fore in r['predictions'].items():
  L=int(cut)
  if L not in new:continue
  for n in [6,7,8]:
   if n<8 and L<=28:continue
   a=float(fore[str(n)]);b=new[L]['C'][n]
   rows.append(dict(lo=r['lo'],base=r['base'],model=r['mode'],cutoff=L,coefficient=n,predicted=a,calculated=b,error=a-b,relative_error=(a-b)/abs(b),scope='Model prediction test, not a continuum error'))
with (ROOT/'results/forecast_validation.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
last=max(new)
for r in rows:
 if r['cutoff']==last:print(r)
