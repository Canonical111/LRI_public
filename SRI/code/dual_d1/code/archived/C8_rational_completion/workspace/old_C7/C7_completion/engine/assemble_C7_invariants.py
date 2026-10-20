from read_expression import load as load_expr
"""Assemble exact C7 from freshly rebuilt beta expressions; never fit the exponent."""
from pathlib import Path
import sympy as s,json,runpy,time,sys,hashlib
ROOT=Path(__file__).resolve().parent
start=time.time()
names='a b c f p A E G q k V R J L M N alpha beta gamma Phi Psi Omega Q P K'.split()
vars={n:s.Symbol(n) for n in names}
if not (ROOT/'D4_symbolic.expr').exists():runpy.run_path(str(ROOT/'derive_D4.py'))
D4formal=load_expr(ROOT/'D4_symbolic.expr',locals=vars)
oldformal=load_expr(ROOT/'old_D4_symbolic.expr',locals=vars)
which={n:n+'_check' for n in ['a','p','A','E','c','f','q','b','G','k']}
which.update({n:n for n in ['V','R','J','L','M','N','alpha','beta','gamma','Phi','Psi','Omega']})
which.update(Q='Qnew',P='Pnew',K='Knew')
record={};mapping={}
for n,f in which.items():
 fp=ROOT/(f+'_symbolic.expr')
 if fp.exists():
  mapping[vars[n]]=load_expr(fp);record[n]={'file':fp.name,'sha256':hashlib.sha256(fp.read_bytes()).hexdigest()}
 elif n!='Omega':raise FileNotFoundError(fp)
old=s.expand(oldformal.xreplace(mapping));assert not set(names)&set(map(str,old.free_symbols)),old.free_symbols
(ROOT/'B4_old_symbolic.expr').write_text(s.sstr(old, order="none"))
Z2,Z3,Z4,Z5,Z6=s.symbols('Z2 Z3 Z4 Z5 Z6')
known=s.Rational(94647,32768)+s.Rational(1011,1024)*Z2+s.Rational(77,4)*Z3-s.Rational(1059,64)*Z4+68*Z5-20*Z2*Z3+s.Rational(343,8)*Z6-16*Z3**2
(ROOT/'C7_known_additive_symbolic.expr').write_text(s.sstr(known, order="none"))
partial=s.expand(D4formal.subs(vars['Omega'],0).xreplace(mapping))
(ROOT/'D4_without_Omega_symbolic.expr').write_text(s.sstr(partial, order="none"))
(ROOT/'C7_without_Omega_symbolic.expr').write_text(s.sstr(s.expand(4*partial+known), order="none"))
status='partial_Omega_missing'
if vars['Omega'] in mapping:
 full=s.expand(partial-mapping[vars['Omega']]/32)
 (ROOT/'D4_symbolic_evaluated.expr').write_text(s.sstr(full, order="none"))
 (ROOT/'D4_value_symbolic.expr').write_text(s.sstr(full, order="none"))
 c7=s.expand(4*full+known);(ROOT/'C7_symbolic.expr').write_text(s.sstr(c7, order="none"))
 assert s.expand(c7-(4*full+known))==0
 status='exact_beta_assembly_complete_pending_numerical_evaluation'
 print('D4 terms',len(s.Add.make_args(full)),'C7 terms',len(s.Add.make_args(c7)),flush=True)
record={'status':status,'inputs':record,'seconds':time.time()-start,'candidate_or_extrapolation_used':False,'known_additive':str(known),'Omega_weight_in_C7':'-1/8'}
(ROOT/'C7_invariant_assembly.json').write_text(json.dumps(record,indent=2))
print(status,'seconds',time.time()-start,flush=True)
