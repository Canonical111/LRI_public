import os
"""Fresh independent Decimal evaluation of deterministic new-period samples."""
from pathlib import Path
from decimal import Decimal,localcontext
import json,hashlib,time
import mpmath as mp
from evaluate_periods_decimal import evaluate
ROOT=Path(__file__).resolve().parent.parent

def main():
 table=json.loads((ROOT/'data/XE_second90.periods.json').read_text())
 ordered=sorted((tuple(map(int,k.split(','))) for k in table),key=lambda w:hashlib.sha256(str(w).encode()).hexdigest())
 sample=set(ordered[:40])
 for n in range(3,8):
  zero=next((w for w in ordered if w[0]==0 and len(w)==n),None)
  if zero:sample.add(zero)
 closed={(a,)+(1,)*(n-1) for a in (1,2,3,6) for n in (1,2,4,7)}
 st=time.time();vals=evaluate(sample|closed,dps=65,R=100,ntaylor=230,nasym=150,stepfrac='.28')
 with localcontext() as ctx:
  ctx.prec=90;err=max(abs(vals[w]-Decimal(table[','.join(map(str,w))])) for w in sample)
 mp.mp.dps=80;cerr=mp.mpf(0)
 for w in closed:
  ex=-mp.log(w[0]) if len(w)==1 else mp.polylog(len(w),1-w[0]);cerr=max(cerr,abs(mp.mpf(str(vals[w]))-ex))
 assert err<Decimal('1e-50') and cerr<mp.mpf('1e-50'),(err,cerr)
 report={'fresh_decimal_sample_periods':len(sample),'closed_period_controls':len(closed),'max_vs_fresh_gmp_difference':str(err),'max_closed_difference':mp.nstr(cerr,30),'target_period_table_sha256':hashlib.sha256((ROOT/'data/XE_second90.periods.json').read_bytes()).hexdigest(),'sample_words':[list(w) for w in sorted(sample)],'seconds':time.time()-st,'interval_certified':False}
 (Path(os.environ.get('F3_REPORT_DIRECTORY',str(ROOT/'data')))/'independent_new_period_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
