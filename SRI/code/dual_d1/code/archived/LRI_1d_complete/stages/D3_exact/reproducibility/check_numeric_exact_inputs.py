from pathlib import Path
import sympy as s,mpmath as mp,json,inspect
from evaluate_periods import evaluate
mp.mp.dps=90
ROOT=Path(__file__).resolve().parent
names=['Avv3_0_0','Qv4_0_0','Zv4_0_1','Qdelta4_0_1','Av5_0_1','Qbase6_0_1','Zbase4_0_0','qd_symbolic','G_symbolic','k_symbolic','D3_symbolic','D3_difference_symbolic']
expr={n:s.sympify((ROOT/(n+'.expr')).read_text()) for n in names}
reg={a:tuple(int(x[1:]) for x in str(a).split('_')[1:]) for ex in expr.values() for a in ex.free_symbols if str(a).startswith('R_')}
val=evaluate(set(reg.values()),dps=90,ntaylor=270,nasym=120)
values={a:val[w] for a,w in reg.items()};values.update({s.Symbol('Z'+str(j)):mp.zeta(j) for j in range(2,6)})
outputs={}
for n,ex in expr.items():
 args=sorted(ex.free_symbols,key=str);f=s.lambdify(args,ex,'mpmath');v=f(*[values[a] for a in args]);outputs[n]=mp.nstr(v,90);print(n,mp.nstr(v,80),flush=True)
p=8-2*mp.zeta(2)-7*mp.zeta(3)-8*mp.log(2);L=-60+12*mp.zeta(2)+12*mp.zeta(3)+8*mp.zeta(4)
print('q assembly residual',mp.mpf(outputs['qd_symbolic'])+4*(mp.mpf(outputs['Qdelta4_0_1'])-4+2*p+L))
(ROOT/'independent_numeric_verified.json').write_text(json.dumps(outputs,indent=2))
