import os
from endpoint_growth_finite import *
import growth_linear_periods as g
import random
import asymptotic_gpl as ag
rng=random.Random(7819);count=0
for n in range(8):
 for j in range(4):
  w=tuple(rng.choice([-1,-2,-3,0]) for _ in range(n))
  for p in range(4):
   lhs=s.expand(sum(s.Rational(c.numerator,c.denominator)*ag.Z(a) for a,c in g.phi(w,p,5)))
   rhs=functional(w,p,5)
   assert s.expand(lhs-rhs)==0,(w,p);count+=1
report={'word_lengths':list(range(8)),'polynomial_degrees':[0,1,2,3],'exact_test_cases':count,'all_equal':True,'zero_letters_and_repeated_letters_included':True}
(Path(os.environ.get('F3_REPORT_DIRECTORY',str(ROOT/'data')))/'linear_growth_general_check.json').write_text(json.dumps(report,indent=2));print('LINEAR GENERAL CHECK',report,flush=True)
