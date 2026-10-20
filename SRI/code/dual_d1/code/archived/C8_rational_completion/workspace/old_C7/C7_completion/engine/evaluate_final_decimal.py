from pathlib import Path
import argparse,json,time
import sympy as s
from read_expression import load
from evaluate_periods_decimal import evaluate
ROOT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--label',default='decimal');ap.add_argument('--dps',type=int,default=90);ap.add_argument('--radius',type=int,default=100);ap.add_argument('--taylor',type=int,default=250);ap.add_argument('--asymptotic',type=int,default=130);ap.add_argument('--step',default='.35');ap.add_argument('names',nargs='+');args=ap.parse_args();st=time.time()
exprs={n:load(ROOT/(n+'_symbolic.expr')) for n in args.names};syms=set().union(*(ex.free_symbols for ex in exprs.values()))
reg={x:tuple(int(t[1:]) if t.startswith('m') else int(t) for t in str(x).split('_')[1:]) for x in syms if str(x).startswith('R_')}
print('required periods',len(reg),'max weight',max(map(len,reg.values())),flush=True)
vals=evaluate(set(reg.values()),dps=args.dps,R=args.radius,ntaylor=args.taylor,nasym=args.asymptotic,stepfrac=args.step)
sub={x:s.Float(str(vals[w]),args.dps) for x,w in reg.items()};sub.update({s.Symbol(f'Z{k}'):s.N(s.zeta(k),args.dps) for k in range(2,7)})
out={}
for n,ex in exprs.items():
 val=s.N(ex.xreplace(sub),args.dps-15);assert not val.free_symbols,(n,val.free_symbols);out[n]=str(val);print(n,val,flush=True)
record={'settings':vars(args),'backend':'decimal C implementation','guard_digits':12,'coefficients':out,'period_count':len(reg),'seconds':time.time()-st,'qualification':'Convergence checks, not certified interval enclosures.'}
(ROOT/f'final_evaluation_{args.label}.json').write_text(json.dumps(record,indent=2));(ROOT/f'final_periods_{args.label}.json').write_text(json.dumps({','.join(map(str,w)):str(v) for w,v in vals.items()},indent=2))
print('DONE',args.label,record['seconds'],flush=True)
