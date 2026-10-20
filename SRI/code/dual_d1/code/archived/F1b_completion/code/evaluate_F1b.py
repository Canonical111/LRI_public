#!/usr/bin/env python3
"""Fresh full-constant evaluations of F1b. No zeta-basis fitting is used."""
from pathlib import Path
import argparse,json,time
import sympy as s
from archived_read_expression import load
from archived_evaluate_periods_decimal import evaluate
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--label',default='check70')
    ap.add_argument('--dps',type=int,default=70)
    ap.add_argument('--radius',type=int,default=80)
    ap.add_argument('--taylor',type=int,default=210)
    ap.add_argument('--asymptotic',type=int,default=125)
    ap.add_argument('--step',default='.30')
    args=ap.parse_args();start=time.time()
    exprs={p.stem:load(p) for p in (ROOT/'data').glob('*.expr')}
    syms=set().union(*(e.free_symbols for e in exprs.values()))
    reg={x:tuple(int(t[1:]) if t.startswith('m') else int(t) for t in str(x).split('_')[1:])
         for x in syms if str(x).startswith('R_')}
    print('Required periods',len(reg),'max weight',max(map(len,reg.values())),flush=True)
    vals=evaluate(set(reg.values()),dps=args.dps,R=args.radius,ntaylor=args.taylor,nasym=args.asymptotic,stepfrac=args.step)
    sub={x:s.Float(str(vals[w]),args.dps) for x,w in reg.items()}
    numbers={}
    for n,ex in exprs.items():
        value=s.N(ex.xreplace(sub),args.dps-12)
        assert not value.free_symbols,(n,value.free_symbols)
        numbers[n]=str(value)
        if n in ('Q4Z2','Q2Z2sq','Q2Z4','Dnorm'):print(n,value,flush=True)
    closure=set()
    for w in reg.values():
        for j in range(len(w)+1):closure.add(w[j:])
    out={'status':'fresh_period_ODE_evaluation','settings':vars(args),'period_count':len(reg),
         'suffix_closure':len(closure),'values':numbers,'seconds':time.time()-start,
         'interval_certified':False,'full_kernel_reintegration':False,
         'no_earlier_period_table_used':True}
    (ROOT/'verification'/f'numerical_{args.label}.json').write_text(json.dumps(out,indent=2))
    (ROOT/'data'/f'periods_{args.label}.json').write_text(json.dumps({','.join(map(str,w)):str(v) for w,v in vals.items()},indent=2))
    print('DONE',args.label,out['seconds'],flush=True)
if __name__=='__main__': main()
