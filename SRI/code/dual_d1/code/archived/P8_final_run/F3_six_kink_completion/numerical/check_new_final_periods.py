"""Independent Decimal checks of deterministic new P8 and J9 periods."""
from pathlib import Path
from decimal import Decimal,localcontext
import hashlib,json,time
import mpmath as mp
from evaluate_periods_decimal import evaluate
ROOT=Path(__file__).resolve().parent.parent

def main():
 tables=[ROOT/'F3_final/eval100.periods.json',ROOT/'F4_data/full100.periods.json'];merged={};samples=set();records=[]
 for path in tables:
  raw=json.loads(path.read_text());ordered=sorted((tuple(map(int,k.split(','))) for k in raw),key=lambda w:hashlib.sha256(str(w).encode()).hexdigest());chosen=set(ordered[:30])
  for size in (5,6,7):
   for zero in (False,True):
    w=next((w for w in ordered if len(w)==size and (w[0]==0)==zero),None)
    if w:chosen.add(w)
  samples.update(chosen);merged.update({tuple(map(int,k.split(','))):v for k,v in raw.items()});records.append({'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sample_words':list(map(list,sorted(chosen)))})
 closed={(a,)+(1,)*(n-1) for a in (1,2,3,6) for n in (1,2,4,7)};start=time.time()
 values=evaluate(samples|closed,dps=70,R=115,ntaylor=265,nasym=175,stepfrac='.27')
 with localcontext() as ctx:
  ctx.prec=100;maximum=max(abs(values[w]-Decimal(merged[w])) for w in samples)
 mp.mp.dps=95;cm=mp.mpf(0)
 for w in closed:
  expected=-mp.log(w[0]) if len(w)==1 else mp.polylog(len(w),1-w[0]);cm=max(cm,abs(mp.mpf(str(values[w]))-expected))
 assert maximum<Decimal('1e-60') and cm<mp.mpf('1e-60'),(maximum,cm)
 report={'complete':True,'sample_periods':len(samples),'closed_controls':len(closed),'maximum_absolute_difference':str(maximum),'maximum_closed_difference':mp.nstr(cm,50),'all_controlled_below_1e_minus60':True,'numerical_interval_not_certified':True,'sources':records,'seconds':time.time()-start}
 out=ROOT/'verification';out.mkdir(exist_ok=True);(out/'independent_final_period_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
