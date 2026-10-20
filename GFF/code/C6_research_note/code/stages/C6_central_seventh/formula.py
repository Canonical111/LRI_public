"""Exact construction of the one-central-sequence seventh-power sector.

The periodization proof is in DERIVATION.md. This module does no numerical
fitting. Legacy definitions stay in the JSON as explicitly inherited provenance.
"""
from pathlib import Path
from copy import deepcopy
import json,re,hashlib
import sympy as s
ROOT=Path(__file__).resolve().parent

def symbols_for(text):
    names=set(re.findall(r'\b[A-Za-z][A-Za-z0-9]*\b',text))
    env={n:s.Symbol(n) for n in names if n not in ['sqrt','log']}
    env.update(sqrt=s.sqrt,log=s.log)
    return env

def build(write=True):
    old=json.loads((ROOT/'inputs/expression.json').read_text())
    env=symbols_for(old['known_polynomial'])
    poly=s.sympify(old['known_polynomial'],locals=env)
    removed={env['Z'+str(r)] for r in [1,2,3,5,7]}|{env['PZ5']}
    newpoly=s.expand(poly.subs({z:0 for z in removed}))
    new=deepcopy(old)
    new['formula']='2187*C6 = known_polynomial + 835584*Lambda + 391680*H5real + 13056*sqrt(2)*(32*G+3*pi**2)*H3real - 393*pi**3*Wcentral + 96*Pa + 24*pi**3*M7central'
    new['known_polynomial']=str(newpoly)
    compact=old['compact_known_polynomial']
    ce=symbols_for(compact)
    new['compact_known_polynomial']=str(s.sympify(compact,locals=ce).subs({ce['PZ5']:0,ce['CZ']:0}))
    # The elementary polynomial has NOT changed: n=0 stays in the new series.
    new['compact_elementary_polynomial']=old['compact_elementary_polynomial']
    new['scope']='Exact central-binomial rewrite of the entire seventh-power sector -36*A*P5-98*mu. Five shifted gamma-ratio streams and their ordinary Z values no longer occur actively. Their weighted contribution is now one central-binomial harmonic series, of degree at most three. Three auxiliary quantities remain. No finite summation or arithmetic-independence claim, and no new upstream graph/RG derivation.'
    legacy=next(x for x in old['single_index_harmonic_series_terms'] if x['id']=='L7')
    new['legacy_L7_definition']=deepcopy(legacy)
    newterm={
        'id':'M7central','name':'complete central seventh-power sector',
        'coefficient_in_r6':'24*pi**3','summation_indices':1,'n_starts_at':0,
        'a_n':'binomial(2*n,n)/4**n',
        'y_n':'n+1/4','h_n':'ell+H_n-H_(2*n)',
        'delta_n':'pi**2/3-4*H_(2*n)^(2)+2*H_n^(2)',
        'u_n':'1-14*y_n*h_n',
        'v_n':'196*y_n*h_n**2-28*h_n+7*y_n*(delta_n-pi**2)',
        'T_n':'80*pi**2*y_n-26*pi*u_n+11*v_n',
        'V_n':'28*pi**2*y_n-10*pi*u_n+3*v_n',
        'F_n':'(98*H_(2*n)+74*ell-6*pi)*T_n-98*pi*V_n-98*(11*u_n-13*pi*y_n)*(pi**2/3+4*H_(2*n)^(2))-8624*y_n*(z3-H_(2*n)^(3))',
        'sum':'sum_(n=0..infinity) (-1)**n*a_n**7*F_n',
        'constant_inputs':['pi','log(2)','zeta(3)'],
        'n_zero_term':'39886*ell**3-10906*ell**2*pi-22792*ell**2-2188*ell*pi**2+8156*ell*pi-1679*pi**3/6+2330*pi**2/3-2156*z3',
        'max_harmonic_polynomial_degree':3,'max_harmonic_order':3,
        'absolute_convergence':True,
        'summand_asymptotic':'(-1)**n*294*log(n)/(pi**(3/2)*n**(5/2))+O(n**(-5/2))',
        'Euler_approximant':'sum_(n=0..N-1) (-1)**n*(1-2**(-N)*sum_(k=0..n)binomial(N,k))*a_n**7*F_n',
        'Euler_tail_bound':'2**(100-N), N>=1; excludes arithmetic error, which certify.py encloses separately',
        'finite_ordinary_hypergeometric_evaluation_claimed':False,
        'tradeoff':'One central coefficient sequence rather than five eighth-shifted gamma-ratio sequences; harmonic degree increases from one to three. P5 and CZ are folded into the same sector, not independently summed to elementary constants.'
    }
    new['single_index_harmonic_series_terms']=[x for x in new['single_index_harmonic_series_terms'] if x['id']!='L7']+[newterm]
    new['active_auxiliary_series']=['Wcentral','Pa','M7central']
    new['counts']['auxiliary_series']=3
    new['counts']['harmonic_auxiliary_series']=2
    new['counts']['finite_ordinary_evaluation_of_new_series']=False
    new['counts']['seventh_power_coefficient_streams']=1
    new['counts']['separate_active_Z_values']=0
    new['counts']['expanded_known_monomials_before']=len(s.Add.make_args(poly))
    new['counts']['expanded_known_monomials_after']=len(s.Add.make_args(newpoly))
    new['latest_identity']='-36*A*PZ5-392*pi**(3/2)*CZ-784*pi**(3/2)*L7 = 24*pi**3*M7central'
    new['known_shift_in_r6']=str(s.expand(newpoly-poly))
    new['provenance_latest']='Central seventh-power periodization and complete weighted insertion, DERIVATION.md. Input U,V reductions and all physical graph/RG assumptions retained.'
    new['numeric_accuracy_note']='The new central seventh-power sum is freshly enclosed from pi, log(2), zeta(3), finite rational harmonic updates, and an explicit Euler-transform remainder. The complete updated expression is assembled using inherited intervals for its unchanged periods. This is not an upstream graph/RG verification.'
    new['latest_analytic_reduction']={
        'name':'one central seventh-power sector',
        'input_sha256':hashlib.sha256((ROOT/'inputs/expression.json').read_bytes()).hexdigest(),
        'input_is_UV_reduced':True,
        'previous_reduction':old['latest_analytic_reduction'],
        'preserved_source_correction':True,
        'active_removed_symbols':['PZ5','Z1','Z2','Z3','Z5','Z7','L7','CZ'],
        'not_finite_elimination_of_independent_periods':True,
        'n_zero_kept':True,
        'new_full_graph_calculation':False
    }
    new['legacy_definition_note']='Old Z, P5, L7, and their generating identities are retained for provenance only. The active formula and known_polynomial have no such symbols. The old compact_CZ_coefficients field is likewise provenance.'
    new['central_seventh_periodization']={
        'Phi':'(pi*Gamma(1-x)/(Gamma(1/2+x)*cos(pi*x)))**7 * sum_(m in Z) (m+t)/(Gamma(3/4-x+m+t)*Gamma(3/4-x-m-t))**7',
        'parameter_neighborhood':'abs(x)<=1/64',
        'Fourier_modes':[1,2,3],
        'Fourier_form':'b1(x)*sin(2*pi*t)+b2(x)*sin(4*pi*t)+b3(x)*sin(6*pi*t)',
        'D_operator':'20-13/(2*pi)*d_t+11/(4*pi**2)*d_t**2',
        'E_operator':'14-5/pi*d_t+3/(2*pi**2)*d_t**2',
        'evaluation_point':'x=0,t=1/4',
        'P5_identity':'PZ5=16*pi**5*D_operator(Phi_0)',
        'mu_identity':'mu=-48*pi**5/7*D_operator(d_x Phi)-6*ell*PZ5+48*pi**6*E_operator(Phi_0)',
        'derivatives_are_proof_only':True
    }
    if write:
        (ROOT/'results/reduced_expression.json').write_text(json.dumps(new,indent=2)+'\n')
    return old,new,env
if __name__=='__main__':
    old,new,_=build();print('Known monomials:',new['counts']['expanded_known_monomials_before'],'->',new['counts']['expanded_known_monomials_after']);print(new['known_polynomial'])
