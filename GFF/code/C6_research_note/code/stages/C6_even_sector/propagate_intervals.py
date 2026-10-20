"""Propagate existing rational intervals through the exact even-sector identity.
No new independent interval evaluation of the even series is claimed.
"""
from pathlib import Path
from fractions import Fraction as F
import json
import dyadic
from dyadic import I,evaluate
from formula import build
ROOT=Path(__file__).resolve().parent
def unpack(obj):
    q=1<<int(obj['denominator_power_of_two'])
    return I.bounds(F(int(obj['lower_numerator']),q),F(int(obj['upper_numerator']),q))
def overlaps(a,b):return a.lower()<=b.upper() and b.lower()<=a.upper()
def main():
    dyadic.set_precision(1280)
    old=json.loads((ROOT/'inputs/complete_intervals.json').read_text())
    seventh=json.loads((ROOT/'inputs/seventh_intervals.json').read_text())
    env={k:unpack(v) for k,v in old['values'].items()}
    p=env['pi'];A=env['A'];Q=env['Q']
    cs=-F(105,4)*A**2-9*A*p+60*Q-F(2469,4)*p**2
    cd=-42*A**2-18*A*p+96*Q-1227*p**2
    old_even=cs*(env['Bminus']+env['Bplus'])+cd*(env['Bminus']-env['Bplus'])
    old_even+=24*env['PB6']+24*env['PZ6']+env['PK6']/3-393*p**3*env['Wcentral']
    env['Ecentral']=(old_even-1048*p**5-655*p**6)/p**3
    env['M7central']=unpack(seventh['runs'][-1]['M7central'])
    out=build()
    rhs=out['formula'].split(' = ',1)[1].replace('known_polynomial','('+out['known_polynomial']+')')
    new=evaluate(rhs,env)/2187
    previous=unpack(seventh['updated_C6_representation'])
    assert overlaps(new,previous)
    res={
      'scope':'Exact outward-rounded propagation of inherited period intervals through the new analytic identity. This is not a new independent interval evaluation of the even series or graph/RG certification.',
      'precision_bits':1280,
      'Ecentral':env['Ecentral'].package(155),
      'C6_representation':new.package(155),
      'overlaps_previous_complete_interval':True,
      'source_correction_unchanged':out['source_correction']==old['unchanged_source_correction'],
      'width_Ecentral_display':f'{float(env["Ecentral"].width()):.6e}',
      'width_C6_display':f'{float(new.width()):.6e}'}
    (ROOT/'results/propagated_intervals.json').write_text(json.dumps(res,indent=2)+'\n')
    return res
if __name__=='__main__':print(json.dumps(main(),indent=2))
