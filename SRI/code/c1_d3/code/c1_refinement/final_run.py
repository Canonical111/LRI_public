import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,numpy as np
from crossing_envelope import Envelope,BASE
from angular_tail import moment_bound
from runtime_config import ratio_interval,EPSILONPRIME_WINDOW
ge=float(sys.argv[1]) if len(sys.argv)>1 else 8
go=float(sys.argv[2]) if len(sys.argv)>2 else 7
padfactor=float(sys.argv[3]) if len(sys.argv)>3 else 1
nit=int(sys.argv[4]) if len(sys.argv)>4 else 10
name=f'final_{ge:g}_{go:g}_pad{padfactor:g}'
env=Envelope(ge,go,level=40,padfactor=padfactor)
o=env.run(nit)
json.dump(o,open(BASE/(name+'.json'),'w'),indent=2)
np.savez_compressed(BASE/(name+'_lp.npz'),A=env.A,B=env.B,Beven=env.Beven,Bodd=env.Bodd)
angular=moment_bound(env,n=100)
json.dump(angular,open(BASE/(name+'_angular.json'),'w'),indent=2)
last=o['iterations'][-1];C=env.reference_C;b=env.reference_b
bs,ae,ao=last['tail_integrals'];positive_ao=min(ao,angular['best_upper']['odd_integral_upper'])
low,hi=last['input_linear_C1_shift'];qpad=last['objective_nonlinear_allowance'];dbmax=env.denominator_box+bs
lo,hi=ratio_interval(C,b,low-qpad-(ae+ao+C*bs)/b,
 hi+qpad+(ae+positive_ao+C*bs)/b,dbmax)
s=dict(interval=[lo,hi],midpoint=(lo+hi)/2,halfwidth=(hi-lo)/2,baseline_C1=C,
 input_linear_shift=last['input_linear_C1_shift'],tail_b=bs,tail_a_even=ae,tail_a_odd=[-ao,positive_ao],
 objective_nonlinear_allowance=qpad,even_gap=ge,odd_gap=go,crossing_padfactor=padfactor,
 h_epsilonprime_interval=list(EPSILONPRIME_WINDOW),level=40,npoints=len(env.z),nparams=len(env.obj),iterations=nit,
 status='Conditional numerical envelope, not a certified physical bound or confidence interval')
json.dump(s,open(BASE/(name+'_summary.json'),'w'),indent=2);print(s,flush=True)
