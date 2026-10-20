"""Exact central-binomial normal form of the complete even-power sector.
This is a structural series reduction, not a finite ordinary-value evaluation.
"""
from pathlib import Path
import copy, json
import sympy as sp
ROOT=Path(__file__).resolve().parent
A,Q,G,pi,z3,z5,ell=sp.symbols('A Q G pi z3 z5 ell')
a,y,h,de=sp.symbols('a y h delta')
Poct,Ell,PB6,PZ6,PK6=sp.symbols('Poct Ell PB6 PZ6 PK6')
rt2=sp.sqrt(2)
Cminus=91*A**2+36*A*pi-208*Q+2459*pi**2
Cplus=7*A**2+4*A*pi-16*Q+271*pi**2
Cs=-sp.Rational(105,4)*A**2-9*A*pi+60*Q-sp.Rational(2469,4)*pi**2
Cd=-42*A**2-18*A*pi+96*Q-1227*pi**2
R4=384*Q-168*A**2-72*A*pi-4908*pi**2-3144*de
R6=pi*y*(480*Q-210*A**2-72*A*pi-4938*pi**2-7860*de)+50688*pi*h+179712*h**2+7488*de
R8=8*pi*((2466-834*rt2)*pi**2*y-1112*pi*(1-16*y*h)+139*rt2*(256*y*h**2-32*h+8*y*de))
even_summand=a**4*(R4+a**2*R6+a**4*R8)
pb_summand=24*pi**3*a**6*(88*pi*h+312*h**2+13*de)
g8=[y,1-16*y*h,256*y*h**2-32*h+8*y*de-8*pi**2*y]
z6_summand=a**8*(pi**6*(816+92*rt2)*g8[0]-368*pi**5*g8[1]+46*rt2*pi**4*g8[2])
k6_summand=a**8*(pi**6*(432+48*rt2)*g8[0]-192*pi**5*g8[1]+24*rt2*pi**4*g8[2])
n0_shift=1048*pi**5+655*pi**6

def build():
    inp=json.loads((ROOT/'inputs/expression.json').read_text())
    known=sp.sympify(inp['known_polynomial'],locals={str(v):v for v in [A,Q,G,pi,z3,z5,ell,Poct,Ell,PB6,PZ6,PK6]})
    primitive_only=sp.expand(known.subs({Poct:0,Ell:0,PB6:0,PZ6:0,PK6:0})+n0_shift)
    out=copy.deepcopy(inp)
    out['formula']='2187*C6 = known_polynomial + 835584*Lambda + 391680*H5real + 13056*sqrt(2)*(32*G+3*pi**2)*H3real + pi**3*Ecentral + 96*Pa + 24*pi**3*M7central'
    out['known_polynomial']=str(primitive_only)
    out['known_shift_in_r6']=str(sp.expand(primitive_only-known))
    out['scope']='Complete even-power sector expressed with one central-binomial coefficient sequence and harmonic degree at most two. Eight old ordinary unit-argument hypergeometric values are folded into this sector, not separately finitely evaluated. No arithmetic-independence reduction or new physical graph/RG certification is claimed.'
    out['legacy_Wcentral_definition']=next(t for t in inp['single_index_harmonic_series_terms'] if t['id']=='Wcentral')
    new={
        'id':'Ecentral','name':'complete even-power sector',
        'coefficient_in_r6':'pi**3','summation_indices':1,'n_starts_at':0,
        'a_n':'binomial(2*n,n)/4**n','y_n':'n+1/4',
        'h_n':'log(2)+H_n-H_(2*n)',
        'delta_n':'pi**2/3-4*H_(2*n)^(2)+2*H_n^(2)',
        'R4':str(R4),'R6':str(R6),'R8':str(R8),
        'sum':'sum(n=0..infinity, a_n**4*(R4_n+a_n**2*R6_n+a_n**4*R8_n))',
        'max_harmonic_polynomial_degree':2,'max_harmonic_order':2,
        'signed':True,'direct_term_bound':'O(n**-2)',
        'finite_ordinary_evaluation_claimed':False,
        'tradeoff':'No shifted gamma-ratio streams or separate ordinary unit-argument periods remain active in this sector; the simple positive wheel is replaced by a signed quadratic-harmonic sector sum. This is consolidation, not a reduction in transcendence degree.'
    }
    out['single_index_harmonic_series_terms']=[new]+[t for t in inp['single_index_harmonic_series_terms'] if t['id']!='Wcentral']
    out['active_auxiliary_series']=['Ecentral','Pa','M7central']
    out['counts']['auxiliary_series']=3
    out['counts']['finite_ordinary_evaluation_of_new_series']=False
    out['counts']['active_unit_argument_ordinary_period_blocks']=0
    out['counts']['old_ordinary_values_folded_into_even_sector']=8
    out['counts']['number_of_special_values_not_reduced']=True
    out['even_sector_reduction']={
        'Bsum':'2*pi**4*sum((4*n+1)*a_n**6,n>=0)',
        'Bdiff':'4*pi**3*sum(a_n**4,n>=0)',
        'Pb':'sum('+str(pb_summand)+',n>=0), a=a_n,y=y_n,h=h_n,delta=delta_n',
        'PZ6':'sum('+str(z6_summand)+',n>=0), a=a_n,y=y_n,h=h_n,delta=delta_n',
        'PK6':'sum('+str(k6_summand)+',n>=0), a=a_n,y=y_n,h=h_n,delta=delta_n',
        'sector_identity':'B_block+24*PB6+24*PZ6+PK6/3-393*pi**3*Wcentral = pi**3*Ecentral+1048*pi**5+655*pi**6',
        'B_block':'Cs*(Bminus+Bplus)+Cd*(Bminus-Bplus)',
        'Cs':str(Cs),'Cd':str(Cd),
        'n0_included':True,
        'removed_explicit_monomial':'pi**6',
        'new_standalone_pi5_coefficient':'-279249/128',
        'physical_source_correction_preserved':True
    }
    out['compact_known_polynomial']=str(primitive_only)
    out['compact_elementary_polynomial']=str(sp.expand(primitive_only.subs(Q,0)))
    out['latest_analytic_reduction']='Central-binomial normal form for all even-power periods; a structural reduction, not a new finite special-value evaluation.'
    out['legacy_latest_identity']=inp.get('latest_identity')
    out['latest_identity']=out['even_sector_reduction']['sector_identity']
    out['legacy_previous_representation_reference']=inp.get('retained_previous_representation')
    out['retained_previous_representation']='inputs/expression.json'
    out['provenance_latest']='Derived in DERIVATION.md from the retained period definitions by sixth/eighth-power finite Fourier interpolation and exact weighted substitution. Bsum/Bdiff normalizations and physical graph/RG identifications are inherited.'

    out['legacy_definition_note']='Previous period, wheel, and evaluator definitions are retained for provenance. Only formula, known_polynomial, active_auxiliary_series, and current single_index_harmonic_series_terms specify the active expression. Old evaluator targets are not silently changed.'
    out['numeric_accuracy_note']='The prior complete interval is inherited. New checks compare the exact transformed identities to its individual periods. Fresh asymptotic numerical summation is an implementation check, not a new interval certificate.'
    return out

if __name__=='__main__':
    out=build()
    (ROOT/'results/reduced_expression.json').write_text(json.dumps(out,indent=2)+'\n')
    print(out['formula']);print(out['known_polynomial'])
