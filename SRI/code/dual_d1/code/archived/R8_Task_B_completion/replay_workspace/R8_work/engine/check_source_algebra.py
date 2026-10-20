"""Independent exact source and expanded-numerator parser checks."""
from pathlib import Path
import random,json,time
import scaled_b as sb
from hyperlog_core import *
from factored_field import Frac
from sympy.polys.domains import QQ
ROOT=sb.ROOT

def main():
 st=time.time();tests=[]
 for n in (4,6):
  for face in range(1,n//2+1):
   fac,ins,N,ids=sb.setup_scaled(n,face)
   W=K.one
   for f,p in fac:W*=f**p
   pp,po=apart(W,1)
   expected={('poly',K.zero,k):c for k,c in pp.items()}
   expected.update({('pole',a,k):c for (a,k),c in po.items()})
   got={}
   for kind,a,k,c in sb.tb.pp_factored(fac):addto(got,(kind,a,k),c)
   got=clean(got)
   assert set(got)==set(expected),(n,face,'keys',len(got),len(expected))
   for key in got:assert not got[key]-expected[key],(n,face,key)
   tests.append({'n':n,'face':face,'principal_parts':len(got),'matches_generic_Laurent_algorithm_exactly':True})
   print('SOURCE_CHECK',tests[-1],time.time()-st,flush=True);sb.tb.br.rr.clear()
 # Eight-kink rational one-variable slices check the same formulas without
 # expanding an unnecessary six-variable common numerator.
 for face in (1,2,3,4):
  fac,ins,N,ids=sb.setup_scaled(8,face)
  got0=sb.tb.pp_factored(fac)
  for sample in range(3):
   def spec(r):
    for i in range(2,N+1):r=sub(r,i,K((i+1)**2+sample*(i+2))/K(sample+1))
    return r
   W=K.one
   for f,p in fac:W*=spec(f)**p
   pp,po=apart(W,1)
   expected={('poly',K.zero,k):c for k,c in pp.items()}
   expected.update({('pole',a,k):c for (a,k),c in po.items()})
   got={}
   for kind,a,k,c in got0:addto(got,(kind,spec(a),k),spec(c))
   got=clean(got)
   assert set(got)==set(expected),(face,sample,'slice keys')
   for key in got:assert not got[key]-expected[key]
   tests.append({'n':8,'face':face,'rational_slice':sample,'generic_univariate_identity_exact':True})
  print('EIGHT_KINK_SLICE_CHECK',face,time.time()-st,flush=True);sb.tb.br.rr.clear()
 # Build polynomials from coefficient dictionaries, independently of parser.
 rng=random.Random(190831);ptests=[]
 for j in range(8):
  d={}
  for k in range(1200):
   m=[0]*K.ngens
   for i in range(1,7):m[i]=rng.randrange(0,5)
   d[tuple(m)]=QQ(rng.randrange(-100,101),rng.randrange(1,19))
  num=K.ring.from_dict(d)
  r=K(num)/(GEN[2]-GEN[1]+2)**2/(GEN[6]+3)**3
  text=str(r);assert len(text)>15000
  parsed=K.from_expr(text)
  assert parsed.numer==r.numer and parsed.denf==r.denf
  ptests.append({'case':j,'monomials':len(num),'text_characters':len(text),'coefficient_dictionary_equal':True})
  print('PARSER_CHECK',ptests[-1],flush=True)
 result={'status':'exact_source_algebra_and_large_parser_pass','initial_pole_checks':tests,'independent_large_numerator_checks':ptests,'seconds':time.time()-st}
 (ROOT/'source_algebra_checks.json').write_text(json.dumps(result,indent=2));print('PASS',flush=True)
if __name__=='__main__':main()
