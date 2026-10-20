"""Insert the standard bivariate-H primitive in the complete saved C6 expression."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'inputs'/'seventh_expression.json'


def construct() -> dict:
    raw=INPUT.read_bytes()
    old=json.loads(raw)
    new=deepcopy(old)
    new['formula']=old['formula'].replace('192*pi**2*PaCubic','standard_primitive_values')
    new['scope']=(
      'The last project-defined sum PaCubic is replaced by four fixed unit-slope '
      'bivariate Fox H values, equivalently bivariate Meijer G values, at (1,1). '
      'This expands the standard-function class beyond Kampe de Feriet but adds no '
      'third or fourth variable. It is not a reduction to ordinary one-variable '
      'constants, an arithmetic-independence result, or a new physical graph/RG proof. '
      'The known polynomial, polylogarithms, even sector, seventh sector and source repair '
      'are unchanged. The primitive contour identity is inherited; the new Meijer G '
      'basis identification and beta transform are proved in DERIVATION.md.')
    new['known_shift_in_r6']='0'
    new['reason_for_known_shift']='No index extraction or constant compensation; exact replacement of the full primitive.'
    new['legacy_PaCubic_definition']=deepcopy(old['double_index_harmonic_series_terms'])
    new['double_index_harmonic_series_terms']=[]
    new['active_auxiliary_series']=[]
    new['standard_primitive_values']='768*pi**3*(10*BH11 + 21*BH12 + 18*BH22 + 15*BH23)'
    new['bivariate_fox_H_terms']=[]
    for j,k,w in [(1,1,10),(1,2,21),(2,2,18),(2,3,15)]:
        new['bivariate_fox_H_terms'].append({
            'id':f'BH{j}{k}',
            'function':'Standard bivariate Fox H, all slope parameters equal to one',
            'equivalent_class':'bivariate Meijer G (not the ordinary univariate Meijer G)',
            'arguments':['1','1'],
            'orders':{'shared':{'p':0,'q':1,'m':0,'n':0},
                      's_local':{'p':4,'q':3,'m':j,'n':4-j},
                      't_local':{'p':4,'q':3,'m':k,'n':4-k}},
            'shared_upper':[],
            'shared_lower':[['0','1','1']],
            's_upper':[['1/2','1'] for _ in range(4)],
            's_lower':[['0','1'] for _ in range(3)],
            't_upper':[['1/2','1'] for _ in range(4)],
            't_lower':[['0','1'] for _ in range(3)],
            'coefficient_in_r6':f'{768*w}*pi**3',
            'mellin_barnes_contours':'s=1/4+i*u, t=1/4+i*v, u,v real, both upward',
            'standard_definition':'Andrade-Rathie-Farias (2018), Definition B, equations (4)-(8)',
            'is_project_defined_infinite_series':False,
            'absolutely_convergent_defining_integral_at_arguments':True,
            'regularization_or_parameter_limit_required':False,
            'positive_real_value':True})
    new['bivariate_fox_H_convention']={
        'shared_factor':'prod Gamma(1-e_j-E_j*s-F_j*t) [first n_shared upper] / (prod Gamma(e_j+E_j*s+F_j*t) [remaining upper] * prod Gamma(1-f_j-A_j*s-B_j*t) [all shared lower])',
        'local_factor':'prod Gamma(b_j+B_j*s) [first m lower] * prod Gamma(1-a_j-A_j*s) [first n upper] / (prod Gamma(1-b_j-B_j*s) [remaining lower] * prod Gamma(a_j+A_j*s) [remaining upper])',
        'integrand':'shared_factor*local_factor_s*local_factor_t*x**(-s)*y**(-t)/(2*pi*i)**2',
        'specialized_kernel':'Gamma(s)**j*Gamma(1/2-s)**(4-j)*Gamma(t)**k*Gamma(1/2-t)**(4-k)/(Gamma(1-s)**(3-j)*Gamma(1/2+s)**j*Gamma(1-t)**(3-k)*Gamma(1/2+t)**k*Gamma(1-s-t))',
        'published_definition_url':'https://doi.org/10.1007/s40314-017-0451-z',
        'author_posted_full_text':'https://www.researchgate.net/publication/316770540_Exact_Bayesian_computation_using_H-functions'}
    new['primitive_standard_identities']={
        'univariate_G':'g_j(x)=G_{3,3}^{j,3-j}(x | (1/2)^3; 0^3), j=1,2,3',
        'g1':'sqrt(pi)*p0',
        'g2':'(p1-pi*p0)/sqrt(pi)',
        'g3':'(p2-2*pi*p1)/(2*pi**(3/2))',
        'p0_p1_p2':'p0=v(x)**2; p1=sqrt(Q)*v(x)*h(1-x); p2=Q*h(1-x)**2',
        'gauss':'v(x)=2F1(1/4,1/4;1;x); h(x)=2F1(1/4,1/4;1/2;x)',
        'beta_pair_for_proof':'BHjk=int_0^1 g_j(x)*g_k(1-x)/sqrt(x*(1-x)) dx',
        'inherited_contour_identity':'I22-4*I12+4*I02-4*I00=0',
        'equivalent_bivariate_identity':'BH33+2*BH13-BH22=0',
        'Pa':'8*pi**3*(10*BH11+21*BH12+18*BH22+15*BH23)',
        'PaCubic':'4*pi*(10*BH11+21*BH12+18*BH22+15*BH23)',
        'coefficient_in_r6':'96*Pa=768*pi**3*(10*BH11+21*BH12+18*BH22+15*BH23)',
        'known_polynomial_shift':'0'}
    new['counts']={
        'project_specific_infinite_sums_before':1,
        'project_specific_infinite_sums_after':0,
        'ordinary_hypergeometric_values_total':len(old['ordinary_hypergeometric_terms']),
        'kampe_de_feriet_values_total':len(old['kampe_de_feriet_terms']),
        'bivariate_fox_H_values_added':4,
        'standard_polylogarithmic_values':len(old['polylogarithm_terms']),
        'expanded_known_monomials_before':21,
        'expanded_known_monomials_after':21,
        'maximum_number_of_function_variables':2,
        'ordinary_one_variable_evaluation_of_primitive_claimed':False,
        'arithmetic_independence_or_minimality_claimed':False,
        'new_physical_graph_RG_certification':False}
    new['proof_status']={
        'new_step':'Meijer G Frobenius identification, absolutely convergent beta-to-bivariate-H transform, exact weighted insertion.',
        'inherited_step':'Primitive symmetric/cubic contour identity, all other special-function conversions, graph/RG identification and source repair.',
        'numerics':'Quadrature and point checks, not a new interval certificate; unchanged sectors are not freshly evaluated.'}
    new['provenance_latest']={
        'input_filename':INPUT.name,
        'input_sha256':sha256(raw).hexdigest(),
        'sources':['NIST DLMF 16.17, 16.21, 15.8, 5.11, 5.12',
                   'Andrade, Rathie, Farias, Comput. Appl. Math. 37 (2018) 2277-2293, Definition B'],
        'preserved_source_correction':new['source_correction']==old['source_correction']}
    return new

if __name__=='__main__':
    out=ROOT/'results'/'updated_expression.json'
    out.write_text(json.dumps(construct(),indent=2)+'\n')
    print(out)
