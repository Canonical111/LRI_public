import sys,json,random,importlib.util
from pathlib import Path
import sympy as s
import series_engine as se
root=Path('/mnt/data/lri_special_function_work/original/long_range_ising_complete/reproduction/python/derivation')
spec=importlib.util.spec_from_file_location('original_se',root/'series_engine.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
subs={s.Symbol('A'):old.A}
for n in range(4):
 for key,r in [('j',s.S(1)),('u',s.Rational(1,4)),('v',s.Rational(1,2)),('w',s.Rational(3,4)),('m',s.Rational(-1,4))]:subs[s.Symbol(key+str(n))]=old.psi(n,r)
checks=[]
rng=random.Random(9)
for _ in range(20):
 slopes=list(map(s.Integer,[rng.choice([-3,-2,-1,1,2,3]) for _ in range(5)]));a,b,c,d,e=slopes
 if e==0 or a+c+e==0 or b+d+e==0:continue
 args=tuple(r+v*se.z for r,v in zip(se.TARGET_A,slopes))
 aa=se.a_jet(args)
 try:bb=old.master(*args)
 except (ValueError,ZeroDivisionError):continue
 diff={k:s.simplify(aa.get(k,0).subs(subs)-bb.get(k,0)) for k in range(-2,3)}
 print(slopes,diff,flush=True)
 assert all(v==0 for v in diff.values()),diff
 checks.append(list(map(str,slopes)))
Path(__file__).with_name('A_d1_checks.json').write_text(json.dumps({'paths':checks,'exact_pass':True},indent=2))
