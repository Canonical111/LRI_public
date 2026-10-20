import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import alternative_models as a
import mpmath as mp
mp.mp.dps=60
C={k:mp.mpf(a.num(e,60)) for k,e in a.input_coeffs().items()}

def pred(N,numer,shift,trans):
    # series starts from Cshift*t**shift. match known tail.
    arr=[C[k]/(mp.factorial(k-shift) if trans=='borel' else 1) for k in range(shift,N+1)]
    m=len(arr)-1;d=m-numer
    try:
        P,Q=mp.pade(arr,numer,d)
        last=-sum(Q[j]*arr[-j] for j in range(1,len(Q)))
        if trans=='borel':last*=mp.factorial(N+1-shift)
        return last
    except Exception as e:return str(e)

for shift in [0,1,2,3]:
 if shift==0:C[0]=mp.mpf(1)
 for tr in ['ordinary','borel']:
  print('\nshift',shift,tr)
  for L in range(0,7-shift):
   print('L',L,'fit6 predict7',mp.nstr(pred(6,min(L,6-shift),shift,tr),12),'fit7 predict8',mp.nstr(pred(7,L,shift,tr),12))
