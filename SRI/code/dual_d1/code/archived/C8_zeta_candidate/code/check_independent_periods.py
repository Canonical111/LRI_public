from pathlib import Path
import sys,json,random,time
import mpmath as mp
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'code/numerical'))
from evaluate_periods_decimal import evaluate
source=ROOT/'data/P6_eval100.periods.json'
table=json.loads(source.read_text());keys=sorted(table,key=lambda k:(len(k.split(',')),k))
rng=random.Random(810271)
# Stratify by length, and add explicit zero-head examples.
sample=[]
for n in range(1,8):
 arr=[k for k in keys if len(k.split(','))==n]
 if arr:sample+=rng.sample(arr,min(5,len(arr)))
zero=[k for k in keys if k.startswith('0,')]
sample+=rng.sample(zero,min(6,len(zero)))
sample=sorted(set(sample))
controls=[(a,)*n for a in (1,2,3) for n in (1,2,4,7)]+[(2,)+(1,)*m for m in range(1,7)]
words={tuple(map(int,k.split(','))) for k in sample}|set(controls)
start=time.time();d=evaluate(words,dps=85,R=110,ntaylor=270,nasym=165,stepfrac='.25')
mp.mp.dps=100
comparisons=[]
for k in sample:
 w=tuple(map(int,k.split(',')));err=abs(mp.mpf(str(d[w]))-mp.mpf(table[k]))
 comparisons.append({'word':list(w),'absolute_difference':mp.nstr(err,15)})
closed=[]
for w in controls:
 if len(set(w))==1:exact=(-mp.log(w[0]))**len(w)/mp.factorial(len(w))
 else:
  n=len(w);exact=-(1-mp.power(2,1-n))*mp.zeta(n)
 err=abs(mp.mpf(str(d[w]))-exact);closed.append({'word':list(w),'absolute_difference':mp.nstr(err,15)})
report={'sample_seed':810271,'sample_count':len(sample),'controls':closed,'target_comparisons':comparisons,
'max_target_difference':mp.nstr(max(mp.mpf(x['absolute_difference']) for x in comparisons),20),
'max_closed_difference':mp.nstr(max(mp.mpf(x['absolute_difference']) for x in closed),20),
'algorithm':'Independent Decimal arithmetic with separate recurrence implementation',
'not_a_bound_for_complete_integral':True,'seconds':time.time()-start}
assert mp.mpf(report['max_target_difference'])<mp.mpf('1e-65')
assert mp.mpf(report['max_closed_difference'])<mp.mpf('1e-65')
(ROOT/'verification/replay_independent_period_sample.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['controls','target_comparisons']},indent=2))
