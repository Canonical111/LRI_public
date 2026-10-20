"""Fresh independent Decimal check of sampled F2 periods and convergent closed values."""
from pathlib import Path
from decimal import Decimal,localcontext
import json,hashlib,time
import mpmath as mp
from evaluate_periods_decimal import evaluate
ROOT=Path(__file__).resolve().parents[1]
def main():
 table=json.loads((ROOT/'verification/run110dfs.periods.json').read_text())
 words=[tuple(map(int,k.split(','))) for k in table]
 ordered=sorted(words,key=lambda w:hashlib.sha256(str(w).encode()).hexdigest())
 sample=set(ordered[:48]);sample.update(next(w for w in ordered if w[0]==0 and len(w)==n) for n in [3,4,5,6,7])
 closed={(a,)+(1,)*(n-1) for a in [1,2,3,6,10] for n in [1,2,4,7]}
 start=time.time();vals=evaluate(sample|closed,dps=75,R=140,ntaylor=260,nasym=165,stepfrac='.28')
 with localcontext() as ctx:
  ctx.prec=100
  err=max(abs(vals[w]-Decimal(table[','.join(map(str,w))])) for w in sample)
 mp.mp.dps=90
 closederr=mp.mpf(0)
 for w in closed:
  expected=-mp.log(w[0]) if len(w)==1 else mp.polylog(len(w),1-w[0])
  closederr=max(closederr,abs(mp.mpf(str(vals[w]))-expected))
 assert err<Decimal('1e-60') and closederr<mp.mpf('1e-60'),(err,closederr)
 r={'fresh_decimal_periods':len(vals),'sample_from_full_F2':len(sample),'closed_period_tests':len(closed),'max_decimal_vs_gmp_difference':str(err),'max_closed_form_difference':mp.nstr(closederr,30),'seconds':time.time()-start,'interval_certified':False}
 (ROOT/'verification/independent_period_check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
if __name__=='__main__':main()
