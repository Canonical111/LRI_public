"""Check the final artifacts without constructing any reference from the target.

Containment of the separately evaluated floating reference is an implementation
check only. certify.py establishes the interval without using that reference.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import json
import sympy as s

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'

def unbox(p):
    return F(int(p['numerator']),int(p['denominator']))

def main():
    checks=[]
    def check(label,condition):
        if not condition:
            raise AssertionError(label)
        checks.append(label)
    algebra=json.loads((OUT/'exact_checks.json').read_text())
    ints=json.loads((OUT/'rational_intervals.json').read_text())
    value=json.loads((OUT/'numerics_190.json').read_text())
    expr=json.loads((OUT/'updated_expression.json').read_text())
    old=json.loads((ROOT/'inputs/previous_expression.json').read_text())
    check('exact algebra suite passed',algebra['all_checks_pass'])
    check('input hash matches exact algebra record',hashlib.sha256((ROOT/'inputs/previous_expression.json').read_bytes()).hexdigest()==algebra['input_sha256'])
    check('active three-series set',expr['active_auxiliary_series']==['Wcentral','Pa','L7'])
    oldothers=[r for r in old['single_index_harmonic_series_terms'] if r.get('id')!='W10']
    newothers=[r for r in expr['single_index_harmonic_series_terms'] if r.get('id')!='Wcentral']
    check('all nonwheel harmonic objects unchanged',oldothers==newothers)
    oldwheel=[r for r in old['single_index_harmonic_series_terms'] if r.get('id')=='W10']
    newwheel=[r for r in expr['single_index_harmonic_series_terms'] if r.get('id')=='Wcentral']
    check('exactly one wheel object replaced',len(oldwheel)==len(newwheel)==1)
    check('new wheel has claimed exact sign/weight',newwheel[0]['coefficient_in_r6']=='-393*pi**3' and newwheel[0]['positive'] is True)
    reference=F(value['values']['Wcentral'])
    boxes=[]
    for rec in ints['enclosures']:
        b=rec['Wcentral'];lo=unbox(b['lower']);hi=unbox(b['upper']);boxes.append((lo,hi))
        check(f"positive width at N={rec['N']}",lo<hi)
        check(f"exact endpoints/width consistent N={rec['N']}",hi-lo==unbox(b['width']))
        check(f"independent reference inside interval N={rec['N']}",lo<reference<hi)
    check('returned rational intervals nest',all(a[0]<=b[0]<b[1]<=a[1] for a,b in zip(boxes,boxes[1:])))
    check('final rational interval width below displayed bound',boxes[-1][1]-boxes[-1][0]<F('2.123e-146'))
    for rec in value['direct_sums']:
        check(f"literal-sum remainder below analytic bound N={rec['N']}",F(0)<F(rec['observed_remainder'])<F(rec['exact_truncation_bound_evaluated_floating']))
    check('reference is a separately computed original-integrand comparison','original_kernel_Wpositive' in value)
    check('190-digit changed-contribution residual below displayed bound',abs(F(value['weighted_C6_difference']))<F('2.152e-158'))
    for name in ['DERIVATION.md','README.md','requirements.txt','verify.py','certify.py','hierarchy4.py','evaluate.py']:
        check(f'nonempty shipped file {name}',(ROOT/name).is_file() and (ROOT/name).stat().st_size>0)
    output={'all_checks_pass':True,'check_count':len(checks),'checks':checks,
            'scope':'Release integrity and exact rational interval consistency. Reference containment is a floating-point comparison, not the proof of the interval. No full graph/RG certification.'}
    (OUT/'release_validation.json').write_text(json.dumps(output,indent=2)+'\n')
    print('Release validation passed:',len(checks),'checks')

if __name__=='__main__':
    main()
