from read_expression import load as load_expr
"""Fresh high-precision assembly from exact regulated-period expressions.
Each run changes its numerical integration settings and uses no archived
coefficient values or proposed closed forms as numerical input.
"""
import argparse,json,time
from pathlib import Path
import sympy as s,mpmath as mp
from evaluate_periods import evaluate
ROOT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--label',default='run1');ap.add_argument('--dps',type=int,default=80);ap.add_argument('--radius',type=int,default=100);ap.add_argument('--taylor',type=int,default=250);ap.add_argument('--asymptotic',type=int,default=120);ap.add_argument('--step',default='.4');ap.add_argument('names',nargs='*');args=ap.parse_args()
names=args.names or ['C6','T3','J','N','R','L','M','V','B_old','a_check','p_check','A_check','E_check','c_check','f_check','q_check','b_check','G_check','k_check']
exprs={name:load_expr(ROOT/(name+'_symbolic.expr')) for name in names}
syms=set().union(*(x.free_symbols for x in exprs.values()))
reg={x:tuple(int(t[1:]) if t.startswith('m') else int(t) for t in str(x).split('_')[1:]) for x in syms if str(x).startswith('R_')}
print('required periods',len(set(reg.values())),'maximum weight',max(map(len,reg.values())),flush=True)
start=time.time();vals=evaluate(set(reg.values()),dps=args.dps,R=args.radius,ntaylor=args.taylor,nasym=args.asymptotic,stepfrac=args.step)
sub={x:s.Float(mp.nstr(vals[w],args.dps),args.dps) for x,w in reg.items()};sub.update({s.Symbol(f'Z{k}'):s.Float(mp.nstr(mp.zeta(k),args.dps),args.dps) for k in range(2,7)})
out={}
for name,ex in exprs.items():
 nu=s.N(ex.xreplace(sub),args.dps-15);assert not nu.free_symbols,(name,nu.free_symbols)
 out[name]=str(nu);print(name,nu,flush=True)
record={'settings':vars(args),'coefficients':out,'period_count':len(reg),'seconds':time.time()-start,'qualification':'Numerical convergence is not an interval-certified bound.'}
(ROOT/f'final_evaluation_{args.label}.json').write_text(json.dumps(record,indent=2))
(ROOT/f'final_periods_{args.label}.json').write_text(json.dumps({','.join(map(str,w)):mp.nstr(v,args.dps) for w,v in vals.items()},indent=2))
print('DONE',args.label,'seconds',record['seconds'],flush=True)
