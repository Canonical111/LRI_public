import lower_controls as lc,json,time
from fractions import Fraction as F
st=time.time()
t=lc.raw(6,'Q','v',0)
assert t[0][1]==-5140
# Independently check the undifferentiated Q8 singular normalization identity.
terms=[(1,[(6,'Q'),(2,'Z')]),(-1,[(4,'Q'),(2,'Z'),(2,'Z')]),(1,[(4,'Q'),(4,'Z')]),(1,[(2,'Q'),(2,'Z'),(2,'Z'),(2,'Z')]),(-2,[(2,'Q'),(2,'Z'),(4,'Z')]),(1,[(2,'Q'),(6,'Z')])]
expected={}
for sign,fs in terms:
 prod={0:(F(1),)}
 for n,k in fs:prod=lc.mult(prod,lc.raw(n,k,'base',1 if k=='Q' else 0),maxp=4)
 for p,poly in prod.items():
  if p<0:expected[p]=lc.tp.padd(expected.get(p,()),tuple(sign*x for x in poly))
actual=lc.raw(8,'Q','base',-1)
for p in [-3,-2,-1]:assert expected[p]==actual[p],(p,expected[p],actual[p])
r={'status':'independent_lower_controls_pass','Q6_v_residue_from_complete_archived_volume':'-5140','Q8_base_singular_polynomials':{str(p):list(map(str,v)) for p,v in actual.items()},'every_singular_polynomial_matches_normalization_exactly':True,'seconds':time.time()-st}
(lc.ROOT/'lower_reference_checks.json').write_text(json.dumps(r,indent=2));print(r)
