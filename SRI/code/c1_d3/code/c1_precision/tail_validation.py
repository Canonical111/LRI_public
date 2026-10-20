"""GFF tests of the radial remainder inequalities; quadrature stability."""
import json,numpy as np
from pathlib import Path
from spectrum import S,E
from tail_integral_probe import rho,prep_even,oddbound,integrate_tails,radialP
ROOT=Path(__file__).resolve().parent

def gff_checks():
 out=[]
 for D in [S,E]:
  G=2*D
  for x in [.2,.35,.49]:
   A=(x/(1-x))**(2*D);r1=rho(x);r2=rho(1-x)
   upper=(1/A-1)/(1-(r1/r2)**G/A)
   ratios=[]
   for r in np.linspace(.001,r2,100):
    z=4*r/(1+r)**2
    actual=z**(2*D)+(z/(1-z))**(2*D)
    bound=upper*(r/r2)**G
    ratios.append(actual/bound)
   if max(ratios)>1+1e-12:raise RuntimeError('Identical-channel GFF bound failed')
   out.append(dict(D=D,x=x,max_actual_over_upper=max(ratios)))
 # Reflection-positive prefactor for two distinct, independent GFF fields.
 r=np.linspace(.001,.4,80);x=4*r/(1+r)**2
 lhs=radialP(r)*x**(S+E)*(1-x)**(-2*S)
 rhs=(4*r)**(S+E)/(1-r)**(2*(S+E))
 rel=float(np.max(abs(lhs-rhs)/rhs))
 if rel>=1e-12:raise RuntimeError('Mixed GFF normalization check failed')
 return dict(identical_remainder_tests=out,mixed_radial_prefactor_relative_error=rel)

if __name__=='__main__':
 fs=prep_even('sigma',gap=8,nsig=2);fe=prep_even('epsilon',gap=8,nsig=2)
 anchors=[oddbound(x,fs,fe,nsig=2) for x in [2/3,.68,.7,.75,.8]]
 tests=[]
 for n in [60,100,140]:
  b,ae,ao=integrate_tails(fs,fe,anchors,8,nr=n,na=n)
  tests.append(dict(nodes=n,b_tail_estimate=b,a_even_tail_estimate=ae,a_odd_tail_estimate=ao,C1_tail_estimate=(ae+ao+.273152423826*b)/12.254914105481))
 out=dict(gff=gff_checks(),quadrature=tests)
 json.dump(out,open(ROOT/'tail_validation_results.json','w'),indent=2);print(out,flush=True)
