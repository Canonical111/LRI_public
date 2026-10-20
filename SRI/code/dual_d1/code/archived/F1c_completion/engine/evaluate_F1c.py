#!/usr/bin/env python3
from pathlib import Path
import argparse,json,time,hashlib
import sympy as s
from read_expression import load
from evaluate_periods_decimal import evaluate
ROOT=Path(__file__).resolve().parent.parent
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--label',default='run70');ap.add_argument('--dps',type=int,default=70)
 ap.add_argument('--radius',type=int,default=90);ap.add_argument('--taylor',type=int,default=230)
 ap.add_argument('--asymptotic',type=int,default=130);ap.add_argument('--step',default='.3')
 args=ap.parse_args();start=time.time()
 exprs={f.stem:load(f) for f in (ROOT/'data').glob('*.expr')}
 rs={x for e in exprs.values() for x in e.free_symbols if str(x).startswith('R_')}
 words={x:tuple(int(a[1:]) if a.startswith('m') else int(a)
             for a in str(x).split('_')[1:]) for x in rs}
 print('PERIODS',len(words),'max length',max(map(len,words.values())),flush=True)
 values=evaluate(set(words.values()),dps=args.dps,R=args.radius,
                 ntaylor=args.taylor,nasym=args.asymptotic,stepfrac=args.step)
 repl={x:s.Float(str(values[w]),args.dps) for x,w in words.items()}
 repl.update({s.Symbol(f'Z{n}'):s.N(s.zeta(n),args.dps) for n in range(2,9)})
 output={}
 for k,e in exprs.items():
  z=s.N(e.xreplace(repl),args.dps-12)
  assert not z.free_symbols,(k,z.free_symbols)
  output[k]=str(z)
  print(k,z,flush=True)
 report={'settings':vars(args),'values':output,'period_count':len(words),
         'seconds':time.time()-start,'interval_certified':False,
         'raw_integrals_reintegrated_in_this_numerical_run':False,
         'earlier_period_table_used':False}
 (ROOT/'verification').mkdir(exist_ok=True)
 (ROOT/'verification'/f'{args.label}.json').write_text(json.dumps(report,indent=2))
 (ROOT/'data'/f'periods_{args.label}.json').write_text(json.dumps(
     {','.join(map(str,w)):str(v) for w,v in values.items()},indent=2))
if __name__=='__main__':main()
