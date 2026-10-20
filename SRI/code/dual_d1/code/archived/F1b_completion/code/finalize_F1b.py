#!/usr/bin/env python3
"""Assemble the finished F1b checkpoint; do not promote it to a finished F1c."""
from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
import json
ROOT=Path(__file__).resolve().parents[1]

def main():
    exact=json.loads((ROOT/'verification/exact_reassembly.json').read_text())
    assert exact['independent_methods_equal'] and exact['previous_expression_exactly_reproduced']
    assert len(exact['two_kink_coefficients_rederived'])==16
    first=json.loads((ROOT/'verification/numerical_check70.json').read_text())
    second=json.loads((ROOT/'verification/numerical_check100.json').read_text())
    a=first['values'];b=second['values']
    with localcontext() as ctx:
        ctx.prec=100
        agreement={n:str(abs(Decimal(a[n])-Decimal(b[n]))) for n in a}
        assert all(Decimal(x)<Decimal('1e-50') for x in agreement.values())
        group_sum=sum(Decimal(b[n]) for n in ('Q4Z2','Q2Z2sq','Q2Z4'))
        assert abs(group_sum-Decimal(b['Dnorm']))<Decimal('1e-80')
        raw=[]
        for path in sorted((ROOT/'inputs/F1a').glob('*.json')):
            data=json.loads(path.read_text())
            x=Decimal(data['volume_log']['vd'])
            raw.append({'file':str(path.relative_to(ROOT)),'raw_P6':str(x),
                        'normalized_K6_vd_log':str(x+Decimal(b['Dnorm']))})
        result={'status':'F1b_complete_from_exact_archived_lower_moments',
          'definition':'Dnorm=[epsilon^0 log(epsilon)] partial_v partial_delta (-Q4*Z2+Q2*Z2^2-Q2*Z4), at v=1,delta=0',
          'Dnorm':b['Dnorm'],'rational_Dnorm':'-8719/2',
          'exact_expression':'data/Dnorm.expr','three_product_contributions':{n:b[n] for n in ('Q4Z2','Q2Z2sq','Q2Z4')},
          'rational_three_product_contributions':exact['group_rational_projections'],
          'normalized_residue_definition':'P6 + Dnorm',
          'normalized_residue_estimate':'-1408.224',
          'normalized_rational_projection':str(Fraction(399343,2)-Fraction(8719,2)),
          'F1a_run_propagation':raw,
          'observed_F1a_spread_not_error_bound':str(abs(Decimal(raw[0]['raw_P6'])-Decimal(raw[1]['raw_P6']))) if len(raw)==2 else None,
          'period_evaluation_difference':agreement['Dnorm'],
          'all_term_evaluation_differences':agreement,
          'checks':{'input_hashes':32,'two_kink_polynomials_rederived':16,
            'Leibniz_terms':13,'independent_jet_product_exact':True,
            'archived_correction_exactly_reproduced':True,
            'fresh_period_runs':2,'numerical_periods':second['period_count']},
          'interval_certified':False,
          'four_kink_integrals_used_as_archived_inputs':True,
          'full_P6_exact_value_evaluated_here':False,
          'F1c_counterterm_subtraction_completed':False,
          'Ndelta_evaluated':False,'C8_full_evaluated':False}
    (ROOT/'result.json').write_text(json.dumps(result,indent=2))
    print('F1b COMPLETE. Dnorm =',result['Dnorm'])
    print('Normalized estimate =',result['normalized_residue_estimate'],'; raw F1a precision remains limiting.')
    return result
if __name__=='__main__':main()
