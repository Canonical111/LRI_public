"""Build the C6 expression with the proved cubic primitive reduction.

Only active primitive fields and current-step metadata change. The complete
quartic expression is retained under inputs/ and its definition is embedded
as legacy metadata. No external connections or numerical fitting are used.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHANGED_FIELDS = {
    'formula', 'scope', 'counts', 'latest_identity', 'active_auxiliary_series',
    'double_index_harmonic_series_terms', 'latest_analytic_reduction',
    'numeric_accuracy_note',
}
NEW_FIELDS = {
    'retained_quartic_primitive_series_terms', 'primitive_cubic_reduction',
    'cubic_reduction_provenance',
}

def build() -> dict:
    path = ROOT / 'inputs/central_expression.json'
    old = json.loads(path.read_text())
    out = copy.deepcopy(old)
    out['formula'] = old['formula'].replace('96*pi*PaCentral', '192*pi**2*PaCubic')
    if out['formula'] == old['formula']:
        raise ValueError('Expected active primitive term was not found.')
    out['scope'] = (
        'An exact contour relation between symmetric beta pairings removes '
        'the quartic logarithmic sector of the primitive. Its new positive '
        'two-index central-binomial summand has harmonic degree and order at '
        'most three. No finite ordinary evaluation of Pa, removal of an '
        'active auxiliary quantity, or new upstream graph/RG certification '
        'is claimed. The known polynomial and other sectors are unchanged.'
    )
    out['retained_quartic_primitive_series_terms'] = copy.deepcopy(
        old['double_index_harmonic_series_terms'])
    out['double_index_harmonic_series_terms'] = [{
        'id': 'PaCubic',
        'name': 'positive cubic central-binomial primitive divided by 2*pi**2',
        'coefficient_in_r6': '192*pi**2',
        'summation_indices': 2,
        'index_range': 'm,n>=0',
        'k': 'm+n',
        'a_n': '(1/2)_n/n!=binomial(2*n,n)/4**n',
        'h_n': 'log(2)+H_n-H_(2*n)',
        'delta_n': 'pi**2/3-4*H_(2*n)^(2)+2*H_n^(2)',
        'H_n_r': 'sum(j=1..n,1/j**r); H_0^(r)=0',
        't_mk': '8*h_m+H_k-H_m',
        'e_mk': '4*delta_m+H_k^(2)-H_m^(2)',
        'T_mn': (
            '15*t_mk*t_nk*(t_mk+t_nk)+15*(t_mk*e_nk+t_nk*e_mk)'
            '+72*pi*(t_mk*t_nk+H_k^(2))'
            '+(30*H_k^(2)+7*pi**2)*(t_mk+t_nk)'
            '+28*pi**3-60*(zeta(3)-H_k^(3))'),
        'summand': 'a_m**4*a_n**4/binomial(m+n,m)*T_mn',
        'definition': 'PaCubic=sum(m,n>=0,summand)',
        'identity': 'Pa=2*pi**2*PaCubic; PaCentral=2*pi*PaCubic',
        'positive': True,
        'pointwise_T_lower_bound': 'T_mn>28*pi**3-60*zeta(3)>681',
        'initial_T_00': (
            '15360*log(2)**3+4608*pi*log(2)**2+'
            '432*pi**2*log(2)+28*pi**3-60*zeta(3)'),
        'zero_index_included': True,
        'known_polynomial_shift': '0',
        'initial_transcendentals': ['pi', 'log(2)', 'zeta(3)'],
        'contains_Q': False,
        'contains_Catalan': False,
        'contains_parameter_derivatives': False,
        'max_harmonic_order': 3,
        'max_harmonic_polynomial_degree': 3,
        'direct_tail_for_Pa': (
            '0 < Pa-2*pi**2*sum(m+n<N,summand) < '
            '400*pi**2/(3*(N-1))*((7+log(N-1))**2+'
            '2*(7+log(N-1))+2), integer N>=2'),
        'arithmetic_note': (
            'The tail theorem concerns exact partial sums. Sample numerical '
            'evaluations are not new outward-rounded interval certificates.'),
        'tradeoff': (
            'Degree/order four becomes degree/order three, with no fourth '
            'harmonic accumulator. Two indices and slow literal convergence '
            'remain; the inherited geometric evaluator is still available.'),
        'finite_ordinary_special_value_evaluation_claimed': False,
    }]
    out['active_auxiliary_series'] = [
        'PaCubic' if a == 'PaCentral' else a
        for a in old['active_auxiliary_series']]
    out['latest_identity'] = 'Pa=2*pi**2*PaCubic'
    out['latest_analytic_reduction'] = 'Primitive beta-pairing contour identity and cubic harmonic kernel'
    out['numeric_accuracy_note'] = (
        'The new relation is proved analytically. Quadrature and finite beta '
        'moment checks are supplementary floating-point checks. Existing '
        'certificates remain inherited through exact identities; this pass '
        'does not construct a new full-C6 interval certificate.')
    out['counts']['this_continuation'] = {
        'auxiliary_quantities': 3,
        'single_index_harmonic_sums': 2,
        'double_index_harmonic_sums': 1,
        'primitive_harmonic_degree_before': 4,
        'primitive_harmonic_degree_after': 3,
        'primitive_max_harmonic_order_before': 4,
        'primitive_max_harmonic_order_after': 3,
        'new_finite_ordinary_evaluations': 0,
        'new_beta_pairing_relation': 1,
        'all_three_use_one_binomial_coefficient_sequence': True,
        'known_polynomial_monomials': 20,
        'legacy_flat_counts_retained_for_provenance': True,
    }
    out['primitive_cubic_reduction'] = {
        'p0': 'v(x)**2',
        'p1': 'sqrt(Q)*v(x)*h(1-x)',
        'p2': 'Q*h(1-x)**2',
        'Iij': 'integral_0^1 p_i(x)*p_j(1-x)/(pi**(i+j)*sqrt(x*(1-x))) dx',
        'pairing_identity': 'I22-4*I12+4*I02-4*I00=0',
        'Pa_in_pairings_before': 'pi**4*(15*I22+24*I11-4*I00)',
        'Pa_in_pairings_after': 'pi**4*(60*I12-60*I02+24*I11+56*I00)',
        'proof_method': (
            'Upper-half-plane contour. The explicitly specified quartic '
            'numerator is real on both exterior real intervals; the beta '
            'square-root weight is imaginary there. The contour integral '
            'has no poles and vanishing arcs. Its real part is the relation.'),
        'f': '2F1(1/4,1/4;1;z)',
        'g': 'sqrt(Q)/pi*2F1(1/4,1/4;1/2;1-z)-f',
        'star': 'evaluation at 1-z, not complex conjugation',
        'contour_numerator': (
            'g**2*gstar**2+g**2*fstar**2+f**2*gstar**2'
            '-4*f*g*fstar*gstar-3*f**2*fstar**2'
            '+4*i*(f*g*fstar**2-f**2*fstar*gstar)'),
        'contour_denominator': 'sqrt(z)*sqrt(1-z), separate principal square roots',
        'real_boundary_matrix': [[-3,0,1],[0,-4,0],[1,0,1]],
        'imaginary_boundary_matrix': [[0,-4,0],[4,0,0],[0,0,0]],
        'basis': '[f**2,f*g,g**2]',
        'large_arc_integrand_bound': 'O(abs(z)**(-2)*(1+log(abs(z)))**4)',
        'endpoint_arc_integrand_bound': 'O(abs(z)**(-1/2)*(1+abs(log(z)))**2), similarly at z=1',
        'positive_kernel_difference': 'p1(x)-pi*p0(x)=sum a_n**3*x**n*(-log(x)+6*h_n)>0',
        'known_polynomial_shift': '0',
        'quartic_summands_equal_pointwise': False,
        'fourth_degree_sector_eliminated_by_global_identity': True,
        'sum_dimension_reduced': False,
        'primitive_constant_eliminated': False,
        'legacy_definition_note': ('Older reduction objects are retained as provenance and alternative representations. The top-level formula, active_auxiliary_series and active series-term lists specify the current expression.'),
        'upstream_graph_RG_recertified': False,
    }
    out['cubic_reduction_provenance'] = {
        'input_filename': 'C6_primitive_central_expression.json',
        'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'derivation': 'DERIVATION.md',
        'exact_checks': 'verify.py',
        'numeric_checks': 'numerical.py',
        'tail_and_partial_sums': 'series.py',
        'changed_preexisting_top_level_fields': sorted(CHANGED_FIELDS),
        'source_correction_preserved_exactly_once': True,
    }
    return out

if __name__ == '__main__':
    destination = ROOT / 'results/cubic_expression.json'
    destination.write_text(json.dumps(build(), indent=2) + '\n')
    print(destination)
