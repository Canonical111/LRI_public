"""Exact rational-sector forecasts of previously fixed trial functions.
The physical result, when available, is read only after the predictions have
been constructed. No forecast is an input to any integral or RG calculation.
"""
from fractions import Fraction as F
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
N=10

def mul(a,b):
 c=[F(0)]*N
 for i,u in enumerate(a):
  for j,v in enumerate(b):
   if i+j<N:c[i+j]+=u*v
 return c

def shifted(a,k):return [F(0)]*k+list(a[:N-k])

def main():
 C=[F(1),F(-2),F(1,2),F(39,16),F(4),F(11249,1024),F(26),F(1798583,32768)]
 # Both fixed log-Gamma dictionaries have a pure-rational log of degree six.
 h=[F(1)]+[-C[n+1]/2 for n in range(1,7)];ell=[F(0)]*8
 for n in range(1,7):ell[n]=h[n]-sum((F(k,n)*ell[k]*h[n-k] for k in range(1,n)),F(0))
 h.append(sum((F(k,7)*ell[k]*h[7-k] for k in range(1,7)),F(0)))
 logforecast=-2*h[7]
 # Fixed unmodified implicit Gamma ansatz: only P survives projection.
 P=[F(0),F(1),F(5,2),F(21,8),F(155,32),F(1075,128),F(8061,512)]
 c=[F(1),F(-2)]
 for n in range(2,9):
  y=[F(0)]+[-v for v in c[1:]];y+= [F(0)]*(N-len(y))
  residual=mul(y,y);residual[2]-=4
  power=[F(1)]+[F(0)]*(N-1)
  for k,p in enumerate(P):
   if k:power=mul(power,y)
   if p:
    for i in range(2,N):residual[i]+=p*power[i-2]
  c.append(residual[n+1]/4)
 assert c[:8]==C
 predictions={'rational_trace_conjecture':str(F(6**4-2**4,8)),
              'quadratic_log_Gamma_and_Borel_Gamma':str(logforecast),
              'unmodified_implicit_Gamma':str(c[8])}
 result={'status':'forecasts_derived_without_new_integral_input','predictions_for_rational_C8':predictions,
         'rational_log_coefficients':list(map(str,ell[1:7])),
         'implicit_trial_matches_first_seven_rational_inputs':True,
         'scope':'formal weight-zero comparisons, not numerical independence of real periods'}
 actual=ROOT/'Task_D_result.json'
 if actual.exists():
  value=F(json.loads(actual.read_text())['C8_weight_zero']);result['independently_evaluated_rational_C8']=str(value)
  result['exact_comparisons']={name:F(q)==value for name,q in predictions.items()}
 (ROOT/'rational_trial_test.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
