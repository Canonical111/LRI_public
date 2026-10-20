from full_runner import *
import random,sympy as s
sys.path.insert(0,'/mnt/data/P8_final_run');import terminal_fibration as tf
random.seed(235);z2,z3,z5,z7=s.symbols('Z2 Z3 Z5 Z7');st=time.time();cases=0
letters=[0,-1,-2,GEN[6],GEN[6]+1,GEN[6]-1]
for i in range(200):
 n=random.randint(1,6);w=tuple(K(random.choice(letters)) for _ in range(n));ref=endpoint_fibrate(w,6);new=tf.fibrate(tuple(tf.let(str(a)) for a in w));d={}
 for (ww,zm),c in new.items():
  co=s.Rational(c.numerator,c.denominator)*z2**zm[0]*z3**zm[1]*z5**zm[2]*z7**zm[3];d[tuple(ww)]=d.get(tuple(ww),0)+co
 for ww,c in ref.items():
  key=tuple(int(a.as_expr()) for a in ww);co=c.as_expr().subs({s.Symbol('Z4'):s.Rational(2,5)*z2**2,s.Symbol('Z6'):s.Rational(8,35)*z2**3});d[key]=d.get(key,0)-co
 assert all(s.expand(c)==0 for c in d.values()),(w,d)
 cases+=1
print('EXACT_TERMINAL_FIBRATION',cases,time.time()-st,flush=True)
(ROOT/'terminal_fibration_check.json').write_text(json.dumps({'exact_coalescing_cases':cases,'weights_through':6,'full_vs_independent_equal':True,'weight7_table_derived_separately':True,'seconds':time.time()-st},indent=2))
