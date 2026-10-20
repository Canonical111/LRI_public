"""Independent symbolic single-derivative check of the full h8 subtraction."""
from pathlib import Path
import sympy as s,json,time
from read_expression import load
import assemble_C7 as a7
ac=a7.ac;v=ac.v;d=ac.d;ell=ac.ell;ROOT=Path(__file__).resolve().parent
OUT=Path(__file__).resolve().parent.parent/'data';REPORT=Path(__file__).resolve().parent.parent/'verification';REPORT.mkdir(exist_ok=True)
# Read the saved normalized inputs with their explicitly labelled new raw scalars.
def m(name,i=0):return load(ROOT/'series'/f'norm_{name}_{i}_0.expr').coeff(ell,0)
def b(name):return load(ROOT/f'{name}_symbolic.expr')
P8,Xvv,Xe=s.symbols('P8 Xvv Xe')
q,k4,k6,e2,e4,e6,b3,b5,b7,h4,h6,k8=[s.Function(n)(v) for n in ['q','k4','k6','e2','e4','e6','b3','b5','b7','h4','h6','k8']]
l2=-2*q-4*v*s.diff(q,v)+2*v*e2
l4=-2*k4-4*v*s.diff(k4,v)+2*v*e4
l6=-2*k6-4*v*s.diff(k6,v)+2*v*e6
expr=-4*s.diff(k8-2*q*b7-4*k4*b5-6*k6*b3-l2*h6-l4*h4+l6,v)
vals={q:[m('Q2',i) for i in range(3)],k4:[m('K4',i) for i in range(3)],k6:[m('K6',i) for i in range(3)],e2:[m('EQ2',i) for i in range(2)],e4:[m('EK4',i) for i in range(2)],e6:[m('EK6',i) for i in range(2)],b3:[s.S.One,b('a_check')],b5:[b('b_check'),b('G_check')],b7:[b('J'),b('Omega')],h4:[-b('c_check')/4,-b('f_check')/4],h6:[-b('k_check')/4,-b('N')/4]}
subs={s.diff(f,v,i):x for f,jets in vals.items() for i,x in enumerate(jets)}
subs[s.diff(k8,v)]=P8+load(OUT/'F3_vacuum_shift.expr')
st=time.time();actual=s.expand(s.expand_log(expr.xreplace(subs).subs(v,1),force=True));expected=load(OUT/'Kv_with_placeholders.expr');diff=s.expand(actual-expected)
assert diff==0
report={'whole_h8_differentiated_before_evaluation':True,'exact_difference':'0','new_raw_coefficient_checks':{str(x):str(actual.coeff(x)) for x in [P8,Xvv,Xe]},'seconds':time.time()-st}
(REPORT/'independent_derivative.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
