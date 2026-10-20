"""Full unprojected eight-kink charge-beta reduction; isolate three new scalars."""
from pathlib import Path
import sympy as s,json,time,hashlib
import assemble_C7 as a7
ac=a7.ac;ell=ac.ell
from read_expression import load
OUT=Path(__file__).resolve().parent.parent/'data';OUT.mkdir(exist_ok=True,parents=True)
ROOT=Path(__file__).resolve().parent
P8,Xvv,Xe=s.symbols('P8 Xvv Xe')
original=ac.ms.pol
req=set()
def partial_polynomial(tag, known):
 # Unknown log coefficients are explicit placeholders, not implicit zeros.
 # Only the specified coefficients are used by the present F3 recurrence.
 return sum(known.get(m, s.Symbol(f'Unknown_{tag}_l{m}'))*ell**m for m in range(11))

def get(n,kind,deriv='base',p=0):
 if (n,kind,deriv,p)==(8,'Q','v',0):return partial_polynomial('Q8v', {1:P8})
 if (n,kind,deriv,p)==(6,'Q','vv',0):return partial_polynomial('Q6vv', {0:Xvv})
 if (n,kind,deriv,p)==(6,'EQ','v',0):return partial_polynomial('EQ6v', {0:Xe})
 req.add((n,kind,deriv,p))
 return original(n,kind,deriv,p)
ac.ms.pol=get
# These new normalized expressions must not reuse an unrelated cache.
for name in ['norm_K8_1_0.expr','norm_K6_2_0.expr','norm_EK6_1_0.expr']:
 p=ROOT/'series'/name
 if p.exists():p.unlink()
def mom(name,iv=0):return ac.npol(name,iv,0).coeff(ell,0)
def coef(name):return load(ROOT/(name+'_symbolic.expr'))
def save(name,ex):
 ex=s.expand(s.expand_log(ex,force=True));(OUT/(name+'.expr')).write_text(s.sstr(ex,order='none'));print('SAVED',name,len(s.Add.make_args(ex)),flush=True);return ex
st=time.time()
q,qv,qvv=[mom('Q2',i) for i in range(3)]
k4,k4v,k4vv=[mom('K4',i) for i in range(3)]
k6,k6v,k6vv=[mom('K6',i) for i in range(3)]
eq,eqv=[mom('EQ2',i) for i in range(2)]
e4,e4v=[mom('EK4',i) for i in range(2)]
e6,e6v=[mom('EK6',i) for i in range(2)]
b3=1;av=coef('a_check');b5=coef('b_check');b5v=coef('G_check');b7=coef('J');b7v=coef('Omega')
h4=-coef('c_check')/4;h4v=-coef('f_check')/4;h6=-coef('k_check')/4;h6v=-coef('N')/4
l2=-2*q-4*qv+2*eq;l2v=-6*qv-4*qvv+2*eq+2*eqv
l4=-2*k4-4*k4v+2*e4;l4v=-6*k4v-4*k4vv+2*e4+2*e4v
l6v=-6*k6v-4*k6vv+2*e6+2*e6v
norm=ac.npol('K8',1,0).coeff(ell,1)-P8
norm=save('F3_vacuum_shift',norm)
ct=save('F3_ct_without_P8', -4*(-2*(qv*b7+q*b7v)-4*(k4v*b5+k4*b5v)-6*(k6v+k6*av)-(l2v*h6+l2*h6v)-(l4v*h4+l4*h4v)+l6v))
full=save('Kv_with_placeholders',-4*(P8+norm)+ct)
assert not any(str(x).startswith('Unknown_') for x in full.free_symbols)
assert full.coeff(P8)==-4 and full.coeff(Xvv)==16 and full.coeff(Xe)==-8
known=save('F3_lower_shift',full.subs({P8:0,Xvv:0,Xe:0}))
positive={a:0 for a in known.atoms(s.Symbol,s.Function) if str(a).startswith(('R_','Z')) or a.func in (s.log,s.polylog,s.zeta)}
rat=s.expand(known.xreplace(positive).subs(s.pi,0))
report={'definition':'Kv = -4 P8 + 16 Xvv - 8 Xe + F3_lower_shift','P8':'[epsilon^0 logepsilon] d_v Q8','Xvv':'[epsilon^0 logepsilon^0] d_v^2 Q6','Xe':'[epsilon^0 logepsilon^0] E d_v Q6','rational_shift':str(rat),'expected_rational_shift':'-952496/3','coefficients':{'P8':'-4','Xvv':'16','Xe':'-8'},'raw_requests':list(sorted(req)),'elapsed':time.time()-st}
assert rat==s.Rational(-952496,3),rat
(OUT/'F3_shift_assembly.json').write_text(json.dumps(report,indent=2));print('COMPLETE',rat,flush=True)
